# ============================================================
# Tests — Database Layer (Milestone 9)
#
# Tests for SQLite schema, pipeline_logger functions, and
# data integrity constraints. Uses a real in-memory SQLite DB
# so no mocking is needed and tests are fast.
#
# Run with: pytest tests/test_database.py -v
# ============================================================

import pytest
import sys
import sqlite3
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def in_memory_db(tmp_path, monkeypatch):
    """
    Set up a fresh in-memory SQLite database for each test.
    Monkeypatches the DB_PATH so tests never touch real data.
    """
    db_file = tmp_path / "test_pipeline.db"
    monkeypatch.setattr("src.config.DB_PATH", db_file)

    from src.database.db import init_db
    init_db()

    yield db_file


# ── Schema Tests ───────────────────────────────────────────────────────────────

class TestDatabaseSchema:
    """Verify that the schema is created correctly."""

    def test_all_tables_exist(self, in_memory_db):
        """All five tables must be created on init_db()."""
        conn = sqlite3.connect(str(in_memory_db))
        tables = {
            row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()

        expected = {"sessions", "queries", "pipeline_steps", "llm_calls",
                    "retrieved_documents", "ingested_documents"}
        assert expected.issubset(tables)

    def test_init_db_is_idempotent(self, in_memory_db):
        """Calling init_db() twice must not raise errors (IF NOT EXISTS guards)."""
        from src.database.db import init_db
        init_db()  # Second call — must not fail
        init_db()  # Third call — also fine

    def test_foreign_key_cascade_delete(self, in_memory_db):
        """
        Deleting a session must cascade-delete all related queries
        (testing ON DELETE CASCADE on the queries.session_id FK).
        """
        from src.database.db import get_connection

        with get_connection() as conn:
            conn.execute("INSERT INTO sessions (session_id) VALUES ('sess_cascade')")
            conn.execute("INSERT INTO queries (session_id, user_message) VALUES ('sess_cascade', 'test')")

        # Delete the session — queries should be gone too
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id='sess_cascade'")

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM queries WHERE session_id='sess_cascade'"
            ).fetchall()
        assert len(rows) == 0


# ── Pipeline Logger Tests ──────────────────────────────────────────────────────

class TestPipelineLogger:
    """
    Tests for pipeline_logger functions.
    Each test uses a fresh isolated DB via the in_memory_db fixture.
    """

    def test_upsert_session_creates_new_session(self, in_memory_db):
        """upsert_session must create a session row if it doesn't exist."""
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.upsert_session("session_001")

        with get_connection() as conn:
            row = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id='session_001'"
            ).fetchone()
        assert row is not None

    def test_upsert_session_increments_count_on_duplicate(self, in_memory_db):
        """
        Calling upsert_session twice for the same ID must increment
        message_count (ON CONFLICT DO UPDATE), not create a duplicate row.
        """
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.upsert_session("session_002")
        pipeline_logger.upsert_session("session_002")

        with get_connection() as conn:
            row = conn.execute(
                "SELECT message_count FROM sessions WHERE session_id='session_002'"
            ).fetchone()
        # First upsert: insert (count stays 0). Second: +1.
        assert row["message_count"] >= 1

    def test_create_query_returns_positive_id(self, in_memory_db):
        """create_query must return a positive integer query_id."""
        from src.database import pipeline_logger

        pipeline_logger.upsert_session("sess_q")
        query_id = pipeline_logger.create_query("sess_q", "What is diabetes?")

        assert isinstance(query_id, int)
        assert query_id > 0

    def test_create_query_returns_minus_one_on_missing_session(self, in_memory_db):
        """
        create_query on a non-existent session must return -1
        (FK violation handled gracefully) rather than raising.
        """
        from src.database import pipeline_logger

        # "ghost_session" was never inserted — FK violation
        query_id = pipeline_logger.create_query("ghost_session", "message")
        assert query_id == -1

    def test_log_step_inserts_row(self, in_memory_db):
        """log_step must insert a row into pipeline_steps."""
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.upsert_session("sess_step")
        qid = pipeline_logger.create_query("sess_step", "user msg")
        pipeline_logger.log_step(qid, "router", "done", "RAG required: YES", duration_ms=120)

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT step_name, status, detail FROM pipeline_steps WHERE query_id=?", (qid,)
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["step_name"] == "router"
        assert rows[0]["status"] == "done"

    def test_log_step_with_negative_query_id_is_noop(self, in_memory_db):
        """
        log_step with query_id=-1 (DB failure marker) must be a silent no-op,
        never raising an exception.
        """
        from src.database import pipeline_logger
        # Must not raise
        pipeline_logger.log_step(-1, "router", "done", "test")

    def test_update_query_fields(self, in_memory_db):
        """update_query must correctly write the specified fields."""
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.upsert_session("sess_upd")
        qid = pipeline_logger.create_query("sess_upd", "test question")
        pipeline_logger.update_query(
            qid,
            rewritten_query="rewritten test question",
            needs_rag=True,
            retry_count=1,
            response_type="rag",
            final_response="The answer is 42.",
            total_duration_ms=999,
        )

        # Query only non-timestamp columns to avoid Python 3.12 converter deprecation
        with get_connection() as conn:
            row = conn.execute(
                "SELECT query_id, session_id, user_message, rewritten_query, "
                "needs_rag, retry_count, response_type, final_response, total_duration_ms "
                "FROM queries WHERE query_id=?",
                (qid,)
            ).fetchone()

        assert row["rewritten_query"] == "rewritten test question"
        assert row["needs_rag"] == 1  # Stored as integer (True → 1)
        assert row["retry_count"] == 1
        assert row["response_type"] == "rag"
        assert row["final_response"] == "The answer is 42."
        assert row["total_duration_ms"] == 999

    def test_get_ingested_files_summary_returns_list(self, in_memory_db):
        """get_ingested_files_summary must return a list (empty if nothing ingested)."""
        from src.database import pipeline_logger
        result = pipeline_logger.get_ingested_files_summary()
        assert isinstance(result, list)

    def test_log_ingested_chunk_and_summary(self, in_memory_db):
        """
        After logging two chunks from the same file, get_ingested_files_summary
        must return one row for that file with chunk_count=2.
        """
        from src.database import pipeline_logger

        for i in range(2):
            pipeline_logger.log_ingested_chunk(
                chunk_id=f"chunk_{i}",
                source_file="diabetes.pdf",
                source_path="/data/diabetes.pdf",
                file_type="pdf",
                chunk_index=i,
                chunk_total=2,
                chunk_text=f"chunk text {i}",
                embedding_model="gemini-embedding-001",
                embedding_dims=768,
            )

        summary = pipeline_logger.get_ingested_files_summary()
        assert len(summary) == 1
        assert summary[0]["source_file"] == "diabetes.pdf"
        assert summary[0]["chunk_count"] == 2

    def test_delete_ingested_file_removes_chunks(self, in_memory_db):
        """delete_ingested_file must remove all chunks for that source file."""
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.log_ingested_chunk(
            chunk_id="del_chunk_1",
            source_file="to_delete.pdf",
            source_path="/tmp/to_delete.pdf",
            file_type="pdf",
            chunk_index=0,
            chunk_total=1,
            chunk_text="text to delete",
            embedding_model="gemini-embedding-001",
            embedding_dims=768,
        )

        pipeline_logger.delete_ingested_file("to_delete.pdf")

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ingested_documents WHERE source_file='to_delete.pdf'"
            ).fetchall()
        assert len(rows) == 0

    def test_log_llm_call_inserts_row(self, in_memory_db):
        """log_llm_call must insert a row into llm_calls."""
        from src.database import pipeline_logger
        from src.database.db import get_connection

        pipeline_logger.upsert_session("sess_llm")
        qid = pipeline_logger.create_query("sess_llm", "test")
        pipeline_logger.log_llm_call(
            query_id=qid,
            call_type="rewriter",
            provider="groq",
            model="llama-3.3-70b",
            system_prompt="You are...",
            user_input="What is aspirin?",
            response="Aspirin is...",
            duration_ms=342,
        )

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT query_id, call_type, provider FROM llm_calls WHERE query_id=?", (qid,)
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["call_type"] == "rewriter"
        assert rows[0]["provider"] == "groq"
