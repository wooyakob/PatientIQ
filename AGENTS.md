# PatientIQ AI Agents

PatientIQ uses two specialized AI agents powered by **Couchbase AI Services** with vector search (2048-dimensional embeddings) to help doctors access and synthesize medical information.

---

## 1. Medical Researcher Agent

**Purpose**: Find and summarize relevant medical research for patient conditions.

### Configuration
- **Prompt**: `prompts/medical_researcher_agent.yaml`
- **Tool**: `fetch_research_articles` (in `tools/research_tools.py`)
- **Database**: `Research.Pubmed.Pulmonary` collection
- **Vector Index**: `hyperscale_pubmed_vectorized_article_vectorized`
- **Vector Field**: `article_vectorized`

### How It Works
1. Doctor provides patient condition (e.g., "Asthma", "Bronchiectasis")
2. Query is embedded into a 2048-dimensional vector using Couchbase AI Services
3. Vector search finds semantically similar research articles
4. LLM synthesizes 3 concise, evidence-based summaries
5. Results are saved and displayed on the frontend

### API Endpoints

**Generate Research Summaries**
```http
POST /api/agents/research-summarizer/run
Content-Type: application/json

{
  "patient_id": "1"
}
```

**Get Saved Research**
```http
GET /api/patients/1/research
```

### Example Query
```json
{
  "patient_id": "1"
}
```

**Response**:
```json
{
  "research_topic": "Asthma Management Recent Advances",
  "summaries": [
    "Recent studies show inhaled corticosteroids combined with long-acting beta-agonists improve control in moderate-to-severe asthma...",
    "Biologic therapies targeting IL-5 and IL-4/IL-13 pathways demonstrate significant reductions in severe exacerbations...",
    "Personalized treatment approaches based on inflammatory phenotypes optimize outcomes and reduce healthcare costs..."
  ],
  "condition": "Asthma",
  "patient_id": "1",
  "articles_analyzed": 5,
  "search_type": "vector_search"
}
```

### Use Cases
- Automatically generate research summaries when viewing patient dashboard
- Stay updated on latest treatment approaches for patient conditions
- Evidence-based decision support for treatment planning
- Quick access to relevant clinical studies

---

## 2. Doctor Notes Buddy Agent

**Purpose**: Search and answer questions about doctor notes using semantic search.

### Configuration
- **Prompt**: `prompts/doctor_notes_buddy_agent.yaml`
- **Tool**: `search_doctor_notes` (in `tools/doctor_notes_tools.py`)
- **Database**: `Scripps.Notes.Doctor` collection
- **Vector Index**: `hyperscale_doctor_notes_vectorized_all_notes_vectorized`
- **Vector Field**: `all_notes_vectorized`

### How It Works
1. Doctor asks a question (e.g., "How is the patient responding to medication?")
2. Question is embedded into a 2048-dimensional vector
3. Vector search finds semantically relevant notes across all patients (or filtered by patient)
4. LLM synthesizes an answer based on the retrieved notes
5. Response includes supporting notes with dates and context

### API Endpoints

**Search Notes (Raw Results)**
```http
POST /api/doctor-notes/search
Content-Type: application/json

{
  "query": "patient response to medication",
  "patient_id": "1",  // optional
  "limit": 5
}
```

**Answer Question (LLM-Powered)**
```http
POST /api/doctor-notes/query
Content-Type: application/json

{
  "query": "How is the patient responding to treatment?",
  "patient_id": "1"  // optional
}
```

### Example Queries

**Search Query**:
```json
{
  "query": "side effects after treatment",
  "patient_id": "1",
  "limit": 5
}
```

**Response**:
```json
{
  "query": "side effects after treatment",
  "found": true,
  "notes": [
    {
      "note_id": "note_123",
      "visit_notes": "Patient reports mild nausea after starting new medication...",
      "visit_date": "2024-01-15",
      "patient_id": "1",
      "doctor_id": "1",
      "relevance_score": 0.89
    }
  ],
  "count": 5,
  "search_type": "vector_search"
}
```

**Question with LLM Answer**:
```json
{
  "query": "How is the patient responding to the new medication?",
  "patient_id": "1"
}
```

**Response**:
```json
{
  "query": "How is the patient responding to the new medication?",
  "answer": "According to Note 1 from January 15th, the patient is responding well to the new medication with improved symptoms. Note 2 from January 22nd indicates the patient reports feeling more energetic and experiencing fewer shortness of breath episodes. However, Note 1 mentions mild nausea as a side effect.",
  "supporting_notes": [
    {
      "note_id": "note_123",
      "visit_notes": "Patient responding well to new medication...",
      "visit_date": "2024-01-15",
      "patient_id": "1",
      "relevance_score": 0.92
    },
    {
      "note_id": "note_456",
      "visit_notes": "Follow-up: Patient reports improvement...",
      "visit_date": "2024-01-22",
      "patient_id": "1",
      "relevance_score": 0.87
    }
  ],
  "notes_count": 2,
  "search_type": "vector_search"
}
```

### Use Cases
- "What symptoms improved after the intervention?"
- "Show me notes about medication changes for this patient"
- "How did the patient respond to the treatment adjustment?"
- "Find all notes mentioning side effects"
- "What progress has been noted over the last month?"
- Search across all patients: "Which patients reported fatigue?"

### Key Features
- **Semantic Search**: Finds relevant notes even with different terminology
- **Cross-Patient Search**: Search all patients or filter by specific patient
- **LLM Synthesis**: Get natural language answers with supporting evidence
- **Relevance Ranking**: Results sorted by semantic similarity score
- **Date Context**: Includes visit dates for temporal understanding

---

## Technical Architecture

### Vector Search Pipeline

Both agents use the same vector search pipeline:

```
Doctor Query
    ↓
Embedding API (Couchbase AI Services)
    ↓
2048-dimensional vector
    ↓
Hyperscale Vector Search (N1QL with SEARCH())
    ↓
Semantically ranked results
    ↓
LLM Processing (OpenAI GPT-4)
    ↓
Natural language response
```

### Embedding Configuration

Both agents share the same embedding model:
```bash
EMBEDDING_MODEL_ENDPOINT=https://...ai.cloud.couchbase.com
EMBEDDING_MODEL_ID=363a064f-...
EMBEDDING_MODEL_DIMENSIONS=2048
EMBEDDING_MODEL_TOKEN=cbsk-v1-...
```

### Database Collections

**Research Database**:
```
Research (bucket)
  └─ Pubmed (scope)
      └─ Pulmonary (collection)
          └─ article_vectorized: [float×2048]
```

**Doctor Notes Database**:
```
Scripps (bucket)
  └─ Notes (scope)
      └─ Doctor (collection)
          └─ all_notes_vectorized: [float×2048]
```

---

## Frontend Integration

### Medical Research Tab
```javascript
// Auto-load research when viewing patient
const response = await fetch('/api/agents/research-summarizer/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ patient_id: '1' })
});

const research = await response.json();
// Display research.summaries in the UI
```

### Doctor Notes Search Tab
```javascript
// Search notes
const searchResponse = await fetch('/api/doctor-notes/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: userQuery,
    patient_id: selectedPatientId,
    limit: 10
  })
});

// Or get LLM-powered answer
const answerResponse = await fetch('/api/doctor-notes/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "How is the patient responding to treatment?",
    patient_id: "1"
  })
});

const answer = await answerResponse.json();
// Display answer.answer and answer.supporting_notes
```

---

## Performance Considerations

- **Vector Search Speed**: Hyperscale indexes provide sub-second search times
- **Embedding Latency**: ~200-500ms per query embedding
- **LLM Processing**: ~2-4 seconds for synthesis
- **Caching**: Research summaries are cached in the database
- **Concurrent Searches**: Both agents can run in parallel

---

## Future Enhancements

- Add more specialized indexes for different medical domains
- Implement hybrid search (vector + keyword)
- Add temporal filtering (recent notes only)
- Support multi-language embedding models
- Real-time note indexing as doctors write
