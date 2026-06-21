import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

# Initialize Qdrant client. It uses standard local persistence if PATH is set.
# Resilient Fallback: If path is locked (e.g. concurrent testing/dev runs) or fails, fallback to in-memory.
if settings.QDRANT_PATH == ":memory:":
    qdrant_client = QdrantClient(location=":memory:")
else:
    try:
        qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
    except Exception as e:
        print(f"Qdrant file lock error on path {settings.QDRANT_PATH}, falling back to in-memory client. Error: {e}")
        qdrant_client = QdrantClient(location=":memory:")

def init_collection(collection_name: str, vector_size: int = 384):
    """
    Initializes a Qdrant collection if it does not exist.
    By default, vector size is 384 (standard size for fastembed / MiniLM models).
    """
    # Check if collection exists
    collections = qdrant_client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)
    
    if not exists:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        print(f"Created Qdrant collection: {collection_name}")
    else:
        print(f"Qdrant collection already exists: {collection_name}")

def get_qdrant() -> QdrantClient:
    """Returns the initialized Qdrant client."""
    return qdrant_client
