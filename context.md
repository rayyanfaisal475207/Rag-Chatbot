# RAG System — Complete Project Context

> This file is a full briefing for any AI assistant helping with this project.
> Read it entirely before answering any question. The student is learning, not
> just building — explain concepts, don't just generate code.

---

## What This Project Is

An **Advanced Retrieval-Augmented Generation (RAG) chatbot** with a production-grade
multi-step pipeline. The system accepts user questions, intelligently decides whether
to retrieve documents, retrieves and re-ranks them, evaluates their relevance, and
retries with improved queries if the first retrieval attempt fails.

This is NOT a basic RAG system. It has multiple LLM calls per query, a retry loop,
a relevance evaluator, and full conversation memory. Every component in the pipeline
has a specific role and must be understood deeply.

---

## The Core Pipeline (Read This Carefully)

The entire system follows this exact flowchart — this was provided as the project
assignment diagram:

```
User Query
    ↓
Load Conversation History        ← Application logic, not an LLM call
    ↓
Query Rewriter                   ← LLM Call 1
Rewrites the user's message as a standalone search query using conversation history
    ↓
Orchestrator (Decision)          ← LLM Call 2
Does this query require RAG?
    ├── NO  → Main LLM Call (answer directly from prompt + history)
    │              ↓
    │         Return Response to User
    │
    └── YES → Retrieve Documents (ChromaDB Vector Search) ← NOT an LLM call
                    ↓
               Re-rank Documents (RRF Algorithm)          ← NOT an LLM call
                    ↓
               Document Relevance Evaluator               ← LLM Call 3
               Are retrieved docs relevant and sufficient?
                    ├── YES → Main LLM Call
                    │         Generate grounded response using:
                    │         - Original query
                    │         - Rewritten query
                    │         - Retrieved documents
                    │         - Conversation history
                    │              ↓
                    │         Return Response to User
                    │
                    └── NO  → Retry Limit Check (application if-else logic)
                                  ├── No retries left → Safe Response
                                  │   ("Not enough relevant information was found")
                                  │
                                  └── Retries available → Increment Retry Count
                                                              ↓
                                                         Query Rewriter (LLM Call)
                                                         Improve query using evaluator feedback
                                                              ↓
                                                         Back to Retrieve Documents ↑

    ↓ (after any response path)
Save Query and Response to Conversation Memory
```

This pipeline is fixed. Do not simplify it or suggest skipping steps.

---

## Technology Stack

### Mandatory (explicitly required by the assignment)

- **ChromaDB** — vector database for document storage and semantic search
- **RRF Algorithm (Reciprocal Rank Fusion)** — re-ranking algorithm that merges
  multiple ranked result lists into one better-ranked list
- **An LLM provider** — at least 3–4 distinct LLM calls per query with different
  roles and prompts (OpenAI GPT-4 / Anthropic Claude are both acceptable)
- **Embedding model** — to convert text chunks into vectors for ChromaDB storage
  and query-time search
- **Python** — primary language for the entire backend

### Chosen / Recommended Stack

- **Backend framework:** FastAPI (async, clean, auto-generates API docs)
- **Frontend:** React + Tailwind CSS (see Frontend section below)
- **LLM:** OpenAI GPT-4o or Anthropic Claude (student's choice)
- **Embeddings:** text-embedding-3-small (OpenAI) or equivalent
- **Memory persistence:** JSON files (simple) or SQLite (production-grade)
- **Environment management:** python-dotenv for .env files

### Optional but Recommended

- LangChain or LlamaIndex (glue frameworks — student should understand what they
  do before using them, not treat them as black boxes)
- BM25 keyword search alongside ChromaDB semantic search (hybrid retrieval improves
  RRF re-ranking significantly)
- Docker + docker-compose for deployment

---

## Multi-Format Document Ingestion (Critical Feature)

The system must accept documents in **multiple formats**. This is a core requirement.
Every format must be converted to clean text before the rest of the pipeline runs.

### Supported Input Formats

1. **Plain text (.txt) and Markdown (.md)** — read directly, attach metadata
2. **PDF (.pdf)** — extract text page by page; handle both text-based PDFs and
   scanned PDFs (which require OCR or a vision LLM since they have no text layer)
3. **Excel (.xlsx, .xls) and CSV (.csv)** — convert rows to readable text strings,
   chunk by row batches (30 rows per chunk), always include column headers in every
   chunk so the text is self-contained
4. **HTML (.html, .htm)** — strip navigation, scripts, footers, and boilerplate;
   extract meaningful content using heading structure as natural section boundaries
5. **Word documents (.docx)** — extract paragraphs and tables, use heading styles
   as section boundaries (same pattern as HTML)
6. **Images (.jpg, .png, .webp, .gif)** — use a Vision LLM (e.g. GPT-4o with image
   input) to extract and describe content including charts, diagrams, tables, and
   any visible text; do NOT use only basic OCR as it fails on non-text visuals

### The Unified Document Interface (Most Important Design Principle)

Every loader, regardless of format, must return the same data structure:

```python
@dataclass
class Document:
    text: str        # extracted text content
    metadata: dict   # source file, page number, sheet name, type, etc.
    doc_id: str      # unique identifier (deterministic, filename-based)
```

After loading, every format is treated identically by the chunker, embedder,
and ChromaDB. The format-specific code ends at the loader.

### Format Router Pattern (Dispatch Table)

Use a dictionary mapping file extensions to loader functions — NOT a long if/elif
chain. This is the Strategy Pattern: adding a new format = adding one line to the
dictionary, no other code changes needed.

```python
LOADER_MAP = {
    ".txt":  load_text_file,
    ".md":   load_text_file,
    ".pdf":  load_pdf,
    ".xlsx": load_excel,
    ".csv":  load_csv,
    ".html": load_html,
    ".docx": load_docx,
    ".jpg":  load_image_with_vision,
    ".png":  load_image_with_vision,
}
```

### Key Ingestion Gotchas

- **Excel merged cells:** Use forward-fill after loading to propagate values across
  merged rows. Always include column headers in every chunk.
- **PDF scanned pages:** If text extraction returns empty or garbled text, fall back
  to the vision LLM approach used for images.
- **HTML JavaScript-rendered content:** Static HTML files from React/Angular apps
  may have empty div tags. Note this as a known limitation.
- **Image cost control:** Resize images over 2000px before sending to vision LLM.
  Cache extracted text so each image is only processed once.
- **Duplicate ingestion:** Always use ChromaDB's `upsert` not `add`. Upsert = insert
  if new, replace if exists. Prevents duplicates on re-ingestion.

---

## Architecture

### Folder Structure

```
rag_system/
│
├── src/
│   ├── main.py                      # Entry point / FastAPI app
│   │
│   ├── pipeline/
│   │   ├── orchestrator.py          # Main pipeline logic + retry loop
│   │   ├── query_rewriter.py        # LLM Call 1 + retry rewriter
│   │   ├── router.py                # LLM Call 2 — RAG needed?
│   │   └── evaluator.py             # LLM Call 3 — docs relevant?
│   │
│   ├── retrieval/
│   │   ├── vector_store.py          # ChromaDB wrapper
│   │   ├── embedder.py              # Embedding model wrapper
│   │   ├── bm25_retriever.py        # Keyword search (for RRF)
│   │   └── reranker.py              # RRF algorithm implementation
│   │
│   ├── memory/
│   │   └── conversation.py          # Load/save conversation history
│   │
│   ├── llm/
│   │   └── client.py                # Single LLM API wrapper for all calls
│   │
│   ├── ingestion/
│   │   ├── document.py              # Document dataclass
│   │   ├── loader_router.py         # Format detection + dispatch table
│   │   ├── chunker.py               # Text splitting logic
│   │   └── loaders/
│   │       ├── text_loader.py
│   │       ├── pdf_loader.py
│   │       ├── excel_loader.py
│   │       ├── html_loader.py
│   │       ├── docx_loader.py
│   │       └── image_loader.py
│   │
│   └── config.py                    # All settings, loaded from .env
│
├── data/
│   ├── documents/                   # Raw source documents to ingest
│   └── chroma_db/                   # ChromaDB persistent storage
│
├── prompts/                         # All LLM prompts as separate text files
│   ├── query_rewriter.txt
│   ├── router.txt
│   ├── evaluator.txt
│   └── final_response.txt
│
├── tests/
│   ├── test_retrieval.py
│   ├── test_pipeline.py
│   └── test_evaluator.py
│
├── .env                             # API keys — never commit
├── .env.example                     # Template with placeholder values
├── requirements.txt
├── docker-compose.yml
└── README.md
```

### Data Flow (One Full Query)

```
1. User sends: "What about the bleeding risk?"

2. Load conversation history
   → [{"role":"user","content":"Tell me about aspirin"},
      {"role":"assistant","content":"Aspirin is..."}]

3. Query Rewriter (LLM Call 1)
   Input:  history + "What about the bleeding risk?"
   Output: "What is the bleeding risk of aspirin?"

4. Router (LLM Call 2)
   Input:  "What is the bleeding risk of aspirin?"
   Output: "YES" (needs retrieval)

5. ChromaDB Vector Search
   Embed the rewritten query → search for top-10 similar chunks

6. RRF Re-ranking
   Merge semantic search results + BM25 keyword results → top-5 chunks

7. Relevance Evaluator (LLM Call 3)
   Input:  original query + rewritten query + top-5 chunks
   Output: {"relevant": true, "reason": "Documents contain specific data"}

8. Grounded LLM Response
   Input:  original + rewritten query + chunks + full history
   Output: Final answer citing the documents

9. Save to memory
   Append {user: original query, assistant: final answer} to session history

10. Return to user
```

---

## Frontend Design (React + Tailwind CSS)

### The Differentiating Feature: Live Pipeline Trace Panel

The UI must make the invisible pipeline **visible**. This is what separates this
project from a basic chatbot. The layout is a two-column design:

**Left column — Chat interface:**
- Standard chat bubbles (user right-aligned, assistant left-aligned)
- Streaming token-by-token response display
- Source citations shown below each assistant response
  (e.g. "Sources: aspirin-monograph.pdf · drug-interactions.pdf")

**Right column — Pipeline trace panel (the key differentiator):**
- Shows each pipeline step as a card: name, status, detail, timing in ms
- Steps animate through states: waiting → active (pulsing) → done (green) → skipped
- When the retry loop triggers, shows: evaluator returning false → retry counter
  incrementing → rewriter producing improved query → second retrieval attempt
- Retrieved documents list with relevance scores (e.g. "aspirin-monograph.pdf 0.91")

**Pipeline trace events (backend sends these as Server-Sent Events or WebSocket):**
```json
{"step": "query_rewriter",  "status": "done", "detail": "Rewritten: '...'",   "ms": 341}
{"step": "router",          "status": "done", "detail": "RAG required: YES",  "ms": 189}
{"step": "retrieval",       "status": "done", "detail": "8 chunks retrieved", "ms": 22}
{"step": "reranker",        "status": "done", "detail": "Top 4 selected",     "ms": 12}
{"step": "evaluator",       "status": "done", "detail": "Relevant: true",     "ms": 412}
{"step": "response",        "status": "streaming", "detail": "Generating..."}
{"step": "memory",          "status": "done", "detail": "Saved to session"}
```

### Visual Design Principles (Tailwind CSS)

The design should feel like a real product, not a student demo. Key principles:

- **Clean, minimal, professional** — think Notion or Linear, not a data science demo
- **Dark/light mode support** — use Tailwind's dark: variant throughout
- **Two-column layout** — chat takes ~60% width, pipeline panel takes ~40%
- **Step cards** have distinct visual states:
  - Waiting: gray, muted opacity
  - Active: blue border + pulsing dot indicator
  - Done: green border + checkmark
  - Error/skipped: reduced opacity
  - Retry triggered: amber/orange to draw attention
- **Typography:** Clean sans-serif, 14px body, good line height (1.6–1.7)
- **Spacing:** Generous padding inside cards (12–16px), clear visual hierarchy
- **No gradients, no heavy shadows** — flat design with subtle borders

### Pages / Views

1. **Chat page** (main view) — two-column layout described above
2. **Ingestion page** — drag-and-drop file upload accepting all supported formats,
   progress indicator per file, shows extracted chunk count after processing
3. **Knowledge base page** — list of ingested documents with metadata, option to
   delete, search within ingested files

### API Communication

- `POST /chat` — sends `{session_id, message}`, receives streamed response
  via SSE (Server-Sent Events) carrying both pipeline trace events and the
  final text response
- `POST /ingest` — multipart form upload, accepts any supported file format
- `GET /documents` — lists all ingested documents from ChromaDB metadata
- `DELETE /documents/{doc_id}` — removes a document from the knowledge base

---

## Prompt Engineering (All Four LLM Calls)

Prompts must be stored in separate files under `prompts/`, not hardcoded in Python.
This allows tuning without touching application code.

### LLM Call 1 — Query Rewriter

**Role:** Resolve pronouns and references from conversation history.
**Input:** conversation history + latest user message
**Output:** a single standalone search query string, nothing else
**Edge case:** if history is empty (first message), return the original message unchanged

```
System: You are a query rewriting assistant. Your only job is to rewrite
the user's latest message as a complete, standalone search query that
includes all context from the conversation history. 
Output ONLY the rewritten query. No explanation. No preamble. No quotes.

If there is no conversation history, return the original message unchanged.
```

### LLM Call 2 — Router / Orchestrator

**Role:** Decide if retrieval is needed.
**Input:** rewritten query
**Output:** "YES" or "NO" only
**Include few-shot examples** — this dramatically improves accuracy

```
System: You decide whether a user query requires searching a knowledge base.
Answer only "YES" or "NO".

YES if: the question asks for specific facts, data, policies, procedures,
        or information that would be in documents.
NO if:  the question is conversational, asks for opinions, is a greeting,
        asks for general knowledge not specific to any document collection,
        or is a simple calculation.

Examples:
Q: "What is the dosage for aspirin?" → YES
Q: "Tell me a joke" → NO
Q: "What are the side effects mentioned in the guidelines?" → YES  
Q: "Thanks, that helps!" → NO
```

### LLM Call 3 — Relevance Evaluator

**Role:** Judge whether retrieved documents are sufficient to answer the query.
**Input:** original query + rewritten query + retrieved document chunks
**Output:** JSON `{"relevant": true/false, "reason": "brief explanation"}`
**The reason field is passed to the retry rewriter — it must be informative**

```
System: You evaluate whether retrieved documents contain sufficient information
to answer a user's question. Be strict but fair.

Respond with JSON only:
{"relevant": true, "reason": "documents contain specific data about X"}
or
{"relevant": false, "reason": "documents discuss Y but not the specific aspect Z the user asked about"}

The reason is used to improve the search query on retry — be specific about
what information is missing.
```

### LLM Call 4 — Final Response (Grounded)

**Role:** Generate the actual answer using retrieved documents as ground truth.
**Input:** original query + rewritten query + document chunks + conversation history
**Key instruction:** cite sources, do not add information not in the documents

```
System: You are a helpful assistant. Answer the user's question based ONLY
on the provided documents. 

If the documents contain the answer, provide it clearly and cite which
document(s) support each claim.
If something is not covered in the documents, say so explicitly rather
than guessing.

Provided documents:
{documents}

Conversation history:
{history}
```

---

## Key Algorithms to Implement from Scratch

### RRF — Reciprocal Rank Fusion

Do not use a library for this. Implement it directly — it's 10 lines of Python
and understanding it manually is part of the learning.

**Formula:** For each document, RRF score = sum of `1 / (rank + k)` across all
ranked lists it appears in. k is typically 60. Documents appearing near the top
of multiple lists score highest.

**Example:**
```
Semantic search:  [Doc A, Doc B, Doc C]   ranks: A=1, B=2, C=3
BM25 keyword:     [Doc C, Doc A, Doc D]   ranks: C=1, A=2, D=3

RRF scores (k=60):
Doc A: 1/(1+60) + 1/(2+60) = 0.0164 + 0.0161 = 0.0325  ← winner
Doc C: 1/(3+60) + 1/(1+60) = 0.0159 + 0.0164 = 0.0323
Doc B: 1/(2+60)             = 0.0161
Doc D: 1/(3+60)             = 0.0159
```

### Retry Loop Logic

```python
MAX_RETRIES = 2

async def process_query(session_id, user_message):
    history = load_history(session_id)
    rewritten = rewrite_query(user_message, history)
    
    needs_rag = route_query(rewritten)
    
    if not needs_rag:
        response = generate_direct_response(user_message, history)
        save_history(session_id, user_message, response)
        return response
    
    retry_count = 0
    current_query = rewritten
    evaluator_feedback = None
    
    while retry_count <= MAX_RETRIES:
        chunks = retrieve_and_rerank(current_query)
        evaluation = evaluate_relevance(user_message, current_query, chunks)
        
        if evaluation["relevant"]:
            response = generate_grounded_response(
                user_message, current_query, chunks, history
            )
            save_history(session_id, user_message, response)
            return response
        
        if retry_count >= MAX_RETRIES:
            safe_response = "I couldn't find sufficient information to answer your question accurately."
            save_history(session_id, user_message, safe_response)
            return safe_response
        
        # Improve query using evaluator feedback before retrying
        evaluator_feedback = evaluation["reason"]
        current_query = rewrite_for_retry(
            original=user_message,
            previous_query=current_query,
            feedback=evaluator_feedback
        )
        retry_count += 1
```

---

## Conversation Memory Design

**Storage format:** JSON files per session, or SQLite table with session_id column.

**Message format (maps directly to LLM API format):**
```json
[
  {"role": "user",      "content": "Tell me about aspirin"},
  {"role": "assistant", "content": "Aspirin is a nonsteroidal..."},
  {"role": "user",      "content": "What about the side effects?"},
  {"role": "assistant", "content": "The main side effects include..."}
]
```

**Token budget management:** Keep last N turns that fit within a token budget
(e.g. 2000 tokens max for history). Older turns get dropped, not the recent ones.

**Edge cases to handle:**
- Empty history (first message in a session) — query rewriter must handle this
  without errors
- Very long sessions — truncate from the oldest end, never the newest
- Error during response — still save the user message even if assistant response failed

---

## Implementation Milestones (Do These in Order)

| # | Milestone | Key Output | Est. Time |
|---|-----------|------------|-----------|
| 1 | Environment + project structure | `python main.py` runs without errors | 2–4 hrs |
| 2 | Multi-format document ingestion | All formats load and store in ChromaDB | 2–3 days |
| 3 | Retrieval layer (vector search + RRF) | `retrieve_and_rerank(query)` works | 2–3 days |
| 4 | LLM client + prompt management | All 4 LLM call functions work independently | 1–2 days |
| 5 | Conversation memory | Load/save across sessions works correctly | 1 day |
| 6 | Full pipeline orchestration + retry loop | End-to-end query processing with retry | 3–4 days |
| 7 | FastAPI layer + SSE streaming | `/chat` endpoint streams pipeline events | 1–2 days |
| 8 | React + Tailwind frontend | Two-column UI with live pipeline trace | 3–5 days |
| 9 | Testing + evaluation report | pytest suite + quality metrics on test set | 2–3 days |
| 10 | Deployment | Live URL or working docker-compose | 1–2 days |

---

## What to Submit

### 1. GitHub Repository (Required)
- Clean folder structure as shown above
- `README.md` with: architecture diagram, design decisions section, demo GIF,
  working setup instructions
- `docs/prompt_engineering.md` explaining each prompt and why it's designed that way
- `docs/evaluation.md` with quality metrics
- `.env.example` with placeholder values (never commit real keys)
- One-command setup: `make setup && make ingest && make run`

### 2. Live Deployment (Required for standing out)
- Deployed URL (Railway / Render / Hugging Face Spaces all have free tiers)
- OR working `docker-compose up` that requires zero manual steps

### 3. Demo Video (2–3 minutes, Required)
Show these three scenarios specifically:
1. Query that goes through full RAG path (happy path)
2. Query that the router sends directly (no retrieval needed)
3. Query that **triggers the retry loop** — show: evaluator returns false →
   counter increments → improved query → second retrieval → success (or safe response)
   The retry demo is the most impressive thing in the entire project. Make it visible.

### 4. Evaluation Report
Test with 20–30 questions. Report:
- Retrieval precision (of retrieved docs, what % were actually relevant)
- Router accuracy (correct YES/NO on labeled test set)
- Answer faithfulness (does answer contradict retrieved docs?)
- Retry effectiveness (how often does retry succeed vs fall back to safe response)

### 5. "What I Would Do With More Time" Section in README
Describe 2–3 genuine improvements you didn't implement. This signals engineering
maturity and understanding of the system's current limitations.

---

## Common Bugs to Watch For

| Bug | Where | Fix |
|-----|-------|-----|
| Retry counter not resetting between user sessions | orchestrator.py | Retry state must be local to `process_query()`, not global |
| Evaluator feedback not reaching the retry rewriter | orchestrator.py | Pass `evaluation["reason"]` explicitly to `rewrite_for_retry()` |
| Memory not saved when error occurs mid-pipeline | orchestrator.py | Use try/finally to save partial state |
| ChromaDB duplicates on re-ingestion | ingestion | Use `upsert` not `add` |
| Empty history crashes query rewriter | query_rewriter.py | Check `if not history` and return original message |
| Context window exceeded on long conversations | memory/conversation.py | Truncate history to token budget before building prompt |
| PDF scanned pages returning empty text | pdf_loader.py | Detect empty extraction, fall back to vision LLM |
| Blocking event loop with synchronous LLM calls | FastAPI routes | Use `asyncio.to_thread()` or async LLM client |
| JSON parse failure from LLM evaluator output | evaluator.py | Wrap `json.loads()` in try/except, retry if malformed |

---

## Scalability and Production Notes

**For a student project:** JSON file memory, local ChromaDB, single FastAPI process
is perfectly fine.

**For production:** Replace JSON memory with PostgreSQL, ChromaDB with a managed
vector DB (Pinecone / Weaviate), add Redis for session caching, deploy FastAPI
with multiple workers (gunicorn + uvicorn).

**Security basics even for student projects:**
- Never commit API keys
- Validate all file uploads (check MIME type, not just extension)
- Limit file upload size (reject files > 50MB)
- Sanitize `session_id` input (used as a filename — path traversal risk)

---

## Teaching Philosophy for This Project

The student is learning through building, not building to submit. When helping:

1. **Always explain the concept before the code** — what is it, why does it exist,
   what problem does it solve
2. **Use analogies** — the post office sorting analogy for the ingestion pipeline,
   the detective analogy for the retry loop, the GPS coordinates analogy for embeddings
3. **Explain every line** — never dump a code block without walking through it
4. **Point out trade-offs** — every design decision has alternatives; name them
5. **Warn about the specific bugs** listed above before the student hits them
6. **Ask conceptual questions** after each explanation to verify understanding
7. **Connect new concepts to previous ones** — the retry loop connects to the
   evaluator which connects to the relevance concept which connects to embeddings
8. Never skip steps. Never assume knowledge. Teach as if the student wants to be
   able to build this entirely independently next time.

---

## Current Progress

- [x] Project fully analyzed and understood
- [x] Complete prerequisite knowledge map created
- [x] Full architecture designed
- [x] All 10 milestones defined with success checklists
- [x] Multi-format ingestion pipeline designed (all 6 formats)
- [x] Frontend design specified (React + Tailwind, two-column layout, pipeline trace)
- [x] UI mockup created showing live pipeline trace panel
- [x] Milestone 1: Environment setup — COMPLETED
- [x] Milestone 2: Document ingestion — COMPLETED
- [x] Milestone 3: Retrieval + RRF — COMPLETED
- [x] Milestone 4: LLM client — COMPLETED
- [x] Milestone 5: Conversation memory — COMPLETED
- [x] Milestone 6: Full pipeline + retry — COMPLETED
- [x] Milestone 7: FastAPI + SSE — COMPLETED
- [x] Milestone 8: React frontend — COMPLETED
- [x] Milestone 9: Testing + evaluation — COMPLETED
- [ ] Milestone 10: Deployment — NOT STARTED

---

*Generated from a full mentoring session. Resume by saying "Start Milestone 1"
or ask about any specific component.*
