# Agentic Healthcare Application

## Dev environment tips
- Use `uv` for Python dependencies (see `pyproject.toml` + `uv.lock`). Prefer `uv add <pkg>` for dependency changes.
- Frontend lives in `frontend/` and uses `npm`.
- Copy `.env.example` to `.env` and fill values locally. Never commit `.env` or secrets.
- The Vite dev server runs on port `8080` and proxies `/api` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`).
- Backend CORS is configured for common Vite ports (see `backend/api.py`). If you change ports, update CORS + Vite proxy together.

## Local run (backend + frontend)

### Backend (FastAPI)
- Install deps:
  - `uv sync --extra dev`
- Run API (from repo root):
  - `uvicorn backend.api:app --reload --port 8000`
- Verify:
  - `http://127.0.0.1:8000/health`
  - `http://127.0.0.1:8000/docs`

### Frontend (Vite + React)
- From `frontend/`:
  - `npm install`
  - `npm run dev`

## Testing / linting instructions

### Backend
- Lint:
  - `uv run ruff check .`
  - `uv run flake8`
- Formatting (if needed):
  - `uv run ruff format .`

### Frontend
- Lint:
  - `npm run lint` (from `frontend/`)
- Build (catches TS/Vite issues):
  - `npm run build` (from `frontend/`)

## Agent Catalog (agentc) workflow
- Index tools:
  - `uv run agentc index tools --tools --no-prompts`
- Index prompts:
  - `uv run agentc index prompts --prompts --no-tools`
- Publish:
  - `uv run agentc publish --bucket agent-catalog`

## Repo map (where to change what)
- **Backend API entrypoint**: `backend/api.py`
- **Agent orchestrator (LLM + prompt loading)**: `backend/agents_agentc.py`
- **DB access layer (Capella/Couchbase scopes + collections)**: `backend/database.py`
- **Prompts**: `prompts/*.yaml`
- **Tools used by prompts**: `tools/*.py`
- **Frontend app**: `frontend/src/App.tsx` and `frontend/src/components/*`

## PR instructions
- Keep changes scoped: don’t refactor unrelated files.
- Before committing:
  - Backend: `uv run ruff check .` (and fix)
  - Frontend: `npm run lint` + `npm run build`
- Do not include secrets, tokens, or cluster connection details in commits.

---

## Mission
Doctors do not have time to make every single decision, especially the small, non-critical decisions. Agents can handle many of these micro decisions for them, intelligently, to ensure that doctors have the information they need to be at their best and make life-saving decisions without burning out.

## System Overview
This application uses four specialized AI agents powered by LangGraph and agentc (Agent Catalog) to provide intelligent, automated support for healthcare professionals. Each agent has specific responsibilities and outputs structured data to the Couchbase Capella database.

---

## Agent 1: Wearable Data Monitoring and Alerting Agent

### Purpose
Continuously monitor patient wearable device data (heart rate, step count) and proactively alert physicians when concerning patterns emerge that may require medical attention.

### Responsibilities
1. **Data Analysis**
   - Analyze 7-day trends in heart rate and step count data
   - Calculate statistical metrics (average, min, max, standard deviation)
   - Compare current readings against patient baseline and age-appropriate norms
   - Identify sudden changes, anomalies, or concerning trends

2. **Clinical Context**
   - Consider patient's medical condition (e.g., cancer, diabetes, hypertension, anxiety)
   - Factor in patient age and gender
   - Account for expected variations based on diagnosis
   - Understand medication effects on vital signs

3. **Alert Generation**
   - Generate alerts ONLY when medical attention is warranted
   - Assign severity levels:
     - **Critical**: Requires immediate attention (e.g., heart rate >130 sustained, <50 sustained)
     - **High**: Should be reviewed within 24 hours
     - **Medium**: Review at next appointment
     - **Low**: For information/trending only
   - Include specific metrics that triggered the alert
   - Provide clear, actionable message for the physician

4. **Pattern Recognition**
   - Detect declining activity trends (e.g., steps decreasing over days)
   - Identify irregular heart rate patterns
   - Flag sudden changes from baseline

### Input
- `patient_id`: Patient identifier
- `patient_data`: Object containing:
  - Demographics (name, age, gender)
  - Medical condition
  - `wearable_data`:
    - `heart_rate`: Array of readings (bpm)
    - `step_count`: Array of readings (steps)

### Output
 Required fields when an alert is generated:
 - `id`: string (uuid)
 - `patient_id`: string
 - `alert_type`: string
 - `severity`: `low` | `medium` | `high` | `critical`
 - `message`: string
 - `metrics`: object containing `heart_rate` (array) and `step_count` (array)
 - `timestamp`: ISO-8601 string

### Guidelines
- **Be Conservative**: Only alert when truly necessary to avoid alert fatigue
- **Be Specific**: Always cite exact numbers and trends
- **Be Contextual**: Consider the patient's condition in your assessment
- **Be Actionable**: Give physicians clear next steps

---

## Agent 2: Medical Research and Summarization Agent

### Purpose
Automatically generate concise, evidence-based medical research summaries relevant to each patient's condition, providing physicians with the latest clinical insights without requiring manual research.

### Responsibilities
1. **Research Topic Identification**
   - Analyze patient's primary condition
   - Identify the most clinically relevant research area
   - Focus on actionable treatment advances and best practices
   - Generate a concise topic title (max 10 words)

2. **Summary Generation**
   - Create exactly 3 research summaries per patient
   - Each summary should be 2-3 sentences
   - Focus on research from the last 2-3 years
   - Prioritize Level 1 evidence (RCTs, meta-analyses, systematic reviews)
   - Include specific outcomes or statistics when relevant

3. **Clinical Relevance**
   - Cover different aspects of the condition:
     - Treatment advances/new therapies
     - Clinical trial results
     - Best practices for management
   - Make summaries actionable for clinical decision-making
   - Use physician-appropriate language (clinical, not patient-facing)

4. **Content Quality**
   - Be factual and evidence-based
   - Avoid speculation or unproven treatments
   - Cite specific interventions or approaches
   - Mention key outcomes (e.g., "reduced hospitalizations by 30%")

### Input
- `patient_id`: Patient identifier
- `patient_data`: Object containing:
  - Patient name
  - Age
  - Primary medical condition
  - Current treatment status (if available)

### Output
 Required fields:
 - `patient_id`: string
 - `condition`: string
 - `topic`: string
 - `summaries`: array of 3 strings
 - `sources`: array (optional)
 - `generated_at`: ISO-8601 string

### Guidelines
- **Be Current**: Focus on 2022-2024 research
- **Be Specific**: Include drug names, trial names, specific percentages
- **Be Diverse**: Cover different aspects (treatment, monitoring, lifestyle)
- **Be Concise**: 2-3 sentences per summary, no more
- **Be Practical**: Information should be usable in clinical practice

---

## Agent 3: Message Board Routing Agent

### Purpose
Intelligently analyze facility-wide announcements and automatically route relevant information to specific staff members based on their roles, specialties, and the content's relevance, ensuring critical information reaches the right people without overwhelming everyone.

### Responsibilities
1. **Message Analysis**
   - Read and understand announcement content
   - Identify key topics, urgency, and scope
   - Determine who needs this information
   - Assess priority level

2. **Relevance Matching**
   - Match announcement content to staff roles and specialties
   - Consider department relevance
   - Identify individuals directly affected
   - Avoid unnecessary routing (reduce noise)

3. **Priority Assessment**
   - **Urgent**: Immediate action required (safety issues, critical updates)
   - **High**: Important, time-sensitive information
   - **Medium**: Relevant information, non-urgent
   - **Low**: FYI, general awareness

4. **Routing Decision**
   - List specific recipients by name/ID
   - Provide reasoning for each routing decision
   - Determine if broadcast is sufficient or if private routing needed
   - Minimize alert fatigue by being selective

### Input
- `announcement`: The message text
- `staff_directory`: Array of staff objects (each object should include at least `name` and `role`; optionally `specialties` and `department`)

### Output
 Required fields:
 - `routes`: array of route objects
 - Each route object:
   - `id`: string (uuid)
   - `original_message`: string
   - `routed_to`: array of strings
   - `priority`: `low` | `medium` | `high` | `urgent`
   - `analysis`: string
   - `timestamp`: ISO-8601 string

### Guidelines
- **Be Selective**: Only route when truly relevant to avoid information overload
- **Be Specific**: Clearly explain why each person should receive the message
- **Be Timely**: Assign appropriate priority based on urgency
- **Be Logical**: Consider workflow and responsibilities in routing decisions

---

## Agent 4: Medical Questionnaire Summarization and Intelligent Timely Delivery Agent

### Purpose
Automatically summarize patient-completed questionnaires before appointments, extracting key clinical information and highlighting concerns, enabling physicians to prepare efficiently and conduct more focused appointments.

### Responsibilities
1. **Questionnaire Analysis**
   - Review all patient responses
   - Identify clinically significant information
   - Detect changes from previous responses (if available)

2. **Summary Creation**
   - Write a concise 3-4 sentence clinical summary
   - Use physician-appropriate medical terminology
   - Focus on information affecting clinical decisions
   - Highlight symptom changes, new concerns, medication issues

3. **Key Points Extraction**
   - Identify 3-5 most important points
   - Prioritize actionable items
   - Note urgent concerns first
   - Include relevant patient-reported outcomes

### Input
- `patient_id`: Patient identifier
- `patient_data`: Patient demographics and condition
- `questionnaire_responses`: Object mapping question text to answer text
- `appointment_date`: Scheduled appointment

### Output
 Required fields:
 - `patient_id`: string
 - `appointment_date`: string
 - `summary`: string
 - `key_points`: array of 3-5 strings
 - `generated_at`: ISO-8601 string

### Guidelines
- **Be Thorough**: Don't miss important details
- **Be Concise**: Busy physicians need scannable summaries
- **Be Clinical**: Use appropriate medical language
- **Be Alert**: Flag anything requiring immediate attention
- **Be Structured**: Organize information logically
- **Be Actionable**: Help physician prepare specific discussion points

---

## Technical Implementation Notes

### Database Schema (Couchbase Capella)

All agent outputs are stored as JSON documents in Couchbase:

- **Patients**: bucket `ckodb`, scope `People`, collection `Patient` (document ID: `patient_id`)
- **Doctor notes**: bucket `ckodb`, scope `Notes`, collection `Doctor`
- **Patient notes**: bucket `ckodb`, scope `Notes`, collection `Patient`
- **Wearable alerts**: bucket `ckodb`, scope `Wearables`, collection `Watch`
- **Research summaries**: bucket `ckodb`, scope `Research`, collection `pubmed`

Current temporary storage locations:

- Message routing records are saved to `ckodb`.`Notes`.`Doctor`.
- Questionnaire summaries are saved to `ckodb`.`Notes`.`Doctor` with `document_type="questionnaire_summary"` until a dedicated `Questionnaires` scope/collection is finalized.

### Agent Integration

Agents use:
- **LangGraph**: State management and workflow orchestration
- **agentc (Agent Catalog)**: Prompt and tool versioning
- **OpenAI GPT-4**: Language model for analysis
- **Couchbase SDK**: Database operations

### Prompts and Tools

- Prompts stored in: `prompts/{agent_name}.yaml`
- Tools stored in: `tools/{category}_tools.py`
- Version controlled via Git + agentc hooks

### API Endpoints

Agents and data are exposed via FastAPI:
- `GET /health`
- `GET /api/agents/status`
- `POST /api/agents/run-now`
- `POST /api/agents/wearable-monitor/run`
- `POST /api/agents/research-summarizer/run`
- `POST /api/agents/message-router/run`
- `POST /api/agents/questionnaire-summarizer/run`
- `POST /api/agents/run-all` (runs all applicable agents)
- `GET /api/patients`
- `GET /api/patients/{patient_id}`
- `POST /api/patients`
- `GET /api/patients/{patient_id}/alerts`
- `GET /api/patients/{patient_id}/research`
- `GET /api/patients/{patient_id}/questionnaire`
- `GET /api/patients/{patient_id}/doctor-notes`
- `GET /api/patients/{patient_id}/patient-notes`

---

## Quality Standards

All agents must:
1. Provide factual, evidence-based information
2. Use appropriate medical terminology
3. Consider clinical context (patient condition, age, medications)
4. Be concise and scannable
5. Include specific metrics and details
6. Avoid unnecessary alerts (reduce fatigue)
7. Output structured JSON for database storage
8. Handle errors gracefully
9. Log decisions for transparency
10. Prioritize patient safety

