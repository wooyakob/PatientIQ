"""
Create necessary indexes for the ckodb database collections.

N1QL queries require indexes to function. This script creates primary indexes
on all collections that need to be queried.
"""

from backend.database import db

def create_indexes():
    """Create primary indexes on all collections."""
    print("="*60)
    print("Creating Database Indexes")
    print("="*60)
    print(f"\nBucket: {db.bucket_name}\n")

    indexes = [
        ("People", "Patient"),
        ("Research", "pubmed"),
        ("Wearables", "Watch"),
        ("Notes", "Doctor"),
        ("Notes", "Patient"),
    ]

    for scope_name, collection_name in indexes:
        try:
            index_name = f"idx_{scope_name}_{collection_name}".replace(".", "_").lower()
            query = f"""
                CREATE PRIMARY INDEX `{index_name}`
                ON `{db.bucket_name}`.`{scope_name}`.`{collection_name}`
            """

            print(f"Creating index on {scope_name}.{collection_name}... ", end="")
            for _ in db.cluster.query(query):
                pass
            print("OK")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "index already exists" in error_msg.lower():
                print("OK (already exists)")
            else:
                print(f"Error: {e}")

    print("\n" + "="*60)
    print("Index creation completed")
    print("="*60)
    print("\nIndexes allow N1QL queries to function efficiently.")
    print("Without indexes, queries will fail with 'No index available' errors.")
    print("\nNext steps:")
    print("  1. Verify indexes: Run query in Capella UI")
    print("  2. Test queries: python -m backend.seed_database")
    print("  3. Start backend: uvicorn backend.api:app --reload --port 8000")

if __name__ == "__main__":
    try:
        create_indexes()
    except Exception as e:
        print(f"\nIndex creation failed: {e}")
        import traceback
        traceback.print_exc()
