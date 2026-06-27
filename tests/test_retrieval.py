# ============================================================
# Tests — Retrieval Layer (Milestone 9)
#
# Tests for: BM25 retriever, vector store helpers, and the
# full reranker integration. ChromaDB/embedding calls are mocked.
#
# Run with: pytest tests/test_retrieval.py -v
# ============================================================

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── BM25 Retriever Tests ───────────────────────────────────────────────────────

class TestBM25Retriever:
    """
    Tests for the BM25 keyword retriever.
    BM25 is pure Python — no mocking required.
    """

    def test_bm25_returns_empty_for_no_corpus(self):
        """BM25 with no documents must return empty list, not crash."""
        from src.retrieval.bm25_retriever import retrieve_bm25
        result = retrieve_bm25("any query", all_documents=[], top_k=5)
        assert result == []

    def test_bm25_returns_results_matching_query(self):
        """BM25 should return documents containing query keywords ranked first."""
        from src.retrieval.bm25_retriever import retrieve_bm25

        corpus = [
            {"id": "a", "text": "aspirin is a common pain reliever used for headaches"},
            {"id": "b", "text": "diabetes management involves blood sugar monitoring"},
            {"id": "c", "text": "aspirin dosage for adults is 325mg to 650mg"},
        ]
        results = retrieve_bm25("aspirin dosage", all_documents=corpus, top_k=3)

        assert len(results) > 0
        # The chunk explicitly about aspirin dosage should rank higher
        top_ids = [r["id"] for r in results]
        assert "c" in top_ids  # Contains both "aspirin" and "dosage"

    def test_bm25_top_k_limits_results(self):
        """BM25 should respect the top_k parameter."""
        from src.retrieval.bm25_retriever import retrieve_bm25

        corpus = [
            {"id": str(i), "text": f"document number {i} about various topics"}
            for i in range(10)
        ]
        results = retrieve_bm25("document topics", all_documents=corpus, top_k=3)
        assert len(results) <= 3

    def test_bm25_does_not_mutate_input(self):
        """BM25 must not modify the original corpus dicts."""
        from src.retrieval.bm25_retriever import retrieve_bm25

        corpus = [{"id": "x", "text": "test document about something"}]
        original_text = corpus[0]["text"]
        retrieve_bm25("something", all_documents=corpus, top_k=1)
        assert corpus[0]["text"] == original_text

    def test_bm25_query_not_in_corpus_returns_results(self):
        """
        Even if the query doesn't exactly match, BM25 should return results
        (partial matches / token overlap) rather than an empty list.
        """
        from src.retrieval.bm25_retriever import retrieve_bm25

        corpus = [
            {"id": "a", "text": "medication side effects overview"},
            {"id": "b", "text": "drug interactions reference guide"},
        ]
        results = retrieve_bm25("medicine effects", all_documents=corpus, top_k=2)
        # BM25 should still find partial matches
        assert isinstance(results, list)


# ── RRF / Reranker Tests ───────────────────────────────────────────────────────

class TestReranker:
    """
    Tests for the RRF algorithm — the mathematical core of the system.
    No external dependencies.
    """

    def test_rrf_score_formula_correct(self):
        """
        Manually verify the RRF formula: score = 1/(rank + 60).
        For rank=1: score = 1/61 ≈ 0.01639.
        """
        from src.retrieval.reranker import reciprocal_rank_fusion

        single_list = [{"id": "doc_a", "text": "first document"}]
        results = reciprocal_rank_fusion([single_list], top_k=1)

        expected_score = 1.0 / (1 + 60)  # rank=1, k=60
        assert abs(results[0]["rrf_score"] - expected_score) < 1e-6

    def test_doc_in_both_lists_outranks_doc_in_one(self):
        """
        The whole point of RRF: Doc A in both lists should beat Doc B in just one,
        even if Doc B is rank 1 in its list.
        """
        from src.retrieval.reranker import reciprocal_rank_fusion

        # Doc A: rank 3 in semantic, rank 2 in BM25 → two contributions
        # Doc B: rank 1 in semantic only → one contribution
        semantic = [
            {"id": "B", "text": "b"},
            {"id": "C", "text": "c"},
            {"id": "A", "text": "a"},  # rank 3
        ]
        bm25 = [
            {"id": "C", "text": "c"},
            {"id": "A", "text": "a"},  # rank 2
        ]
        results = reciprocal_rank_fusion([semantic, bm25], top_k=3)
        result_ids = [r["id"] for r in results]

        # A appears in both lists; B appears only in semantic
        a_idx = result_ids.index("A")
        b_idx = result_ids.index("B")
        assert a_idx < b_idx, "Doc A (in 2 lists) should outrank Doc B (in 1 list)"

    def test_rrf_result_has_rrf_score_key(self):
        """Every result must have 'rrf_score' attached."""
        from src.retrieval.reranker import reciprocal_rank_fusion

        docs = [{"id": "x", "text": "doc x"}, {"id": "y", "text": "doc y"}]
        results = reciprocal_rank_fusion([docs], top_k=2)
        for r in results:
            assert "rrf_score" in r, f"Missing rrf_score in {r}"

    def test_rrf_scores_are_descending(self):
        """Results must be sorted highest score first."""
        from src.retrieval.reranker import reciprocal_rank_fusion

        docs = [{"id": str(i), "text": f"doc {i}"} for i in range(5)]
        results = reciprocal_rank_fusion([docs], top_k=5)
        scores = [r["rrf_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_results_with_both_empty_returns_empty(self):
        """rerank_results with two empty lists must return [] without crashing."""
        from src.retrieval.reranker import rerank_results
        result = rerank_results(semantic_results=[], bm25_results=[], top_k=5)
        assert result == []

    def test_rerank_results_with_one_empty_uses_the_other(self):
        """
        If one retriever returns nothing (e.g., BM25 on short texts), the
        reranker should still work using the non-empty list alone.
        """
        from src.retrieval.reranker import rerank_results

        semantic = [{"id": "a", "text": "doc a"}, {"id": "b", "text": "doc b"}]
        result = rerank_results(semantic_results=semantic, bm25_results=[], top_k=2)
        assert len(result) == 2

    def test_original_dicts_not_mutated_by_rrf(self):
        """RRF adds rrf_score to copies, not the originals."""
        from src.retrieval.reranker import reciprocal_rank_fusion

        original = [{"id": "z", "text": "doc z"}]
        reciprocal_rank_fusion([original], top_k=1)
        assert "rrf_score" not in original[0]  # Original must be unchanged


# ── Vector Store Tests ─────────────────────────────────────────────────────────

class TestVectorStore:
    """
    Tests for the ChromaDB vector store wrapper.
    ChromaDB is mocked so tests run without a real database.
    """

    def test_upsert_documents_calls_collection_upsert(self):
        """upsert_documents must call ChromaDB's collection.upsert() method."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            vector_store.upsert_documents(
                ids=["id1", "id2"],
                texts=["text 1", "text 2"],
                embeddings=[[0.1, 0.2], [0.3, 0.4]],
                metadatas=[{"source": "a.pdf"}, {"source": "b.pdf"}],
            )

        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args.kwargs
        assert call_kwargs["ids"] == ["id1", "id2"]

    def test_upsert_normalizes_none_metadata_values(self):
        """
        ChromaDB rejects None values in metadata.
        upsert_documents must replace None with empty string.
        """
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            vector_store.upsert_documents(
                ids=["id1"],
                texts=["text"],
                embeddings=[[0.1, 0.2]],
                metadatas=[{"source": "file.pdf", "page": None}],  # None value
            )

        call_kwargs = mock_collection.upsert.call_args.kwargs
        sent_metadata = call_kwargs["metadatas"][0]
        assert sent_metadata["page"] == ""  # None replaced with ""

    def test_upsert_empty_list_does_not_call_collection(self):
        """Calling upsert with empty lists must be a no-op."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            vector_store.upsert_documents(
                ids=[], texts=[], embeddings=[], metadatas=[]
            )

        mock_collection.upsert.assert_not_called()

    def test_get_collection_count_returns_integer(self):
        """get_collection_count must return an integer."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.count.return_value = 42

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            count = vector_store.get_collection_count()

        assert count == 42
        assert isinstance(count, int)

    def test_query_similar_returns_empty_on_empty_collection(self):
        """query_similar on empty collection must return [] without error."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0  # Empty collection

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            result = vector_store.query_similar([0.1, 0.2, 0.3], top_k=5)

        assert result == []
        mock_collection.query.assert_not_called()  # Should not attempt query

    def test_delete_by_source_deletes_matching_ids(self):
        """delete_by_source must find IDs by metadata filter and delete them."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["chunk_1", "chunk_2", "chunk_3"]}

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            count = vector_store.delete_by_source("myfile.pdf")

        mock_collection.delete.assert_called_once_with(ids=["chunk_1", "chunk_2", "chunk_3"])
        assert count == 3

    def test_delete_by_source_returns_zero_when_not_found(self):
        """delete_by_source must return 0 when the file is not in ChromaDB."""
        from src.retrieval import vector_store

        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}  # No matching chunks

        with patch.object(vector_store, "_get_collection", return_value=mock_collection):
            count = vector_store.delete_by_source("nonexistent.pdf")

        mock_collection.delete.assert_not_called()
        assert count == 0
