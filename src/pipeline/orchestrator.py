# ============================================================
# Orchestrator — The Full RAG Pipeline
#
# This is the brain of the system. It coordinates all other components
# in the correct order and implements the retry loop.
# It also logs every step to the SQLite pipeline logger.
# ============================================================

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator

from src import config
from src.memory.conversation import load_history, save_history, format_history_for_prompt
from src.pipeline.query_rewriter import rewrite_query, rewrite_for_retry
from src.pipeline.router import route_query
from src.pipeline.evaluator import evaluate_relevance
from src.retrieval.embedder import embed_text
from src.retrieval.vector_store import query_similar
from src.retrieval.bm25_retriever import retrieve_bm25
from src.retrieval.reranker import rerank_results
from src.llm.client import call_llm, stream_llm

from src.database import pipeline_logger

logger = logging.getLogger(__name__)

# Load final response prompt template
_FINAL_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "final_response.txt"
)
_FINAL_PROMPT_TEMPLATE = _FINAL_PROMPT_PATH.read_text(encoding="utf-8")

# Safe response when all retries are exhausted
_SAFE_RESPONSE = (
    "I couldn't find sufficient information in the knowledge base to accurately "
    "answer your question. You may want to try rephrasing your question or "
    "ensure the relevant documents have been ingested into the system."
)


async def process_query(
    session_id: str,
    user_message: str,
) -> AsyncGenerator[dict, None]:
    """
    Run the full RAG pipeline for a user message.
    """
    import time

    # Init session and query in DB
    pipeline_logger.upsert_session(session_id)
    query_id = pipeline_logger.create_query(session_id, user_message)
    query_start_time = time.monotonic()

    def event(step: str, status: str, detail: str = "", ms: int = None, retry_num: int = 0) -> dict:
        evt = {"step": step, "status": status, "detail": detail}
        if ms is not None:
            evt["ms"] = ms
        # Log to DB
        pipeline_logger.log_step(query_id, step, status, detail, ms, retry_num)
        return evt

    # ─── Step 1: Load Conversation History ────────────────────────────────
    history = load_history(session_id)
    logger.info(
        "Session '%s': loaded %d messages. User: '%s'",
        session_id, len(history), user_message[:60]
    )

    # ─── Step 2: Query Rewriter (LLM Call 1) ──────────────────────────────
    yield event("query_rewriter", "active")
    t0 = time.monotonic()
    try:
        rewritten_query = await rewrite_query(user_message, history)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        pipeline_logger.log_llm_call(
            query_id, "rewriter", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
            "Rewrite system prompt", user_message, rewritten_query, elapsed_ms
        )
    except Exception as exc:
        logger.error("Query rewriter failed: %s", exc)
        yield event("query_rewriter", "error", str(exc))
        rewritten_query = user_message  # Fall back to original
        elapsed_ms = int((time.monotonic() - t0) * 1000)
    
    pipeline_logger.update_query(query_id, rewritten_query=rewritten_query)
    yield event("query_rewriter", "done", f"Rewritten: '{rewritten_query}'", elapsed_ms)

    # ─── Step 3: Router (LLM Call 2) ──────────────────────────────────────
    yield event("router", "active")
    t0 = time.monotonic()
    try:
        needs_rag = await route_query(rewritten_query)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        pipeline_logger.log_llm_call(
            query_id, "router", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
            "Router system prompt", rewritten_query, str(needs_rag), elapsed_ms
        )
    except Exception as exc:
        logger.error("Router failed: %s", exc)
        yield event("router", "error", str(exc))
        needs_rag = True  # Default to retrieval on error (safer)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
    
    pipeline_logger.update_query(query_id, needs_rag=needs_rag)
    yield event("router", "done", f"RAG required: {'YES' if needs_rag else 'NO'}", elapsed_ms)

    # ─── No retrieval needed path ──────────────────────────────────────────
    if not needs_rag:
        yield event("retrieval", "skipped", "Router decided no retrieval needed")
        yield event("reranker", "skipped")
        yield event("evaluator", "skipped")

        yield event("response", "active", "Generating direct response...")
        t0 = time.monotonic()

        history_text = format_history_for_prompt(history)
        direct_system = (
            "You are a helpful assistant. Answer the user's question directly and accurately. "
            f"Conversation history:\n{history_text}" if history_text else
            "You are a helpful assistant. Answer the user's question directly and accurately."
        )

        full_response = ""
        async for token in stream_llm(direct_system, rewritten_query):
            full_response += token
            yield event("response", "streaming", token)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        yield event("response", "done", f"Response generated ({len(full_response)} chars)", elapsed_ms)
        
        pipeline_logger.log_llm_call(
            query_id, "direct_response", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
            direct_system, rewritten_query, full_response, elapsed_ms
        )
        
        total_ms = int((time.monotonic() - query_start_time) * 1000)
        pipeline_logger.update_query(query_id, response_type="direct", final_response=full_response, total_duration_ms=total_ms)

        # Save to memory
        try:
            save_history(session_id, user_message, full_response)
            yield event("memory", "done", "Saved to session")
        except Exception as exc:
            logger.error("Failed to save history: %s", exc)
            yield event("memory", "error", str(exc))

        return  # End of no-RAG path

    # ─── Retrieval path: retry loop ────────────────────────────────────────
    retry_count = 0
    current_query = rewritten_query
    evaluator_feedback = None
    final_response = _SAFE_RESPONSE  # default if all retries fail
    response_type = "safe"

    while retry_count <= config.MAX_RETRIES:
        # If this is a retry, rewrite the query with evaluator feedback
        if retry_count > 0 and evaluator_feedback:
            yield event(
                "query_rewriter",
                "active",
                f"Retry {retry_count}: improving query based on feedback",
                retry_num=retry_count
            )
            t0 = time.monotonic()
            
            try:
                current_query = await rewrite_for_retry(
                    original_message=user_message,
                    previous_query=current_query,
                    evaluator_feedback=evaluator_feedback,
                )
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                pipeline_logger.log_llm_call(
                    query_id, "retry_rewriter", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
                    "Retry rewriter prompt", f"User: {user_message}\nPrev: {current_query}\nFeedback: {evaluator_feedback}", current_query, elapsed_ms, retry_count
                )
            except Exception as e:
                logger.error("Retry rewriter failed: %s", e)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                
            yield event(
                "query_rewriter",
                "done",
                f"Retry query: '{current_query}'",
                elapsed_ms,
                retry_num=retry_count
            )

        # ── Retrieve ────────────────────────────────────────────────────────
        yield event("retrieval", "active", f"Searching for: '{current_query[:60]}'", retry_num=retry_count)
        t0 = time.monotonic()

        query_embedding = await embed_text(current_query)
        semantic_results = query_similar(query_embedding, top_k=config.TOP_K_RETRIEVAL)

        # For BM25: we need to pass the same documents that are in ChromaDB
        bm25_results = retrieve_bm25(current_query, semantic_results, top_k=config.TOP_K_RETRIEVAL)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        yield event(
            "retrieval",
            "done",
            f"{len(semantic_results)} chunks retrieved",
            elapsed_ms,
            retry_num=retry_count
        )
        
        # Log retrieved docs to DB
        pipeline_logger.log_retrieved_docs(query_id, semantic_results, "semantic", retry_number=retry_count)
        pipeline_logger.log_retrieved_docs(query_id, bm25_results, "bm25", retry_number=retry_count)

        # ── Re-rank ─────────────────────────────────────────────────────────
        yield event("reranker", "active", retry_num=retry_count)
        t0 = time.monotonic()
        reranked = rerank_results(semantic_results, bm25_results, top_k=config.TOP_K_RERANK)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        yield event("reranker", "done", f"Top {len(reranked)} selected", elapsed_ms, retry_num=retry_count)

        pipeline_logger.log_retrieved_docs(query_id, reranked, "rrf", retry_number=retry_count)

        # ── Evaluate ─────────────────────────────────────────────────────────
        yield event("evaluator", "active", retry_num=retry_count)
        t0 = time.monotonic()
        try:
            evaluation = await evaluate_relevance(user_message, current_query, reranked)
        except Exception as e:
            logger.error("Evaluator failed: %s", e)
            evaluation = {"relevant": True, "reason": "Evaluator failed, proceeding"}
            
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        is_relevant = evaluation.get("relevant", False)
        eval_reason = evaluation.get("reason", "")
        
        pipeline_logger.log_llm_call(
            query_id, "evaluator", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
            "Evaluator prompt", current_query, str(evaluation), elapsed_ms, retry_count
        )
        
        # Update relevance for RRF docs in DB
        pipeline_logger.update_retrieved_docs_relevance(query_id, is_relevant, retry_count)
        
        yield event(
            "evaluator",
            "done",
            f"Relevant: {is_relevant} — {eval_reason[:60]}",
            elapsed_ms,
            retry_num=retry_count
        )

        if is_relevant:
            # ── Generate grounded response ───────────────────────────────────
            yield event("response", "streaming", "Generating grounded response...", retry_num=retry_count)
            t0 = time.monotonic()

            documents_text = _format_documents_for_prompt(reranked)
            history_text = format_history_for_prompt(history)
            system_prompt = _FINAL_PROMPT_TEMPLATE.format(
                documents=documents_text,
                history=history_text or "(no previous conversation)",
            )

            full_response = ""
            async for token in stream_llm(system_prompt, user_message):
                full_response += token
                yield event("response", "streaming", token, retry_num=retry_count)

            elapsed_ms = int((time.monotonic() - t0) * 1000)
            yield event("response", "done", f"Response generated ({len(full_response)} chars)", elapsed_ms, retry_num=retry_count)
            
            pipeline_logger.log_llm_call(
                query_id, "response", config.LLM_PROVIDER, config.GROQ_MODEL if config.LLM_PROVIDER=="groq" else config.GEMINI_MODEL,
                system_prompt, user_message, full_response, elapsed_ms, retry_count
            )

            final_response = full_response
            response_type = "rag"
            break  # Success — exit retry loop

        else:
            # Not relevant — check retry budget
            if retry_count >= config.MAX_RETRIES:
                logger.warning(
                    "All %d retries exhausted for session '%s'. Returning safe response.",
                    config.MAX_RETRIES, session_id
                )
                yield event(
                    "evaluator",
                    "error",
                    f"Max retries ({config.MAX_RETRIES}) reached — returning safe response",
                    retry_num=retry_count
                )
                final_response = _SAFE_RESPONSE
                response_type = "safe"
                
                # Stream the safe response so the frontend actually receives it
                import asyncio
                yield event("response", "streaming", "Generating safe response...", retry_num=retry_count)
                for word in _SAFE_RESPONSE.split(" "):
                    yield event("response", "streaming", word + " ", retry_num=retry_count)
                    await asyncio.sleep(0.02)
                yield event("response", "done", f"Response generated ({len(final_response)} chars)", 0, retry_num=retry_count)
                
                break

            # Store feedback for the retry rewriter
            evaluator_feedback = eval_reason
            retry_count += 1
            yield event(
                "query_rewriter",
                "active",
                f"Retry {retry_count}/{config.MAX_RETRIES}: {eval_reason[:60]}",
                retry_num=retry_count
            )
            logger.info(
                "Retry %d/%d for session '%s'. Feedback: %s",
                retry_count, config.MAX_RETRIES, session_id, eval_reason[:80]
            )

    # Update query final status in DB
    total_ms = int((time.monotonic() - query_start_time) * 1000)
    pipeline_logger.update_query(
        query_id,
        retry_count=retry_count,
        response_type=response_type,
        final_response=final_response,
        total_duration_ms=total_ms
    )

    # ─── Save to Memory ────────────────────────────────────────────────────
    try:
        save_history(session_id, user_message, final_response)
        yield event("memory", "done", "Saved to session")
    except Exception as exc:
        logger.error("Failed to save history for session '%s': %s", session_id, exc)
        yield event("memory", "error", str(exc))


def _format_documents_for_prompt(chunks: list[dict]) -> str:
    """
    Format retrieved chunks for insertion into the final response prompt.
    """
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        page = meta.get("page", "")
        section = meta.get("section", "")
        location = f"page {page}" if page else (f"section: {section}" if section else "")
        location_str = f" ({location})" if location else ""
        rrf = chunk.get("rrf_score", "")
        score_str = f" [relevance: {rrf:.4f}]" if rrf else ""

        parts.append(
            f"[Document {i}] {source}{location_str}{score_str}\n"
            f"{chunk.get('text', '')}"
        )

    return "\n\n---\n\n".join(parts)
