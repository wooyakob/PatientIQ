"""
Tool to vectorize wearable time-series data for similarity search.

Converts 30-day wearable trends (heart rate, O2, stress, etc.) into embedding vectors
that can be used for vector similarity search in Couchbase.
"""

import agentc
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.utils.embedding_client import embedding_vector
import asyncio


def _normalize_metric(values: list[float], metric_name: str) -> list[float]:
    """
    Normalize metric values to 0-1 range for consistent embeddings.

    Args:
        values: List of metric values
        metric_name: Name of the metric for appropriate normalization

    Returns:
        Normalized values in 0-1 range
    """
    if not values:
        return []

    # Define expected ranges for each metric
    ranges = {
        "heart_rate": (40, 200),  # BPM
        "blood_oxygen_level": (80, 100),  # Percentage
        "steps": (0, 20000),  # Daily steps
        "stress_level": (1, 3),  # Numeric: Low=1, Medium=2, High=3
        "exercise_duration": (0, 4),  # Hours
        "calories_burned": (0, 1000),  # Calories
    }

    min_val, max_val = ranges.get(metric_name, (min(values), max(values)))

    # Normalize to 0-1
    normalized = []
    for v in values:
        if max_val - min_val == 0:
            normalized.append(0.5)
        else:
            norm = (v - min_val) / (max_val - min_val)
            normalized.append(max(0, min(1, norm)))  # Clamp to [0, 1]

    return normalized


def _create_trend_text(wearable_data: list[dict], patient_condition: Optional[str] = None) -> str:
    """
    Create a natural language description of wearable trends for embedding.

    This text will be converted to a vector and captures the clinical pattern
    of the time-series data.

    Args:
        wearable_data: List of wearable data records
        patient_condition: Patient's medical condition

    Returns:
        Natural language description of trends
    """
    if not wearable_data:
        return ""

    # Extract time-series metrics
    heart_rates = []
    oxygen_levels = []
    steps_counts = []
    stress_levels = []

    for record in wearable_data:
        metrics = record.get("metrics", {})

        if metrics.get("heart_rate"):
            heart_rates.append(float(metrics["heart_rate"]))
        if metrics.get("blood_oxygen_level"):
            oxygen_levels.append(float(metrics["blood_oxygen_level"]))
        if metrics.get("steps"):
            steps_counts.append(float(metrics["steps"]))
        if metrics.get("stress_level"):
            stress_map = {"Low": 1, "Medium": 2, "High": 3}
            stress_levels.append(stress_map.get(metrics["stress_level"], 2))

    # Build clinical description
    parts = []

    # Add condition context
    if patient_condition:
        parts.append(f"Patient with {patient_condition}.")

    # Heart rate pattern
    if heart_rates:
        avg_hr = sum(heart_rates) / len(heart_rates)
        min_hr = min(heart_rates)
        max_hr = max(heart_rates)

        if avg_hr > 100:
            parts.append(
                f"Elevated heart rate averaging {avg_hr:.0f} BPM with peaks at {max_hr:.0f} BPM."
            )
        elif avg_hr < 60:
            parts.append(f"Low heart rate averaging {avg_hr:.0f} BPM.")
        else:
            parts.append(
                f"Normal heart rate averaging {avg_hr:.0f} BPM ranging from {min_hr:.0f} to {max_hr:.0f} BPM."
            )

    # Oxygen saturation pattern
    if oxygen_levels:
        avg_o2 = sum(oxygen_levels) / len(oxygen_levels)
        min_o2 = min(oxygen_levels)
        days_below_92 = sum(1 for o2 in oxygen_levels if o2 < 92)

        if min_o2 < 90:
            parts.append(
                f"Critical oxygen desaturation with minimum {min_o2:.1f}% and {days_below_92} days below 92%."
            )
        elif avg_o2 < 92:
            parts.append(
                f"Low oxygen saturation averaging {avg_o2:.1f}% with {days_below_92} days below normal."
            )
        else:
            parts.append(f"Oxygen saturation within normal range averaging {avg_o2:.1f}%.")

    # Activity pattern
    if steps_counts:
        avg_steps = sum(steps_counts) / len(steps_counts)
        low_activity_days = sum(1 for s in steps_counts if s < 3000)

        if avg_steps < 3000:
            parts.append(
                f"Very low activity with average {avg_steps:.0f} steps per day and {low_activity_days} days below 3000 steps."
            )
        elif avg_steps < 5000:
            parts.append(f"Low activity with average {avg_steps:.0f} steps per day.")
        elif avg_steps > 10000:
            parts.append(f"High activity level with average {avg_steps:.0f} steps per day.")
        else:
            parts.append(f"Moderate activity with average {avg_steps:.0f} steps per day.")

    # Stress pattern
    if stress_levels:
        avg_stress = sum(stress_levels) / len(stress_levels)
        high_stress_days = sum(1 for s in stress_levels if s >= 3)

        if avg_stress >= 2.5:
            parts.append(f"Persistent high stress with {high_stress_days} high-stress days.")
        elif avg_stress >= 2:
            parts.append("Moderate stress levels.")
        else:
            parts.append("Low stress levels.")

    return " ".join(parts)


@agentc.catalog.tool
def vectorize_wearable_trends(
    wearable_data: list[dict], patient_condition: Optional[str] = None
) -> dict:
    """
    Vectorize wearable time-series data for similarity search.

    Converts 30-day wearable trends into:
    1. A clinical trend description (natural language)
    2. An embedding vector for that description
    3. Normalized metric arrays for direct comparison

    This enables fast vector similarity search to find patients with similar
    wearable patterns instead of slow statistical analysis.

    Args:
        wearable_data: List of wearable data records (from get_wearable_data_by_patient)
        patient_condition: Patient's medical condition for context

    Returns:
        Dictionary containing:
        - trend_text: Natural language description of the trend
        - trend_vector: Embedding vector (1024-dim) for similarity search
        - normalized_metrics: Normalized time-series arrays for each metric
        - summary: Quick statistics

    Example:
        >>> vectorize_wearable_trends(wearable_data, "Asthma")
        {
            "trend_text": "Patient with Asthma. Elevated heart rate averaging 148 BPM...",
            "trend_vector": [0.123, -0.456, ...],  # 1024-dim vector
            "normalized_metrics": {
                "heart_rate": [0.68, 0.69, 0.75, ...],  # 30 values, 0-1 range
                "blood_oxygen_level": [0.45, 0.42, 0.48, ...],
                ...
            },
            "summary": {
                "days_analyzed": 30,
                "metrics_tracked": ["heart_rate", "blood_oxygen_level", "steps", "stress_level"]
            }
        }
    """
    if not wearable_data or isinstance(wearable_data, dict):
        return {
            "error": "No wearable data provided or invalid format",
            "trend_text": "",
            "trend_vector": [],
            "normalized_metrics": {},
        }

    # Filter valid data
    valid_data = [d for d in wearable_data if "metrics" in d and isinstance(d.get("metrics"), dict)]

    if not valid_data:
        return {
            "error": "No valid wearable data found",
            "trend_text": "",
            "trend_vector": [],
            "normalized_metrics": {},
        }

    # Step 1: Create clinical trend description
    trend_text = _create_trend_text(valid_data, patient_condition)

    # Step 2: Generate embedding vector for the trend
    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    trend_vector = loop.run_until_complete(embedding_vector(trend_text))

    # Step 3: Extract and normalize time-series metrics
    normalized_metrics = {}

    # Extract raw metrics
    heart_rates = []
    oxygen_levels = []
    steps_counts = []
    stress_levels = []
    exercise_durations = []
    calories = []

    for record in valid_data:
        metrics = record.get("metrics", {})

        heart_rates.append(
            float(metrics.get("heart_rate", 0)) if metrics.get("heart_rate") else None
        )
        oxygen_levels.append(
            float(metrics.get("blood_oxygen_level", 0))
            if metrics.get("blood_oxygen_level")
            else None
        )
        steps_counts.append(float(metrics.get("steps", 0)) if metrics.get("steps") else None)

        stress_map = {"Low": 1, "Medium": 2, "High": 3}
        stress_levels.append(stress_map.get(metrics.get("stress_level"), None))

        exercise_durations.append(
            float(metrics.get("exercise_duration", 0)) if metrics.get("exercise_duration") else None
        )
        calories.append(
            float(metrics.get("calories_burned", 0)) if metrics.get("calories_burned") else None
        )

    # Normalize each metric
    if any(hr is not None for hr in heart_rates):
        clean_hrs = [hr for hr in heart_rates if hr is not None]
        if clean_hrs:
            normalized_metrics["heart_rate"] = _normalize_metric(clean_hrs, "heart_rate")

    if any(o2 is not None for o2 in oxygen_levels):
        clean_o2 = [o2 for o2 in oxygen_levels if o2 is not None]
        if clean_o2:
            normalized_metrics["blood_oxygen_level"] = _normalize_metric(
                clean_o2, "blood_oxygen_level"
            )

    if any(s is not None for s in steps_counts):
        clean_steps = [s for s in steps_counts if s is not None]
        if clean_steps:
            normalized_metrics["steps"] = _normalize_metric(clean_steps, "steps")

    if any(s is not None for s in stress_levels):
        clean_stress = [s for s in stress_levels if s is not None]
        if clean_stress:
            normalized_metrics["stress_level"] = _normalize_metric(clean_stress, "stress_level")

    if any(e is not None for e in exercise_durations):
        clean_ex = [e for e in exercise_durations if e is not None]
        if clean_ex:
            normalized_metrics["exercise_duration"] = _normalize_metric(
                clean_ex, "exercise_duration"
            )

    if any(c is not None for c in calories):
        clean_cal = [c for c in calories if c is not None]
        if clean_cal:
            normalized_metrics["calories_burned"] = _normalize_metric(clean_cal, "calories_burned")

    return {
        "trend_text": trend_text,
        "trend_vector": trend_vector,
        "normalized_metrics": normalized_metrics,
        "summary": {
            "days_analyzed": len(valid_data),
            "metrics_tracked": list(normalized_metrics.keys()),
            "vector_dimensions": len(trend_vector),
        },
    }
