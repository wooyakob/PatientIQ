import os
import traceback
from datetime import timedelta

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


endpoint = os.getenv("CLUSTER_CONNECTION_STRING")
username = os.getenv("CLUSTER_NAME")
password = os.getenv("CLUSTER_PASS")
bucket_name = os.getenv("COUCHBASE_BUCKET", "ckodb")

if not endpoint or not username or not password:
    raise RuntimeError(
        "Missing required environment variables. "
        "Please set CLUSTER_CONNECTION_STRING, CLUSTER_NAME, and CLUSTER_PASS (e.g. in .env)."
    )


auth = PasswordAuthenticator(username, password)
options = ClusterOptions(auth)
options.apply_profile("wan_development")

print(f"Testing Couchbase connection...")
print(f"  Cluster: {endpoint}")
print(f"  Bucket: {bucket_name}")
print()

try:
    # Connect to cluster
    cluster = Cluster(endpoint, options)
    cluster.wait_until_ready(timedelta(seconds=5))
    print("Connected to Couchbase cluster successfully")

    # Access bucket
    bucket = cluster.bucket(bucket_name)
    print(f"Bucket '{bucket_name}' is accessible")

    # Test each scope and collection
    print(f"\nTesting scopes and collections:")

    scopes_to_test = {
        "People": ["Patient", "Doctor"],
        "Research": ["pubmed"],
        "Wearables": ["Watch", "Phone"],
        "Notes": ["Patient", "Doctor"]
    }

    all_good = True
    for scope_name, collections in scopes_to_test.items():
        try:
            scope = bucket.scope(scope_name)
            print(f"  Scope: {scope_name}")

            for collection_name in collections:
                try:
                    collection = scope.collection(collection_name)
                    print(f"    Collection: {collection_name}")
                except Exception as e:
                    print(f"    Collection: {collection_name} - {e}")
                    all_good = False

        except Exception as e:
            print(f"  Scope: {scope_name} - {e}")
            all_good = False

    print()

    if all_good:
        print("Database structure is correct!")
        print(f"\nNext step: Start the backend with:")
        print(f"  uvicorn backend.api:app --reload --port 8000")
    else:
        print("Some scopes/collections are missing")
        print("\nExpected structure:")
        print(f"  ckodb/")
        for scope_name, collections in scopes_to_test.items():
            print(f"    {scope_name}/")
            for collection_name in collections:
                print(f"      - {collection_name}")
        print(f"\nSee DATABASE_STRUCTURE.md for details")

except Exception as e:
    print(f"Connection failed: {e}")
    traceback.print_exc()
    print("\nTroubleshooting:")
    print(f"  1. Verify credentials in .env file")
    print(f"  2. Check IP allowlist in Couchbase Capella")
    print(f"  3. Ensure ckodb bucket exists with proper scopes")
    print(f"  4. See capella_structure.md for expected structure")
