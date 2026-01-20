"""
Tool to find patients with similar demographics for cohort comparison.

Uses SQL++ queries to find patients matching age range, gender, and medical condition.
"""

import agentc
import couchbase.options
from _shared import cluster
from typing import Optional


@agentc.catalog.tool
def find_similar_patients_demographics(
    patient_id: str,
    age_range: int = 5,
    same_condition: bool = True,
    same_gender: bool = True,
    limit: int = 10
) -> list[dict]:
    """
    Find patients with similar demographics for comparison analysis.
    
    Searches for patients matching specified demographic criteria to create
    a cohort for comparative analysis of wearable data and health outcomes.
    
    Args:
        patient_id: Reference patient ID to match demographics against
        age_range: Age tolerance in years (e.g., 5 = ±5 years) (default: 5)
        same_condition: Whether to match medical condition (default: True)
        same_gender: Whether to match gender (default: True)
        limit: Maximum number of similar patients to return (default: 10)
    
    Returns:
        List of similar patients, each containing:
        - patient_id: Patient identifier
        - patient_name: Full name
        - age: Patient age
        - gender: Patient gender
        - medical_conditions: Medical condition(s)
        - similarity_score: How closely they match (0-100)
        - matching_criteria: Which criteria matched
    
    Example:
        >>> find_similar_patients_demographics("1", age_range=5, same_condition=True)
        [
            {
                "patient_id": "3",
                "patient_name": "Robert Chen",
                "age": 35,
                "gender": "male",
                "medical_conditions": "Asthma",
                "similarity_score": 95,
                "matching_criteria": ["age", "gender", "condition"]
            },
            ...
        ]
    """
    if not cluster:
        return [{"error": "Database connection not available"}]
    
    try:
        # First, get the reference patient's demographics
        ref_query = """
        SELECT p.patient_id, p.age, p.gender, p.medical_conditions
        FROM `Scripps`.People.Patients p
        WHERE p.patient_id = $patient_id
        LIMIT 1
        """
        
        ref_result = cluster.query(
            ref_query,
            couchbase.options.QueryOptions(named_parameters={"patient_id": patient_id}),
        )
        
        ref_rows = list(ref_result.rows())
        if not ref_rows:
            return [{"error": f"Reference patient {patient_id} not found"}]
        
        ref_patient = ref_rows[0]
        ref_age = int(ref_patient.get("age", 0))
        ref_gender = ref_patient.get("gender", "")
        ref_condition = ref_patient.get("medical_conditions", "")
        
        # Build dynamic query based on criteria
        conditions = [
            f"p.patient_id != '{patient_id}'",  # Exclude reference patient
            f"ABS(TO_NUMBER(p.age) - {ref_age}) <= {age_range}"  # Age range
        ]
        
        if same_gender and ref_gender:
            conditions.append(f"LOWER(p.gender) = '{ref_gender.lower()}'")
        
        if same_condition and ref_condition:
            # Handle both string and array conditions
            conditions.append(
                f"(LOWER(p.medical_conditions) = '{ref_condition.lower()}' OR "
                f"ANY c IN p.medical_conditions SATISFIES LOWER(c) = '{ref_condition.lower()}' END)"
            )
        
        where_clause = " AND ".join(conditions)
        
        # Query for similar patients
        query = f"""
        SELECT 
            p.patient_id,
            p.patient_name,
            p.age,
            p.gender,
            p.medical_conditions,
            ABS(TO_NUMBER(p.age) - {ref_age}) AS age_difference
        FROM `Scripps`.People.Patients p
        WHERE {where_clause}
        ORDER BY age_difference ASC
        LIMIT $limit
        """
        
        result = cluster.query(
            query,
            couchbase.options.QueryOptions(named_parameters={"limit": limit}),
        )
        
        rows = list(result.rows())
        
        # Calculate similarity scores and matching criteria
        similar_patients = []
        for row in rows:
            matching_criteria = ["age"]
            similarity_score = 100
            
            # Age matching (loses points based on difference)
            age_diff = row.get("age_difference", 0)
            similarity_score -= (age_diff / age_range) * 20  # Max 20 point penalty
            
            # Gender matching
            if same_gender:
                if row.get("gender", "").lower() == ref_gender.lower():
                    matching_criteria.append("gender")
                else:
                    similarity_score -= 30
            
            # Condition matching
            if same_condition:
                patient_cond = row.get("medical_conditions", "")
                if isinstance(patient_cond, str):
                    if patient_cond.lower() == ref_condition.lower():
                        matching_criteria.append("condition")
                    else:
                        similarity_score -= 50
                elif isinstance(patient_cond, list):
                    if ref_condition.lower() in [c.lower() for c in patient_cond]:
                        matching_criteria.append("condition")
                    else:
                        similarity_score -= 50
            
            similar_patients.append({
                "patient_id": row.get("patient_id"),
                "patient_name": row.get("patient_name"),
                "age": row.get("age"),
                "gender": row.get("gender"),
                "medical_conditions": row.get("medical_conditions"),
                "similarity_score": max(0, int(similarity_score)),
                "matching_criteria": matching_criteria,
                "age_difference_years": age_diff
            })
        
        # Sort by similarity score
        similar_patients.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similar_patients if similar_patients else [{
            "message": f"No similar patients found matching criteria for patient {patient_id}",
            "reference_patient": {
                "patient_id": patient_id,
                "age": ref_age,
                "gender": ref_gender,
                "condition": ref_condition
            }
        }]
        
    except Exception as e:
        return [{
            "error": f"Failed to find similar patients: {str(e)}",
            "patient_id": patient_id
        }]
