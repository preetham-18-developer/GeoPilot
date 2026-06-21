import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

class ResilientQdrantClient:
    """Wrapper that intercepts client queries and falls back to in-memory database on failures."""
    def __init__(self, main: QdrantClient, fallback: QdrantClient):
        self._main = main
        self._fallback = fallback
        self._using_fallback = (main is fallback)

    def _execute(self, method_name: str, *args, **kwargs):
        if self._using_fallback:
            return getattr(self._fallback, method_name)(*args, **kwargs)
        try:
            return getattr(self._main, method_name)(*args, **kwargs)
        except Exception as e:
            print(f"Qdrant query failed on main client, falling back to memory. Error: {e}")
            self._using_fallback = True
            # Re-create collection on fallback if needed
            coll = kwargs.get("collection_name") or (args[0] if args else None)
            if coll:
                try:
                    self._fallback.create_collection(
                        collection_name=coll,
                        vectors_config=models.VectorParams(
                            size=384,
                            distance=models.Distance.COSINE
                        )
                    )
                except Exception:
                    pass
            return getattr(self._fallback, method_name)(*args, **kwargs)

    def __getattr__(self, name):
        return lambda *args, **kwargs: self._execute(name, *args, **kwargs)

# Initialize Qdrant client. It uses standard local persistence if PATH is set.
# Resilient Fallback: If path is locked (e.g. concurrent testing/dev runs) or fails, fallback to in-memory.
fallback_client = QdrantClient(location=":memory:")
if settings.QDRANT_PATH == ":memory:":
    main_client = fallback_client
else:
    try:
        main_client = QdrantClient(path=settings.QDRANT_PATH)
    except Exception as e:
        print(f"Qdrant file lock error on path {settings.QDRANT_PATH}, falling back to in-memory client. Error: {e}")
        main_client = fallback_client

qdrant_client = ResilientQdrantClient(main_client, fallback_client)

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

def delete_collection(collection_name: str):
    """
    Safely deletes a Qdrant collection if it exists.
    Does not throw exceptions if the collection does not exist.
    """
    try:
        # Check if collection exists first to avoid warnings/unnecessary exceptions
        collections = qdrant_client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if exists:
            qdrant_client.delete_collection(collection_name=collection_name)
            print(f"Successfully deleted Qdrant collection: {collection_name}")
        else:
            print(f"Qdrant collection {collection_name} does not exist. Deletion skipped.")
    except Exception as e:
        print(f"Warning: Failed to delete Qdrant collection {collection_name}: {e}")

def get_qdrant() -> QdrantClient:
    """Returns the initialized Qdrant client."""
    return qdrant_client
