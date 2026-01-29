#!/usr/bin/env python3
"""
Script to populate wearable trend vectors.

This script:
1. Reads existing wearable data for each patient
2. Vectorizes the 30-day trends using the new vectorization tool
3. Stores the vectors in Couchbase for vector similarity search
"""

import sys
import os
from pathlib import Path

# Add project root and tools directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))

from backend.database import CouchbaseDB
from tools.vectorize_wearable_trends import vectorize_wearable_trends
from tools.get_wearable_data_by_patient import get_wearable_data_by_patient
from tools.find_conditions_by_patient_id import find_conditions_by_patient_id

def main():
    """Populate wearable trend vectors for all patients."""
    
    print("=" * 80)
    print("POPULATING WEARABLE TREND VECTORS")
    print("=" * 80)
    
    # Initialize database
    db = CouchbaseDB()
    db._ensure_connected()
    
    if db._connection_error:
        print(f"❌ Database connection failed: {db._connection_error}")
        return 1
    
    print("✓ Connected to Couchbase")
    
    # Patient IDs to process
    patient_ids = ["1", "2", "3", "4", "5"]
    
    # Condition mapping (for demo purposes)
    # In production, we'd get this from the database
    condition_map = {
        "1": "Asthma",
        "2": "COPD", 
        "3": "Pulmonary Fibrosis",
        "4": "Asthma",
        "5": "COPD"
    }
    
    success_count = 0
    error_count = 0
    
    for patient_id in patient_ids:
        print(f"\n{'─' * 80}")
        print(f"Processing Patient {patient_id}...")
        print(f"{'─' * 80}")
        
        try:
            # Step 1: Get wearable data
            print(f"  1. Fetching wearable data (30 days)...")
            wearable_data = get_wearable_data_by_patient(
                patient_id=patient_id,
                days=30
            )
            
            # Check if it's a list or dict response
            if isinstance(wearable_data, dict):
                # If dict, extract the data array
                wearable_data = wearable_data.get("wearable_data", wearable_data.get("data", []))
            
            if not wearable_data or not isinstance(wearable_data, list):
                print(f"  ⚠️  No wearable data found for patient {patient_id}")
                error_count += 1
                continue
            
            print(f"     ✓ Found {len(wearable_data)} data points")
            
            # Step 2: Get patient condition
            print(f"  2. Getting patient condition...")
            # Try to get from database first
            try:
                condition_result = find_conditions_by_patient_id(patient_id=patient_id)
                conditions = condition_result.get("conditions", [])
                if conditions and len(conditions) > 0:
                    condition = conditions[0].get("condition_name", condition_map.get(patient_id, "Unknown"))
                else:
                    condition = condition_map.get(patient_id, "Unknown")
            except Exception:
                condition = condition_map.get(patient_id, "Unknown")
            
            print(f"     ✓ Condition: {condition}")
            
            # Step 3: Vectorize the trend
            print(f"  3. Vectorizing wearable trends...")
            vector_result = vectorize_wearable_trends(
                wearable_data=wearable_data,
                patient_condition=condition
            )
            
            if "error" in vector_result:
                print(f"     ❌ Vectorization failed: {vector_result['error']}")
                error_count += 1
                continue
            
            trend_text = vector_result.get("trend_text", "")
            trend_vector = vector_result.get("trend_vector", [])
            normalized_metrics = vector_result.get("normalized_metrics", {})
            summary = vector_result.get("summary", {})
            
            print(f"     ✓ Vector dimensions: {summary.get('vector_dimensions', 0)}")
            print(f"     ✓ Metrics tracked: {', '.join(summary.get('metrics_tracked', []))}")
            print(f"     ✓ Trend: {trend_text[:100]}...")
            
            # Step 4: Store in database
            print(f"  4. Storing vector in Couchbase...")
            
            # Get patient name from first wearable record
            patient_name = wearable_data[0].get("patient_name", f"Patient {patient_id}")
            
            # Create trend summary document
            trend_doc = {
                "type": "wearable_trend_summary",
                "patient_id": patient_id,
                "patient_name": patient_name,
                "condition": condition,
                "trend_summary": trend_text,
                "wearable_trend_vector": trend_vector,
                "normalized_metrics": normalized_metrics,
                "last_updated": "2026-01-22T00:00:00Z",
                "days_analyzed": len(wearable_data),
                "vector_dimensions": len(trend_vector),
                "metrics_tracked": summary.get("metrics_tracked", [])
            }
            
            # Store in Wearables scope for the patient
            try:
                collection = db.bucket.scope("Wearables").collection(f"Patient_{patient_id}")
                collection.upsert(f"trend_summary", trend_doc)
                print(f"     ✓ Stored in Wearables.Patient_{patient_id}")
                success_count += 1
            except Exception as e:
                print(f"     ⚠️  Failed to store in patient collection: {e}")
                error_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing patient {patient_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Total patients: {len(patient_ids)}")
    print(f"  ✓ Success: {success_count}")
    print(f"  ✗ Errors: {error_count}")    
    print(f"\n{'=' * 80}\n")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
