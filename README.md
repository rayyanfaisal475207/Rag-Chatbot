<div align="center">

# RAG Chatbot

**A production-grade Retrieval-Augmented Generation system with multi-step LLM pipeline, hybrid search, and real-time trace visibility.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.0%2B-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)

[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-Embeddings_%26_Vision-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Fallback-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Anthropic](https://img.shields.io/badge/Anthropic-Fallback-191919?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6719?style=for-the-badge&logoColor=white)](https://www.trychroma.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Pipeline_Logs-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

[![pytest](https://img.shields.io/badge/pytest-Async_Testing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Technology Stack](#️-technology-stack)
- [Getting Started](#-getting-started)
- [Pipeline Deep Dive](#-pipeline-deep-dive)
- [Pipeline Observability & SQLite Logging](#-pipeline-observability--sqlite-logging)
- [Document Ingestion](#-document-ingestion)
- [Frontend](#-frontend)
- [Testing](#-testing)
- [Project Structure](#-project-structure)

---

## 🔍 Overview

This is not a basic RAG system. It implements a **multi-step agentic pipeline** that intelligently routes queries, evaluates retrieval quality, and retries with improved queries when results are insufficient — all while streaming live pipeline traces to the frontend in real time.

> Built for accuracy over speed: the system will loop and self-correct rather than hallucinate an answer.

---

## 🏗 Architecture

The system processes every user query through a structured pipeline of LLM calls and application logic:

```
User Query
    │
    ▼
Load Conversation History
    │
    ▼
[LLM Call 1] Query Rewriter ──► Rewrite query using conversation context
    │
    ▼
[LLM Call 2] Orchestrator ──► Does this query need RAG?
    │                               │
    │ No                            │ Yes
    ▼                               ▼
[LLM] Direct Response       ChromaDB Vector Search
                                    │
                                    ▼
                             RRF Re-ranking (BM25 + Semantic)
                                    │
                                    ▼
                      [LLM Call 3] Relevance Evaluator
                         Are documents sufficient?
                           │                 │
                           │ Yes             │ No
                           ▼                 ▼
                  [LLM] Grounded      Retry Limit Check
                       Response         │         │
                           │           │ No       │ Yes
                           │           ▼          ▼
                           │     Safe Response  [LLM] Improve Query
                           │                        │
                           │                        └──► Retry Retrieval
                           ▼
                  Return Response to User
                           │
                           ▼
                  Save to Conversation Memory
```

---

## 🚀 Key Features

### 1. Multi-Step Intelligent Pipeline

Four distinct LLM interactions, each with a specific role:

| Step       | Role                            | Description                                                                            |
| ---------- | ------------------------------- | -------------------------------------------------------------------------------------- |
| LLM Call 1 | **Query Rewriter**              | Rephrases the user's message into a standalone search query using conversation history |
| LLM Call 2 | **Orchestrator / Router**       | Decides whether the query requires knowledge base retrieval or a direct response       |
| LLM Call 3 | **Relevance Evaluator**         | Assesses whether retrieved documents actually answer the query                         |
| LLM Call 4 | **Grounded Response Generator** | Synthesizes a final answer strictly from retrieved context with source citations       |

### 2. Smart Retry Loop

When the Relevance Evaluator determines retrieved documents are insufficient, the system:

1. Feeds evaluator feedback back to the Query Rewriter
2. Generates an improved search query
3. Re-runs retrieval with the refined query
4. Repeats until documents are relevant or the retry limit is hit

This eliminates hallucinations — the system returns a safe "not enough information" response rather than fabricating an answer.

### 3. Hybrid Retrieval with RRF

Implements **Reciprocal Rank Fusion (RRF)** from scratch to blend two retrieval signals:

- **Semantic Search** — ChromaDB vector similarity using Gemini embeddings
- **Keyword Search** — BM25 (`rank-bm25`) for precise term matching

The fused ranking consistently outperforms either signal in isolation.

### 4. Universal Document Ingestion

A unified ingestion pipeline normalizes all file types into a standard `{ text, metadata, doc_id }` format:

| Format          | Loader                                                                            |
| --------------- | --------------------------------------------------------------------------------- |
| `.txt`, `.md`   | Direct reading                                                                    |
| `.pdf`          | Page-by-page extraction via PyMuPDF; falls back to Gemini Vision for scanned PDFs |
| `.csv`, `.xlsx` | Pandas row-to-text conversion with header context                                 |
| `.html`         | BeautifulSoup4 structural extraction                                              |
| `.docx`         | `python-docx` heading and paragraph extraction                                    |
| Images          | Gemini Vision LLM for diagrams, charts, and embedded text                         |

### 5. Live Pipeline Trace Panel

The frontend's unique two-column layout includes a **real-time Pipeline Trace panel** powered by Server-Sent Events (SSE):

- Displays each backend step as it executes (routing → retrieving → evaluating → generating)
- Shows execution time in milliseconds per step
- Gives full visibility into what the system is doing behind the scenes

### 6. Conversation Memory

Session-based memory with JSON file persistence and a **token budget strategy**:

- Retains the most relevant recent interactions within a configurable token window
- Gracefully discards older context without crashing
- All history is passed to the Query Rewriter and final response generator

### 7. Pipeline Observability with SQLite

Every step of every pipeline run is written to a **normalized SQLite database** in real time. This creates a full audit trail across three linked tables — sessions, pipeline runs, and individual step logs — enabling latency analysis, debugging, and replay of any past query.

### 8. Modular Architecture

- **Isolated Prompts**: All LLM system prompts live in `/prompts`, decoupled from application code — change behavior without touching logic
- **Strategy Pattern**: Document loaders use a dispatch dictionary, eliminating `if/elif` chains and making it trivial to add new file types

---

## 🛠️ Technology Stack

### Backend

| Layer               | Technology                                     |
| ------------------- | ---------------------------------------------- |
| Language            | Python 3.9+                                    |
| Framework           | FastAPI (async, high-performance)              |
| Vector Database     | ChromaDB                                       |
| Relational Database | SQLite (pipeline step logging & observability) |
| Keyword Search      | BM25 via `rank-bm25`                           |

### AI & LLMs

| Role                | Provider                       |
| ------------------- | ------------------------------ |
| Primary inference   | Groq (LLaMA 3.3)               |
| Embeddings & Vision | Google Gemini (`google-genai`) |
| Fallback            | OpenAI, Anthropic              |

### Frontend

| Layer      | Technology           |
| ---------- | -------------------- |
| Framework  | React 18+            |
| Styling    | Tailwind CSS 3.0+    |
| Build Tool | Vite with TypeScript |

### Document Processing

| Format      | Library                |
| ----------- | ---------------------- |
| PDF         | PyMuPDF (`pymupdf`)    |
| Excel / CSV | Pandas + OpenPyXL      |
| HTML        | BeautifulSoup4         |
| Word        | `python-docx`          |
| Images      | Pillow + Gemini Vision |

---

## ⚡ Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- API keys for Groq and Google Gemini (minimum); OpenAI/Anthropic optional

### Backend Setup

```bash
# Clone the repository
cd advanced-rag-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start the API server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`, with the API running at `http://localhost:8000`.

### Environment Variables

```env
# Required
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_gemini_api_key

# Optional fallbacks
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Configuration
MAX_RETRIES=3
CHROMA_PERSIST_DIR=./chroma_db
MEMORY_TOKEN_BUDGET=4000
```

---

## 🔬 Pipeline Deep Dive

### Query Rewriter (LLM Call 1)

Takes the raw user message and conversation history, outputs a self-contained search query stripped of pronouns and references to previous turns. This ensures ChromaDB receives a query that makes sense in isolation.

### Orchestrator (LLM Call 2)

A lightweight routing LLM that classifies the rewritten query:

- **Needs RAG** → triggers document retrieval
- **Direct answer** → skips retrieval (e.g., greetings, simple factual questions the model can answer without context)

### RRF Hybrid Retrieval

```
Semantic score (ChromaDB)  ──┐
                              ├──► RRF Fusion ──► Unified ranked list
Keyword score (BM25)       ──┘
```

RRF formula: `score(d) = Σ 1 / (k + rank(d))` where `k=60`

### Relevance Evaluator (LLM Call 3)

Evaluates retrieved documents against both the original and rewritten query, returning a structured verdict:

- **Sufficient** → proceed to response generation
- **Insufficient + feedback** → trigger retry loop with improvement hints

---

## 🗄 Pipeline Observability & SQLite Logging

Every pipeline execution is persisted to a local **SQLite database** (`pipeline_logs.db`) using a normalized three-table schema. This gives you a full, queryable audit trail of every query the system has ever processed — including latency per step, retry counts, routing decisions, and final outcomes.

### Schema

```
sessions
├── session_id       TEXT  PRIMARY KEY
├── created_at       TEXT
└── metadata         TEXT  (JSON)

pipeline_runs
├── run_id           TEXT  PRIMARY KEY
├── session_id       TEXT  → sessions.session_id
├── original_query   TEXT
├── rewritten_query  TEXT
├── routed_to_rag    INTEGER  (0 / 1)
├── retry_count      INTEGER
├── final_outcome    TEXT  ('grounded_response' | 'direct_response' | 'safe_response')
├── total_duration_ms INTEGER
└── created_at       TEXT

pipeline_steps
├── step_id          INTEGER  PRIMARY KEY AUTOINCREMENT
├── run_id           TEXT  → pipeline_runs.run_id
├── step_name        TEXT  ('query_rewriter' | 'orchestrator' | 'retrieval' |
│                           'rrf_rerank' | 'relevance_evaluator' | 'response_generator')
├── step_order       INTEGER
├── status           TEXT  ('success' | 'skipped' | 'retry' | 'failed')
├── duration_ms      INTEGER
├── input_summary    TEXT  (JSON — truncated snapshot of step input)
├── output_summary   TEXT  (JSON — truncated snapshot of step output)
└── created_at       TEXT
```

### What Gets Logged

Each pipeline step writes a row to `pipeline_steps` the moment it completes, with the step's input and output captured as normalized JSON snapshots. This means you can reconstruct exactly what happened at any point in any pipeline run:

| Step                | Logged Input                          | Logged Output                       |
| ------------------- | ------------------------------------- | ----------------------------------- |
| Query Rewriter      | Original query + conversation history | Rewritten query                     |
| Orchestrator        | Rewritten query                       | Routing decision (`rag` / `direct`) |
| Retrieval           | Rewritten query                       | Top-N document IDs + scores         |
| RRF Re-rank         | Semantic + BM25 ranked lists          | Fused ranked list                   |
| Relevance Evaluator | Query + retrieved doc summaries       | Verdict + feedback string           |
| Response Generator  | Full context bundle                   | Final response text                 |

### Example Queries

```sql
-- Average latency per pipeline step across all runs
SELECT step_name, AVG(duration_ms) AS avg_ms
FROM pipeline_steps
GROUP BY step_name
ORDER BY avg_ms DESC;

-- All runs that triggered a retry
SELECT run_id, original_query, retry_count, final_outcome
FROM pipeline_runs
WHERE retry_count > 0;

-- Full step-by-step trace for a specific run
SELECT step_order, step_name, status, duration_ms, output_summary
FROM pipeline_steps
WHERE run_id = 'your-run-id'
ORDER BY step_order;

-- Sessions with the highest average total pipeline duration
SELECT s.session_id, AVG(p.total_duration_ms) AS avg_duration
FROM sessions s
JOIN pipeline_runs p ON s.session_id = p.session_id
GROUP BY s.session_id
ORDER BY avg_duration DESC;
```

### Environment Variable

```env
SQLITE_DB_PATH=./pipeline_logs.db
```

---

## 📂 Document Ingestion

Upload documents to populate the knowledge base via the `/ingest` endpoint:

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@document.pdf"
```

Supported formats: `.pdf`, `.txt`, `.md`, `.csv`, `.xlsx`, `.html`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.webp`

All documents are chunked, embedded via Gemini, and stored in ChromaDB. BM25 indices are rebuilt automatically after ingestion.

---

## 🖥 Frontend

The React frontend features a **two-column layout**:

```
┌─────────────────────┬──────────────────────┐
│                     │   Pipeline Trace      │
│   Chat Interface    │                       │
│                     │  ✓ Query rewritten    │
│  User: ...          │  ✓ Routed to RAG      │
│  Assistant: ...     │  ✓ Retrieved 5 docs   │
│                     │  ✓ Evaluated: pass    │
│  [Input box]        │  ✓ Response generated │
│                     │    Total: 1,243ms     │
└─────────────────────┴──────────────────────┘
```

Pipeline trace steps update in real time via SSE as the backend processes each stage.

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with async support
pytest --asyncio-mode=auto

# Run specific test file
pytest tests/test_retrieval.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

Tests use `pytest`, `pytest-asyncio`, and `httpx` for async API testing.

---

## 📁 Project Structure

```
advanced-rag-chatbot/
├── main.py                  # FastAPI app entry point
├── prompts/                 # All LLM system prompts (externalized)
│   ├── query_rewriter.txt
│   ├── orchestrator.txt
│   ├── relevance_evaluator.txt
│   └── response_generator.txt
├── loaders/                 # Document loaders (strategy pattern)
│   ├── pdf_loader.py
│   ├── csv_loader.py
│   ├── html_loader.py
│   └── image_loader.py
├── retrieval/               # Hybrid search & RRF
│   ├── chroma_search.py
│   ├── bm25_search.py
│   └── rrf.py
├── memory/                  # Conversation memory management
│   └── session_store.py
├── observability/           # SQLite pipeline logging
│   ├── db.py                # Schema init & connection management
│   ├── logger.py            # Step logging helpers
│   └── pipeline_logs.db     # Auto-created SQLite database
├── tests/                   # pytest test suite
├── frontend/                # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   └── PipelineTrace.tsx
│   │   └── App.tsx
│   └── package.json
├── requirements.txt
├── .env.example
└── README.md
```

---

<div align="center">

Built with care to prioritize **accuracy over speed** and **transparency over black-box magic**.

</div>
