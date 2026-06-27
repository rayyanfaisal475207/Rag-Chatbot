git config user.email "rayyanfaisal475207@github.com"
git config user.name "Rayyan Faisal"

git add .gitignore
git commit -m "chore: Add gitignore configuration" -m "Ignore environments, node_modules, and cache files"

git add README.md
git commit -m "docs: Add project README with architecture details" -m "Detail tech stack, pipeline logic, and setup instructions"

git add context.md
git commit -m "docs: Add project context and specifications" -m "Include extensive developer instructions and design constraints"

git add project_audit.md
git commit -m "docs: Add comprehensive project audit report" -m "Provide a detailed overview of project features and capabilities"

if (Test-Path RAG.pdf) {
    git add RAG.pdf
    git commit -m "docs: Add original RAG assignment instructions"
}

git add requirements.txt
git commit -m "build: Add Python backend dependencies" -m "Specify FastAPI, ChromaDB, Pandas, and LLM SDKs"

git add .env.example
git commit -m "build: Add environment variable template" -m "Provide placeholder variables for API keys"

git add docs/
git commit -m "docs: Add detailed evaluation and prompt engineering docs"

git add prompts/
git commit -m "feat(prompts): Isolate LLM prompt templates" -m "Separate rewriter, router, evaluator, and response prompts from code"

git add src/config.py src/main.py src/__init__.py
git commit -m "feat(backend): Initialize FastAPI application and config" -m "Set up core routing and environment variable loading"

if (Test-Path src/database) {
    git add src/database/
    git commit -m "feat(database): Add SQLite logging and DB setup"
}

if (Test-Path src/memory) {
    git add src/memory/
    git commit -m "feat(memory): Implement session-based conversation memory"
}

if (Test-Path src/llm) {
    git add src/llm/
    git commit -m "feat(llm): Implement unified LLM client interface" -m "Wrap API calls for Groq, Gemini, OpenAI, and Anthropic"
}

if (Test-Path src/retrieval) {
    git add src/retrieval/
    git commit -m "feat(retrieval): Add ChromaDB vector store and RRF ranking" -m "Implement semantic search blended with BM25 keyword search"
}

if (Test-Path src/ingestion) {
    git add src/ingestion/
    git commit -m "feat(ingestion): Implement multi-format document chunking" -m "Add loaders for PDF, Excel, CSV, HTML, Word, and Images"
}

if (Test-Path src/pipeline) {
    git add src/pipeline/
    git commit -m "feat(pipeline): Build core RAG orchestrator and retry loop" -m "Wire up query rewriting, routing, evaluation, and retries"
}

if (Test-Path tests) {
    git add tests/
    git commit -m "test: Add comprehensive test suite for RAG pipeline"
}

if (Test-Path data) {
    git add data/
    git commit -m "chore: Setup data directories for ChromaDB and memory"
}

if (Test-Path frontend/package.json) {
    git add frontend/package.json frontend/package-lock.json frontend/tsconfig.* frontend/vite.config.ts frontend/tailwind.config.js frontend/postcss.config.js frontend/.gitignore frontend/.oxlintrc.json
    git commit -m "build(frontend): Initialize React Vite project configuration" -m "Set up TypeScript, Tailwind, and dependencies"
}

if (Test-Path frontend/index.html) {
    git add frontend/index.html frontend/public/
    git commit -m "feat(frontend): Add static HTML and public assets"
}

if (Test-Path frontend/src/index.css) {
    git add frontend/src/index.css frontend/src/App.css
    git commit -m "feat(frontend): Add global styles and Tailwind configuration"
}

if (Test-Path frontend/src/main.tsx) {
    git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/types/ frontend/src/lib/ frontend/src/store/
    git commit -m "feat(frontend): Setup core React app, routing, and state"
}

if (Test-Path frontend/src/components/layout) {
    git add frontend/src/components/layout/
    git commit -m "feat(frontend): Add App layout and Sidebar components"
}

if (Test-Path frontend/src/components/chat) {
    git add frontend/src/components/chat/
    git commit -m "feat(frontend): Implement Chat interface components" -m "Add ChatPanel, ChatInput, and MessageBubble"
}

if (Test-Path frontend/src/components/pipeline) {
    git add frontend/src/components/pipeline/
    git commit -m "feat(frontend): Implement Pipeline Trace visualization" -m "Add live step-by-step UI for backend tracing"
}

if (Test-Path frontend/src/pages) {
    git add frontend/src/pages/
    git commit -m "feat(frontend): Add application page views" -m "Add ChatPage, IngestPage, and KnowledgeBasePage"
}

if (Test-Path frontend/src/assets) {
    git add frontend/src/assets/ frontend/README.md
    git commit -m "chore(frontend): Add frontend assets and docs"
}

git add .
git commit -m "chore: Add remaining miscellaneous files"

git branch -m master main
git remote add origin https://github.com/rayyanfaisal475207/Rag-Chatbot.git
git push -u origin main -f
