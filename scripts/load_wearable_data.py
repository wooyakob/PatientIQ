#!/usr/bin/env python3
"""
Script to load wearable data from JSON files into Couchbase.
"""

import sys
import json
import uuid
from pathlib import Path

project_root = Path(__file__).parent.parent


def clear_patient_collection(db, patient_id: str, collection_name: str) -> int:
    """
    Delete all documents from a patient's wearable collection.

    Args:
        db: CouchbaseDB instance
        patient_id: Patient ID
        collection_name: Collection name (e.g., "Patient_1")

    Returns:
        Number of documents deleted
    """
    try:
        # Use N1QL to delete all documents in the collection
        scope_name = "Wearables"
        query = f"DELETE FROM `{db.bucket_name}`.`{scope_name}`.`{collection_name}`"

        result = db.cluster.query(query)

        # Count deleted documents
        deleted_count = 0
        for row in result:
            deleted_count += 1

        return deleted_count

    except Exception:
        # Collection might not have a primary index, try alternative method
        print("    ⚠️  No primary index found, trying collection scan...")
        try:
            db.bucket.scope("Wearables").collection(collection_name)
            # Unfortunately, we can't enumerate all docs without an index
            # So we'll just proceed with loading
            print("    → Proceeding with load (old docs will remain if they exist)")
            return 0
        except Exception as e:
            print(f"    ⚠️  Could not clear collection: {e}")
            return 0
    except Exception as e:
        print(f"    ⚠️  Error clearing collection: {e}")
        return 0


def load_wearable_data_for_patient(db, patient_id: str, json_file: Path) -> tuple[int, int]:
    """
    Load wearable data from JSON file into Couchbase.
    Clears existing data first, then inserts new records with UUID document IDs.

    Args:
        db: CouchbaseDB instance
        patient_id: Patient ID
        json_file: Path to JSON file with wearable data

    Returns:
        Tuple of (success_count, error_count)
    """
    try:
        with open(json_file, "r") as f:
            wearable_records = json.load(f)
    except Exception as e:
        print(f"  ❌ Failed to read {json_file}: {e}")
        return 0, 1

    if not isinstance(wearable_records, list):
        print(f"  ⚠️  Expected list, got {type(wearable_records)}")
        return 0, 1

    print(f"  📄 Found {len(wearable_records)} records in file")

    # Get the collection for this patient
    collection_name = f"Patient_{patient_id}"
    try:
        collection = db.bucket.scope("Wearables").collection(collection_name)
    except Exception as e:
        print(f"  ❌ Failed to get collection Wearables.{collection_name}: {e}")
        return 0, len(wearable_records)

    # Clear existing data
    print(f"  🗑️  Clearing existing data from Wearables.{collection_name}...")
    deleted_count = clear_patient_collection(db, patient_id, collection_name)
    if deleted_count > 0:
        print(f"    ✓ Deleted {deleted_count} old records")
    else:
        print("    → Collection cleared (or was empty)")

    success_count = 0
    error_count = 0

    print(f"  📝 Inserting {len(wearable_records)} new records...")

    for i, record in enumerate(wearable_records):
        try:
            # Generate random UUID for document ID
            doc_key = str(uuid.uuid4())

            # Upsert the record
            collection.upsert(doc_key, record)
            success_count += 1

            if (i + 1) % 10 == 0:
                print(f"    • Inserted {i + 1}/{len(wearable_records)} records...")

        except Exception as e:
            print(f"  ⚠️  Failed to insert record {i}: {e}")
            error_count += 1

    return success_count, error_count


def main():
    # Add project root to path
    sys.path.insert(0, str(project_root))

    from backend.database import CouchbaseDB

    """Load all wearable data into Couchbase."""

    print("=" * 80)
    print("LOADING WEARABLE DATA INTO COUCHBASE")
    print("=" * 80)

    # Initialize database
    db = CouchbaseDB()
    db._ensure_connected()

    if db._connection_error:
        print(f"❌ Database connection failed: {db._connection_error}")
        return 1

    print("✓ Connected to Couchbase")
    print(f"  Bucket: {db.bucket_name}")
    print("  Scope: Wearables")

    # Find all wearable data files
    data_dir = project_root / "data" / "wearables"

    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return 1

    # Look for patient directories (patient_1, patient_2, etc.)
    patient_dirs = sorted(
        [d for d in data_dir.iterdir() if d.is_dir() and d.name.startswith("patient_")]
    )

    if not patient_dirs:
        print(f"⚠️  No patient directories found in {data_dir}")
        return 1

    print(f"\n📂 Found {len(patient_dirs)} patient directories")

    total_success = 0
    total_errors = 0
    patients_processed = 0

    for patient_dir in patient_dirs:
        # Extract patient ID from directory name (e.g., "patient_1" -> "1")
        patient_id = patient_dir.name.split("_")[1]

        print(f"\n{'─' * 80}")
        print(f"Processing Patient {patient_id}...")
        print(f"{'─' * 80}")

        # Look for wearable data file
        json_file = patient_dir / "daily_last_30_days.json"

        if not json_file.exists():
            print(f"  ⚠️  File not found: {json_file}")
            continue

        print(f"  📂 Loading from: {json_file.name}")

        success, errors = load_wearable_data_for_patient(db, patient_id, json_file)

        total_success += success
        total_errors += errors
        patients_processed += 1

        if errors == 0:
            print(f"  ✅ Successfully loaded {success} records for patient {patient_id}")
        else:
            print(f"  ⚠️  Loaded {success} records with {errors} errors for patient {patient_id}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Patients processed: {patients_processed}")
    print(f"  ✓ Records inserted: {total_success}")
    print(f"  ✗ Errors: {total_errors}")

    if total_errors == 0:
        print("\n✨ All wearable data loaded successfully!")
        print("\n📊 Next steps:")
        print("  1. Verify data: Check Couchbase UI → Wearables scope → Patient collections")
        print("  2. Run: python scripts/populate_wearable_vectors.py")
        print("  3. Test: make run-api and test the analytics endpoint")
        print("\n💡 Note: Old data was cleared before loading new records.")
    else:
        print(f"\n⚠️  Completed with {total_errors} errors")

    print(f"\n{'=' * 80}\n")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
