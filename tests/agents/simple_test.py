#!/usr/bin/env python3
"""
Simple test script for agents without pytest dependency.
Validates basic agent functionality and integration with FastAPI backend.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import agentc
import langchain_core.messages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def test_docnotes_search_agent():
    """Test the DocNotesSearcher agent."""
    logger.info("=" * 80)
    logger.info("TEST: DocNotesSearcher Agent")
    logger.info("=" * 80)

    # Clear any cached modules to avoid conflicts
    modules_to_clear = ["graph", "node", "edge"]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    # Add agent directory to path
    agent_dir = str(Path(__file__).parent.parent.parent / "agents" / "docnotes_search_agent")
    sys.path.insert(0, agent_dir)

    try:
        from graph import DocNotesSearcher

        logger.info("✓ DocNotesSearcher imported successfully")

        # Initialize catalog and agent
        catalog = agentc.Catalog()
        logger.info("✓ Agent Catalog initialized")

        searcher = DocNotesSearcher(catalog=catalog)
        logger.info("✓ DocNotesSearcher agent initialized")

        # Test state building
        state = DocNotesSearcher.build_starting_state(
            patient_id="P001", question="What medications was the patient prescribed?"
        )
        logger.info("✓ Starting state created")
        logger.info(f"  - State keys: {list(state.keys())}")
        logger.info(f"  - Patient ID: {state['patient_id']}")
        logger.info(f"  - Question: {state['question']}")

        # Add human message
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content='{"patient_id": "P001", "patient_name": "", "question": "What medications was the patient prescribed?"}'
            )
        )

        logger.info("\nInvoking agent...")
        result = searcher.invoke(input=state)

        logger.info("\nAgent Results:")
        logger.info(f"  - Patient ID: {result.get('patient_id', 'N/A')}")
        logger.info(f"  - Patient Name: {result.get('patient_name', 'N/A')}")
        logger.info(f"  - Notes found: {len(result.get('notes', []))}")
        logger.info(f"  - Answer length: {len(result.get('answer', ''))} chars")

        if result.get("answer"):
            logger.info(f"\nAnswer preview:\n{result.get('answer')[:200]}...")

        logger.info("\n✓ DocNotesSearcher test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n✗ DocNotesSearcher test FAILED: {e}", exc_info=True)
        return False
    finally:
        sys.path.remove(agent_dir)


def test_pulmonary_research_agent():
    """Test the PulmonaryResearcher agent."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: PulmonaryResearcher Agent")
    logger.info("=" * 80)

    # Clear any cached modules to avoid conflicts
    modules_to_clear = ["graph", "node", "edge"]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    # Add agent directory to path
    agent_dir = str(Path(__file__).parent.parent.parent / "agents" / "pulmonary_research_agent")
    sys.path.insert(0, agent_dir)

    try:
        from graph import PulmonaryResearcher

        logger.info("✓ PulmonaryResearcher imported successfully")

        # Initialize catalog and agent
        catalog = agentc.Catalog()
        logger.info("✓ Agent Catalog initialized")

        researcher = PulmonaryResearcher(catalog=catalog)
        logger.info("✓ PulmonaryResearcher agent initialized")

        # Test state building
        state = PulmonaryResearcher.build_starting_state(
            patient_id="P001", question="What are evidence-based treatment options for COPD?"
        )
        logger.info("✓ Starting state created")
        logger.info(f"  - State keys: {list(state.keys())}")
        logger.info(f"  - Patient ID: {state['patient_id']}")
        logger.info(f"  - Question: {state['question']}")

        # Add human message
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content='{"patient_id": "P001", "question": "What are evidence-based treatment options for COPD?"}'
            )
        )

        logger.info("\nInvoking agent...")
        result = researcher.invoke(input=state)

        logger.info("\nAgent Results:")
        logger.info(f"  - Patient ID: {result.get('patient_id', 'N/A')}")
        logger.info(f"  - Patient Name: {result.get('patient_name', 'N/A')}")
        logger.info(f"  - Condition: {result.get('condition', 'N/A')}")
        logger.info(f"  - Papers found: {len(result.get('papers', []))}")
        logger.info(f"  - Answer length: {len(result.get('answer', ''))} chars")

        if result.get("papers"):
            logger.info(f"\nFirst paper: {result.get('papers')[0].get('title', 'N/A')}")

        if result.get("answer"):
            logger.info(f"\nAnswer preview:\n{result.get('answer')[:200]}...")

        logger.info("\n✓ PulmonaryResearcher test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n✗ PulmonaryResearcher test FAILED: {e}", exc_info=True)
        return False
    finally:
        sys.path.remove(agent_dir)


def test_backend_api_integration():
    """Test that the backend API imports and initializes correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Backend API Integration")
    logger.info("=" * 80)

    try:
        from backend.api import _catalog, _pulmonary_researcher, _docnotes_searcher

        logger.info("✓ Backend API imported successfully")
        logger.info(f"✓ Catalog initialized: {type(_catalog).__name__}")
        logger.info(f"✓ PulmonaryResearcher initialized: {type(_pulmonary_researcher).__name__}")
        logger.info(f"✓ DocNotesSearcher initialized: {type(_docnotes_searcher).__name__}")

        # Test that we can build states using the imported classes
        pulm_state = _pulmonary_researcher.build_starting_state(
            patient_id="TEST", question="Test question"
        )
        logger.info(f"✓ PulmonaryResearcher can build state: {list(pulm_state.keys())}")

        doc_state = _docnotes_searcher.build_starting_state(
            patient_id="TEST", question="Test question"
        )
        logger.info(f"✓ DocNotesSearcher can build state: {list(doc_state.keys())}")

        logger.info("\n✓ Backend API Integration test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n✗ Backend API Integration test FAILED: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING AGENT TESTS")
    logger.info("=" * 80)

    results = {
        "DocNotesSearcher": test_docnotes_search_agent(),
        "PulmonaryResearcher": test_pulmonary_research_agent(),
        "Backend API Integration": test_backend_api_integration(),
    }

    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")

    all_passed = all(results.values())
    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("ALL TESTS PASSED")
        logger.info("=" * 80)
        return 0
    else:
        logger.info("SOME TESTS FAILED")
        logger.info("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
