#!/usr/bin/env python3
"""
CLI tool to test the pre-visit summary agent.

Usage:
    python main.py <patient_id>

Example:
    python main.py 2
"""

import argparse
import json
import sys

import agentc
import dotenv
import langchain_core.messages

from graph import PrevisitSummarizer

dotenv.load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Generate pre-visit summary for a patient")
    parser.add_argument("patient_id", help="Patient ID to generate summary for")
    parser.add_argument(
        "--no-tracing",
        action="store_true",
        help="Disable tracing output",
    )
    args = parser.parse_args()

    try:
        # Initialize catalog
        catalog = agentc.Catalog()

        # Create the summarizer
        summarizer = PrevisitSummarizer(catalog=catalog)

        # Build starting state
        state = PrevisitSummarizer.build_starting_state(patient_id=args.patient_id)

        # Add initial message
        state["messages"].append(
            langchain_core.messages.HumanMessage(content=f'{{"patient_id": "{args.patient_id}"}}')
        )

        print(f"\n🏥 Generating pre-visit summary for patient {args.patient_id}...\n")

        # Run the agent
        result = summarizer.invoke(input=state)

        # Display results
        print("=" * 80)
        print(f"PATIENT: {result.get('patient_name', 'Unknown')}")
        print("=" * 80)
        print()
        print("CLINICAL SUMMARY:")
        print(result.get("clinical_summary", "No summary generated"))
        print()
        print("=" * 80)
        print(f"CURRENT MEDICATIONS ({len(result.get('current_medications', []))}):")
        for med in result.get("current_medications", []):
            print(f"  • {med.get('name')} - {med.get('dosage')} - {med.get('frequency')}")
        print()
        print("ALLERGIES:")
        allergies = result.get("allergies", {})
        if allergies.get("drug"):
            print(f"  Drug: {', '.join(allergies['drug'])}")
        if allergies.get("food"):
            print(f"  Food: {', '.join(allergies['food'])}")
        if allergies.get("environmental"):
            print(f"  Environmental: {', '.join(allergies['environmental'])}")
        print()
        print(f"KEY SYMPTOMS ({len(result.get('key_symptoms', []))}):")
        for symptom in result.get("key_symptoms", []):
            print(f"  • {symptom}")
        print()
        print(f"PATIENT CONCERNS ({len(result.get('patient_concerns', []))}):")
        for concern in result.get("patient_concerns", []):
            print(f"  • {concern}")
        print()
        if result.get("recent_note_summary"):
            print("RECENT NOTE:")
            print(f"  {result.get('recent_note_summary')}")
            print()
        print("=" * 80)
        print()

        # Optionally output JSON
        print("Full JSON Output:")
        output_data = {
            "patient_id": result.get("patient_id"),
            "patient_name": result.get("patient_name"),
            "clinical_summary": result.get("clinical_summary"),
            "current_medications": result.get("current_medications"),
            "allergies": result.get("allergies"),
            "key_symptoms": result.get("key_symptoms"),
            "patient_concerns": result.get("patient_concerns"),
            "recent_note_summary": result.get("recent_note_summary"),
        }
        print(json.dumps(output_data, indent=2))

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
