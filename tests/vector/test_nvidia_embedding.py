"""
Test script for querying the Couchbase NVIDIA embedding model.
Uses the working API format: /v1/embeddings (OpenAI-compatible)
"""

import json
import os
import warnings
from datetime import datetime

import numpy as np
import requests
from dotenv import load_dotenv

# Disable SSL warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Load environment variables
load_dotenv()


def get_nvidia_embedding(text: str) -> dict:
    """
    Get embeddings from Couchbase NVIDIA model using OpenAI-compatible API.

    Args:
        text: The text to embed

    Returns:
        Dictionary containing the embedding vector and metadata
    """
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_name = os.getenv("EMBEDDING_MODEL_NAME")
    dimensions = int(os.getenv("EMBEDDING_MODEL_DIMENSIONS", "2048"))

    if not all([endpoint, token, model_name]):
        raise ValueError("Missing required environment variables for embedding model")

    # Use OpenAI-compatible endpoint
    url = f"{endpoint}/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "model": model_name
    }

    print(f"Sending query to NVIDIA embedding model")
    print(f"Model: {model_name}")
    print(f"Endpoint: {url}")
    print(f"Text: '{text}'")
    print(f"Expected dimensions: {dimensions}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status()

        result = response.json()

        # Extract embedding from OpenAI-compatible response
        if "data" in result and len(result["data"]) > 0:
            embedding = result["data"][0].get("embedding", [])

            return {
                "text": text,
                "model": model_name,
                "endpoint": endpoint,
                "dimensions": len(embedding),
                "expected_dimensions": dimensions,
                "embedding": embedding,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "api_format": "OpenAI-compatible /v1/embeddings"
            }
        else:
            return {
                "text": text,
                "model": model_name,
                "status": "error",
                "message": "No embedding data in response",
                "response": result,
                "timestamp": datetime.now().isoformat()
            }

    except requests.exceptions.RequestException as e:
        return {
            "text": text,
            "model": model_name,
            "status": "error",
            "message": f"API request failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main test function"""
    # Test query
    #test_query = "What are the treatment options for pulmonary fibrosis?"
    test_query = "What did I discuss with Emily regarding Enzymes on 2024-03-26?"

    print("=" * 80)
    print("Testing Couchbase NVIDIA Embedding Model API")
    print("=" * 80)
    print()

    # Get embedding from NVIDIA model
    result = get_nvidia_embedding(test_query)

    # Print summary
    print("\n" + "=" * 80)
    print("RESULT SUMMARY")
    print("=" * 80)
    print(f"Status: {result.get('status')}")
    print(f"API Format: {result.get('api_format', 'N/A')}")
    print(f"Model: {result.get('model')}")
    print(f"Endpoint: {result.get('endpoint')}")
    print(f"Text: {result.get('text')}")

    if result.get("status") == "success":
        embedding = result.get("embedding", [])
        print(f"\nEmbedding dimensions: {result.get('dimensions')}")
        print(f"Expected dimensions: {result.get('expected_dimensions')}")
        print(f"Dimensions match: {result.get('dimensions') == result.get('expected_dimensions')}")

        if isinstance(embedding, list) and len(embedding) > 0:
            print(f"\nFirst 10 values: {embedding[:10]}")
            print(f"Last 10 values: {embedding[-10:]}")
            print(f"\nEmbedding statistics:")
            print(f"  Mean value: {np.mean(embedding):.6f}")
            print(f"  Std deviation: {np.std(embedding):.6f}")
            print(f"  Min value: {np.min(embedding):.6f}")
            print(f"  Max value: {np.max(embedding):.6f}")
    else:
        print(f"\nError: {result.get('message')}")

    # Save to output file
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "nvidia_embedding_output_2.json")

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nFull output saved to: {output_file}")
    print("=" * 80)

    return result


if __name__ == "__main__":
    main()
