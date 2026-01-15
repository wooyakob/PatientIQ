"""
Shared utilities for Couchbase medical tools.

This module provides common resources like database connections and helper functions
that are used across multiple tools. It's prefixed with _ to avoid being indexed as a tool.
"""

import couchbase.auth
import couchbase.cluster
import couchbase.exceptions
import couchbase.options
import dotenv
import os
import requests
import warnings

dotenv.load_dotenv()
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Shared Couchbase cluster connection
# Agent Catalog imports tool files, so this connection is reused across tools
try:
    cluster = couchbase.cluster.Cluster(
        os.getenv("CLUSTER_CONNECTION_STRING") or os.getenv("CB_CONN_STRING"),
        couchbase.options.ClusterOptions(
            authenticator=couchbase.auth.PasswordAuthenticator(
                username=os.getenv("CLUSTER_USERNAME") or os.getenv("CB_USERNAME"),
                password=os.getenv("CLUSTER_PASS") or os.getenv("CB_PASSWORD"),
                certpath=os.getenv("AGENT_CATALOG_CONN_ROOT_CERTIFICATE")
                or os.getenv("CB_CERTIFICATE"),
            )
        ),
    )
except couchbase.exceptions.CouchbaseException as e:
    print(f"""
        Could not connect to Couchbase cluster!
        Make sure environment variables are set correctly.
        {str(e)}
    """)
    cluster = None


def get_nvidia_embedding(text: str) -> list[float]:
    """
    Generate a 2048-dimensional embedding vector using NVIDIA's embedding model.

    Args:
        text: The text to embed

    Returns:
        2048-dimensional embedding vector

    Raises:
        ValueError: If environment variables are missing or embedding fails
    """
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_name = os.getenv("EMBEDDING_MODEL_NAME", "nvidia/llama-3.2-nv-embedqa-1b-v2")

    if not all([endpoint, token]):
        raise ValueError("Missing EMBEDDING_MODEL_ENDPOINT or EMBEDDING_MODEL_TOKEN in environment")

    url = f"{endpoint}/v1/embeddings"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"input": text, "model": model_name}

    res = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    res.raise_for_status()
    data = res.json()

    embedding = data["data"][0]["embedding"]
    if not isinstance(embedding, list) or len(embedding) != 2048:
        raise ValueError(f"Unexpected embedding length: {len(embedding)}")

    return embedding
