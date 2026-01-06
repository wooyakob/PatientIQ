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
 
 ## Cluster Configuration
 
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

 ### Cluster Cost Estimate
 
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

### AI Services Testing
Doc for what is available from Adam Clevy: https://docs.google.com/document/d/1rONaLuQQc4ik3zZ4VQsSFkNfgqHGP7UVwAaqlLI2TMw/edit?tab=t.0

Solutions Engineers have restricted access, cloud architecture team is in control.

#### Using S3 as a source of data. 
Have noted limitations e.g. 
"I'd also add that for vectorizing structured data from S3, if we're not able to specify a folder/bucket and all SEs are using this one bucket then it'll vectorize all JSON (if specified) uploaded here. Not sure how we'd separate the data we're using without being able to specify a folder/file path."
Can vectorize but it will vectorize all data. 
Do not use for now.

#### AI Functions
Mask sensitive data - patient, doctor notes (name of patient).
Sentiment analysis - general sentiment of patient from their notes.
Summarize research for medical research summary.
Classify content, Extract entities - pulling out condition "cancer", december - date.
Correct grammar, spelling for doctor, patient notes - avoid doctor's handwriting scrawl, untidy notes.

Can use OpenAI model or Bedrock model, nova.
Neither work currently as not able to detect an operational cluster.
Have to raise this issue too, perhaps it is meant to be this way as testing has stopped.

#### Workflows
S3
structured (JSON)
unstructured 
to vectorize, neither work due to S3 bucket restrictions.

data from capella
research papers stored in Capella
testing workflow
using predeployed embedding model
nvidia/llama-3.2-nv-embedqa-1b-v2
129 documents
Workflow failed, no failure report or error message.
No detail in monitoring for failed workflow.

#### Models
Not able to deploy models.
We have an embedding model available.
No LLM is available, may be able to use Bedrock.
But will require API, not in same VPC.

#### Agent Catalog
Agentc initialized in this project.
Tools are stored and versioned in Tools Hub.
Prompts are stored and versioned in Prompt Hub.
No traces in Agent Tracer as agent not in use yet. Still have to test traces.

#### Private Endpoints
Between capella and AWS model for example.

Private endpoint secures traffic between a virtual private cloud (VPC) and AWS services
Not able to update this, insufficient permissions.