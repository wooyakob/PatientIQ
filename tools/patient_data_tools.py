"""
Tools for retrieving and managing patient data in the healthcare agent system.
These tools are registered with agentc and can be used by any agent.
"""

import agentc


def _get_db():
    from backend.database import db
    return db


@agentc.catalog.tool
def get_patient_data(patient_id: str) -> dict:
    """
    Retrieve patient data from the database.

    Args:
        patient_id: The unique identifier for the patient

    Returns:
        Dictionary containing patient information including demographics,
        condition, wearable data, and medical history
    """
    db = _get_db()
    patient = db.get_patient(patient_id)
    if not patient:
        return {"error": f"Patient {patient_id} not found"}
    return patient


@agentc.catalog.tool
def get_all_patients() -> list[dict]:
    """
    Retrieve all patients from the database.

    Returns:
        List of dictionaries containing patient information
    """
    db = _get_db()
    return db.get_all_patients()


@agentc.catalog.tool
def update_patient_data(patient_id: str, updates: dict) -> dict:
    """
    Update patient data in the database.

    Args:
        patient_id: The unique identifier for the patient
        updates: Dictionary of fields to update

    Returns:
        Dictionary with success status and message
    """
    db = _get_db()
    patient = db.get_patient(patient_id)
    if not patient:
        return {"success": False, "message": f"Patient {patient_id} not found"}

    # Merge updates into existing patient data
    patient.update(updates)
    success = db.upsert_patient(patient_id, patient)

    return {
        "success": success,
        "message": "Patient updated successfully" if success else "Update failed"
    }
