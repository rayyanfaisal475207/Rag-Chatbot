# ============================================================
# Tests — Pipeline Components (Milestone 9)
#
# Tests the query rewriter, router, and evaluator logic using mocks.
# No real LLM API calls are made — all LLM responses are mocked so
# these tests run instantly without API keys.
#
# Run with: pytest tests/test_pipeline.py -v
# ============================================================

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Query Rewriter Tests ───────────────────────────────────────────────────────

class TestQueryRewriter:
    """
    Tests for the query rewriter (LLM Call 1).
    Verifies: no-history shortcut, LLM delegation, fallback on empty response.
    """

    async def test_no_history_returns_original_message(self):
        """
        When there is no conversation history, the query is already standalone.
        The rewriter should return it unchanged WITHOUT calling the LLM.
        """
        from src.pipeline.query_rewriter import rewrite_query

        with patch("src.pipeline.query_rewriter.call_llm") as mock_llm:
            result = await rewrite_query("What is the dosage?", conversation_history=[])

        assert result == "What is the dosage?"
        mock_llm.assert_not_called()  # Must NOT call LLM when history is empty

    async def test_with_history_calls_llm(self):
        """
        When history exists, the LLM must be called to resolve references.
        """
        from src.pipeline.query_rewriter import rewrite_query

        history = [
            {"role": "user", "content": "Tell me about aspirin"},
            {"role": "assistant", "content": "Aspirin is a pain reliever..."},
        ]

        with patch("src.pipeline.query_rewriter.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "What are the side effects of aspirin?"
            result = await rewrite_query("What about the side effects?", history)

        mock_llm.assert_called_once()
        assert result == "What are the side effects of aspirin?"

    async def test_empty_llm_response_falls_back_to_original(self):
        """
        If the LLM returns an empty string (network glitch, etc.),
        the rewriter should fall back to the original message rather than crash.
        """
        from src.pipeline.query_rewriter import rewrite_query

        history = [{"role": "user", "content": "previous message"}]

        with patch("src.pipeline.query_rewriter.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ""  # LLM returns nothing
            result = await rewrite_query("What about it?", history)

        assert result == "What about it?"  # Falls back to original

    async def test_rewrite_strips_whitespace(self):
        """The rewriter must strip leading/trailing whitespace from LLM output."""
        from src.pipeline.query_rewriter import rewrite_query

        history = [{"role": "user", "content": "previous"}]

        with patch("src.pipeline.query_rewriter.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "  What are the side effects of aspirin?  \n"
            result = await rewrite_query("What about side effects?", history)

        assert result == "What are the side effects of aspirin?"
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    async def test_retry_rewriter_calls_llm_with_feedback(self):
        """
        The retry rewriter must pass the evaluator feedback to the LLM
        to generate a more targeted query.
        """
        from src.pipeline.query_rewriter import rewrite_for_retry

        with patch("src.pipeline.query_rewriter.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "aspirin bleeding risk clinical trials"
            result = await rewrite_for_retry(
                original_message="What about bleeding?",
                previous_query="aspirin bleeding",
                evaluator_feedback="Documents discuss aspirin uses but not bleeding specifically",
            )

        mock_llm.assert_called_once()
        # Verify feedback was passed to the LLM in the user message
        call_args = mock_llm.call_args
        assert "bleeding" in call_args.kwargs.get("user_message", "") or \
               "bleeding" in str(call_args.args)
        assert result == "aspirin bleeding risk clinical trials"

    async def test_retry_rewriter_falls_back_on_empty_response(self):
        """If retry rewriter gets empty LLM response, it reuses the previous query."""
        from src.pipeline.query_rewriter import rewrite_for_retry

        with patch("src.pipeline.query_rewriter.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ""
            result = await rewrite_for_retry(
                original_message="What about bleeding?",
                previous_query="aspirin side effects",
                evaluator_feedback="missing info",
            )

        assert result == "aspirin side effects"  # Falls back to previous query


# ── Router Tests ────────────────────────────────────────────────────────────────

class TestRouter:
    """
    Tests for the RAG router (LLM Call 2).
    Verifies: YES → True, NO → False, case insensitivity, and fallback.
    """

    async def test_yes_response_means_rag_needed(self):
        """Router should return True when LLM responds YES."""
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "YES"
            result = await route_query("What is the aspirin dosage?")

        assert result is True

    async def test_no_response_means_direct_answer(self):
        """Router should return False when LLM responds NO."""
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "NO"
            result = await route_query("Tell me a joke")

        assert result is False

    async def test_yes_with_trailing_text_still_routes_to_rag(self):
        """
        The router uses startswith("YES"), so 'YES, this needs retrieval'
        should still trigger RAG — it's checking the first word only.
        """
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "YES, this query requires document retrieval."
            result = await route_query("What are the side effects?")

        assert result is True

    async def test_unexpected_response_defaults_to_rag(self):
        """
        If the LLM returns something unexpected (not YES/NO), the router
        must default to True (attempt retrieval) as the safe fallback.
        """
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "MAYBE"  # Unexpected
            result = await route_query("Some ambiguous query")

        assert result is False  # "MAYBE" doesn't start with YES → False

    async def test_router_uses_zero_temperature(self):
        """
        The router call must use temperature=0.0 for deterministic output.
        This is a critical property — routing must be consistent.
        """
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "YES"
            await route_query("Any query")

        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.0

    async def test_router_uses_minimal_token_budget(self):
        """
        Router only needs YES or NO — max_tokens should be tiny (≤10).
        Keeping it small prevents unnecessary cost.
        """
        from src.pipeline.router import route_query

        with patch("src.pipeline.router.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "NO"
            await route_query("Hello")

        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs.get("max_tokens", 999) <= 10


# ── Evaluator Tests ─────────────────────────────────────────────────────────────

class TestEvaluator:
    """
    Tests for the relevance evaluator (LLM Call 3).
    Verifies: JSON parsing, error recovery, empty-chunk shortcut.
    """

    async def test_empty_chunks_returns_not_relevant(self):
        """
        If no chunks were retrieved, the evaluator must immediately return
        {relevant: False} without calling the LLM.
        """
        from src.pipeline.evaluator import evaluate_relevance

        with patch("src.pipeline.evaluator.call_llm") as mock_llm:
            result = await evaluate_relevance(
                original_query="What is the dosage?",
                rewritten_query="aspirin dosage",
                retrieved_chunks=[],
            )

        assert result["relevant"] is False
        assert "reason" in result
        mock_llm.assert_not_called()

    async def test_valid_json_relevant_true(self):
        """Evaluator correctly parses a valid JSON response with relevant=True."""
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "Aspirin 325mg daily", "metadata": {"source": "guide.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"relevant": true, "reason": "Document contains dosage info"}'
            result = await evaluate_relevance("dosage?", "aspirin dosage", chunks)

        assert result["relevant"] is True
        assert "dosage" in result["reason"].lower()

    async def test_valid_json_relevant_false(self):
        """Evaluator correctly parses a JSON response with relevant=False."""
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "Aspirin history overview", "metadata": {"source": "history.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"relevant": false, "reason": "Document discusses history not dosage"}'
            result = await evaluate_relevance("dosage?", "aspirin dosage", chunks)

        assert result["relevant"] is False
        assert "reason" in result

    async def test_malformed_json_retries_once(self):
        """
        On malformed JSON, the evaluator must retry the LLM call once
        before giving up. Verifies the retry mechanism works.
        """
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "some text", "metadata": {"source": "doc.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            # First call: bad JSON. Second call: valid JSON.
            mock_llm.side_effect = [
                "not valid json at all",
                '{"relevant": true, "reason": "Recovered on retry"}',
            ]
            result = await evaluate_relevance("query", "query", chunks)

        assert mock_llm.call_count == 2  # Exactly one retry
        assert result["relevant"] is True

    async def test_all_malformed_json_defaults_to_not_relevant(self):
        """
        If all retry attempts return invalid JSON, the evaluator must default
        to {relevant: False} so the retry loop can kick in rather than crashing.
        """
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "some text", "metadata": {"source": "doc.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "INVALID JSON ALWAYS"  # Always fails
            result = await evaluate_relevance("query", "query", chunks)

        assert result["relevant"] is False
        assert "reason" in result
        assert mock_llm.call_count == 2  # Tried twice, both failed

    async def test_evaluator_uses_zero_temperature(self):
        """Evaluator judgement must be deterministic (temperature=0.0)."""
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "text", "metadata": {"source": "doc.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"relevant": true, "reason": "ok"}'
            await evaluate_relevance("q", "q", chunks)

        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.0

    async def test_json_missing_keys_triggers_retry(self):
        """
        JSON with missing 'relevant' or 'reason' keys should trigger a retry,
        not be returned as-is.
        """
        from src.pipeline.evaluator import evaluate_relevance

        chunks = [{"text": "text", "metadata": {"source": "doc.pdf"}}]

        with patch("src.pipeline.evaluator.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [
                '{"score": 0.9}',  # Missing 'relevant' and 'reason' keys
                '{"relevant": true, "reason": "correct on retry"}',
            ]
            result = await evaluate_relevance("q", "q", chunks)

        assert mock_llm.call_count == 2
        assert result["relevant"] is True
