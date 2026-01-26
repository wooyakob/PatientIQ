import json
from pathlib import Path
from typing import Optional

import agentc.catalog


@agentc.catalog.tool
def get_previsit_questionnaire(patient_id: str) -> Optional[dict]:
    """
    Get the pre-visit questionnaire for a patient.

    Args:
        patient_id: The ID of the patient

    Returns:
        The questionnaire data as a dictionary, or None if not found
    """
    try:
        # Find the questionnaire file in the data directory
        root = Path(__file__).resolve().parent.parent
        questionnaire_path = (
            root
            / "data"
            / "questionnaires"
            / f"patient_{patient_id}"
            / "pre_visit_questionnaire.json"
        )

        if not questionnaire_path.exists():
            return None

        # Load and parse the JSON file
        data = json.loads(questionnaire_path.read_text(encoding="utf-8"))

        # The JSON file contains an array with one object
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data

        return None

    except Exception as e:
        print(f"Error loading questionnaire for patient {patient_id}: {e}")
        return None
