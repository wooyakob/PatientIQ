"""
Test script for querying the Couchbase NVIDIA embedding API endpoint.
Tries multiple API formats to find the correct endpoint structure.
"""

import json
import os
import warnings
from datetime import datetime

import requests
from dotenv import load_dotenv

# Disable SSL warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Load environment variables
load_dotenv()


def try_api_format_1(text: str) -> dict:
    """Try API format: /v1/functions/{id}/invoke"""
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_id = os.getenv("EMBEDDING_MODEL_ID")
    model_name = os.getenv("EMBEDDING_MODEL_NAME")

    url = f"{endpoint}/v1/functions/{model_id}/invoke"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "model": model_name
    }

    print(f"Testing Format 1: /v1/functions/{{id}}/invoke")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            return {"format": "format_1", "success": True, "data": response.json()}
        else:
            return {"format": "format_1", "success": False, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        return {"format": "format_1", "success": False, "error": str(e)}


def try_api_format_2(text: str) -> dict:
    """Try API format: /v1/embeddings (OpenAI-compatible)"""
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_name = os.getenv("EMBEDDING_MODEL_NAME")

    url = f"{endpoint}/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "model": model_name
    }

    print(f"\nTesting Format 2: /v1/embeddings")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            return {"format": "format_2", "success": True, "data": response.json()}
        else:
            return {"format": "format_2", "success": False, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        return {"format": "format_2", "success": False, "error": str(e)}


def try_api_format_3(text: str) -> dict:
    """Try API format: /api/v1/embed"""
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_id = os.getenv("EMBEDDING_MODEL_ID")

    url = f"{endpoint}/api/v1/embed"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "function_id": model_id
    }

    print(f"\nTesting Format 3: /api/v1/embed")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            return {"format": "format_3", "success": True, "data": response.json()}
        else:
            return {"format": "format_3", "success": False, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        return {"format": "format_3", "success": False, "error": str(e)}


def try_api_format_4(text: str) -> dict:
    """Try API format: /v2/embeddings"""
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    key = os.getenv("EMBEDDING_MODEL_KEY")
    model_name = os.getenv("EMBEDDING_MODEL_NAME")

    url = f"{endpoint}/v2/embeddings"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": key,
        "Content-Type": "application/json"
    }

    payload = {
        "input": [text],
        "model": model_name
    }

    print(f"\nTesting Format 4: /v2/embeddings with X-API-Key")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            return {"format": "format_4", "success": True, "data": response.json()}
        else:
            return {"format": "format_4", "success": False, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        return {"format": "format_4", "success": False, "error": str(e)}


def try_api_format_5(text: str) -> dict:
    """Try API format: Direct function invocation with function_id"""
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")
    model_id = os.getenv("EMBEDDING_MODEL_ID")

    url = f"{endpoint}/invoke/{model_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text
    }

    print(f"\nTesting Format 5: /invoke/{{id}}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            return {"format": "format_5", "success": True, "data": response.json()}
        else:
            return {"format": "format_5", "success": False, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        return {"format": "format_5", "success": False, "error": str(e)}


def main():
    """Main test function"""
    test_query = "What are the treatment options for pulmonary fibrosis?"

    print("=" * 80)
    print("Testing Couchbase NVIDIA Embedding API Endpoint")
    print("=" * 80)
    print(f"Query: {test_query}")
    print(f"Model: {os.getenv('EMBEDDING_MODEL_NAME')}")
    print(f"Endpoint: {os.getenv('EMBEDDING_MODEL_ENDPOINT')}")
    print(f"Model ID: {os.getenv('EMBEDDING_MODEL_ID')}")
    print("=" * 80)

    results = []

    # Try all API formats
    formats = [
        try_api_format_1,
        try_api_format_2,
        try_api_format_3,
        try_api_format_4,
        try_api_format_5
    ]

    for format_func in formats:
        try:
            result = format_func(test_query)
            results.append(result)

            if result.get("success"):
                print("\n" + "🎉" * 40)
                print("SUCCESS! Found working API format!")
                print("🎉" * 40)
                break
        except Exception as e:
            results.append({
                "format": format_func.__name__,
                "success": False,
                "error": str(e)
            })

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY OF ALL ATTEMPTS")
    print("=" * 80)

    successful = None
    for result in results:
        status = "✓ SUCCESS" if result.get("success") else "✗ FAILED"
        print(f"{status} - {result.get('format', 'unknown')}")
        if result.get("success"):
            successful = result

    # Save results
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "couchbase_api_test_results.json")

    final_output = {
        "timestamp": datetime.now().isoformat(),
        "query": test_query,
        "endpoint": os.getenv("EMBEDDING_MODEL_ENDPOINT"),
        "model": os.getenv("EMBEDDING_MODEL_NAME"),
        "all_attempts": results,
        "successful_format": successful
    }

    with open(output_file, "w") as f:
        json.dump(final_output, f, indent=2)

    print(f"\nFull results saved to: {output_file}")

    if successful:
        print("\n" + "=" * 80)
        print("SUCCESSFUL EMBEDDING RESULT")
        print("=" * 80)
        data = successful.get("data", {})
        if "data" in data and len(data["data"]) > 0:
            embedding = data["data"][0].get("embedding", [])
            print(f"Embedding dimensions: {len(embedding)}")
            print(f"First 10 values: {embedding[:10]}")
        else:
            print(f"Response structure: {json.dumps(data, indent=2)[:500]}")

    print("=" * 80)


if __name__ == "__main__":
    main()
