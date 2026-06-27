git config user.email "rayyanfaisal475207@github.com"
git config user.name "Rayyan Faisal"

git add .gitignore context.md project_audit.md RAG.pdf
git commit -m "docs: Add project context, audit report, and specs"

git add rag_system/README.md rag_system/docs
git commit -m "docs: Add comprehensive system README and evaluation reports"

git add rag_system/requirements.txt rag_system/pytest.ini rag_system/.gitignore rag_system/.env.example
git commit -m "build: Add backend dependencies and environment templates"

git add rag_system/src/config.py rag_system/src/main.py rag_system/src/memory
git commit -m "feat(backend): Setup core configuration, entry point, and session memory"

git add rag_system/src/ingestion
git commit -m "feat(backend): Implement multi-format document ingestion pipeline"

git add rag_system/src/retrieval rag_system/data
git commit -m "feat(backend): Add retrieval logic, RRF algorithm, and vector DB setup"

git add rag_system/src/llm rag_system/src/pipeline rag_system/prompts
git commit -m "feat(backend): Integrate LLM interactions and core RAG orchestrator"

git add rag_system/tests rag_system/test_chat_api.py
git commit -m "test: Add unit and integration evaluation suite"

git add rag_system/generate_dataset.py rag_system/generate_media.py
git commit -m "chore: Add dataset and media generation utilities"

git add rag_system/frontend
git commit -m "feat(frontend): Initialize React application with live pipeline trace"

git add .
git commit -m "chore: Add remaining project files"
