# CKO - PatientIQ

## Team Name: Latent Potential
## App Name: PatientIQ
## One Liner: 
PatientIQ centralizes patient data and minimizes a doctor’s cognitive load by making intelligent micro decisions, freeing up more space for the life saving ones made by the experts.

## Abstract:
Doctors today face countless daily micro decisions, many of which are administrative and pull focus away from life saving care. PatientIQ centralizes key patient information and uses agents to handle routine administrative tasks, giving clinicians more time to focus on analysis and delivery of patient care. Centralizing patient data, real time signals, and agent-driven workflows on Couchbase AI Services’ secure, HIPAA-compliant unified data platform allows the application to support real time insights, automation, and enterprise-grade security from a single system.

## Setup
 This repo contains:
 
 - `backend/`: a FastAPI service
 - `frontend/`: a Vite + React + TypeScript UI
 - `prompts/` and `tools/`: content that can be indexed/published to the Agent Catalog via `agentc`
 
 ### Prerequisites
 - Python `>=3.11,<3.14`
 - Node.js (recommended: current LTS)
 - `uv` for Python dependency management
 
 ### Environment
 This repo expects environment variables for Couchbase/Capella + Agent Catalog.
 
 - Copy `.env.example` to `.env`
 - Fill in the values locally
 
 `*.env` files and secrets should not be committed.
 
 ### Backend (FastAPI)
 
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
 
 ### Frontend (Vite)
 
 Frontend dependencies are managed with `npm` in `frontend/`.
 
 ```sh
 cd frontend
 npm install
 npm run dev
 ```
 
 The dev server defaults to port `8080`. If that port is already in use, Vite will pick the next available port and print it.
 
 ### Agent Catalog (agentc)
 
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
 - Embeddings model used for prompts/tools: https://huggingface.co/microsoft/MiniLM-L12-H384-uncased
 
 ### Cluster Configuration
 Cluster used for testing (high level):
 - AWS US East
 - Couchbase Server `8.0`
 - 5 nodes total
 - Data service group: 3 nodes
 - Index/Query/Search/Eventing group: 2 nodes

### Database Schema
ckodb/                                    # Main bucket
  ├── People/                             # Scope
  │   ├── Patient/                        # Collection - Patient data
  │   └── Doctor/                         # Collection - Doctor data
  ├── Research/                           # Scope
  │   └── pubmed/                         # Collection - Research summaries
  ├── Wearables/                          # Scope
  │   ├── Watch/                          # Collection - Wearable alerts
  │   └── Phone/                          # Collection - Phone data
  ├── Notes/                              # Scope
  │   ├── Patient/                        # Collection - Patient notes
  │   └── Doctor/                         # Collection - Doctor notes
  └── Questionnaires/                     # Scope (collection names TBD)

 ## Cluster Cost Estimate
 **Window**

 - **Feb 8–12**
 - **Feb 12:** cluster destroyed
 
 **Assumptions used in this estimate**
 
 - **Weekdays (Mon–Fri):** 9am–noon (3 hours/day)
 - **Weekend:** Sat/Sun off
 - **Rate (on):** 2.77
 - **Rate (off):** 0.16
 
 **Weekly estimate**
 
 | Category | Calculation | Weekly hours | Cost |
 | --- | --- | ---: | ---: |
 | On time | 3 hours/day × 5 days | 15 | $41.55 |
 | Off time | (21 hours × 5 days) + (24 hours × 2 days) | 153 | $24.48 |
 | **Total** |  |  | **$66.03** |
 
 **Projected total (3–4 weeks):** $198.09

## AI Services Testing
Doc for what is available from Adam Clevy: https://docs.google.com/document/d/1rONaLuQQc4ik3zZ4VQsSFkNfgqHGP7UVwAaqlLI2TMw/edit?tab=t.0