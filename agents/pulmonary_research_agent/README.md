# Pulmonary Research Agent

A medical research agent built with Couchbase Agent Catalog and LangGraph that helps doctors research pulmonary conditions and get evidence-based treatment recommendations.

## Features

- **Patient Condition Retrieval**: Fetches patient medical conditions from Couchbase
- **Semantic Search**: Uses vector search to find relevant medical research papers
- **Clinical Summaries**: Generates concise, doctor-friendly summaries from research papers
- **Observability**: Built-in tracing with Agent Tracer for monitoring and debugging
- **FastAPI Integration**: REST API endpoint for easy integration
- **CLI Interface**: Command-line tool for testing and development

## Architecture

This agent follows the standard LangGraph + Agent Catalog pattern:

```
graph.py         - Agent workflow orchestration
node.py          - Agent logic and state management
edge.py          - Routing logic between nodes
server.py        - FastAPI REST API endpoint
main.py          - CLI interface for testing
```

### External Dependencies

**Tools** (from `/tools` folder):
- `find_patient_by_id.sqlpp` - SQL++ query to fetch patient data
- `find_condition_by_patient_id.sqlpp` - SQL++ query for conditions
- `paper_search.yaml` - Vector search configuration for research papers

**Prompts** (from `/prompts` folder):
- `pulmonary_research_agent.yaml` - Agent system prompt and output schema

## Prerequisites

- Python 3.11+
- Couchbase cluster with:
  - `Scripps.People.Patients` collection (patient data)
  - `Research.Pubmed.Pulmonary` collection (research papers with embeddings)
- NVIDIA API key for embeddings
- OpenAI API key for LLM

## Setup

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Index the agent catalog**:
   ```bash
   agentc index ../../tools ../../prompts
   ```

## Usage

### CLI Interface

Run the agent interactively:

```bash
python main.py
```

You'll be prompted for:
- Patient ID (default: 1)
- Clinical question (default: treatment options)

### FastAPI Server

Start the API server:

```bash
python server.py
# or
uvicorn server:app --reload
```

Make a research request:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-123",
    "patient_id": "1",
    "question": "What are evidence-based treatment options for this patient?",
    "enable_tracing": true
  }'
```

Response:

```json
{
  "patient_id": "1",
  "patient_name": "John Doe",
  "condition": "Chronic Obstructive Pulmonary Disease (COPD)",
  "question": "What are evidence-based treatment options?",
  "papers": [
    {
      "title": "COPD Treatment Guidelines 2024",
      "author": "Smith et al.",
      "article_citation": "NEJM 2024;380:1234-1245",
      "pmc_link": "https://..."
    }
  ],
  "answer": "Based on current research...",
  "error": null
}
```

### Integration with Existing Backend

To integrate with your existing backend API (e.g., `backend/api.py`), import and use the agent:

```python
from agents.pulmonary_research_agent.graph import PulmonaryResearcher
import agentc

catalog = agentc.Catalog()
researcher = PulmonaryResearcher(catalog=catalog)

# In your endpoint:
state = PulmonaryResearcher.build_starting_state(
    patient_id=patient_id,
    question=question
)
result = researcher.invoke(input=state)
```

## How It Works

1. **User submits** patient ID and clinical question
2. **Agent retrieves** patient's pulmonary condition from Couchbase
3. **Vector search** finds relevant research papers using NVIDIA embeddings
4. **LLM generates** a 3-paragraph clinical summary from the papers
5. **Results returned** with papers, citations, and summary

## Data Flow

```
User Input (patient_id, question)
  ↓
PulmonaryResearchAgent
  ↓
find_patient_by_id (SQL++ Tool)
  ↓
paper_search (Vector Search Tool)
  ↓
OpenAI GPT-4o-mini (LLM Summarization)
  ↓
Structured Output (papers + summary)
```

## Observability

The agent includes built-in tracing with Agent Tracer. View traces in:
- `.agent-activity/` directory (local traces)
- Agent Catalog dashboard (if configured)

## Development

Run pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

Format code:

```bash
ruff format .
ruff check --fix .
```

## Configuration

Key environment variables:

```bash
# Couchbase connection
CLUSTER_CONNECTION_STRING=couchbases://...
CLUSTER_USERNAME=...
CLUSTER_PASS=...

# NVIDIA embeddings
EMBEDDING_MODEL_ENDPOINT=https://integrate.api.nvidia.com
EMBEDDING_MODEL_TOKEN=nvapi-...
EMBEDDING_MODEL_NAME=nvidia/llama-3.2-nv-embedqa-1b-v2

# OpenAI
OPENAI_API_KEY=sk-...
```

## Troubleshooting

**Agent catalog not finding tools/prompts?**
- Run `agentc index ../../tools ../../prompts` from this directory
- Verify `.agentcignore` doesn't exclude important files

**Vector search failing?**
- Check that `Research.Pubmed.Pulmonary` has vectorized embeddings
- Verify NVIDIA API key is valid
- Ensure FTS vector index exists: `hyperscale_pubmed_vectorized_article_vectorized`

**Connection errors?**
- Verify Couchbase connection string and credentials
- Check certificate path if using Capella
- Test connection with `cbc ping`

## License

PatientIQ Internal Use
