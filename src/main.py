# ============================================================
# FastAPI Application — Entry Point
#
# This file wires together the entire system into a web API.
# At Milestone 1, this file proves the project structure is correct
# by starting without import errors.
#
# WHAT THIS FILE DOES:
# 1. Creates the FastAPI app instance
# 2. Validates configuration at startup
# 3. Ensures required directories exist
# 4. Registers API route handlers (stubs at Milestone 1, real at Milestone 7)
# 5. Provides a health check endpoint to verify the server is running
#
# TO RUN (from the rag_system/ directory):
#   uvicorn src.main:app --reload
# OR (using this file directly):
#   python src/main.py
# ============================================================

import logging
import sys
from contextlib import asynccontextmanager
import json
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import config
from src.config import ensure_directories, validate_config
from src.database import pipeline_logger
from src.pipeline.orchestrator import process_query
from src.ingestion.service import ingest_directory

# ── Logging Setup ──────────────────────────────────────────────────────────────
# Configure logging before anything else so all startup messages are captured.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Lifespan Handler (startup + shutdown) ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager: runs startup code before the server
    accepts requests, and shutdown code when the server is stopping.

    asynccontextmanager: the `yield` separates startup (before) from
    shutdown (after). Think of it as: everything before yield = __init__,
    everything after yield = __del__.
    """
    # ── STARTUP ──────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("RAG System starting up...")
    logger.info("=" * 60)

    # Ensure all required directories exist before any component tries to use them
    ensure_directories()
    logger.info("Data directories ensured.")

    # Initialize SQLite database
    from src.database.db import init_db
    init_db()

    # Validate configuration — warn about missing API keys but don't crash
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            logger.warning("[WARN] Config warning: %s", error)
        logger.warning(
            "Server starting with configuration warnings. "
            "API calls will fail until API keys are set in .env"
        )
    else:
        logger.info("[OK] Configuration valid. LLM provider: %s", config.LLM_PROVIDER)

    logger.info("ChromaDB persist dir: %s", config.CHROMA_PERSIST_DIR)
    logger.info("Memory dir: %s", config.MEMORY_DIR)
    logger.info("Server ready at http://%s:%d", config.HOST, config.PORT)

    yield  # Server is running — handle requests

    # ── SHUTDOWN ─────────────────────────────────────────────────────────
    logger.info("RAG System shutting down. Goodbye!")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RAG Chatbot API",
    description=(
        "Advanced Retrieval-Augmented Generation system with multi-format document "
        "ingestion, hybrid retrieval (semantic + BM25), RRF re-ranking, relevance "
        "evaluation, and automatic retry loop."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow the React frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """
    Simple health check endpoint.
    Returns a 200 OK with system status.
    Used by deployment platforms and monitoring to verify the service is alive.
    """
    from src.retrieval.vector_store import get_collection_count

    doc_count = 0
    chroma_status = "ok"
    try:
        doc_count = get_collection_count()
    except Exception as exc:
        chroma_status = f"error: {exc}"

    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_provider": config.LLM_PROVIDER,
        "chroma_status": chroma_status,
        "documents_in_store": doc_count,
    }


# ── API Routes ────────────────────────────────────────────────────────────────
@app.post("/chat", tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint — accepts a user message and streams pipeline trace events
    + the final response as Server-Sent Events.
    """
    async def event_generator():
        try:
            async for event in process_query(request.session_id, request.message):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("Chat pipeline error: %s", e)
            error_event = {"step": "system", "status": "error", "detail": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/ingest", tags=["Ingestion"])
async def ingest_endpoint(background_tasks: BackgroundTasks):
    """
    Document ingestion endpoint — triggers directory ingestion in the background.
    """
    background_tasks.add_task(ingest_directory)
    return {"message": "Ingestion started in the background."}


@app.get("/documents", tags=["Documents"])
async def list_documents():
    """
    List all ingested documents in the knowledge base.
    """
    return pipeline_logger.get_ingested_files_summary()


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """
    Remove a document from the knowledge base.
    """
    from src.retrieval.vector_store import delete_by_source
    
    deleted_count = delete_by_source(doc_id)
    pipeline_logger.delete_ingested_file(doc_id)
    
    if deleted_count > 0:
        return {"message": f"Successfully deleted '{doc_id}' ({deleted_count} chunks removed)."}
    else:
        return {"message": f"Document '{doc_id}' not found."}



# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
    )
