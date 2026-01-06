"""
Seed database with fake data for testing functionality.

This script populates all collections in the ckodb bucket with realistic test data:
- People.Patient: Patient demographics and wearable data
- Research.pubmed: Medical research summaries from PubMedCentral.json
- Wearables.Watch: Wearable alerts
- Notes.Doctor: Doctor notes
- Notes.Patient: Patient notes
- Notes.Doctor (temp): Questionnaire summaries
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

from backend.database import db

# Sample patient data matching frontend structure
PATIENTS_DATA = [
    {
        "id": "patient-001",
        "name": "Sarah Mitchell",
        "age": 45,
        "gender": "Female",
        "condition": "Breast Cancer Stage II",
        "avatar": "SM",
        "last_visit": "2024-01-15",
        "next_appointment": "2024-02-01",
        "wearable_data": {
            "heart_rate": [72, 75, 68, 71, 74, 69, 73, 70, 72, 74],
            "step_count": [4500, 5200, 3800, 4100, 4800, 5500, 4200, 4900, 5100, 4700]
        },
        "sentiment": "good",
        "private_notes": "Feeling more optimistic after last treatment. Energy levels improving. Family support has been incredible."
    },
    {
        "id": "patient-002",
        "name": "James Anderson",
        "age": 62,
        "gender": "Male",
        "condition": "Type 2 Diabetes",
        "avatar": "JA",
        "last_visit": "2024-01-18",
        "next_appointment": "2024-02-15",
        "wearable_data": {
            "heart_rate": [78, 82, 76, 80, 79, 77, 81, 78, 80, 79],
            "step_count": [3200, 2800, 3500, 2900, 3100, 3400, 2700, 3300, 2950, 3150]
        },
        "sentiment": "neutral",
        "private_notes": "Struggling with diet changes. Miss my usual foods. Trying to stay positive but it's hard."
    },
    {
        "id": "patient-003",
        "name": "Emily Chen",
        "age": 34,
        "gender": "Female",
        "condition": "Anxiety Disorder",
        "avatar": "EC",
        "last_visit": "2024-01-20",
        "next_appointment": "2024-01-27",
        "wearable_data": {
            "heart_rate": [85, 92, 78, 88, 82, 90, 86, 89, 84, 87],
            "step_count": [6200, 7500, 5800, 8100, 6900, 7200, 6500, 7800, 6400, 7100]
        },
        "sentiment": "poor",
        "private_notes": "Work stress overwhelming. Sleep has been terrible. Panic attacks returning. Feel like I'm failing at everything."
    },
    {
        "id": "patient-004",
        "name": "Robert Williams",
        "age": 55,
        "gender": "Male",
        "condition": "Hypertension",
        "avatar": "RW",
        "last_visit": "2024-01-12",
        "next_appointment": "2024-02-12",
        "wearable_data": {
            "heart_rate": [68, 70, 66, 72, 69, 71, 67, 69, 70, 68],
            "step_count": [8500, 9200, 7800, 8900, 9500, 8100, 8700, 9100, 8800, 9000]
        },
        "sentiment": "amazing",
        "private_notes": "Feeling the best I have in years! Walking every day, blood pressure under control. Life is good!"
    },
    {
        "id": "patient-005",
        "name": "Maria Rodriguez",
        "age": 38,
        "gender": "Female",
        "condition": "Multiple Sclerosis",
        "avatar": "MR",
        "last_visit": "2024-01-22",
        "next_appointment": "2024-02-05",
        "wearable_data": {
            "heart_rate": [74, 76, 72, 75, 73, 77, 74, 75, 73, 76],
            "step_count": [2500, 2800, 2200, 2600, 2900, 2400, 2700, 2550, 2650, 2750]
        },
        "sentiment": "neutral",
        "private_notes": "Some days are better than others. Fatigue is still my biggest challenge. New medication seems promising."
    }
]

# Condition to research topic mapping
CONDITION_RESEARCH_KEYWORDS = {
    "Breast Cancer Stage II": ["breast cancer", "cancer therapy", "oncology", "tumor"],
    "Type 2 Diabetes": ["diabetes", "glucose", "insulin", "glycemic"],
    "Anxiety Disorder": ["anxiety", "mental health", "psychiatric", "stress"],
    "Hypertension": ["hypertension", "blood pressure", "cardiovascular"],
    "Multiple Sclerosis": ["multiple sclerosis", "neurological", "autoimmune", "neurodegenerative"]
}

# Doctor notes templates
DOCTOR_NOTES_TEMPLATES = {
    "Breast Cancer Stage II": [
        "Patient responding well to current treatment regimen. Tumor markers showing decrease. Recommend continuing current protocol.",
        "Reviewed imaging results. No new metastases detected. Patient reports mild fatigue but manageable.",
        "Discussed treatment options. Patient elected to continue with current chemotherapy cycle. Next scan scheduled."
    ],
    "Type 2 Diabetes": [
        "HbA1c improved to 7.2%. Discussed importance of consistent medication adherence. Referred to dietitian for meal planning support.",
        "Blood glucose levels showing improvement. Continue with current medication regimen. Emphasized importance of daily exercise.",
        "Patient struggling with dietary compliance. Adjusted medication dosage. Scheduled follow-up with nutritionist."
    ],
    "Anxiety Disorder": [
        "Increased anxiety symptoms noted. Adjusted medication dosage. Strongly recommended resuming weekly therapy sessions. Follow-up in one week.",
        "Patient stable on current regimen. Practicing breathing exercises regularly. Continue monitoring.",
        "Panic attacks have increased in frequency. Referred to CBT specialist. Adjusted SSRI dosage."
    ],
    "Hypertension": [
        "Excellent progress! BP consistently at target. Patient highly motivated with exercise regimen. Reduced medication dosage as reward for lifestyle changes.",
        "Blood pressure readings within normal range. Continue current medication. Encouraged to maintain physical activity.",
        "Slight elevation in BP noted. Discussed stress management techniques. May need to adjust medication if trends continue."
    ],
    "Multiple Sclerosis": [
        "MRI stable, no new lesions detected. Patient tolerating new DMT well. Continue current treatment plan.",
        "Fatigue levels reported as moderate. Discussed energy conservation strategies. Consider physical therapy referral.",
        "Recent exacerbation managed with IV steroids. Good response observed. Resume maintenance therapy."
    ]
}

# Wearable alert templates
WEARABLE_ALERTS = [
    {
        "alert_type": "Elevated Heart Rate",
        "severity": "high",
        "message_template": "Sustained elevated heart rate detected. Average HR: {avg_hr} bpm over the past 7 days, exceeding normal range for patient's age and condition.",
        "trigger": lambda data: sum(data["heart_rate"][-7:]) / 7 > 85
    },
    {
        "alert_type": "Low Activity Level",
        "severity": "medium",
        "message_template": "Step count below recommended threshold. Average: {avg_steps} steps/day. Target: 5000+ steps for optimal cardiovascular health.",
        "trigger": lambda data: sum(data["step_count"][-7:]) / 7 < 4000
    },
    {
        "alert_type": "Heart Rate Variability",
        "severity": "medium",
        "message_template": "Increased heart rate variability detected. This may indicate stress or irregular activity patterns. Recent range: {min_hr}-{max_hr} bpm.",
        "trigger": lambda data: max(data["heart_rate"][-7:]) - min(data["heart_rate"][-7:]) > 20
    }
]

def load_pubmed_articles() -> List[Dict]:
    """Load PubMedCentral.json articles."""
    pubmed_path = os.path.join(os.path.dirname(__file__), "..", "data", "PubMedCentral.json")
    try:
        with open(pubmed_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} articles from PubMedCentral.json")
        return articles
    except Exception as e:
        print(f"Error loading PubMedCentral.json: {e}")
        return []

def extract_research_summary(article_text: str, max_length: int = 500) -> str:
    """Extract a meaningful summary from article text."""
    # Try to find the abstract or introduction
    if "Abstract" in article_text:
        start = article_text.find("Abstract")
        end = article_text.find("\n\n", start + 100)
        if end > start:
            summary = article_text[start:end].replace("Abstract", "").strip()
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            return summary

    # Otherwise, take first meaningful paragraph
    paragraphs = [p.strip() for p in article_text.split("\n\n") if len(p.strip()) > 100]
    if paragraphs:
        summary = paragraphs[0]
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary

    return "Research summary not available."

def find_relevant_research(condition: str, articles: List[Dict], num_summaries: int = 3) -> List[str]:
    """Find relevant research articles for a condition."""
    keywords = CONDITION_RESEARCH_KEYWORDS.get(condition, [])
    if not keywords or not articles:
        return [
            f"Recent advances in {condition} treatment continue to show promise.",
            f"Clinical trials for {condition} demonstrate improved patient outcomes.",
            f"New therapeutic approaches for {condition} are under investigation."
        ]

    relevant_articles = []
    for article in articles:
        article_text = article.get("article_text", "").lower()
        # Check if any keyword appears in the article
        if any(keyword.lower() in article_text for keyword in keywords):
            relevant_articles.append(article)
            if len(relevant_articles) >= num_summaries * 2:  # Get extra for variety
                break

    # Extract summaries
    summaries = []
    for article in relevant_articles[:num_summaries]:
        summary = extract_research_summary(article.get("article_text", ""))
        if summary and summary not in summaries:
            summaries.append(summary)

    # Fill with generic summaries if needed
    while len(summaries) < num_summaries:
        summaries.append(f"Research on {condition} continues to advance with new clinical findings.")

    return summaries[:num_summaries]

def seed_patients(articles: List[Dict]):
    """Seed the People.Patient collection."""
    print("\n=== Seeding Patients ===")

    for patient_data in PATIENTS_DATA:
        try:
            # Add research content
            research_summaries = find_relevant_research(patient_data["condition"], articles)
            patient_data["research_topic"] = f"{patient_data['condition']} Treatment Advances"
            patient_data["research_content"] = research_summaries

            # Save to database
            success = db.upsert_patient(patient_data["id"], patient_data)
            if success:
                print(f"Created patient: {patient_data['name']} ({patient_data['id']})")
            else:
                print(f"Failed to create patient: {patient_data['name']}")
        except Exception as e:
            print(f"Error creating patient {patient_data['name']}: {e}")

def seed_research_summaries(articles: List[Dict]):
    """Seed the Research.pubmed collection."""
    print("\n=== Seeding Research Summaries ===")

    for patient_data in PATIENTS_DATA:
        try:
            research_summaries = find_relevant_research(patient_data["condition"], articles)

            research_doc = {
                "patient_id": patient_data["id"],
                "condition": patient_data["condition"],
                "topic": f"{patient_data['condition']} Treatment Advances",
                "summaries": research_summaries,
                "sources": [f"PMID:{random.randint(10000000, 40000000)}" for _ in range(len(research_summaries))],
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }

            research_id = f"research-{uuid.uuid4()}"
            success = db.save_research_summary(research_id, research_doc)
            if success:
                print(f"Created research summary for: {patient_data['name']}")
            else:
                print(f"Failed to create research summary for: {patient_data['name']}")
        except Exception as e:
            print(f"Error creating research summary for {patient_data['name']}: {e}")

def seed_wearable_alerts():
    """Seed the Wearables.Watch collection."""
    print("\n=== Seeding Wearable Alerts ===")

    for patient_data in PATIENTS_DATA:
        try:
            wearable_data = patient_data["wearable_data"]

            # Check each alert condition
            for alert_config in WEARABLE_ALERTS:
                if alert_config["trigger"](wearable_data):
                    # Create alert
                    avg_hr = sum(wearable_data["heart_rate"][-7:]) / 7
                    avg_steps = sum(wearable_data["step_count"][-7:]) / 7
                    min_hr = min(wearable_data["heart_rate"][-7:])
                    max_hr = max(wearable_data["heart_rate"][-7:])

                    message = alert_config["message_template"].format(
                        avg_hr=int(avg_hr),
                        avg_steps=int(avg_steps),
                        min_hr=min_hr,
                        max_hr=max_hr
                    )

                    alert_doc = {
                        "patient_id": patient_data["id"],
                        "alert_type": alert_config["alert_type"],
                        "severity": alert_config["severity"],
                        "message": message,
                        "metrics": {
                            "heart_rate": wearable_data["heart_rate"][-7:],
                            "step_count": wearable_data["step_count"][-7:]
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }

                    alert_id = f"alert-{uuid.uuid4()}"
                    success = db.save_wearable_alert(alert_id, alert_doc)
                    if success:
                        print(f"Created {alert_config['alert_type']} alert for: {patient_data['name']}")
        except Exception as e:
            print(f"Error creating wearable alert for {patient_data['name']}: {e}")

def seed_doctor_notes():
    """Seed the Notes.Doctor collection."""
    print("\n=== Seeding Doctor Notes ===")

    for patient_data in PATIENTS_DATA:
        try:
            condition = patient_data["condition"]
            notes_templates = DOCTOR_NOTES_TEMPLATES.get(condition, [
                "Patient visit completed. Continue monitoring.",
                "Reviewed treatment plan with patient. No changes at this time."
            ])

            # Create 2-3 notes per patient
            num_notes = random.randint(2, 3)
            for i in range(num_notes):
                # Calculate date (going backwards from today)
                days_ago = (num_notes - i) * 7  # Weekly notes
                note_date = datetime.now() - timedelta(days=days_ago)

                note_doc = {
                    "patient_id": patient_data["id"],
                    "doctor_id": "doctor-001",
                    "date": note_date.strftime("%Y-%m-%d"),
                    "time": f"{random.randint(9, 16)}:{random.choice(['00', '15', '30', '45'])} {'AM' if random.randint(9, 16) < 12 else 'PM'}",
                    "content": random.choice(notes_templates),
                    "tags": ["follow-up", "treatment-review"] if i == 0 else ["routine-visit"]
                }

                note_id = f"note-{uuid.uuid4()}"
                success = db.save_doctor_note(note_id, note_doc)
                if success:
                    print(f"Created doctor note for: {patient_data['name']} ({note_date.strftime('%Y-%m-%d')})")
        except Exception as e:
            print(f"Error creating doctor note for {patient_data['name']}: {e}")

def seed_patient_notes():
    """Seed the Notes.Patient collection."""
    print("\n=== Seeding Patient Notes ===")

    for patient_data in PATIENTS_DATA:
        try:
            # Use private_notes as content
            note_doc = {
                "patient_id": patient_data["id"],
                "content": patient_data["private_notes"],
                "mood": patient_data["sentiment"],
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            note_id = f"patient-note-{uuid.uuid4()}"
            success = db.save_patient_note(note_id, note_doc)
            if success:
                print(f"Created patient note for: {patient_data['name']}")
        except Exception as e:
            print(f"Error creating patient note for {patient_data['name']}: {e}")

def seed_questionnaires():
    """Seed questionnaire summaries (temporary location in Notes.Doctor)."""
    print("\n=== Seeding Questionnaire Summaries ===")

    questionnaire_templates = {
        "good": "Patient reports improved symptoms and overall well-being. Treatment compliance is excellent.",
        "amazing": "Patient feeling significantly better with marked improvement in quality of life.",
        "neutral": "Patient condition stable with mixed response to current treatment regimen.",
        "poor": "Patient reporting worsening symptoms. Treatment adjustments may be needed.",
        "terrible": "Patient experiencing severe symptoms requiring immediate attention."
    }

    for patient_data in PATIENTS_DATA:
        try:
            sentiment = patient_data["sentiment"]

            questionnaire_doc = {
                "patient_id": patient_data["id"],
                "appointment_date": patient_data["next_appointment"],
                "summary": questionnaire_templates.get(sentiment, "Patient questionnaire completed."),
                "key_points": [
                    f"Current condition: {patient_data['condition']}",
                    f"Overall mood: {sentiment}",
                    patient_data["private_notes"][:100] + "..." if len(patient_data["private_notes"]) > 100 else patient_data["private_notes"]
                ],
                "red_flags": [] if sentiment in ["good", "amazing", "neutral"] else ["Increased symptom severity", "Consider urgent follow-up"],
                "questionnaire_responses": {
                    "How are you feeling overall?": sentiment.capitalize(),
                    "Any new symptoms?": "See notes for details",
                    "Treatment compliance?": "Good" if sentiment in ["good", "amazing"] else "Moderate"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }

            questionnaire_id = f"questionnaire-{uuid.uuid4()}"
            success = db.save_questionnaire_summary(questionnaire_id, questionnaire_doc)
            if success:
                print(f"Created questionnaire summary for: {patient_data['name']}")
        except Exception as e:
            print(f"Error creating questionnaire for {patient_data['name']}: {e}")

def main():
    """Main seeding function."""
    print("="*60)
    print("Database Seeding Script")
    print("="*60)
    print(f"\nBucket: {db.bucket_name}")
    print(f"Collections to seed:")
    print("  - People.Patient")
    print("  - Research.pubmed")
    print("  - Wearables.Watch")
    print("  - Notes.Doctor")
    print("  - Notes.Patient")
    print("  - Notes.Doctor (questionnaire_summary)")
    print()

    try:
        # Load research articles
        articles = load_pubmed_articles()

        # Seed all collections
        seed_patients(articles)
        seed_research_summaries(articles)
        seed_wearable_alerts()
        seed_doctor_notes()
        seed_patient_notes()
        seed_questionnaires()

        print("\n" + "=" * 60)
        print("Database seeding completed!")
        print("=" * 60)
        print(f"\nSeeded data:")
        print(f"  - {len(PATIENTS_DATA)} patients")
        print(f"  - {len(PATIENTS_DATA)} research summaries")
        print(f"  - Wearable alerts (condition-based)")
        print(f"  - {len(PATIENTS_DATA) * 2} doctor notes (avg)")
        print(f"  - {len(PATIENTS_DATA)} patient notes")
        print(f"  - {len(PATIENTS_DATA)} questionnaire summaries")
        print("\nNext steps:")
        print("  1. Start backend: uvicorn backend.api:app --reload --port 8000")
        print("  2. Test API: curl http://localhost:8000/api/patients")
        print("  3. View in browser: http://localhost:8080")

    except Exception as e:
        print(f"\nSeeding failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
