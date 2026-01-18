"""
Test suite for the Pulmonary Research Agent.

This test file validates the pulmonary_research_agent functionality including:
- Agent initialization
- State building
- Patient condition retrieval
- Medical research paper search via PubMed
- Clinical summary generation from research papers
"""

import logging
import sys
from pathlib import Path

import agentc
import langchain_core.messages
import pytest
from graph import PulmonaryResearcher

# Add agent directory to path
agent_dir = str(Path(__file__).parent.parent.parent / "agents" / "pulmonary_research_agent")
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
def pulmonary_researcher(catalog):
    """Initialize PulmonaryResearcher once for all tests."""
    logger.info("=" * 80)
    logger.info("Initializing PulmonaryResearcher agent")
    logger.info("=" * 80)
    researcher = PulmonaryResearcher(catalog=catalog)
    logger.info("PulmonaryResearcher agent initialized successfully")
    return researcher


class TestPulmonaryResearcherInitialization:
    """Test agent initialization and setup."""

    def test_catalog_initialization(self, catalog):
        """Test that the catalog initializes correctly."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Catalog Initialization")
        logger.info("=" * 80)
        assert catalog is not None, "Catalog should be initialized"
        logger.info("✓ Catalog initialized successfully")

    def test_agent_initialization(self, pulmonary_researcher):
        """Test that the PulmonaryResearcher agent initializes correctly."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: PulmonaryResearcher Agent Initialization")
        logger.info("=" * 80)
        assert pulmonary_researcher is not None, "PulmonaryResearcher should be initialized"
        logger.info("✓ PulmonaryResearcher agent initialized successfully")


class TestPulmonaryResearcherState:
    """Test state building and management."""

    def test_build_starting_state_empty(self):
        """Test building an empty starting state."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Build Empty Starting State")
        logger.info("=" * 80)
        state = PulmonaryResearcher.build_starting_state()
        logger.info(f"State keys: {list(state.keys())}")

        assert state is not None, "State should not be None"
        assert "messages" in state, "State should have messages"
        assert "patient_id" in state, "State should have patient_id"
        assert "condition" in state, "State should have condition"
        assert "question" in state, "State should have question"
        assert "papers" in state, "State should have papers"
        assert "answer" in state, "State should have answer"

        logger.info(f"✓ Empty state created with {len(state)} fields")

    def test_build_starting_state_with_params(self):
        """Test building a starting state with parameters."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Build Starting State with Parameters")
        logger.info("=" * 80)

        patient_id = "P001"
        question = "What are the latest treatment options for COPD?"

        logger.info(f"Input patient_id: {patient_id}")
        logger.info(f"Input question: {question}")

        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        assert state["patient_id"] == patient_id, f"Expected patient_id={patient_id}"
        assert state["question"] == question, f"Expected question={question}"

        logger.info(f"✓ State created with patient_id={state['patient_id']}")
        logger.info(f"✓ State created with question={state['question']}")


class TestPulmonaryResearcherResearch:
    """Test medical research functionality."""

    @pytest.mark.parametrize(
        "patient_id,question",
        [
            ("P001", "What are evidence-based treatment options for COPD?"),
            ("P002", "What are the latest guidelines for pulmonary fibrosis management?"),
            ("P003", "What medications are recommended for chronic bronchitis?"),
        ],
    )
    def test_run_pulmonary_research(self, pulmonary_researcher, patient_id, question):
        """Test running pulmonary research for various patients and questions."""
        logger.info("\n" + "=" * 80)
        logger.info(f"TEST: Run Pulmonary Research - Patient {patient_id}")
        logger.info("=" * 80)
        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Question: {question}")

        # Build starting state
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message
        message_content = f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
        state["messages"].append(langchain_core.messages.HumanMessage(content=message_content))

        logger.info("Invoking PulmonaryResearcher agent...")

        # Invoke the agent
        result = pulmonary_researcher.invoke(input=state)

        # Log results
        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Patient ID: {result.get('patient_id', 'N/A')}")
        logger.info(f"Patient Name: {result.get('patient_name', 'N/A')}")
        logger.info(f"Condition: {result.get('condition', 'N/A')}")
        logger.info(f"Question: {result.get('question', 'N/A')}")
        logger.info(f"Number of papers found: {len(result.get('papers', []))}")
        logger.info(f"Answer length: {len(result.get('answer', ''))} characters")

        if result.get("papers"):
            logger.info("\nRetrieved papers:")
            for i, paper in enumerate(result.get("papers", []), 1):
                logger.info(f"  Paper {i}:")
                logger.info(f"    - Title: {paper.get('title', 'N/A')}")
                logger.info(f"    - Authors: {paper.get('authors', 'N/A')}")
                logger.info(f"    - Journal: {paper.get('journal', 'N/A')}")
                logger.info(f"    - Year: {paper.get('year', 'N/A')}")
                logger.info(f"    - PMID: {paper.get('pmid', 'N/A')}")

        if result.get("answer"):
            logger.info(f"\nGenerated Clinical Summary:\n{result.get('answer')}")

        logger.info("=" * 80)

        # Assertions
        assert result is not None, "Result should not be None"
        assert result.get("patient_id") == patient_id, f"Expected patient_id={patient_id}"
        assert result.get("question") == question, f"Expected question={question}"
        assert "condition" in result, "Result should contain condition"
        assert "papers" in result, "Result should contain papers"
        assert "answer" in result, "Result should contain answer"

        logger.info(f"✓ Research completed successfully for patient {patient_id}")

    def test_research_default_question(self, pulmonary_researcher):
        """Test running pulmonary research with default question."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Run Pulmonary Research with Default Question")
        logger.info("=" * 80)

        patient_id = "P001"
        question = "What are evidence-based treatment options and practical next steps for this patient's condition?"

        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Question (default): {question}")

        # Build starting state
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message
        message_content = f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
        state["messages"].append(langchain_core.messages.HumanMessage(content=message_content))

        logger.info("Invoking PulmonaryResearcher agent...")

        # Invoke the agent
        result = pulmonary_researcher.invoke(input=state)

        # Log results
        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Condition: {result.get('condition', 'N/A')}")
        logger.info(f"Number of papers: {len(result.get('papers', []))}")
        logger.info(f"Answer length: {len(result.get('answer', ''))} characters")

        # Assertions
        assert result.get("patient_id") == patient_id
        assert "condition" in result
        assert "papers" in result
        assert "answer" in result

        logger.info("✓ Research with default question completed successfully")

    def test_research_specific_condition(self, pulmonary_researcher):
        """Test researching a specific pulmonary condition."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Research Specific Pulmonary Condition")
        logger.info("=" * 80)

        patient_id = "P001"
        question = "What are the current best practices for managing acute exacerbations of COPD?"

        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Question: {question}")

        # Build starting state
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message
        message_content = f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
        state["messages"].append(langchain_core.messages.HumanMessage(content=message_content))

        logger.info("Invoking PulmonaryResearcher agent...")

        # Invoke the agent
        result = pulmonary_researcher.invoke(input=state)

        # Log results
        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Condition: {result.get('condition', 'N/A')}")
        logger.info(f"Number of papers: {len(result.get('papers', []))}")

        if result.get("papers"):
            logger.info("\nPaper details:")
            for i, paper in enumerate(result.get("papers", []), 1):
                logger.info(f"  {i}. {paper.get('title', 'N/A')} ({paper.get('year', 'N/A')})")
                if paper.get("article_text"):
                    logger.info(f"     Abstract preview: {paper.get('article_text', '')[:150]}...")

        if result.get("answer"):
            logger.info(f"\nClinical Summary:\n{result.get('answer')}")

        logger.info("=" * 80)

        # Assertions
        assert result.get("patient_id") == patient_id
        assert result.get("question") == question
        assert "papers" in result
        assert "answer" in result

        logger.info("✓ Specific condition research completed successfully")


class TestPulmonaryResearcherErrorHandling:
    """Test error handling and edge cases."""

    def test_research_nonexistent_patient(self, pulmonary_researcher):
        """Test researching for a non-existent patient."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Research Non-existent Patient")
        logger.info("=" * 80)

        patient_id = "P999999"
        question = "What are the treatment options?"

        logger.info(f"Patient ID: {patient_id} (non-existent)")
        logger.info(f"Question: {question}")

        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        logger.info("Invoking PulmonaryResearcher agent...")

        result = pulmonary_researcher.invoke(input=state)

        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Result keys: {list(result.keys())}")
        logger.info(f"Condition: {result.get('condition', 'N/A')}")
        logger.info(f"Number of papers: {len(result.get('papers', []))}")
        logger.info(f"Answer: {result.get('answer', 'N/A')}")

        # Should handle gracefully - may return empty or informative message
        assert result is not None
        assert "papers" in result or "answer" in result

        logger.info("✓ Non-existent patient handled gracefully")

    def test_research_empty_question(self, pulmonary_researcher):
        """Test researching with an empty question."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Research with Empty Question")
        logger.info("=" * 80)

        patient_id = "P001"
        question = ""

        logger.info(f"Patient ID: {patient_id}")
        logger.info("Question: (empty)")

        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        logger.info("Invoking PulmonaryResearcher agent...")

        result = pulmonary_researcher.invoke(input=state)

        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Result: {result}")

        # Should handle gracefully
        assert result is not None

        logger.info("✓ Empty question handled gracefully")

    def test_research_broad_question(self, pulmonary_researcher):
        """Test researching with a very broad question."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Research with Broad Question")
        logger.info("=" * 80)

        patient_id = "P002"
        question = "Tell me everything about pulmonary diseases."

        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Question: {question}")

        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        logger.info("Invoking PulmonaryResearcher agent...")

        result = pulmonary_researcher.invoke(input=state)

        logger.info("=" * 80)
        logger.info("AGENT RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Number of papers: {len(result.get('papers', []))}")
        logger.info(f"Answer length: {len(result.get('answer', ''))} characters")

        # Should handle broad questions by narrowing to patient's condition
        assert result is not None
        assert "papers" in result
        assert "answer" in result

        logger.info("✓ Broad question handled successfully")


class TestPulmonaryResearcherIntegration:
    """Integration tests that mirror FastAPI endpoint behavior."""

    def test_integration_get_patient_research(self, pulmonary_researcher):
        """Test the full flow as called from GET /api/patients/{patient_id}/research endpoint."""
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST: GET /api/patients/{patient_id}/research")
        logger.info("=" * 80)

        patient_id = "P001"
        question = "What are evidence-based treatment options and practical next steps for this patient's condition?"

        logger.info(f"Simulating GET /api/patients/{patient_id}/research")
        logger.info(f"Default question: {question}")

        # Simulate FastAPI endpoint behavior
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        logger.info("Invoking PulmonaryResearcher agent...")
        agent_result = pulmonary_researcher.invoke(input=state)

        # Format response as FastAPI would
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name"),
            "condition": agent_result.get("condition", ""),
            "question": agent_result.get("question", question),
            "papers": agent_result.get("papers", []),
            "answer": agent_result.get("answer", ""),
        }

        logger.info("=" * 80)
        logger.info("API RESPONSE FORMAT:")
        logger.info("=" * 80)
        logger.info(f"patient_id: {result['patient_id']}")
        logger.info(f"patient_name: {result['patient_name']}")
        logger.info(f"condition: {result['condition']}")
        logger.info(f"papers count: {len(result['papers'])}")
        logger.info(f"answer length: {len(result['answer'])} characters")

        # Assertions matching FastAPI expectations
        assert result["patient_id"] == patient_id
        assert "condition" in result
        assert "papers" in result
        assert "answer" in result

        logger.info("✓ Integration test passed - endpoint simulation successful")

    def test_integration_ask_research_question(self, pulmonary_researcher):
        """Test the full flow as called from POST /api/patients/{patient_id}/research/ask endpoint."""
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST: POST /api/patients/{patient_id}/research/ask")
        logger.info("=" * 80)

        patient_id = "P002"
        question = "What are the latest clinical trials for idiopathic pulmonary fibrosis?"

        logger.info(f"Simulating POST /api/patients/{patient_id}/research/ask")
        logger.info(f"Custom question: {question}")

        # Simulate FastAPI endpoint behavior
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        logger.info("Invoking PulmonaryResearcher agent...")
        agent_result = pulmonary_researcher.invoke(input=state)

        # Format response as FastAPI would
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name"),
            "condition": agent_result.get("condition", ""),
            "question": agent_result.get("question", question),
            "papers": agent_result.get("papers", []),
            "answer": agent_result.get("answer", ""),
        }

        logger.info("=" * 80)
        logger.info("API RESPONSE FORMAT:")
        logger.info("=" * 80)
        logger.info(f"patient_id: {result['patient_id']}")
        logger.info(f"condition: {result['condition']}")
        logger.info(f"question: {result['question']}")
        logger.info(f"papers count: {len(result['papers'])}")

        # Assertions matching FastAPI expectations
        assert result["patient_id"] == patient_id
        assert result["question"] == question
        assert "papers" in result
        assert "answer" in result

        logger.info("✓ Integration test passed - custom question endpoint simulation successful")


if __name__ == "__main__":
    # Allow running tests directly with: python -m pytest tests/agents/test_pulmonary_research_agent.py -v -s
    pytest.main([__file__, "-v", "-s"])
