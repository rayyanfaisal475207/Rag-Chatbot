# ============================================================
# ChromaDB Vector Store Wrapper
#
# WHAT IS ChromaDB?
# ChromaDB is a vector database — a specialised database that stores
# text alongside its embedding vectors and can answer the question:
# "which stored texts are semantically most similar to this query?"
#
# ChromaDB stores data on disk (in CHROMA_PERSIST_DIR) so documents
# survive server restarts. It uses an HNSW index (a fast approximate
# nearest-neighbour algorithm) to search millions of vectors quickly.
#
# WHY UPSERT NOT ADD?
# If we ingest the same document twice, `add` creates duplicates.
# `upsert` = "update if exists, insert if new". Since our doc_ids are
# deterministic (same file → same ID), upsert is idempotent: safe to
# run as many times as you want without polluting the database.
#
# COLLECTION:
# ChromaDB organises data into "collections" (like tables in SQL).
# We use a single collection for all documents. Filtering by source
# file is done via metadata filtering, not separate collections.
# ============================================================

import logging
from typing import Optional

from src import config

logger = logging.getLogger(__name__)

# Module-level singleton — we only create the client once per process
_chroma_client = None
_collection = None


def _get_collection():
    """
    Lazily initialise the ChromaDB client and collection.

    We use lazy initialisation (create on first use, not at import time)
    so that importing this module doesn't immediately require ChromaDB to
    be installed and the persist directory to exist. This makes testing easier.
    """
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    try:
        import chromadb
    except ImportError:
        raise ImportError(
            "chromadb is required for vector storage. "
            "Install with: pip install chromadb"
        )

    # Ensure persist directory exists
    config.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    # PersistentClient saves data to disk automatically
    _chroma_client = chromadb.PersistentClient(
        path=str(config.CHROMA_PERSIST_DIR)
    )

    # get_or_create_collection: creates the collection if it doesn't exist,
    # returns the existing one if it does. Safe to call on every startup.
    _collection = _chroma_client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        # Cosine similarity: measures the angle between vectors.
        # Better than Euclidean distance for text embeddings because it's
        # scale-invariant — the length of the vector doesn't matter, only direction.
        metadata={"hnsw:space": "cosine"},
    )

    count = _collection.count()
    logger.info(
        "ChromaDB collection '%s' ready. Contains %d documents.",
        config.CHROMA_COLLECTION_NAME, count
    )
    return _collection


def upsert_documents(
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    """
    Store or update document chunks in ChromaDB.

    All four lists must be the same length and aligned by index.

    Args:
        ids:        Unique document IDs (doc_id from each Document object).
        texts:      The text content of each chunk.
        embeddings: Pre-computed embedding vectors (one per chunk).
        metadatas:  Metadata dicts (one per chunk).
    """
    if not ids:
        logger.warning("upsert_documents called with empty list.")
        return

    collection = _get_collection()

    # ChromaDB metadata values must be str, int, float, or bool — not None
    # This normalises any None values to empty string
    safe_metadatas = [
        {k: (v if v is not None else "") for k, v in m.items()}
        for m in metadatas
    ]

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=safe_metadatas,
    )
    logger.info("Upserted %d chunks into ChromaDB", len(ids))


def query_similar(
    query_embedding: list[float],
    top_k: int = config.TOP_K_RETRIEVAL,
    where: Optional[dict] = None,
) -> list[dict]:
    """
    Find the top-k most similar document chunks to a query embedding.

    Args:
        query_embedding: The embedded form of the user's (rewritten) query.
        top_k:           How many results to return.
        where:           Optional ChromaDB metadata filter, e.g. {"source": "myfile.pdf"}

    Returns:
        List of result dicts, each containing:
            - "id": the chunk's doc_id
            - "text": the chunk's text content
            - "metadata": the chunk's metadata dict
            - "distance": cosine distance (0 = identical, 1 = completely different)
              Note: ChromaDB returns distance, not similarity. Lower = more relevant.
    """
    collection = _get_collection()
    current_count = collection.count()

    if current_count == 0:
        logger.warning("ChromaDB collection is empty — no documents have been ingested.")
        return []

    # Don't request more results than exist in the collection
    actual_k = min(top_k, current_count)

    query_kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": actual_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    # ChromaDB wraps results in an extra list (batch dimension) — unwrap it
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "id": doc_id,
            "text": text,
            "metadata": meta,
            "distance": dist,
        }
        for doc_id, text, meta, dist in zip(ids, documents, metadatas, distances)
    ]


def get_all_documents_metadata() -> list[dict]:
    """
    Retrieve metadata for all stored document chunks.

    Used by the /documents API endpoint to list ingested files.

    Returns:
        List of metadata dicts (one per chunk stored in ChromaDB).
    """
    collection = _get_collection()
    count = collection.count()

    if count == 0:
        return []

    # Get all documents (ids + metadata only — no need to fetch embeddings)
    results = collection.get(include=["metadatas"])
    return [
        {"id": doc_id, **meta}
        for doc_id, meta in zip(results["ids"], results["metadatas"])
    ]


def delete_by_source(source_filename: str) -> int:
    """
    Delete all chunks that came from a specific source file.

    Uses ChromaDB's metadata filtering to find and delete all chunks
    where metadata["source"] == source_filename.

    Args:
        source_filename: The filename (not full path) to delete, e.g. "myfile.pdf".

    Returns:
        Number of chunks deleted.
    """
    collection = _get_collection()

    # First: find all IDs matching this source
    results = collection.get(
        where={"source": source_filename},
        include=[],  # Only need IDs
    )
    ids_to_delete = results["ids"]

    if not ids_to_delete:
        logger.info("No chunks found for source '%s'", source_filename)
        return 0

    collection.delete(ids=ids_to_delete)
    logger.info(
        "Deleted %d chunks from source '%s'", len(ids_to_delete), source_filename
    )
    return len(ids_to_delete)


def get_collection_count() -> int:
    """Return the total number of chunks stored in ChromaDB."""
    return _get_collection().count()
