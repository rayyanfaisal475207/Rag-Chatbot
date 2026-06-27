# Evaluation Report — RAG Chatbot

## Overview

This document covers the automated test suite (109 tests, 0 failures) and
the qualitative evaluation framework for the RAG pipeline.

---

## 1. Automated Test Suite Results

```
======================== 109 passed, 0 failed in 2.15s ========================
```

| Test File | Tests | Focus |
|---|---|---|
| `test_structure.py` | 27 | File structure, imports, chunker, RRF, memory, config |
| `test_pipeline.py` | 21 | Query rewriter, router, evaluator (all mocked — no API keys) |
| `test_retrieval.py` | 20 | BM25, RRF algorithm, ChromaDB vector store (mocked) |
| `test_database.py` | 21 | SQLite schema, pipeline logger CRUD, FK cascades |
| `test_api.py` | 20 | FastAPI endpoints: /health, /documents, /ingest, /chat |
| **Total** | **109** | **All green** |

### Key Properties Verified

**No API keys required** — all LLM calls are mocked via `unittest.mock.AsyncMock`.
Entire suite runs in ~2 seconds.

---

## 2. What Good Looks Like

### Successful RAG Path (happy path)
```
query_rewriter  done   "What are the side effects of aspirin?" (300ms)
router          done   "RAG required: YES" (120ms)
retrieval       done   "8 chunks retrieved" (450ms)
reranker        done   "Top 4 selected after RRF" (5ms)
evaluator       done   "relevant: true — Documents contain detailed side effects" (280ms)
response        done   "Aspirin can cause..." (1200ms)
memory          done   "History saved" (2ms)
```

### Retry Path (evaluator fires)
```
query_rewriter  done   "What about it?" (280ms)
router          done   "RAG required: YES" (100ms)
retrieval       done   "8 chunks retrieved" (430ms)
reranker        done   "Top 4 selected after RRF" (4ms)
evaluator       done   "relevant: false — Documents don't contain specific dosage" (260ms)
  ↳ RETRY #1
query_rewriter  done   "What is the recommended aspirin dosage for adults?" (250ms)
retrieval       done   "8 chunks retrieved" (440ms)
reranker        done   "Top 4 selected after RRF" (4ms)
evaluator       done   "relevant: true — Dosage section found" (255ms)
response        done   "The recommended adult dose is..." (1100ms)
memory          done   "History saved" (2ms)
```

### Direct Path (no retrieval)
```
query_rewriter  done   "Hello!" (280ms)
router          done   "RAG not required: NO" (95ms)
response        done   "Hello! How can I help you?" (800ms)
memory          done   "History saved" (2ms)
```

---

## 3. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| BM25 built in-memory each query | Slow for large corpora | Pre-build index on startup |
| Evaluator uses same LLM provider as response | Correlated failures | Use a separate evaluator model |
| Max 2 retries before safe fallback | May miss some queries | Tune `MAX_RETRIES` in `.env` |
| No cross-encoder reranking | Lower precision on subtle queries | Add `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Session memory is file-based JSON | Not suitable for multi-instance | Move to Redis for production |
