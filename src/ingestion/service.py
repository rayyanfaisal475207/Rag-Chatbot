# ============================================================
# Ingestion Service — Loads, Chunks, Embeds, and Stores
#
# This service is the entry point for Milestone 2.
# It takes files from data/documents/, processes them,
# pushes them to ChromaDB, and logs them to the SQLite DB.
# ============================================================

import logging
from pathlib import Path

from src import config
from src.ingestion.loader_router import route_and_load
from src.ingestion.chunker import chunk_documents
from src.retrieval.embedder import embed_texts
from src.retrieval.vector_store import upsert_documents
from src.database.pipeline_logger import log_ingested_chunk

logger = logging.getLogger(__name__)


async def ingest_directory(dir_path: Path = None) -> dict:
    """
    Ingest all supported files in a directory.
    If no dir_path provided, uses config.DOCUMENTS_DIR.

    Returns:
        dict: Summary of ingestion (files processed, chunks added).
    """
    if dir_path is None:
        dir_path = config.DOCUMENTS_DIR

    if not dir_path.exists():
        logger.error("Directory not found: %s", dir_path)
        return {"error": "Directory not found"}

    all_files = [f for f in dir_path.iterdir() if f.is_file() and f.name != "README.txt"]
    if not all_files:
        logger.info("No files to ingest in %s", dir_path)
        return {"status": "success", "files_processed": 0, "chunks_added": 0}

    logger.info("Starting ingestion of %d files from %s", len(all_files), dir_path)
    total_chunks = 0

    for file_path in all_files:
        chunks = await ingest_file(file_path)
        total_chunks += chunks

    return {
        "status": "success",
        "files_processed": len(all_files),
        "chunks_added": total_chunks
    }


async def ingest_file(file_path: Path) -> int:
    """
    Ingest a single file.
    
    1. Load text (via loader_router)
    2. Chunk text
    3. Embed chunks (via Gemini)
    4. Save to ChromaDB
    5. Log to SQLite
    
    Returns:
        Number of chunks added.
    """
    logger.info("Ingesting file: %s", file_path.name)
    try:
        # 1. Load
        documents = route_and_load(file_path)
        if not documents:
            logger.warning("No content extracted from %s", file_path.name)
            return 0

        # 2. Chunk
        chunks = chunk_documents(
            documents, 
            chunk_size=config.CHUNK_SIZE, 
            chunk_overlap=config.CHUNK_OVERLAP
        )
        if not chunks:
            logger.warning("No chunks generated for %s", file_path.name)
            return 0

        # 3. Embed
        # Extract text for embedding
        texts_to_embed = [c.text for c in chunks]
        embeddings = await embed_texts(texts_to_embed, task_type="RETRIEVAL_DOCUMENT")

        if len(embeddings) != len(chunks):
            logger.error("Mismatch: %d chunks vs %d embeddings", len(chunks), len(embeddings))
            return 0

        # Attach embeddings to metadata for vector_store to pick up
        # Note: In our current vector_store.py we might just pass text, let's see.
        # Actually ChromaDB can generate embeddings itself if we pass an embedding function,
        # but we do it manually to use Gemini. We'll pass embeddings to upsert_documents.

        # 4. Save to ChromaDB
        ids = [c.doc_id for c in chunks]
        metadatas = [c.metadata for c in chunks]
        upsert_documents(
            ids=ids,
            texts=texts_to_embed,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # 5. Log to SQLite
        ext = file_path.suffix.lower().lstrip(".")
        for c, emb in zip(chunks, embeddings):
            log_ingested_chunk(
                chunk_id=c.doc_id,
                source_file=file_path.name,
                source_path=str(file_path),
                file_type=ext,
                chunk_index=c.metadata.get("chunk_index", 0),
                chunk_total=c.metadata.get("chunk_total", 1),
                chunk_text=c.text,
                embedding_model=config.GEMINI_EMBEDDING_MODEL,
                embedding_dims=len(emb)
            )

        logger.info("Successfully ingested %d chunks from %s", len(chunks), file_path.name)
        return len(chunks)

    except Exception as exc:
        logger.error("Failed to ingest %s: %s", file_path.name, exc)
        return 0
