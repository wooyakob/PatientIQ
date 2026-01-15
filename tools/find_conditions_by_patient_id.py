"""
Tool to get medical conditions for a specific patient.

Returns conditions as a comma-separated string for easy use in prompts.
Uses the find_patient_by_id SQL++ tool from the catalog.
"""

import agentc
import couchbase.options
from _shared import cluster


@agentc.catalog.tool
def find_conditions_by_patient_id(patient_id: str) -> str:
    """
    Get the medical conditions for a specific patient as a string.

    Args:
        patient_id: The patient's ID (e.g., "1", "2", "123")

    Returns:
        Comma-separated string of medical conditions, or error message

    Example:
        >>> find_conditions_by_patient_id("1")
        "Chronic Obstructive Pulmonary Disease (COPD), Asthma, Hypertension"

        >>> find_conditions_by_patient_id("999")
        "Patient not found"
    """
    if not cluster:
        return "Database connection not available"

    # Query patient directly
    query = cluster.query(
        """
        SELECT p.*
        FROM `Scripps`.People.Patients p
        WHERE p.patient_id = $patient_id
        LIMIT 1
        """,
        couchbase.options.QueryOptions(named_parameters={"patient_id": patient_id}),
    )

    results = list(query.rows())
    if not results:
        return "Patient not found"

    patient = results[0]
    conditions = patient.get("medical_conditions", [])

    if isinstance(conditions, list):
        return ", ".join(conditions) if conditions else "No conditions listed"

    return str(conditions)
