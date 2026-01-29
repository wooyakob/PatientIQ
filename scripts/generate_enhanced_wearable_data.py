#!/usr/bin/env python3
"""
Script to generate enhanced mock wearable data with stress correlations.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_enhanced_patient_data(
    patient_id: str,
    patient_name: str,
    condition: str,
    base_o2: float,
    base_hr: int,
    stress_pattern: str = "moderate",
) -> list:
    """
    Generate 30 days of realistic wearable data with stress correlations.

    Args:
        patient_id: Patient ID
        patient_name: Patient name
        condition: Medical condition
        base_o2: Baseline oxygen saturation (88-95)
        base_hr: Baseline heart rate (60-80)
        stress_pattern: "low", "moderate", "high", "escalating"

    Returns:
        List of daily wearable data records
    """
    data = []
    today = datetime.now()

    # Stress patterns
    stress_patterns = {
        "low": lambda day: 1 if random.random() < 0.8 else 2,  # Mostly low stress
        "moderate": lambda day: random.choices([1, 2, 3], weights=[0.2, 0.5, 0.3])[0],  # Mixed
        "high": lambda day: 3 if random.random() < 0.7 else 2,  # Mostly high stress
        "escalating": lambda day: 1
        if day < 10
        else (2 if day < 20 else 3),  # Stress increases over time
    }

    stress_fn = stress_patterns.get(stress_pattern, stress_patterns["moderate"])

    for day_offset in range(30):
        date = today - timedelta(days=(30 - day_offset))

        # Determine stress level for this day
        stress_numeric = stress_fn(day_offset)
        stress_level = ["", "Low", "Medium", "High"][stress_numeric]

        # Correlate metrics with stress
        # High stress → Lower O2, Higher HR
        stress_factor = (stress_numeric - 1) / 2  # 0.0 (low) to 1.0 (high)

        # O2 saturation: decreases with stress
        o2_adjustment = -2.0 * stress_factor + random.uniform(-1, 1)
        oxygen_level = base_o2 + o2_adjustment
        oxygen_level = max(85, min(98, oxygen_level))  # Clamp to realistic range

        # Heart rate: increases with stress
        hr_adjustment = 20 * stress_factor + random.uniform(-5, 10)
        heart_rate = base_hr + hr_adjustment
        heart_rate = max(60, min(180, int(heart_rate)))

        # Steps: decreases slightly with high stress (less motivation)
        base_steps = 8000
        steps_adjustment = -1000 * stress_factor
        steps = int(base_steps + steps_adjustment + random.uniform(-1000, 2000))
        steps = max(3000, min(15000, steps))

        # Exercise: less exercise on high stress days
        if stress_numeric == 3 and random.random() < 0.4:
            exercise_type = "Stretching"
            exercise_intensity = "Low"
            exercise_duration = random.uniform(0.2, 0.5)
        elif stress_numeric == 1 and random.random() < 0.5:
            exercise_type = random.choice(["Cycling", "HIIT", "Running"])
            exercise_intensity = "High"
            exercise_duration = random.uniform(0.8, 1.5)
        else:
            exercise_type = random.choice(["Walking", "Elliptical", "Stationary Bike", "Yoga"])
            exercise_intensity = "Moderate"
            exercise_duration = random.uniform(0.5, 1.2)

        # Calories and distance based on activity
        intensity_multiplier = {"Low": 0.6, "Moderate": 1.0, "High": 1.4}[exercise_intensity]
        calories = int(steps * 0.045 * intensity_multiplier + random.uniform(-50, 50))
        distance = steps / 1300 + random.uniform(-0.5, 0.5)

        # ECG: slightly more abnormal on high stress days
        if stress_numeric == 3 and random.random() < 0.15:
            ecg = "Abnormal"
        else:
            ecg = "Normal"

        # Build record
        record = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "device": "Apple Watch Series 4",
            "timestamp": date.strftime("%Y-%m-%dT10:30:00-08:00"),
            "metrics": {
                "steps": steps,
                "calories_burned": round(calories, 1),
                "distance_covered": round(distance, 3),
                "exercise_type": exercise_type,
                "exercise_duration": round(exercise_duration, 3),
                "exercise_intensity": exercise_intensity,
                "heart_rate": heart_rate,
                "blood_oxygen_level": round(oxygen_level, 2),
                "ecg": ecg,
                "stress_level": stress_level,
            },
        }

        data.append(record)

    return data


def main():
    """Generate enhanced wearable data for all demo patients."""

    print("=" * 80)
    print("GENERATING ENHANCED MOCK WEARABLE DATA")
    print("=" * 80)

    # Define patient scenarios with stress patterns
    patients = [
        {
            "id": "1",
            "name": "James Smith",
            "condition": "Asthma",
            "base_o2": 91.0,  # Lower baseline for asthma
            "base_hr": 75,
            "stress_pattern": "escalating",  # Stress gets worse over time
            "description": "Asthma patient with escalating stress → worsening symptoms",
        },
        {
            "id": "2",
            "name": "Maria Garcia",
            "condition": "COPD",
            "base_o2": 89.5,  # Low baseline for COPD
            "base_hr": 72,
            "stress_pattern": "high",  # Consistently high stress
            "description": "COPD patient with chronic high stress",
        },
        {
            "id": "3",
            "name": "Sarah Johnson",
            "condition": "Pulmonary Fibrosis",
            "base_o2": 88.0,  # Very low baseline
            "base_hr": 78,
            "stress_pattern": "moderate",  # Mixed stress levels
            "description": "Pulmonary Fibrosis patient with moderate stress",
        },
        {
            "id": "4",
            "name": "Robert Chen",
            "condition": "Asthma",
            "base_o2": 93.5,  # Better controlled asthma
            "base_hr": 68,
            "stress_pattern": "low",  # Well-managed stress
            "description": "Well-controlled asthma with low stress (good comparison)",
        },
        {
            "id": "5",
            "name": "Lisa Anderson",
            "condition": "COPD",
            "base_o2": 90.5,  # Moderate COPD
            "base_hr": 74,
            "stress_pattern": "moderate",  # Average stress
            "description": "COPD patient with moderate stress management",
        },
    ]

    # Output directory
    data_dir = Path(__file__).parent.parent / "data" / "wearables"

    for patient in patients:
        print(f"\nGenerating data for {patient['name']} (Patient {patient['id']})...")
        print(f"  Condition: {patient['condition']}")
        print(f"  Stress pattern: {patient['stress_pattern']}")
        print(f"  Description: {patient['description']}")

        # Generate data
        data = generate_enhanced_patient_data(
            patient_id=patient["id"],
            patient_name=patient["name"],
            condition=patient["condition"],
            base_o2=patient["base_o2"],
            base_hr=patient["base_hr"],
            stress_pattern=patient["stress_pattern"],
        )

        # Calculate some stats
        stress_counts = {"Low": 0, "Medium": 0, "High": 0}
        o2_values = []
        hr_values = []

        for record in data:
            metrics = record["metrics"]
            stress_counts[metrics["stress_level"]] += 1
            o2_values.append(metrics["blood_oxygen_level"])
            hr_values.append(metrics["heart_rate"])

        avg_o2 = sum(o2_values) / len(o2_values)
        avg_hr = sum(hr_values) / len(hr_values)

        print("  Stats:")
        print(
            f"    Stress distribution: Low={stress_counts['Low']}, Med={stress_counts['Medium']}, High={stress_counts['High']}"
        )
        print(f"    Avg O2: {avg_o2:.1f}%")
        print(f"    Avg HR: {avg_hr:.0f} BPM")

        # Save to file
        output_path = data_dir / f"patient_{patient['id']}" / "daily_last_30_days.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  ✓ Saved to {output_path}")

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Generated wearable data for {len(patients)} patients")
    print("\nKey patterns for demo:")
    print("  • Patient 1: Escalating stress → worsening asthma symptoms")
    print("  • Patient 2: High stress → low O2 with COPD")
    print("  • Patient 3: Moderate stress with pulmonary fibrosis")
    print("  • Patient 4: LOW stress → better asthma control (good comparison)")
    print("  • Patient 5: Moderate stress with COPD")
    print("\nThese patterns will:")
    print("  ✓ Show clear stress-symptom correlations")
    print("  ✓ Be easy to find via vector similarity search")
    print("  ✓ Correlate with medical research on stress & respiratory disease")
    print("  ✓ Make clinical sense for pulmonology")
    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    main()
