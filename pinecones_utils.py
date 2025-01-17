# pinecones_utils.py

import os
import time
import logging
from typing import List, Dict, Any
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)

DEFAULT_INDEX_NAME = "general-conference"
DEFAULT_NAMESPACE = "gc-2018-2024"
DIMENSION = 1024

def setup_pinecone_index(index_name: str = DEFAULT_INDEX_NAME) -> Any:
    if not pc.has_index(index_name):
        logging.info(f"Creating index '{index_name}' with dimension={DIMENSION}...")
        pc.create_index(
            name=index_name,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )

    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)

    logging.info(f"Pinecone index '{index_name}' is ready.")
    return pc.Index(index_name)

def embed_texts_with_pinecone_inference(texts: List[str], model="multilingual-e5-large") -> List[Dict[str, Any]]:
    logging.info(f"Embedding {len(texts)} texts using model '{model}'...")
    embeddings = pc.inference.embed(
        model=model,
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"}
    )
    return embeddings

def query_paragraphs(
    query: str,
    top_k: int = 15,
    index_name: str = DEFAULT_INDEX_NAME,
    namespace: str = DEFAULT_NAMESPACE,
    embedding_model: str = "multilingual-e5-large"
) -> List[Dict[str, Any]]:
    index = setup_pinecone_index(index_name)

    query_emb = embed_texts_with_pinecone_inference([query], model=embedding_model)[0]["values"]
    logging.info(f"Querying index='{index_name}', namespace='{namespace}' for top {top_k} matches...")
    
    response = index.query(
        vector=query_emb,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True
    )

    matches = response["matches"]
    logging.info(f"Retrieved {len(matches)} matches from Pinecone for query='{query}'")

    paragraphs = []
    for match in matches:
        paragraphs.append({
            "id": match["id"],
            "score": match["score"],
            "paragraph_text": match["metadata"].get("paragraph_text", ""),
            "metadata": match["metadata"]
        })
    return paragraphs