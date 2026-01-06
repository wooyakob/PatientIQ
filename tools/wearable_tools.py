"""
Tools for managing wearable data alerts in the healthcare agent system.
"""

import agentc
from datetime import datetime


def _get_db():
    from backend.database import db
    return db


@agentc.catalog.tool
def save_wearable_alert(
    alert_id: str,
    patient_id: str,
    alert_type: str,
    message: str,
    severity: str,
    metrics: dict
) -> dict:
    """
    Save a wearable data alert to the database.

    Args:
        alert_id: Unique identifier for the alert
        patient_id: Patient the alert is for
        alert_type: Type of alert (e.g., "Elevated Heart Rate")
        message: Detailed message for the physician
        severity: Alert severity (low, medium, high, critical)
        metrics: Dictionary of relevant wearable metrics

    Returns:
        Dictionary with success status
    """
    alert_data = {
        "patient_id": patient_id,
        "alert_type": alert_type,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics
    }

    db = _get_db()
    success = db.save_wearable_alert(alert_id, alert_data)

    return {
        "success": success,
        "alert_id": alert_id,
        "message": "Alert saved successfully" if success else "Failed to save alert"
    }


@agentc.catalog.tool
def get_patient_alerts(patient_id: str) -> list[dict]:
    """
    Retrieve all alerts for a specific patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        List of alert dictionaries for the patient
    """
    db = _get_db()
    return db.get_alerts_for_patient(patient_id)
