"""
Backward compatibility wrapper for the pulmonary research agent.

This module provides the same interface as the old pulmonary_research_agent.py
for seamless integration with existing backend code.

All tools are now loaded from the Agent Catalog (/tools folder), not imported directly.
"""

import sys

from pathlib import Path

# Add this directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import agentc
import langchain_core.messages

from graph import PulmonaryResearcher

# Initialize catalog once at module level
_catalog = None


def _get_catalog() -> agentc.Catalog:
    """Get or create the catalog instance"""
    global _catalog
    if _catalog is None:
        _catalog = agentc.Catalog()
    return _catalog


def run_pulmonary_research(patient_id: str, question: str, enable_tracing: bool = True) -> dict:  # noqa: ARG001
    """
    Run pulmonary research for a patient's condition using the new agent structure.

    This function maintains backward compatibility with the old implementation
    while using the new LangGraph-based agent architecture.

    Args:
        patient_id: The patient's ID
        question: The doctor's clinical question
        enable_tracing: Whether to enable Agent Tracer (default: True)

    Returns:
        Dictionary with patient_id, condition, question, papers, and answer
    """
    try:
        catalog = _get_catalog()
        if enable_tracing:
            span = catalog.Span(name="PulmonaryResearch")
            researcher = PulmonaryResearcher(catalog=catalog, span=span)
        else:
            researcher = PulmonaryResearcher(catalog=catalog)

        # Build starting state
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message in JSON format
        state["messages"].append(
            langchain_core.messages.HumanMessage(content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}')
        )

        # Invoke the agent
        result = researcher.invoke(input=state)

        # Format response to match old interface
        return {
            "patient_id": result.get("patient_id", patient_id),
            "patient_name": result.get("patient_name"),
            "condition": result.get("condition", ""),
            "question": result.get("question", question),
            "papers": result.get("papers", []),
            "answer": result.get("answer", ""),
        }

    except Exception as e:
        return {
            "error": f"Error during research: {str(e)}",
            "patient_id": patient_id,
            "question": question,
        }


def run_medical_research(patient_id: str, question: str, enable_tracing: bool = True) -> dict:  # noqa: ARG001
    """Alias for run_pulmonary_research for backward compatibility"""
    return run_pulmonary_research(patient_id, question, enable_tracing)
