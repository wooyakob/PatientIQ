"""
Tools for managing medical research summaries in the healthcare agent system.
"""

import agentc
from datetime import datetime


def _get_db():
    from backend.database import db
    return db


@agentc.catalog.tool
def save_research_summary(
    summary_id: str,
    patient_id: str,
    condition: str,
    topic: str,
    summaries: list[str],
    sources: list[str] = None
) -> dict:
    """
    Save a medical research summary to the database.

    Args:
        summary_id: Unique identifier for the summary
        patient_id: Patient the research is for
        condition: Patient's medical condition
        topic: Research topic title
        summaries: List of research summary paragraphs
        sources: Optional list of source citations

    Returns:
        Dictionary with success status
    """
    research_data = {
        "patient_id": patient_id,
        "condition": condition,
        "topic": topic,
        "summaries": summaries,
        "sources": sources or [],
        "generated_at": datetime.now().isoformat()
    }

    db = _get_db()
    success = db.save_research_summary(summary_id, research_data)

    return {
        "success": success,
        "summary_id": summary_id,
        "message": "Research summary saved successfully" if success else "Failed to save summary"
    }


@agentc.catalog.tool
def get_patient_research(patient_id: str) -> dict:
    """
    Retrieve the latest research summary for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        Dictionary containing the latest research summary, or None if not found
    """
    db = _get_db()
    research = db.get_research_for_patient(patient_id)
    if not research:
        return {"found": False, "message": "No research summary found"}
    return {"found": True, "research": research}
