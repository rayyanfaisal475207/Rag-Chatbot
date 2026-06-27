# Project Audit: Advanced RAG Chatbot

This document provides a comprehensive audit of the Advanced Retrieval-Augmented Generation (RAG) Chatbot project, outlining its core features, technology stack, and distinct functionalities.

## 🛠️ Technology Stack

### Backend
- **Language**: Python 3.9+
- **Framework**: FastAPI (Async, high-performance API)
- **Vector Database**: ChromaDB (Semantic search and document storage)
- **Keyword Search**: BM25 (`rank-bm25`) for hybrid retrieval alongside ChromaDB.

### LLMs & AI Models
- **Primary Inference Engine**: Groq (Fast LLaMA 3.3 inference)
- **Embeddings & Vision**: Google Gemini (`google-genai` SDK)
- **Fallback Models**: OpenAI (`openai`), Anthropic (`anthropic`)

### Frontend
- **Framework**: React 18+
- **Styling**: Tailwind CSS 3.0+
- **Build Tool**: Vite (with TypeScript support)

### Data Processing & Document Loaders
- **PDFs**: PyMuPDF (`pymupdf`)
- **Excel/CSV**: Pandas (`pandas`) and OpenPyXL (`openpyxl`)
- **HTML**: BeautifulSoup4 (`beautifulsoup4`)
- **Word Docs**: `python-docx`
- **Images**: Pillow (`Pillow`) for resizing before Vision API calls

### Testing
- **Frameworks**: `pytest`, `pytest-asyncio`, `httpx`

---

## 🚀 Key Features and Functionalities

### 1. Multi-Step Intelligent Pipeline
Unlike basic RAG systems, this project implements a sophisticated query processing pipeline with four distinct LLM interactions:
- **Query Rewriter**: Rephrases user messages into standalone search queries using conversation history.
- **Orchestrator / Router**: Automatically decides if the query needs knowledge base retrieval or if it can be answered directly (e.g., standard greetings).
- **Relevance Evaluator**: Assesses if the retrieved documents actually answer the user's query.
- **Grounded Response Generator**: Synthesizes the final answer using strictly the retrieved contexts and cites sources.

### 2. Smart Retry Loop
If the *Relevance Evaluator* determines that retrieved documents are insufficient, the system leverages a feedback loop to improve the query and retry the retrieval process, ensuring highly accurate responses instead of hallucinating.

### 3. Advanced Retrieval with RRF
Implements **Reciprocal Rank Fusion (RRF)** from scratch to blend Semantic Search (ChromaDB) and Keyword Search (BM25) results. This hybrid approach yields superior document relevance compared to basic vector search.

### 4. Universal Document Ingestion
The system can digest numerous file formats through a **Unified Document Interface**. Regardless of the source type, it normalizes documents into a standard format (`text`, `metadata`, `doc_id`).
- **Text & Markdown**: Direct reading.
- **PDFs**: Page-by-page text extraction (falls back to Vision LLM for scanned PDFs).
- **Data (CSV/Excel)**: Converts rows to self-contained text chunks including headers.
- **HTML & Word**: Structural extraction via headings/paragraphs.
- **Images**: Uses Vision LLMs (Gemini) to extract diagrams, text, and contextual descriptions.

### 5. Live Pipeline Trace Panel (Frontend)
The frontend features a unique two-column layout:
- **Chat Interface**: For standard interactions.
- **Pipeline Trace**: Visually tracks the background RAG operations in real-time via Server-Sent Events (SSE). It reveals backend steps (e.g., routing, retrieving, evaluating) along with their execution times in milliseconds.

### 6. Conversation Memory
Session-based memory management using JSON file persistence. Incorporates a token budget strategy to retain only the most relevant recent interactions, discarding older contexts gracefully without application crashes.

### 7. Modular Architecture
- **Isolated Prompts**: All LLM prompts are stored externally (in `/prompts`) from application code, allowing for rapid tuning.
- **Strategy Pattern Routing**: Uses a clean dispatch dictionary for processing varied document loaders without convoluted `if/elif` chains.
