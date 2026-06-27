# ============================================================
# Tests — Structure Validation (Milestone 1)
#
# These tests verify that the project structure is correct and
# all modules can be imported without errors. They do NOT make
# any API calls (no keys required to run these tests).
#
# Run with: pytest tests/test_structure.py -v
# ============================================================

import pytest
import sys
from pathlib import Path

# Add the project root (rag_system/) to the Python path
# This allows `from src.xxx import yyy` imports to work in tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestProjectStructure:
    """Verify that all required files exist."""

    def test_src_directory_exists(self):
        assert (PROJECT_ROOT / "src").is_dir()

    def test_main_py_exists(self):
        assert (PROJECT_ROOT / "src" / "main.py").is_file()

    def test_config_py_exists(self):
        assert (PROJECT_ROOT / "src" / "config.py").is_file()

    def test_pipeline_directory_exists(self):
        pipeline = PROJECT_ROOT / "src" / "pipeline"
        assert pipeline.is_dir()
        for f in ["orchestrator.py", "query_rewriter.py", "router.py", "evaluator.py"]:
            assert (pipeline / f).is_file(), f"Missing {f}"

    def test_retrieval_directory_exists(self):
        retrieval = PROJECT_ROOT / "src" / "retrieval"
        assert retrieval.is_dir()
        for f in ["vector_store.py", "embedder.py", "bm25_retriever.py", "reranker.py"]:
            assert (retrieval / f).is_file(), f"Missing {f}"

    def test_memory_directory_exists(self):
        assert (PROJECT_ROOT / "src" / "memory" / "conversation.py").is_file()

    def test_llm_directory_exists(self):
        assert (PROJECT_ROOT / "src" / "llm" / "client.py").is_file()

    def test_ingestion_directory_exists(self):
        ingestion = PROJECT_ROOT / "src" / "ingestion"
        assert ingestion.is_dir()
        for f in ["document.py", "loader_router.py", "chunker.py"]:
            assert (ingestion / f).is_file(), f"Missing {f}"

    def test_loaders_directory_exists(self):
        loaders = PROJECT_ROOT / "src" / "ingestion" / "loaders"
        assert loaders.is_dir()
        for f in ["text_loader.py", "pdf_loader.py", "excel_loader.py",
                  "html_loader.py", "docx_loader.py", "image_loader.py"]:
            assert (loaders / f).is_file(), f"Missing {f}"

    def test_prompts_directory_exists(self):
        prompts = PROJECT_ROOT / "prompts"
        assert prompts.is_dir()
        for f in ["query_rewriter.txt", "router.txt", "evaluator.txt", "final_response.txt"]:
            assert (prompts / f).is_file(), f"Missing {f}"

    def test_requirements_exists(self):
        assert (PROJECT_ROOT / "requirements.txt").is_file()

    def test_env_example_exists(self):
        assert (PROJECT_ROOT / ".env.example").is_file()


class TestImports:
    """Verify all modules can be imported without errors."""

    def test_import_config(self):
        from src import config
        assert hasattr(config, "LLM_PROVIDER")
        assert hasattr(config, "CHROMA_PERSIST_DIR")
        assert hasattr(config, "MAX_RETRIES")

    def test_import_document(self):
        from src.ingestion.document import Document
        # Basic instantiation test
        doc = Document(text="Hello world", metadata={"source": "test.txt"})
        assert doc.text == "Hello world"
        assert doc.doc_id != ""

    def test_document_id_is_deterministic(self):
        from src.ingestion.document import Document
        # Same inputs must produce the same ID
        doc1 = Document(text="Same text", metadata={"source": "same.txt"})
        doc2 = Document(text="Same text", metadata={"source": "same.txt"})
        assert doc1.doc_id == doc2.doc_id

    def test_document_id_differs_by_source(self):
        from src.ingestion.document import Document
        doc1 = Document(text="Same text", metadata={"source": "file_a.txt"})
        doc2 = Document(text="Same text", metadata={"source": "file_b.txt"})
        assert doc1.doc_id != doc2.doc_id

    def test_import_chunker(self):
        from src.ingestion.chunker import split_text_into_chunks, chunk_documents
        assert callable(split_text_into_chunks)
        assert callable(chunk_documents)

    def test_import_reranker(self):
        from src.retrieval.reranker import reciprocal_rank_fusion, rerank_results
        assert callable(reciprocal_rank_fusion)

    def test_import_conversation(self):
        from src.memory.conversation import load_history, save_history
        assert callable(load_history)
        assert callable(save_history)

    def test_import_llm_client(self):
        from src.llm.client import call_llm, stream_llm
        assert callable(call_llm)
        assert callable(stream_llm)


class TestChunker:
    """Test the text chunker with no external dependencies."""

    def test_empty_text_returns_empty(self):
        from src.ingestion.chunker import split_text_into_chunks
        assert split_text_into_chunks("") == []
        assert split_text_into_chunks("   ") == []

    def test_short_text_returns_one_chunk(self):
        from src.ingestion.chunker import split_text_into_chunks
        text = "This is a short text."
        chunks = split_text_into_chunks(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        from src.ingestion.chunker import split_text_into_chunks
        # Generate text longer than chunk_size
        text = "Word " * 300  # 1500 chars
        chunks = split_text_into_chunks(text, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1

    def test_chunks_are_not_empty(self):
        from src.ingestion.chunker import split_text_into_chunks
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = split_text_into_chunks(text, chunk_size=30, chunk_overlap=5)
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_chunk_documents_adds_metadata(self):
        from src.ingestion.document import Document
        from src.ingestion.chunker import chunk_documents
        doc = Document(
            text="Word " * 200,  # Long enough to create multiple chunks
            metadata={"source": "test.txt", "type": "txt"},
        )
        chunks = chunk_documents([doc], chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert "chunk_index" in chunk.metadata
            assert "chunk_total" in chunk.metadata
            assert chunk.metadata["chunk_index"] == i


class TestRRF:
    """Test the RRF algorithm with no external dependencies."""

    def test_rrf_basic(self):
        from src.retrieval.reranker import reciprocal_rank_fusion
        list1 = [{"id": "A", "text": "a"}, {"id": "B", "text": "b"}, {"id": "C", "text": "c"}]
        list2 = [{"id": "C", "text": "c"}, {"id": "A", "text": "a"}, {"id": "D", "text": "d"}]
        result = reciprocal_rank_fusion([list1, list2], top_k=4)
        # Doc A should rank highest (rank 1 in list1, rank 2 in list2)
        assert result[0]["id"] == "A"
        assert all("rrf_score" in doc for doc in result)

    def test_rrf_with_single_list(self):
        from src.retrieval.reranker import reciprocal_rank_fusion
        lst = [{"id": "X", "text": "x"}, {"id": "Y", "text": "y"}]
        result = reciprocal_rank_fusion([lst], top_k=2)
        assert len(result) == 2
        assert result[0]["id"] == "X"  # X is rank 1, so higher RRF score

    def test_rrf_empty_input(self):
        from src.retrieval.reranker import reciprocal_rank_fusion
        result = reciprocal_rank_fusion([], top_k=5)
        assert result == []

    def test_rrf_top_k_limits_results(self):
        from src.retrieval.reranker import reciprocal_rank_fusion
        lst = [{"id": str(i), "text": f"doc {i}"} for i in range(10)]
        result = reciprocal_rank_fusion([lst], top_k=3)
        assert len(result) == 3


class TestMemory:
    """Test conversation memory with temp directory (no real files needed)."""

    def test_load_nonexistent_session_returns_empty(self, tmp_path, monkeypatch):
        from src.memory import conversation
        from src import config
        # Point memory to a temp directory so we don't pollute the real data dir
        monkeypatch.setattr(config, "MEMORY_DIR", tmp_path)
        history = conversation.load_history("nonexistent_session_xyz")
        assert history == []

    def test_save_and_load_history(self, tmp_path, monkeypatch):
        from src.memory import conversation
        from src import config
        monkeypatch.setattr(config, "MEMORY_DIR", tmp_path)

        conversation.save_history("test_session", "Hello", "Hi there!")
        history = conversation.load_history("test_session")

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"

    def test_session_id_sanitization(self, tmp_path, monkeypatch):
        from src.memory import conversation
        from src import config
        monkeypatch.setattr(config, "MEMORY_DIR", tmp_path)

        # Path traversal attempt should be sanitized
        malicious_id = "../../etc/passwd"
        # Should not raise, should not create a file outside tmp_path
        conversation.save_history(malicious_id, "test", "test response")
        history = conversation.load_history(malicious_id)
        assert len(history) == 2

    def test_format_history_for_prompt_empty(self):
        from src.memory.conversation import format_history_for_prompt
        result = format_history_for_prompt([])
        assert result == ""

    def test_format_history_for_prompt(self):
        from src.memory.conversation import format_history_for_prompt
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = format_history_for_prompt(history)
        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result


class TestConfigValidation:
    """Test the config validation function."""

    def test_validate_config_returns_list(self):
        from src.config import validate_config
        result = validate_config()
        assert isinstance(result, list)

    def test_missing_openai_key_flagged(self, monkeypatch):
        from src import config
        monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
        monkeypatch.setattr(config, "OPENAI_API_KEY", "")
        errors = config.validate_config()
        assert any("OPENAI_API_KEY" in e for e in errors)

    def test_invalid_overlap_flagged(self, monkeypatch):
        from src import config
        monkeypatch.setattr(config, "CHUNK_SIZE", 100)
        monkeypatch.setattr(config, "CHUNK_OVERLAP", 200)  # overlap > size = invalid
        errors = config.validate_config()
        assert any("CHUNK_OVERLAP" in e for e in errors)
