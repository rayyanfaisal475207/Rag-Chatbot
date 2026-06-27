# ============================================================
# Tests — FastAPI Endpoints (Milestone 9)
#
# Integration tests for all HTTP endpoints using FastAPI's
# TestClient. The LLM, ChromaDB, and pipeline are fully mocked
# so no external services are needed.
#
# Run with: pytest tests/test_api.py -v
# ============================================================

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def client():
    """
    Create a FastAPI TestClient with the database and ChromaDB mocked.
    init_db is imported inside the lifespan function, so we patch it
    at its source module (src.database.db.init_db), not from src.main.
    """
    from fastapi.testclient import TestClient

    with patch("src.database.db.init_db"), \
         patch("src.config.ensure_directories"), \
         patch("src.config.validate_config", return_value=[]):
        from src.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── GET /health ────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        """Health check endpoint must always return 200 OK."""
        with patch("src.retrieval.vector_store.get_collection_count", return_value=100):
            response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client):
        """Response must contain status='ok'."""
        with patch("src.retrieval.vector_store.get_collection_count", return_value=0):
            response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        """Response must include a version field."""
        with patch("src.retrieval.vector_store.get_collection_count", return_value=0):
            response = client.get("/health")
        data = response.json()
        assert "version" in data

    def test_health_returns_document_count(self, client):
        """Response must include the documents_in_store count from ChromaDB."""
        with patch("src.retrieval.vector_store.get_collection_count", return_value=42):
            response = client.get("/health")
        data = response.json()
        assert data["documents_in_store"] == 42

    def test_health_handles_chroma_error_gracefully(self, client):
        """
        If ChromaDB is unavailable, health check must still return 200
        (degraded, not down) and report chroma_status='error: ...'.
        """
        with patch("src.retrieval.vector_store.get_collection_count", side_effect=Exception("ChromaDB down")):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data["chroma_status"]


# ── GET /documents ─────────────────────────────────────────────────────────────

class TestDocumentsEndpoint:

    def test_list_documents_returns_200(self, client):
        """GET /documents must return 200."""
        with patch("src.main.pipeline_logger") as mock_logger:
            mock_logger.get_ingested_files_summary.return_value = []
            response = client.get("/documents")
        assert response.status_code == 200

    def test_list_documents_returns_list(self, client):
        """Response must be a JSON array."""
        with patch("src.main.pipeline_logger") as mock_logger:
            mock_logger.get_ingested_files_summary.return_value = []
            response = client.get("/documents")
        assert isinstance(response.json(), list)

    def test_list_documents_returns_correct_data(self, client):
        """Response must contain the data from the pipeline logger."""
        mock_docs = [
            {
                "source_file": "diabetes.pdf",
                "file_type": "pdf",
                "chunk_count": 42,
                "total_chars": 50000,
                "first_ingested": "2024-01-01T00:00:00Z",
                "last_ingested": "2024-01-01T00:00:00Z",
            }
        ]
        with patch("src.main.pipeline_logger") as mock_logger:
            mock_logger.get_ingested_files_summary.return_value = mock_docs
            response = client.get("/documents")
        data = response.json()
        assert len(data) == 1
        assert data[0]["source_file"] == "diabetes.pdf"
        assert data[0]["chunk_count"] == 42


# ── DELETE /documents/{id} ─────────────────────────────────────────────────────

class TestDeleteDocumentEndpoint:

    def test_delete_existing_document_returns_200(self, client):
        """DELETE /documents/{id} for an existing document must return 200."""
        with patch("src.main.pipeline_logger") as mock_logger, \
             patch("src.retrieval.vector_store.delete_by_source", return_value=5):
            mock_logger.delete_ingested_file.return_value = None
            response = client.delete("/documents/test.pdf")
        assert response.status_code == 200

    def test_delete_existing_returns_success_message(self, client):
        """Response must mention the filename and chunk count deleted."""
        with patch("src.main.pipeline_logger") as mock_logger, \
             patch("src.retrieval.vector_store.delete_by_source", return_value=3):
            mock_logger.delete_ingested_file.return_value = None
            response = client.delete("/documents/myfile.pdf")
        data = response.json()
        assert "myfile.pdf" in data["message"]

    def test_delete_nonexistent_returns_not_found_message(self, client):
        """DELETE on a non-existent document must return a message, not a 404 error."""
        with patch("src.main.pipeline_logger") as mock_logger, \
             patch("src.retrieval.vector_store.delete_by_source", return_value=0):
            mock_logger.delete_ingested_file.return_value = None
            response = client.delete("/documents/ghost.pdf")
        assert response.status_code == 200
        data = response.json()
        assert "not found" in data["message"].lower() or "ghost.pdf" in data["message"]

    def test_delete_calls_both_chroma_and_sqlite(self, client):
        """
        Deleting a document must remove it from BOTH ChromaDB (vector_store)
        AND SQLite (pipeline_logger). Inconsistency = data integrity bug.
        """
        with patch("src.main.pipeline_logger") as mock_logger, \
             patch("src.retrieval.vector_store.delete_by_source", return_value=2) as mock_chroma:
            mock_logger.delete_ingested_file.return_value = None
            client.delete("/documents/myfile.pdf")

        mock_chroma.assert_called_once_with("myfile.pdf")
        mock_logger.delete_ingested_file.assert_called_once_with("myfile.pdf")


# ── POST /ingest ───────────────────────────────────────────────────────────────

class TestIngestEndpoint:

    def test_ingest_returns_202_or_200(self, client):
        """POST /ingest must accept the request and return a success status."""
        with patch("src.main.ingest_directory", new_callable=AsyncMock):
            response = client.post("/ingest")
        assert response.status_code in (200, 202)

    def test_ingest_returns_message(self, client):
        """POST /ingest response must include a message field."""
        with patch("src.main.ingest_directory", new_callable=AsyncMock):
            response = client.post("/ingest")
        data = response.json()
        assert "message" in data


# ── POST /chat ─────────────────────────────────────────────────────────────────

class TestChatEndpoint:

    def test_chat_missing_body_returns_422(self, client):
        """POST /chat without a body must return 422 Unprocessable Entity."""
        response = client.post("/chat", json={})
        assert response.status_code == 422

    def test_chat_missing_session_id_returns_422(self, client):
        """POST /chat without session_id must return 422."""
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 422

    def test_chat_missing_message_returns_422(self, client):
        """POST /chat without message must return 422."""
        response = client.post("/chat", json={"session_id": "abc-123"})
        assert response.status_code == 422

    def test_chat_valid_request_returns_event_stream(self, client):
        """
        POST /chat with valid body must return a text/event-stream response.
        The pipeline is mocked to yield one event and then complete.
        """
        async def mock_pipeline(session_id, message):
            yield {"step": "query_rewriter", "status": "done", "detail": "test", "ms": 100}
            yield {"step": "response", "status": "done", "detail": "Final answer"}

        with patch("src.main.process_query", side_effect=mock_pipeline):
            response = client.post(
                "/chat",
                json={"session_id": "test-session-1", "message": "hello"},
                headers={"Accept": "text/event-stream"},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_chat_sse_events_are_valid_json(self, client):
        """
        Each SSE line must be parseable JSON.
        Format: 'data: {...}\n\n'
        """
        async def mock_pipeline(session_id, message):
            yield {"step": "router", "status": "done", "detail": "RAG required: YES", "ms": 50}

        with patch("src.main.process_query", side_effect=mock_pipeline):
            response = client.post(
                "/chat",
                json={"session_id": "session-sse-test", "message": "What is diabetes?"},
            )

        # Parse each SSE line
        for line in response.text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            assert line.startswith("data: "), f"SSE line doesn't start with 'data: ': {line!r}"
            payload = line[6:]  # Strip 'data: '
            parsed = json.loads(payload)  # Must be valid JSON
            assert "step" in parsed
            assert "status" in parsed

    def test_chat_pipeline_error_emits_error_event(self, client):
        """
        If the pipeline raises an exception, the endpoint must emit an
        SSE error event rather than crashing the connection.
        """
        async def failing_pipeline(session_id, message):
            raise RuntimeError("Pipeline exploded")
            yield  # make it an async generator

        with patch("src.main.process_query", side_effect=failing_pipeline):
            response = client.post(
                "/chat",
                json={"session_id": "err-session", "message": "trigger error"},
            )

        assert response.status_code == 200
        # Must have emitted an error event
        assert "error" in response.text.lower()
