"""
Backward compatibility wrapper for the doc notes search agent.

Provides an interface for easy integration with existing backend code.
"""

import sys
from pathlib import Path

from typing import Optional

import agentc
import langchain_core.messages

# Import from this directory specifically
import importlib.util


# Add this directory to path for imports - insert at beginning to take precedence
agent_dir = str(Path(__file__).parent)
if agent_dir in sys.path:
    sys.path.remove(agent_dir)
sys.path.insert(0, agent_dir)

graph_path = Path(__file__).parent / "graph.py"
spec = importlib.util.spec_from_file_location("docnotes_graph", graph_path)
docnotes_graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docnotes_graph)
DocNotesSearcher = docnotes_graph.DocNotesSearcher

# Initialize catalog once at module level
_catalog = None
_searcher = None


def _get_catalog() -> agentc.Catalog:
    """Get or create the catalog instance"""
    global _catalog
    if _catalog is None:
        _catalog = agentc.Catalog()
    return _catalog


def _get_searcher() -> DocNotesSearcher:
    """Get or create the searcher instance"""
    global _searcher
    if _searcher is None:
        catalog = _get_catalog()
        _searcher = DocNotesSearcher(catalog=catalog)
    return _searcher


def search_doctor_notes(
    patient_id: str,
    question: str,
    patient_name: Optional[str] = None,
    enable_tracing: bool = True,
) -> dict:  # noqa: ARG001
    """
    Search doctor notes for a patient using semantic search.

    Args:
        patient_id: The patient's ID
        question: The doctor's question about past visits
        enable_tracing: Whether to enable Agent Tracer (default: True)

    Returns:
        Dictionary with patient_id, patient_name, question, notes, and answer
    """
    try:
        searcher = _get_searcher()

        # Build starting state
        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)
        if patient_name:
            state["patient_name"] = patient_name

        # Add the question as a human message in JSON format
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "patient_name": "{patient_name or ""}", "question": "{question}"}}'
            )
        )

        # Invoke the agent
        result = searcher.invoke(input=state)

        # Format response
        return {
            "patient_id": result.get("patient_id", patient_id),
            "patient_name": result.get("patient_name"),
            "question": result.get("question", question),
            "notes": result.get("notes", []),
            "answer": result.get("answer", ""),
        }

    except Exception as e:
        return {
            "error": f"Error during search: {str(e)}",
            "patient_id": patient_id,
            "question": question,
        }
