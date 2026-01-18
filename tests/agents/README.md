# Agent Tests

This directory contains comprehensive test suites for the CKO healthcare agents.

## Test Files

- `test_docnotes_search_agent.py` - Tests for the Doctor Notes Search Agent
- `test_pulmonary_research_agent.py` - Tests for the Pulmonary Research Agent

## Running Tests

### Run all agent tests
```bash
python -m pytest tests/agents/ -v -s
```

### Run specific test file
```bash
# Doctor Notes Search Agent tests
python -m pytest tests/agents/test_docnotes_search_agent.py -v -s

# Pulmonary Research Agent tests
python -m pytest tests/agents/test_pulmonary_research_agent.py -v -s
```

### Run specific test class
```bash
python -m pytest tests/agents/test_docnotes_search_agent.py::TestDocNotesSearcherSearch -v -s
```

### Run specific test
```bash
python -m pytest tests/agents/test_docnotes_search_agent.py::TestDocNotesSearcherSearch::test_search_doctor_notes -v -s
```

## Test Features

Both test suites include:

- **Clear logging**: Each test logs its progress with detailed output
- **Initialization tests**: Verify Agent Catalog and agent setup
- **State building tests**: Test state creation with various parameters
- **Functional tests**: Test core search/research functionality
- **Error handling tests**: Test edge cases and error scenarios
- **Integration tests**: Mirror FastAPI endpoint behavior

## Test Output

The `-s` flag shows detailed logging output including:
- Agent initialization steps
- Input parameters (patient_id, questions)
- Retrieved data (notes, papers)
- Generated responses (answers, summaries)
- Execution flow and results

## Environment

Tests require:
- Agent Catalog (agentc)
- LangChain dependencies
- Access to Couchbase (for database operations)
- Environment variables set in `.env`

## Notes

- Tests use parametrized inputs to cover multiple scenarios
- Integration tests simulate the full FastAPI endpoint flow
- All tests include clear logging for debugging and verification
