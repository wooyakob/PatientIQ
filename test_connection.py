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

if not endpoint or not username or not password:
	raise RuntimeError(
		"Missing required environment variables. Please set CLUSTER_CONNECTION_STRING, CLUSTER_NAME, and CLUSTER_PASS (e.g. in .env)."
	)


auth = PasswordAuthenticator(username, password)
options = ClusterOptions(auth)
options.apply_profile("wan_development")

try:
	cluster = Cluster(endpoint, options)
	cluster.wait_until_ready(timedelta(seconds=5))
	print("Connected to Couchbase cluster successfully.")
except Exception:
	traceback.print_exc()
