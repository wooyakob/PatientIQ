"""
Tool to retrieve wearable data for a specific patient.

Uses Couchbase to fetch raw wearable metrics from the Wearables scope.
Returns structured data including heart rate, O2 levels, steps, etc.
"""

import agentc
import couchbase.options
from _shared import cluster
from typing import Optional


@agentc.catalog.tool
def get_wearable_data_by_patient(
    patient_id: str, 
    days: int = 30,
    limit: Optional[int] = None
) -> list[dict]:
    """
    Retrieve wearable device data for a specific patient.
    
    Fetches metrics like heart rate, blood oxygen, steps, exercise data,
    stress levels, and ECG readings from the patient's wearable device.
    
    Args:
        patient_id: The patient's ID (e.g., "1", "2", "3")
        days: Number of days to look back (default: 30)
        limit: Maximum number of records to return (default: all within time range)
    
    Returns:
        List of wearable data records, each containing:
        - patient_id: Patient identifier
        - patient_name: Patient full name
        - device: Wearable device type
        - timestamp: ISO format timestamp
        - metrics: Dictionary with:
            - steps: Daily step count
            - calories_burned: Calories burned
            - distance_covered: Distance in kilometers
            - exercise_type: Type of exercise performed
            - exercise_duration: Duration in hours
            - exercise_intensity: Low/Medium/High
            - heart_rate: Heart rate in BPM
            - blood_oxygen_level: O2 saturation percentage
            - ecg: ECG reading status
            - stress_level: Stress level assessment
    
    Example:
        >>> get_wearable_data_by_patient("1", days=7)
        [
            {
                "patient_id": "1",
                "patient_name": "James Smith",
                "device": "Apple Watch Series 4",
                "timestamp": "2025-01-15T10:30:00-08:00",
                "metrics": {
                    "steps": 7644,
                    "heart_rate": 154,
                    "blood_oxygen_level": 91.79,
                    ...
                }
            },
            ...
        ]
    """
    if not cluster:
        return [{"error": "Database connection not available"}]
    
    try:
        # Query wearable data from the patient's collection
        # Each patient has their own collection: Patient_1, Patient_2, etc.
        collection_name = f"Patient_{patient_id}"
        
        query = f"""
        SELECT w.*
        FROM `Scripps`.Wearables.`{collection_name}` w
        WHERE DATE_DIFF_STR(NOW_STR(), w.timestamp, 'day') <= $days
        ORDER BY w.timestamp DESC
        {f'LIMIT {limit}' if limit else ''}
        """
        
        result = cluster.query(
            query,
            couchbase.options.QueryOptions(named_parameters={"days": days}),
        )
        
        rows = list(result.rows())
        
        if not rows:
            return [{
                "message": f"No wearable data found for patient {patient_id} in the last {days} days",
                "patient_id": patient_id
            }]
        
        return rows
        
    except Exception as e:
        return [{
            "error": f"Failed to retrieve wearable data: {str(e)}",
            "patient_id": patient_id
        }]
