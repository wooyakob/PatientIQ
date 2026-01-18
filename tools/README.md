# Tools Directory

This directory contains all tools used by agents in the application. Each tool is a separate file following Agent Catalog best practices.

## Tool Types

### 1. SQL++ Tools (*.sqlpp)

Direct database queries for simple data retrieval:

- `find_patient_by_id.sqlpp` - Get patient record by ID
- `appointments_by_patient_id_date_range.sqlpp` - Get patient appointments
- `docnotes_by_patient_id_date_range.sqlpp` - Get doctor notes for date range
- `docnotes_latest_by_patient_id.sqlpp` - Get most recent doctor note
- And many more...

### 2. Semantic Search Tools (*.yaml)

Vector search configurations for AI-powered search:

- `paper_search_semantic.yaml` - Base semantic search for medical papers
- `doc_notes_search_semantic.yaml` - Semantic search for doctor notes

### 3. Python Function Tools (*.py)

Complex business logic tools with custom processing:

- `find_conditions_by_patient_id.py` - Get patient conditions formatted as string
- `paper_search.py` - Search papers with patient context and fallbacks

### 4. Shared Utilities (_shared.py)

Common code shared across Python tools (not indexed as a tool itself):

- Database connection pooling
- NVIDIA embedding generation
- Helper functions

## Tool Naming Convention

**One tool = One file**

- Each tool must be in its own file
- Tool name should match the main function/query name
- Avoid duplicates - if SQL++ exists, don't create Python wrapper unless it adds value

## Current Tools for Pulmonary Research Agent

The pulmonary research agent uses these three tools (defined in `/prompts/pulmonary_research_agent.yaml`):

1. **find_patient_by_id** (SQL++)
   - File: `find_patient_by_id.sqlpp`
   - Returns full patient record

2. **find_conditions_by_patient_id** (Python)
   - File: `find_conditions_by_patient_id.py`
   - Returns formatted condition string
   - Adds business logic over raw SQL query

3. **paper_search** (Python)
   - File: `paper_search.py`
   - Searches medical papers with patient context
   - Uses NVIDIA embeddings and vector search
   - Handles fallbacks and error cases

## Adding New Tools

### SQL++ Tool

Create a new `.sqlpp` file:

```sql
/*
name: tool_name

description: >
    What this tool does

input: >
    {
      "type": "object",
      "properties": {
        "param": { "type": "string" }
      }
    }

secrets:
    - couchbase:
        conn_string: CLUSTER_CONNECTION_STRING
        username: CLUSTER_USERNAME
        password: CLUSTER_PASS
*/

SELECT ...
FROM ...
WHERE ...;
```

### Python Function Tool

Create a new `.py` file:

```python
"""
Tool description
"""

import agentc
from _shared import cluster  # For database access

@agentc.catalog.tool
def tool_name(param: str) -> dict:
    """
    Docstring describing the tool for LLMs.

    Args:
        param: Description

    Returns:
        Description of return value
    """
    # Implementation
    return result
```

### Semantic Search Tool

Create a new `.yaml` file:

```yaml
record_kind: semantic_search

name: tool_name

description: >
    What this searches for

input: >
   {
     "type": "object",
     "properties": {
       "query": { "type": "string" },
       "top_k": { "type": "integer", "default": 3 }
     },
     "required": ["query"]
   }

secrets:
  - couchbase:
      conn_string: CLUSTER_CONNECTION_STRING
      username: CLUSTER_USERNAME
      password: CLUSTER_PASS
  - embedding:
      auth: EMBEDDING_MODEL_TOKEN

vector_search:
  bucket: BucketName
  scope: ScopeName
  collection: CollectionName
  index: vector_index_name
  vector_field: field_with_embeddings
  text_field: output_field_name
  embedding_model:
    name: EMBEDDING_MODEL_NAME
    base_url: EMBEDDING_MODEL_ENDPOINT
  num_candidates: 3
```

## Indexing

After adding or modifying tools, re-index the catalog:

```bash
make index-catalog
# or
agentc index tools prompts
```

## Tool Dependencies

Tools can use shared code from `_shared.py` but should NOT import other tools directly. The Agent Catalog handles tool dependencies at runtime.

**❌ Don't do this:**
```python
from find_patient_by_id import find_patient_by_id
```

**✅ Do this instead:**
```python
# Query database directly or let the agent compose tools
query = cluster.query(...)
```

## Verification

Check indexed tools:

```bash
agentc ls tools | grep tool_name
```

## References

- [Agent Catalog Documentation](https://docs.couchbase.com/ai/build/integrate-agent-with-catalog.html)
- [Tool Definition Guide](https://docs.couchbase.com/ai/concepts/tools.html)
