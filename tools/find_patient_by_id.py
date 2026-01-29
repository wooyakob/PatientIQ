"""
Tool to find a patient by their ID.

Retrieves basic patient demographic information including name, age, gender,
and medical conditions from the database.
"""

import agentc
from backend.database import db


@agentc.catalog.tool
def find_patient_by_id(patient_id: str) -> dict:
    """
    Find a patient by their ID and return demographic information.
    
    Args:
        patient_id: The unique patient identifier
    
    Returns:
        Dictionary containing:
        - patient_id: The patient's ID
        - name: Patient's full name
        - age: Patient's age
        - gender: Patient's gender
        - medical_conditions: List of known medical conditions
    
    Example:
        >>> find_patient_by_id("1")
        {
            "patient_id": "1",
            "name": "James Smith",
            "age": 45,
            "gender": "Male",
            "medical_conditions": ["Asthma", "Hypertension"]
        }
    """
    try:
        patient = db.get_patient(patient_id)
        
        if not patient:
            return {
                "error": f"Patient with ID {patient_id} not found",
                "patient_id": patient_id
            }
        
        return {
            "patient_id": str(patient.get("id", patient_id)),
            "name": str(patient.get("name", "Unknown")),
            "age": int(patient.get("age", 0)),
            "gender": str(patient.get("gender", "Unknown")),
            "medical_conditions": patient.get("medical_conditions", [])
        }
    except Exception as e:
        return {
            "error": f"Error retrieving patient: {str(e)}",
            "patient_id": patient_id
        }
