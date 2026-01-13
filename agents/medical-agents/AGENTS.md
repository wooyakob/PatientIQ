# PatientIQ Agents

## Medical Researcher
The Medical Research agent answers a clinician question by:
1. Looking up the patient and their condition in Couchbase
2. Retrieving relevant papers via vector search
3. Producing a concise clinical summary
4. And answering follow up questions

### Files
- `agents/medical-agents/research_agent_catalog.py`
- `agents/medical-agents/medical_tools.py`

### Setup
Configure `.env` (see `.env.example`). Common variables used by the agent/tools:
   - `CB_CONN_STRING`, `CB_USERNAME`, `CB_PASSWORD`, `CB_CERTIFICATE`
   - `EMBEDDING_MODEL_ENDPOINT`, `EMBEDDING_MODEL_TOKEN`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_MODEL_DIMENSIONS`

Index catalog entries (run after tool/prompt changes):
   - `agentc init`
   - `agentc index tools prompts`

### Tracing
Agent Tracer: https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html

