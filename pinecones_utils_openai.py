import os
import time
import logging
from typing import List

from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv() 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment setup
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "default_pinecone_key")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "default_openai_key")
print(f"PINECONE_API_KEY: {PINECONE_API_KEY}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")

if not PINECONE_API_KEY or not OPENAI_API_KEY:
    raise ValueError("Missing required API keys. Please set PINECONE_API_KEY and OPENAI_API_KEY environment variables.")

# Create the clients
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Constants
INDEX_NAME = "general-conf-embed3"  # Index for 3072-dim embeddings
NAMESPACE = "gc-2018-2024"
DIMENSION = 3072
BATCH_SIZE = 100

# Global Pinecone index to avoid reinitialization
pinecone_index = None

def validate_embedding_dimension(embedding: List[float]) -> None:
    """Validates that an embedding has the correct dimension."""
    if len(embedding) != DIMENSION:
        raise ValueError(f"Expected dimension {DIMENSION}, got {len(embedding)}")

def setup_openai_pinecone_index():
    """Creates or checks the Pinecone index and initializes it globally."""
    global pinecone_index
    if pinecone_index:
        return pinecone_index

    logger.info(f"Checking for index: {INDEX_NAME}")
    if not pinecone_client.has_index(INDEX_NAME):
        logger.info(f"Creating new index: {INDEX_NAME}")
        pinecone_client.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        logger.info(f"Created Pinecone index: {INDEX_NAME}")

    logger.info("Waiting for index to be ready...")
    while not pinecone_client.describe_index(INDEX_NAME).status['ready']:
        time.sleep(1)

    pinecone_index = pinecone_client.Index(INDEX_NAME)
    logger.info(f"Pinecone index '{INDEX_NAME}' is ready.")
    return pinecone_index

def embed_texts_with_openai(texts: List[str], model: str = "text-embedding-3-large", batch_size: int = BATCH_SIZE) -> List[List[float]]:
    """
    Creates embeddings using OpenAI's API and returns a list of embeddings.
    """
    all_embeddings = []
    total_batches = (len(texts) - 1) // batch_size + 1
    
    logger.info(f"Starting embedding process for {len(texts)} texts in {total_batches} batches")
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"Processing batch {batch_num}/{total_batches}, size {len(batch)}")
        
        try:
            response = openai_client.embeddings.create(
                model=model,
                input=batch
            )
            # Extract embeddings from response
            batch_embeddings = [item.embedding for item in response.data]
            
            # Validate dimensions
            for emb in batch_embeddings:
                validate_embedding_dimension(emb)
                
            all_embeddings.extend(batch_embeddings)
            logger.info(f"Successfully embedded batch {batch_num}")
            
            # Rate limiting
            if i + batch_size < len(texts):
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in batch {batch_num}: {e}")
            raise

    logger.info(f"Completed embedding all {len(texts)} texts")
    return all_embeddings

def query_openai_paragraphs(query: str, top_k=10) -> List[dict]:
    """
    Query the index using OpenAI embeddings.
    Returns a list of matching paragraph metadata.
    """
    index = setup_openai_pinecone_index()  # Use global index
    logger.info("Pinecone index ready for querying.")

    # Embed the query using OpenAI
    logger.info(f"Embedding query: '{query}'")
    query_embedding = embed_texts_with_openai([query])[0]  # Get first (and only) embedding
    logger.info("Query embedding completed.")

    # Query Pinecone
    logger.info(f"Querying Pinecone for top {top_k} matches...")
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=NAMESPACE,
        include_metadata=True
    )

    matches = response.matches
    logger.info(f"Retrieved {len(matches)} matches from Pinecone.")

    # Format the results
    return [
        {
            "id": match.id,
            "score": match.score,
            "paragraph_text": match.metadata.get("paragraph_text", ""),
            "metadata": match.metadata
        }
        for match in matches
    ]

def upsert_openai_embeddings(paragraphs: List[dict]) -> None:
    """
    Create OpenAI embeddings for paragraphs and upsert to Pinecone.
    Each paragraph should be a dict with at least 'paragraph_text' and other metadata.
    """
    index = setup_openai_pinecone_index()
    
    # Extract texts for embedding
    texts = [p["paragraph_text"] for p in paragraphs]
    logger.info(f"Creating OpenAI embeddings for {len(texts)} paragraphs")
    
    # Get embeddings
    embeddings = embed_texts_with_openai(texts)
    
    # Prepare records for upserting
    records = []
    for i, (p, embedding) in enumerate(zip(paragraphs, embeddings)):
        paragraph_id = p.get("id", f"p{i}")
        metadata = {
            "speaker": p.get("speaker", ""),
            "role": p.get("role", ""),
            "title": p.get("title", ""),
            "youtube_link": p.get("youtube_link", ""),
            "paragraph_deep_link": p.get("paragraph_deep_link", ""),
            "paragraph_text": p.get("paragraph_text", ""),
            "paragraph_index": p.get("paragraph_index", 0),
            "start_time": p.get("start_time", 0),
            "end_time": p.get("end_time", 0)
        }
        records.append((paragraph_id, embedding, metadata))

    # Upsert to Pinecone
    logger.info(f"Upserting {len(records)} records to Pinecone...")
    try:
        index.upsert(vectors=records, namespace=NAMESPACE)
        logger.info("Upsert completed successfully")
    except Exception as e:
        logger.error(f"Error during upsert: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    sample_query = "How can I find peace in life?"
    results = query_openai_paragraphs(sample_query, top_k=3)
    
    print("\nQuery Results:")
    for r in results:
        print(f"\nID: {r['id']}")
        print(f"Score: {r['score']}")
        print(f"Text: {r['paragraph_text'][:200]}...")