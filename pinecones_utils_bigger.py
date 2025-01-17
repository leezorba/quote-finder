# pinecones_utils_bigger.py

import os
import time
import logging
import json

from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec

# Import the embedding function from your working module
from pinecones_utils import embed_texts_with_pinecone_inference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "general-conference"
NAMESPACE = "gc-bigger-chunks"
DIMENSION = 1024

def setup_pinecone_index():
    if not pc.has_index(INDEX_NAME):
        logging.info(f"Index '{INDEX_NAME}' not found. Creating with dimension={DIMENSION}.")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        logging.info(f"Created Pinecone index: {INDEX_NAME}")

    # Wait until it's ready
    while not pc.describe_index(INDEX_NAME).status['ready']:
        time.sleep(1)

    logging.info(f"Index '{INDEX_NAME}' is ready.")
    return pc.Index(INDEX_NAME)

def upsert_bigger_chunks_from_folder(bigger_folder="talks_json_bigger"):
    """
    Read larger text chunks from JSON files, embed them, and upsert to Pinecone.
    Each JSON file contains an array of objects with paragraph text and metadata.
    """
    index = setup_pinecone_index()
    logging.info(f"Upserting bigger-chunks from folder: {bigger_folder}")

    # Process each JSON file in the folder
    for file_name in os.listdir(bigger_folder):
        if not file_name.endswith(".json"):
            continue

        file_path = os.path.join(bigger_folder, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            big_chunks = json.load(f)

        if not big_chunks:
            logging.warning(f"No data found in {file_name}, skipping.")
            continue

        # Extract texts for embedding
        texts = [bc["paragraph_text"] for bc in big_chunks]
        logging.info(f"Embedding {len(texts)} chunks from file: {file_name}")

        # Get embeddings using the imported function
        embeddings = embed_texts_with_pinecone_inference(texts)
        if not embeddings:
            logging.error(f"Embedding failed for {file_name}, skipping.")
            continue

        # Build records for upserting
        records = []
        for i, bc in enumerate(big_chunks):
            paragraph_id = f"{file_name}-chunk-{i}"
            meta = {
                "speaker": bc.get("speaker", ""),
                "role": bc.get("role", ""),
                "title": bc.get("title", ""),
                "youtube_link": bc.get("youtube_link", ""),
                "paragraph_deep_link": bc.get("paragraph_deep_link", ""),
                "paragraph_text": bc.get("paragraph_text", ""),
                "start_time": bc.get("start_time", 0),
                "end_time": bc.get("end_time", 0)
            }
            
            # Extract just the values array from the embedding
            vector = embeddings[i]["values"]
            records.append((paragraph_id, vector, meta))

        # Upsert all records for this file
        try:
            index.upsert(vectors=records, namespace=NAMESPACE)
            logging.info(f"Upserted {len(records)} bigger-chunk vectors from '{file_name}' into namespace='{NAMESPACE}'")
        except Exception as e:
            logging.error(f"Failed to upsert records from {file_name}: {str(e)}")

def query_bigger_chunks(query, top_k=15):
    """
    Query the bigger chunks namespace using the provided query string.
    Returns top_k matching chunks with their metadata.
    """
    index = setup_pinecone_index()
    logging.info("Pinecone index ready for querying bigger chunks.")

    # Embed the query
    logging.info(f"Embedding query: '{query}'")
    query_emb = embed_texts_with_pinecone_inference([query])[0]["values"]
    logging.info("Query embedding completed.")

    # Query Pinecone
    logging.info(f"Querying Pinecone for top {top_k} matches in bigger chunks...")
    response = index.query(
        vector=query_emb,
        top_k=top_k,
        namespace=NAMESPACE,
        include_metadata=True
    )

    matches = response.matches
    logging.info(f"Retrieved {len(matches)} matches from bigger chunks.")

    # Format the results
    results = []
    for match in matches:
        results.append({
            "id": match.id,
            "score": match.score,
            "paragraph_text": match.metadata.get("paragraph_text", ""),
            "metadata": match.metadata
        })

    return results

if __name__ == "__main__":
    # Example usage:
    upsert_bigger_chunks_from_folder("talks_json_bigger")
    logging.info("Finished upserting all bigger-chunks to Pinecone.")

    # Optional: Test a query
    # sample_query = "How can I find peace in life?"
    # results = query_bigger_chunks(sample_query, top_k=3)
    # for r in results:
    #     print(f"ID: {r['id']}, Score: {r['score']}, Text: {r['paragraph_text']}")