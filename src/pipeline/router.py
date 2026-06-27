# ============================================================
# Router — LLM Call 2: Does This Query Need Retrieval?
#
# PURPOSE:
# Not every question requires searching the document store.
# "Hello! How are you?" doesn't need retrieval.
# "What is the bleeding risk of aspirin?" definitely does.
#
# Routing correctly has two benefits:
# 1. Speed: skipping retrieval makes conversational responses instant
# 2. Quality: retrieving documents for a general question can inject
#    irrelevant context that confuses the final response
#
# THE PROMPT STRATEGY (FEW-SHOT):
# The router prompt includes 10 example Q→YES/NO pairs.
# This "few-shot prompting" dramatically improves accuracy compared to
# just describing the rules in words. The examples serve as calibration
# data embedded directly in the prompt.
#
# OUTPUT FORMAT:
# Strictly "YES" or "NO". We strip the response and check the first
# word only, so "YES, because..." still works. If the LLM returns
# something unexpected, we default to YES (safer — try retrieval).
# ============================================================

import logging
from pathlib import Path

from src.llm.client import call_llm

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "router.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


async def route_query(rewritten_query: str) -> bool:
    """
    Decide whether the query requires RAG (document retrieval).

    LLM Call 2 in the pipeline.

    Args:
        rewritten_query: The standalone query from the query rewriter.

    Returns:
        True if retrieval is needed (YES).
        False if the query can be answered directly (NO).
    """
    response = await call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_message=rewritten_query,
        temperature=0.0,  # Must be deterministic — this is a binary decision
        max_tokens=5,     # Only need "YES" or "NO" — tiny token budget
    )

    # Parse the response: look for YES or NO in the first word
    answer = response.strip().upper()
    needs_rag = answer.startswith("YES")

    logger.info(
        "Router decision for '%s': %s",
        rewritten_query[:60], "YES (retrieve)" if needs_rag else "NO (direct answer)"
    )

    return needs_rag
