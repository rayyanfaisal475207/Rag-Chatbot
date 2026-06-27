# ============================================================
# Query Rewriter — LLM Call 1
#
# PURPOSE:
# Users often ask follow-up questions that reference previous messages.
# "What about the side effects?" is meaningless without knowing we've
# been talking about aspirin. The query rewriter resolves these references
# by using the conversation history to make the query self-contained.
#
# This is critical for retrieval quality: ChromaDB doesn't know about
# the conversation, it only sees the query text. If you pass in
# "What about the side effects?", ChromaDB will search for "side effects"
# of nothing in particular — and return irrelevant results.
#
# After rewriting: "What are the side effects of aspirin?" — precise search.
#
# RETRY MODE:
# The same rewriter runs again during the retry loop, but with different
# input: instead of just conversation history, it also gets the evaluator's
# feedback about why the previous retrieval failed.
# This produces a more targeted query for the second retrieval attempt.
# ============================================================

import logging
from pathlib import Path

from src.llm.client import call_llm

logger = logging.getLogger(__name__)

# Load the prompt template once at module import time.
# Prompts live in files so they can be tuned without touching Python code.
_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "query_rewriter.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


async def rewrite_query(
    user_message: str,
    conversation_history: list[dict],
) -> str:
    """
    Rewrite the user's message as a standalone search query.

    LLM Call 1 in the pipeline.

    Args:
        user_message:          The user's latest message (possibly a follow-up).
        conversation_history:  Previous messages in this session.

    Returns:
        A self-contained query string suitable for vector search.
        If history is empty or the message is already standalone, returns
        the original message unchanged (the prompt instructs the LLM to do this).
    """
    # Edge case: no history — the query is already standalone
    if not conversation_history:
        logger.debug("No history — returning original query unchanged.")
        return user_message.strip()

    # Format history for the prompt
    history_text = _format_history(conversation_history)

    user_input = (
        f"Conversation history:\n{history_text}\n\n"
        f"Latest message: {user_message}"
    )

    rewritten = await call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_message=user_input,
        temperature=0.0,   # Deterministic: same input should always produce same rewrite
        max_tokens=200,    # Queries are short — no need for large budget
    )

    rewritten = rewritten.strip()

    # Safety: if the LLM returns an empty string (shouldn't happen), fall back
    if not rewritten:
        logger.warning("Query rewriter returned empty string. Using original message.")
        return user_message.strip()

    logger.info("Query rewritten: '%s' → '%s'", user_message[:50], rewritten[:80])
    return rewritten


async def rewrite_for_retry(
    original_message: str,
    previous_query: str,
    evaluator_feedback: str,
) -> str:
    """
    Rewrite the query specifically to address evaluator feedback.

    This is called when the relevance evaluator returns {"relevant": false}.
    The evaluator provides a reason for failure (e.g., "documents discuss X
    but not the specific aspect Y the user asked about"). This function uses
    that feedback to craft a better retrieval query.

    Args:
        original_message:    The user's original message (unchanged).
        previous_query:      The query that failed to retrieve relevant docs.
        evaluator_feedback:  The evaluator's explanation of what was missing.

    Returns:
        An improved query string targeting what the evaluator said was missing.
    """
    retry_prompt = (
        "You are a search query optimizer. A previous search query failed to "
        "retrieve relevant documents. Use the feedback below to write a better "
        "search query.\n\n"
        "Output ONLY the improved query. No explanation. No quotes.\n\n"
        "Rules:\n"
        "- The new query should target specifically what the feedback says is missing.\n"
        "- Use different keywords or synonyms than the previous query.\n"
        "- Keep the query focused and specific."
    )

    user_input = (
        f"Original user question: {original_message}\n\n"
        f"Previous search query (which failed): {previous_query}\n\n"
        f"Why it failed (evaluator feedback): {evaluator_feedback}\n\n"
        f"Write an improved search query:"
    )

    improved = await call_llm(
        system_prompt=retry_prompt,
        user_message=user_input,
        temperature=0.2,  # Slight creativity to try different keywords
        max_tokens=150,
    )

    improved = improved.strip()

    if not improved:
        logger.warning("Retry rewriter returned empty string. Reusing previous query.")
        return previous_query

    logger.info(
        "Retry rewrite: '%s' → '%s' (feedback: %s)",
        previous_query[:50], improved[:80], evaluator_feedback[:60]
    )
    return improved


def _format_history(history: list[dict]) -> str:
    """Format conversation history for insertion into the rewriter prompt."""
    lines = []
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)
