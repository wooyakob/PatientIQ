"""
Tool to analyze wearable data trends and generate clinical alerts.

Performs statistical analysis on time-series wearable data to identify
concerning patterns, anomalies, and trends that require clinical attention.
"""

import agentc
from typing import Optional
from statistics import mean, stdev


@agentc.catalog.tool
def analyze_wearable_trends(
    wearable_data: list[dict], patient_condition: Optional[str] = None
) -> dict:
    """
    Analyze wearable data for trends and generate prioritized clinical alerts.

    Performs statistical analysis on metrics like heart rate, oxygen saturation,
    activity levels, and stress to identify concerning patterns. Alert severity
    is adjusted based on patient's medical condition.

    Args:
        wearable_data: List of wearable data records (from get_wearable_data_by_patient)
        patient_condition: Patient's medical condition for context-aware analysis

    Returns:
        Dictionary containing:
        - alerts: List of prioritized alerts with severity levels
        - trends: Statistical trend analysis for each metric
        - summary: High-level summary of findings
        - recommendations: Clinical recommendations based on findings

    Example:
        >>> analyze_wearable_trends(wearable_data, "Asthma")
        {
            "alerts": [
                {
                    "metric": "blood_oxygen_level",
                    "severity": "high",
                    "message": "O2 saturation trending below 92% for 5 consecutive days",
                    "values": [91.5, 91.2, 90.8, 91.0, 90.5],
                    "threshold": 92.0,
                    "clinical_significance": "Critical for Asthma patients"
                }
            ],
            "trends": {...},
            "summary": "3 high-priority alerts detected",
            "recommendations": [...]
        }
    """
    if not wearable_data or isinstance(wearable_data, dict):
        return {
            "error": "No wearable data provided or invalid format",
            "alerts": [],
            "trends": {},
            "summary": "No analysis performed",
        }

    # Filter out error messages
    valid_data = [d for d in wearable_data if "metrics" in d and isinstance(d.get("metrics"), dict)]

    if not valid_data:
        return {
            "error": "No valid wearable data found",
            "alerts": [],
            "trends": {},
            "summary": "No valid data to analyze",
        }

    alerts = []
    trends = {}

    # Extract metrics
    heart_rates = []
    oxygen_levels = []
    steps_counts = []
    stress_levels = []
    exercise_durations = []

    for record in valid_data:
        metrics = record.get("metrics", {})

        if "heart_rate" in metrics and metrics["heart_rate"]:
            heart_rates.append(float(metrics["heart_rate"]))

        if "blood_oxygen_level" in metrics and metrics["blood_oxygen_level"]:
            oxygen_levels.append(float(metrics["blood_oxygen_level"]))

        if "steps" in metrics and metrics["steps"]:
            steps_counts.append(float(metrics["steps"]))

        if "stress_level" in metrics and metrics["stress_level"]:
            stress_map = {"Low": 1, "Medium": 2, "High": 3}
            stress_levels.append(stress_map.get(metrics["stress_level"], 2))

        if "exercise_duration" in metrics and metrics["exercise_duration"]:
            exercise_durations.append(float(metrics["exercise_duration"]))

    # Condition-specific thresholds
    condition_lower = (patient_condition or "").lower()

    # Oxygen level thresholds (condition-specific)
    o2_critical = 88 if "copd" in condition_lower else 90
    o2_warning = 92 if any(c in condition_lower for c in ["asthma", "copd", "fibrosis"]) else 94

    # Heart rate thresholds
    hr_warning = 100
    hr_critical = 120

    # Steps/activity thresholds
    low_activity_threshold = 3000

    # === OXYGEN LEVEL ANALYSIS ===
    if oxygen_levels:
        avg_o2 = mean(oxygen_levels)
        min_o2 = min(oxygen_levels)

        # Check for consistently low O2
        recent_o2 = oxygen_levels[-7:] if len(oxygen_levels) >= 7 else oxygen_levels
        low_o2_days = sum(1 for o2 in recent_o2 if o2 < o2_warning)

        trends["blood_oxygen"] = {
            "average": round(avg_o2, 2),
            "minimum": round(min_o2, 2),
            "maximum": round(max(oxygen_levels), 2),
            "std_dev": round(stdev(oxygen_levels), 2) if len(oxygen_levels) > 1 else 0,
            "days_below_threshold": low_o2_days,
            "threshold": o2_warning,
        }

        # Critical alert
        if min_o2 < o2_critical:
            alerts.append(
                {
                    "metric": "blood_oxygen_level",
                    "severity": "critical",
                    "priority": 1,
                    "message": f"CRITICAL: O2 saturation dropped to {min_o2}% (below {o2_critical}%)",
                    "values": recent_o2,
                    "threshold": o2_critical,
                    "clinical_significance": f"Immediate attention required for {patient_condition or 'patient'}",
                }
            )

        # High alert for trend
        elif low_o2_days >= 3:
            alerts.append(
                {
                    "metric": "blood_oxygen_level",
                    "severity": "high",
                    "priority": 2,
                    "message": f"O2 saturation below {o2_warning}% for {low_o2_days} of last 7 days",
                    "values": recent_o2,
                    "threshold": o2_warning,
                    "clinical_significance": f"Concerning pattern for {patient_condition or 'pulmonary conditions'}",
                }
            )

        # Medium alert for average
        elif avg_o2 < o2_warning:
            alerts.append(
                {
                    "metric": "blood_oxygen_level",
                    "severity": "medium",
                    "priority": 3,
                    "message": f"Average O2 saturation at {avg_o2:.1f}% (below {o2_warning}%)",
                    "values": recent_o2,
                    "threshold": o2_warning,
                    "clinical_significance": "Monitor closely",
                }
            )

    # === HEART RATE ANALYSIS ===
    if heart_rates:
        avg_hr = mean(heart_rates)
        max_hr = max(heart_rates)

        recent_hr = heart_rates[-7:] if len(heart_rates) >= 7 else heart_rates
        elevated_hr_days = sum(1 for hr in recent_hr if hr > hr_warning)

        trends["heart_rate"] = {
            "average": round(avg_hr, 1),
            "minimum": round(min(heart_rates), 1),
            "maximum": round(max_hr, 1),
            "std_dev": round(stdev(heart_rates), 1) if len(heart_rates) > 1 else 0,
            "days_elevated": elevated_hr_days,
        }

        # Critical HR
        if max_hr > hr_critical:
            alerts.append(
                {
                    "metric": "heart_rate",
                    "severity": "high",
                    "priority": 2,
                    "message": f"Peak heart rate at {max_hr} BPM (above {hr_critical} BPM)",
                    "values": recent_hr,
                    "threshold": hr_critical,
                    "clinical_significance": "Evaluate for cardiac stress or arrhythmia",
                }
            )

        # Consistently elevated
        elif elevated_hr_days >= 5:
            alerts.append(
                {
                    "metric": "heart_rate",
                    "severity": "medium",
                    "priority": 3,
                    "message": f"Elevated heart rate (>{hr_warning} BPM) for {elevated_hr_days} of last 7 days",
                    "values": recent_hr,
                    "threshold": hr_warning,
                    "clinical_significance": "May indicate increased cardiac workload",
                }
            )

    # === ACTIVITY LEVEL ANALYSIS ===
    if steps_counts:
        avg_steps = mean(steps_counts)
        recent_steps = steps_counts[-7:] if len(steps_counts) >= 7 else steps_counts
        low_activity_days = sum(1 for steps in recent_steps if steps < low_activity_threshold)

        trends["activity"] = {
            "average_steps": round(avg_steps, 0),
            "minimum_steps": round(min(steps_counts), 0),
            "maximum_steps": round(max(steps_counts), 0),
            "low_activity_days": low_activity_days,
        }

        # Low activity warning
        if low_activity_days >= 5:
            alerts.append(
                {
                    "metric": "activity_level",
                    "severity": "medium",
                    "priority": 4,
                    "message": f"Low activity (<{low_activity_threshold} steps) for {low_activity_days} of last 7 days",
                    "values": recent_steps,
                    "threshold": low_activity_threshold,
                    "clinical_significance": "Reduced mobility may indicate symptom worsening",
                }
            )

    # === STRESS LEVEL ANALYSIS ===
    if stress_levels:
        avg_stress = mean(stress_levels)
        recent_stress = stress_levels[-7:] if len(stress_levels) >= 7 else stress_levels
        high_stress_days = sum(1 for s in recent_stress if s >= 3)

        stress_label = "Low" if avg_stress < 1.5 else "Medium" if avg_stress < 2.5 else "High"

        trends["stress"] = {
            "average_level": stress_label,
            "high_stress_days": high_stress_days,
            "average_numeric": round(avg_stress, 2),
        }

        if high_stress_days >= 4:
            alerts.append(
                {
                    "metric": "stress_level",
                    "severity": "low",
                    "priority": 5,
                    "message": f"High stress levels for {high_stress_days} of last 7 days",
                    "values": recent_stress,
                    "clinical_significance": "Stress can exacerbate respiratory conditions",
                }
            )

    # === EXERCISE ANALYSIS ===
    if exercise_durations:
        avg_exercise = mean(exercise_durations)
        trends["exercise"] = {
            "average_duration_hours": round(avg_exercise, 2),
            "total_hours": round(sum(exercise_durations), 2),
        }

    # Sort alerts by priority
    alerts.sort(key=lambda x: x.get("priority", 999))

    # Generate summary
    critical_count = sum(1 for a in alerts if a["severity"] == "critical")
    high_count = sum(1 for a in alerts if a["severity"] == "high")
    medium_count = sum(1 for a in alerts if a["severity"] == "medium")

    if critical_count > 0:
        summary = f"⚠️ {critical_count} CRITICAL alert(s) requiring immediate attention"
    elif high_count > 0:
        summary = f"⚠️ {high_count} HIGH priority alert(s) detected"
    elif medium_count > 0:
        summary = f"ℹ️ {medium_count} MEDIUM priority alert(s) - monitor closely"
    else:
        summary = "✓ No significant alerts - metrics within acceptable ranges"

    # Generate recommendations
    recommendations = []
    for alert in alerts[:3]:  # Top 3 alerts
        if alert["metric"] == "blood_oxygen_level":
            recommendations.append(
                "Consider pulmonary function tests and review oxygen therapy needs"
            )
            recommendations.append("Evaluate for respiratory infection or condition exacerbation")
        elif alert["metric"] == "heart_rate":
            recommendations.append("Consider ECG and cardiac evaluation")
            recommendations.append("Review medications that may affect heart rate")
        elif alert["metric"] == "activity_level":
            recommendations.append("Assess for symptom worsening limiting mobility")
            recommendations.append("Consider pulmonary rehabilitation referral")

    # Remove duplicates
    recommendations = list(dict.fromkeys(recommendations))

    return {
        "alerts": alerts,
        "trends": trends,
        "summary": summary,
        "recommendations": recommendations,
        "alert_counts": {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": len(alerts) - critical_count - high_count - medium_count,
        },
        "data_points_analyzed": len(valid_data),
        "analysis_period_days": len(valid_data),
    }
