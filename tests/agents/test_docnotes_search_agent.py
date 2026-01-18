"""
Test suite for the Doctor Notes Search Agent.

This test file validates the docnotes_search_agent functionality including:
- Agent initialization
- State building
- Patient name retrieval
- Doctor notes search via semantic/vector search
- Answer generation from retrieved notes
"""

import logging
import sys
from pathlib import Path

import agentc
import langchain_core.messages
import pytest

from graph import DocNotesSearcher

# Add agent directory to path
agent_dir = str(Path(__file__).parent.parent.parent / "agents" / "docnotes_search_agent")
sys.path.insert(0, agent_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def catalog():
    """Initialize Agent Catalog once for all tests."""
    logger.info("=" * 80)
    logger.info("Initializing Agent Catalog")
    logger.info("=" * 80)
    catalog = agentc.Catalog()
    logger.info("Agent Catalog initialized successfully")
    return catalog


@pytest.fixture(scope="module")
def docnotes_searcher(catalog):
    """Initialize DocNotesSearcher once for all tests."""
    logger.info("=" * 80)
    logger.info("Initializing DocNotesSearcher agent")
    logger.info("=" * 80)
    searcher = DocNotesSearcher(catalog=catalog)
    logger.info("DocNotesSearcher agent initialized successfully")
    return searcher


class TestDocNotesSearcherInitialization:
    """Test agent initialization and setup."""

    def test_catalog_initialization(self, catalog):
        """Test that the catalog initializes correctly."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Catalog Initialization")
        logger.info("=" * 80)
        assert catalog is not None, "Catalog should be initialized"
        logger.info("✓ Catalog initialized successfully")

    def test_agent_initialization(self, docnotes_searcher):
        """Test that the DocNotesSearcher agent initializes correctly."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: DocNotesSearcher Agent Initialization")
        logger.info("=" * 80)
        assert docnotes_searcher is not None, "DocNotesSearcher should be initialized"
        logger.info("✓ DocNotesSearcher agent initialized successfully")


class TestDocNotesSearcherState:
    """Test state building and management."""

    def test_build_starting_state_empty(self):
        """Test building an empty starting state."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Build Empty Starting State")
        logger.info("=" * 80)
        state = DocNotesSearcher.build_starting_state()
        logger.info(f"State keys: {list(state.keys())}")

        assert state is not None, "State should not be None"
        assert "messages" in state, "State should have messages"
        assert "patient_id" in state, "State should have patient_id"
        assert "question" in state, "State should have question"
        assert "notes" in state, "State should have notes"
        assert "answer" in state, "State should have answer"

        logger.info(f"✓ Empty state created with {len(state)} fields")

    def test_build_starting_state_with_params(self):
        """Test building a starting state with parameters."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Build Starting State with Parameters")
        logger.info("=" * 80)

        patient_id = "P001"
        question = "What was discussed in the last visit?"

        logger.info(f"Input patient_id: {patient_id}")
        logger.info(f"Input question: {question}")

        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)

        assert state["patient_id"] == patient_id, f"Expected patient_id={patient_id}"
        assert state["question"] == question, f"Expected question={question}"

        logger.info(f"✓ State created with patient_id={state['patient_id']}")
        logger.info(f"✓ State created with question={state['question']}")


class TestDocNotesSearcherSearch:
    """Test doctor notes search functionality."""

    @pytest.mark.parametrize(
        "patient_id,question",
        [
            ("P001", "What medications was the patient prescribed?"),
            ("P002", "What were the findings from the last chest X-ray?"),
            ("P003", "Has the patient shown improvement in symptoms?"),
        ],
    )
    def test_search_doctor_notes(self, docnotes_searcher, patient_id, question):
        """Test searching doctor notes for various patients and questions."""
        logger.info("\n" + "=" * 80)
        logger.info(f"TEST: Search Doctor Notes - Patient {patient_id}")
        logger.info("=" * 80)
        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Question: {question}")

        # Build starting state
        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message
        message_content = (
            f'{{"patient_id": "{patient_id}", "patient_name": "", "question": "{question}"}}'
        )
        state["messages"].append(langchain_core.messages.HumanMessage(content=message_content))

        logger.info("Invoking DocNotesSearcher agent...")

        # Invoke the agent
        result = docnotes_searcher.invoke(input=state)

        # Log results
        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Patient ID: {result.get('patient_id', 'N/A')}")
        logger.info(f"Patient Name: {result.get('patient_name', 'N/A')}")
        logger.info(f"Question: {result.get('question', 'N/A')}")
        logger.info(f"Number of notes found: {len(result.get('notes', []))}")
        logger.info(f"Answer length: {len(result.get('answer', ''))} characters")

        if result.get("notes"):
            logger.info("\nRetrieved notes:")
            for i, note in enumerate(result.get("notes", []), 1):
                logger.info(f"  Note {i}:")
                logger.info(f"    - Visit Date: {note.get('visit_date', 'N/A')}")
                logger.info(f"    - Doctor: {note.get('doctor_name', 'N/A')}")
                logger.info(f"    - Notes (preview): {note.get('visit_notes', '')[:100]}...")

        if result.get("answer"):
            logger.info(f"\nGenerated Answer:\n{result.get('answer')}")

        logger.info("=" * 80)

        # Assertions
        assert result is not None, "Result should not be None"
        assert result.get("patient_id") == patient_id, f"Expected patient_id={patient_id}"
        assert result.get("question") == question, f"Expected question={question}"
        assert "notes" in result, "Result should contain notes"
        assert "answer" in result, "Result should contain answer"

        logger.info(f"✓ Search completed successfully for patient {patient_id}")

    def test_search_with_patient_name(self, docnotes_searcher):
        """Test searching doctor notes with patient name provided."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Search Doctor Notes with Patient Name")
        logger.info("=" * 80)

        patient_id = "P001"
        patient_name = "John Doe"
        question = "What was the patient's blood pressure reading?"

        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Patient Name: {patient_name}")
        logger.info(f"Question: {question}")

        # Build starting state
        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)
        state["patient_name"] = patient_name

        # Add the question as a human message
        message_content = f'{{"patient_id": "{patient_id}", "patient_name": "{patient_name}", "question": "{question}"}}'
        state["messages"].append(langchain_core.messages.HumanMessage(content=message_content))

        logger.info("Invoking DocNotesSearcher agent...")

        # Invoke the agent
        result = docnotes_searcher.invoke(input=state)

        # Log results
        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Patient Name in result: {result.get('patient_name', 'N/A')}")
        logger.info(f"Number of notes: {len(result.get('notes', []))}")
        logger.info(f"Answer length: {len(result.get('answer', ''))} characters")

        # Assertions
        assert result.get("patient_id") == patient_id
        assert "patient_name" in result

        logger.info("✓ Search with patient name completed successfully")


class TestDocNotesSearcherErrorHandling:
    """Test error handling and edge cases."""

    def test_search_nonexistent_patient(self, docnotes_searcher):
        """Test searching for a non-existent patient."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Search Non-existent Patient")
        logger.info("=" * 80)

        patient_id = "P999999"
        question = "What was discussed?"

        logger.info(f"Patient ID: {patient_id} (non-existent)")
        logger.info(f"Question: {question}")

        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "patient_name": "", "question": "{question}"}}'
            )
        )

        logger.info("Invoking DocNotesSearcher agent...")

        result = docnotes_searcher.invoke(input=state)

        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Result keys: {list(result.keys())}")
        logger.info(f"Number of notes: {len(result.get('notes', []))}")
        logger.info(f"Answer: {result.get('answer', 'N/A')}")

        # Should handle gracefully - may return empty notes or an informative answer
        assert result is not None
        assert "notes" in result or "answer" in result

        logger.info("✓ Non-existent patient handled gracefully")

    def test_search_empty_question(self, docnotes_searcher):
        """Test searching with an empty question."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Search with Empty Question")
        logger.info("=" * 80)

        patient_id = "P001"
        question = ""

        logger.info(f"Patient ID: {patient_id}")
        logger.info("Question: (empty)")

        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "patient_name": "", "question": "{question}"}}'
            )
        )

        logger.info("Invoking DocNotesSearcher agent...")

        result = docnotes_searcher.invoke(input=state)

        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Result: {result}")

        # Should handle gracefully
        assert result is not None

        logger.info("✓ Empty question handled gracefully")


if __name__ == "__main__":
    # Allow running tests directly with: python -m pytest tests/agents/test_docnotes_search_agent.py -v -s
    pytest.main([__file__, "-v", "-s"])
