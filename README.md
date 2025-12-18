# CKO
 
 This repo contains:
 
 - `backend/`: a FastAPI service
 - `frontend/`: a Vite + React + TypeScript UI
 - `prompts/` and `tools/`: content that can be indexed/published to the Agent Catalog via `agentc`
 
 ## Prerequisites
 
 - Python `>=3.11,<3.14`
 - Node.js (recommended: current LTS)
 - `uv` for Python dependency management
 
 ## Environment setup
 
 This repo expects environment variables for Couchbase/Capella + Agent Catalog.
 
 - Copy `.env.example` to `.env`
 - Fill in the values locally
 
 `*.env` files and secrets should not be committed.
 
 ## Backend (FastAPI)
 
 Python dependencies are managed with `uv` via `pyproject.toml` and `uv.lock`.
 
 ```sh
 uv sync --extra dev
 ```
 
 Run the API (from repo root):
 
 ```sh
 uvicorn backend.api:app --reload --port 8000
 ```
 
 Verify:
 
 - `http://127.0.0.1:8000/health`
 - `http://127.0.0.1:8000/docs`
 
 ## Frontend (Vite)
 
 Frontend dependencies are managed with `npm` in `frontend/`.
 
 ```sh
 cd frontend
 npm install
 npm run dev
 ```
 
 The dev server defaults to port `8080`. If that port is already in use, Vite will pick the next available port and print it.
 
 ## Agent Catalog (agentc)
 
 `agentc` is installed as part of the backend Python dependencies.
 
 The Agent Catalog connection values are configured via `.env` (see `.env.example` for required variables).
 
 Index tools:
 
 ```sh
 uv run agentc index tools --tools --no-prompts
 ```
 
 Index prompts:
 
 ```sh
 uv run agentc index prompts --prompts --no-tools
 ```
 
 Publish to the catalog bucket:
 
 ```sh
 uv run agentc publish --bucket agent-catalog
 ```
 
 Notes:
 
 - If you change Python dependencies, prefer `uv add <pkg>` (it updates `pyproject.toml` and `uv.lock`).
 - If you change prompt/tool content, re-run the `agentc index ...` commands before `publish`.
 
 ## Challenge / cluster notes
 
 Cluster used for testing (high level):
 
 - AWS US East
 - Couchbase Server `8.0`
 - 5 nodes total
 - Data service group: 3 nodes
 - Index/Query/Search/Eventing group: 2 nodes
 
 Observations:
 
 - Support plan had to be switched from Basic to Dev Pro due to an unsupported configuration.
 - Workflow testing hit failure limits on the shared embedding model (reported; WIP).
 - Vectorizing structured content from S3 is limited when using a shared bucket without path-level separation (reported; WIP).
 
 Embeddings model used for prompts/tools:
 
 - https://huggingface.co/microsoft/MiniLM-L12-H384-uncased
