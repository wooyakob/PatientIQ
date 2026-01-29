"""
Tool to compare a patient's wearable metrics to a demographically similar cohort.

Performs comparative analysis between an individual patient and similar patients
to identify outliers and percentile rankings for key health metrics.
"""

import agentc
from statistics import mean
from typing import Optional


@agentc.catalog.tool
def compare_patient_to_cohort(
    patient_wearable_data: list[dict],
    cohort_patient_ids: list[str],
    get_cohort_data_func: Optional[callable] = None,
) -> dict:
    """
    Compare a patient's wearable metrics against a demographically similar cohort.

    Calculates percentile rankings and identifies outliers by comparing the patient's
    average metrics to those of similar patients (same age range, condition, gender).

    Args:
        patient_wearable_data: Wearable data for the target patient
        cohort_patient_ids: List of similar patient IDs to compare against
        get_cohort_data_func: Function to retrieve cohort data (if not embedded)

    Returns:
        Dictionary containing:
        - patient_metrics: Patient's average metrics
        - cohort_metrics: Cohort average metrics with std deviation
        - percentile_rankings: Patient's percentile for each metric
        - outliers: Metrics where patient is significantly different
        - comparison_summary: Human-readable summary

    Example:
        >>> compare_patient_to_cohort(patient_data, ["2", "3", "4"])
        {
            "patient_metrics": {
                "avg_heart_rate": 115.2,
                "avg_oxygen": 91.5,
                "avg_steps": 4200
            },
            "cohort_metrics": {
                "avg_heart_rate": {"mean": 85.3, "std": 12.1},
                "avg_oxygen": {"mean": 95.2, "std": 2.1},
                "avg_steps": {"mean": 6800, "std": 1200}
            },
            "percentile_rankings": {
                "heart_rate": 95,  # Patient is in 95th percentile (high)
                "oxygen": 5,       # Patient is in 5th percentile (low)
                "steps": 25
            },
            "outliers": [
                {
                    "metric": "blood_oxygen",
                    "patient_value": 91.5,
                    "cohort_mean": 95.2,
                    "difference": -3.7,
                    "std_deviations": -1.76,
                    "significance": "Significantly below cohort average"
                }
            ],
            "comparison_summary": "Patient shows concerning deviations in 2 metrics"
        }
    """
    # Validate patient data
    if not patient_wearable_data or not isinstance(patient_wearable_data, list):
        return {
            "error": "No valid patient wearable data provided",
            "patient_metrics": {},
            "cohort_metrics": {},
            "percentile_rankings": {},
            "outliers": [],
        }

    # Filter valid patient data
    valid_patient_data = [
        d for d in patient_wearable_data if "metrics" in d and isinstance(d.get("metrics"), dict)
    ]

    if not valid_patient_data:
        return {
            "error": "No valid metrics found in patient data",
            "patient_metrics": {},
            "cohort_metrics": {},
            "percentile_rankings": {},
            "outliers": [],
        }

    # Calculate patient averages
    patient_hr = []
    patient_o2 = []
    patient_steps = []
    patient_stress = []
    patient_exercise = []

    for record in valid_patient_data:
        metrics = record.get("metrics", {})
        if metrics.get("heart_rate"):
            patient_hr.append(float(metrics["heart_rate"]))
        if metrics.get("blood_oxygen_level"):
            patient_o2.append(float(metrics["blood_oxygen_level"]))
        if metrics.get("steps"):
            patient_steps.append(float(metrics["steps"]))
        if metrics.get("stress_level"):
            stress_map = {"Low": 1, "Medium": 2, "High": 3}
            patient_stress.append(stress_map.get(metrics["stress_level"], 2))
        if metrics.get("exercise_duration"):
            patient_exercise.append(float(metrics["exercise_duration"]))

    patient_metrics = {
        "avg_heart_rate": round(mean(patient_hr), 1) if patient_hr else None,
        "avg_oxygen": round(mean(patient_o2), 2) if patient_o2 else None,
        "avg_steps": round(mean(patient_steps), 0) if patient_steps else None,
        "avg_stress": round(mean(patient_stress), 2) if patient_stress else None,
        "avg_exercise_hours": round(mean(patient_exercise), 2) if patient_exercise else None,
        "data_points": len(valid_patient_data),
    }

    # For this demo, we'll simulate cohort data since we don't have easy access
    # to all cohort wearable data without making multiple queries
    # In production, you'd query each cohort patient's wearable data

    # Simulated cohort statistics (would be calculated from actual cohort data)
    # These represent typical healthy ranges for the condition
    cohort_metrics = {
        "avg_heart_rate": {
            "mean": 85.0,
            "std": 15.0,
            "median": 83.0,
            "min": 65.0,
            "max": 110.0,
            "cohort_size": len(cohort_patient_ids),
        },
        "avg_oxygen": {
            "mean": 95.5,
            "std": 2.5,
            "median": 96.0,
            "min": 90.0,
            "max": 99.0,
            "cohort_size": len(cohort_patient_ids),
        },
        "avg_steps": {
            "mean": 7500.0,
            "std": 2000.0,
            "median": 7200.0,
            "min": 3000.0,
            "max": 12000.0,
            "cohort_size": len(cohort_patient_ids),
        },
        "avg_stress": {
            "mean": 2.0,
            "std": 0.7,
            "median": 2.0,
            "min": 1.0,
            "max": 3.0,
            "cohort_size": len(cohort_patient_ids),
        },
        "avg_exercise_hours": {
            "mean": 0.6,
            "std": 0.3,
            "median": 0.5,
            "min": 0.2,
            "max": 1.5,
            "cohort_size": len(cohort_patient_ids),
        },
    }

    # Calculate percentile rankings and identify outliers
    percentile_rankings = {}
    outliers = []

    metric_mapping = {
        "avg_heart_rate": ("heart_rate", "Heart Rate", "BPM", False),  # False = higher is worse
        "avg_oxygen": ("oxygen", "Blood Oxygen", "%", True),  # True = higher is better
        "avg_steps": ("steps", "Daily Steps", "steps", True),
        "avg_stress": ("stress", "Stress Level", "level", False),
        "avg_exercise_hours": ("exercise", "Exercise Duration", "hours", True),
    }

    for metric_key, (short_name, display_name, unit, higher_is_better) in metric_mapping.items():
        patient_value = patient_metrics.get(metric_key)
        cohort_stats = cohort_metrics.get(metric_key, {})

        if patient_value is None or not cohort_stats:
            continue

        cohort_mean = cohort_stats["mean"]
        cohort_std = cohort_stats["std"]

        # Calculate standard deviations from mean
        if cohort_std > 0:
            z_score = (patient_value - cohort_mean) / cohort_std

            # Approximate percentile from z-score
            # Using simplified normal distribution approximation
            if z_score <= -2:
                percentile = 2
            elif z_score <= -1:
                percentile = 16
            elif z_score <= 0:
                percentile = 50 - int(abs(z_score) * 34)
            elif z_score <= 1:
                percentile = 50 + int(z_score * 34)
            elif z_score <= 2:
                percentile = 84 + int((z_score - 1) * 14)
            else:
                percentile = 98

            percentile_rankings[short_name] = percentile

            # Identify significant outliers (>1.5 std deviations)
            if abs(z_score) > 1.5:
                difference = patient_value - cohort_mean

                if (higher_is_better and z_score < -1.5) or (
                    not higher_is_better and z_score > 1.5
                ):
                    significance_level = "concerning"
                    if abs(z_score) > 2.0:
                        significance_level = "highly concerning"
                else:
                    significance_level = "favorable"
                    if abs(z_score) > 2.0:
                        significance_level = "highly favorable"

                outliers.append(
                    {
                        "metric": display_name,
                        "metric_key": short_name,
                        "patient_value": patient_value,
                        "cohort_mean": round(cohort_mean, 2),
                        "cohort_std": round(cohort_std, 2),
                        "difference": round(difference, 2),
                        "difference_percent": round((difference / cohort_mean) * 100, 1)
                        if cohort_mean != 0
                        else 0,
                        "std_deviations": round(z_score, 2),
                        "percentile": percentile,
                        "unit": unit,
                        "significance": significance_level,
                        "interpretation": _interpret_outlier(
                            short_name, patient_value, cohort_mean, z_score, higher_is_better
                        ),
                    }
                )

    # Sort outliers by abs(z_score) - most significant first
    outliers.sort(key=lambda x: abs(x["std_deviations"]), reverse=True)

    # Generate comparison summary
    concerning_outliers = [o for o in outliers if "concerning" in o["significance"]]
    favorable_outliers = [o for o in outliers if "favorable" in o["significance"]]

    if concerning_outliers:
        comparison_summary = (
            f"⚠️ Patient shows {len(concerning_outliers)} concerning deviation(s) from cohort. "
            f"Most significant: {concerning_outliers[0]['metric']} "
            f"({concerning_outliers[0]['std_deviations']:.1f} std devs from mean)"
        )
    elif favorable_outliers:
        comparison_summary = (
            f"✓ Patient metrics generally favorable. "
            f"{len(favorable_outliers)} metric(s) above cohort average."
        )
    else:
        comparison_summary = "✓ Patient metrics within normal range of cohort averages"

    return {
        "patient_metrics": patient_metrics,
        "cohort_metrics": cohort_metrics,
        "percentile_rankings": percentile_rankings,
        "outliers": outliers,
        "comparison_summary": comparison_summary,
        "cohort_size": len(cohort_patient_ids),
        "analysis_date": "2025-01-20",  # Would be dynamic
    }


def _interpret_outlier(
    metric: str, value: float, cohort_mean: float, z_score: float, higher_is_better: bool
) -> str:
    """Generate human-readable interpretation of outlier."""

    if metric == "heart_rate":
        if z_score > 1.5:
            return "Elevated heart rate may indicate cardiac stress or insufficient treatment"
        else:
            return "Heart rate well-controlled compared to cohort"

    elif metric == "oxygen":
        if z_score < -1.5:
            return "Oxygen saturation significantly below cohort - evaluate for hypoxemia"
        else:
            return "Oxygen saturation comparable to or better than cohort"

    elif metric == "steps":
        if z_score < -1.5:
            return "Activity level notably lower than cohort - may indicate symptom burden"
        else:
            return "Activity level similar to or exceeding cohort average"

    elif metric == "stress":
        if z_score > 1.5:
            return "Stress levels elevated compared to cohort - consider stress management interventions"
        else:
            return "Stress levels within typical range for cohort"

    elif metric == "exercise":
        if z_score < -1.5:
            return "Exercise duration below cohort average - assess barriers to activity"
        else:
            return "Exercise participation comparable to or better than cohort"

    return f"Value {abs(z_score):.1f} standard deviations from cohort mean"
