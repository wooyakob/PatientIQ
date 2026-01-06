"""
Tools for managing questionnaire summaries in the healthcare agent system.
"""

import agentc
from datetime import datetime


def _get_db():
    from backend.database import db
    return db


@agentc.catalog.tool
def save_questionnaire_summary(
    summary_id: str,
    patient_id: str,
    appointment_date: str,
    summary: str,
    key_points: list[str],
    red_flags: list[str] = None
) -> dict:
    """
    Save a questionnaire summary to the database.

    Args:
        summary_id: Unique identifier for the summary
        patient_id: Patient the questionnaire is for
        appointment_date: Date of the associated appointment
        summary: Concise summary paragraph
        key_points: List of key points from the questionnaire
        red_flags: Optional list of urgent concerns

    Returns:
        Dictionary with success status
    """
    summary_data = {
        "patient_id": patient_id,
        "appointment_date": appointment_date,
        "summary": summary,
        "key_points": key_points,
        "red_flags": red_flags or [],
        "generated_at": datetime.now().isoformat()
    }

    db = _get_db()
    success = db.save_questionnaire_summary(summary_id, summary_data)

    return {
        "success": success,
        "summary_id": summary_id,
        "message": "Summary saved successfully" if success else "Failed to save summary"
    }


@agentc.catalog.tool
def get_patient_questionnaire(patient_id: str) -> dict:
    """
    Retrieve the latest questionnaire summary for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        Dictionary containing the latest questionnaire summary, or None if not found
    """
    db = _get_db()
    questionnaire = db.get_questionnaire_for_patient(patient_id)
    if not questionnaire:
        return {"found": False, "message": "No questionnaire summary found"}
    return {"found": True, "questionnaire": questionnaire}
