# PatientIQ - Agentic Patient 360

## Team Name: Latent Potential
## App Name: PatientIQ
## One Liner:
PatientIQ centralizes patient data and minimizes a doctor's cognitive load by making intelligent micro decisions, freeing up more space for the life saving ones made by the experts.

## Abstract:
Doctors today face countless daily micro decisions, many of which are administrative and pull focus away from life saving care. PatientIQ centralizes key patient information and uses AI agents to handle routine information retrieval, giving clinicians more time to focus on analysis and delivery of patient care. Using **Couchbase AI Services with vector search**, the application provides semantic search over medical research and clinical notes, enabling doctors to quickly find relevant information through natural language queries.

## Agentc
See: `/agents/AGENTS.md` for the agent inventory, workflows, and the Couchbase-backed tool architecture.

`agentc` is used in this repo to:
- Index Python tools (e.g., `agents/medical-agents/medical_tools.py`) decorated with `@agentc.catalog.tool`
- Index prompt files in `prompts/`
- Publish a local Agent Catalog snapshot for use by agents

### Setup
- **Install deps**
  - `uv sync --extra dev`
- **Initialize agentc workspace (one-time)**
  - `agentc init`
  - If you don’t have `agentc` on PATH, use: `uv run agentc init`

### Common commands
- **Index tools and prompts (run after edits)**
  - `agentc index agents/medical-agents prompts`
- **List what’s indexed**
  - `agentc ls tools`
  - `agentc ls prompts`
- **Search prompts/tools by name**
  - `agentc ls prompts | grep wearable`
- **Publish the catalog**
  - `agentc publish`

### Adding new catalog entries
- **New tool**
  - Add a function in `agents/medical-agents/medical_tools.py` with `@agentc.catalog.tool`, then re-run `agentc index agents/medical-agents`
- **New prompt**
  - Add a YAML prompt under `prompts/`, then re-run `agentc index prompts`

Agent Tracer: https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html

## Technology Stack

### Vector Search Architecture
- **Couchbase AI Services**: Embedding model with 2048-dimensional vectors
- **Hyperscale Vector Indexes**:
  - `hyperscale_pubmed_vectorized_article_vectorized` (Research)
  - `hyperscale_doctor_notes_vectorized_all_notes_vectorized` (Notes)

### Running Locally
- `make dev`
- `make stop`

### Backend (FastAPI)
- Install deps:
  - `uv sync --extra dev`
- Run API (from repo root):
  - `uvicorn backend.api:app --reload --port 8000`

### Code Quality (Ruff)
- Install dev tools:
  - `uv sync --extra dev`
- Lint:
  - `uv run ruff check .`
- Check formatting (no changes):
  - `uv run ruff format --check .`
- Apply formatting:
  - `uv run ruff format .`

 ### Cluster Configuration
 Cluster used for testing (high level):
 - AWS US East
 - Couchbase Server `8.0`
 - 5 nodes total
 - Data service group: 3 nodes
 - Index/Query/Search/Eventing group: 2 nodes
 - MultiAZ required for AI Functions to work
 - Private Networking Enabled for Workflows, Embedding Model to Work

### Database Schema

Configured via environment variables:
- `COUCHBASE_BUCKET` (defaults to `Scripps`)
- `COUCHBASE_RESEARCH_BUCKET` (defaults to `Research`)

Research (bucket)
  Pubmed (scope)
    Pulmonary (collection)
    questions (collection)
    answers (collection)

Scripps (bucket)
  Notes (scope)
    Doctor (collection)
    Patient (collection)
  People (scope)
    Doctors (collection)
    Patients (collection)
  Wearables (scope)
    Patient_1 (collection)
    Patient_2 (collection)
    Patient_3 (collection)
    Patient_4 (collection)
    Patient_5 (collection)
  Questionnaires (scope)
    Patient_1 (collection)
    Patient_2 (collection)
    Patient_3 (collection)
    Patient_4 (collection)
    Patient_5 (collection)
  Messages (scope)
    Private (collection)
    Public (collection)
  Calendar
    Appointments (collection)
  

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