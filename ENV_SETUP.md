# Environment Variables Configuration

Copy this file to `.env` and fill in your actual values.

```bash
# Couchbase Cluster Configuration
CLUSTER_CONNECTION_STRING=couchbases://your-cluster.cloud.couchbase.com
CLUSTER_NAME=your-username
CLUSTER_PASS=your-password
COUCHBASE_BUCKET=your-bucket-name

# Agent Catalog Configuration (if needed)
# AGENT_CATALOG_API_KEY=your-api-key
# AGENT_CATALOG_ENDPOINT=https://your-catalog-endpoint
```

## Variable Descriptions

- **CLUSTER_CONNECTION_STRING**: Connection string for your Couchbase cluster (e.g., `couchbases://hostname`)
- **CLUSTER_NAME**: Your Couchbase username
- **CLUSTER_PASS**: Your Couchbase password
- **COUCHBASE_BUCKET**: The bucket name to connect to

## Setup Instructions

1. Create a `.env` file in the project root
2. Copy the variables above into `.env`
3. Replace the placeholder values with your actual credentials
4. Run `uv sync` to install dependencies including `acouchbase`
5. Start the backend with `uvicorn backend.api:app --reload --port 8000`



