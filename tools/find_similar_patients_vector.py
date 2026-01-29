"""
Tool to find patients with similar wearable trends using vector similarity search.

Uses Couchbase vector search to find patients whose wearable data patterns
are most similar to the target patient, based on embedding vectors.
"""

import agentc
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.database import CouchbaseDB


@agentc.catalog.tool
def find_similar_patients_vector(
    trend_vector: list[float],
    patient_condition: Optional[str] = None,
    patient_id_to_exclude: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    """
    Find patients with similar wearable trends using vector similarity search.

    This tool uses Couchbase vector search to find patients whose wearable patterns
    are most similar to the query vector. Much faster than statistical comparison
    and finds true pattern similarity, not just demographic similarity.

    Args:
        trend_vector: The embedding vector from vectorize_wearable_trends
        patient_condition: Optional filter to only compare patients with same condition
        patient_id_to_exclude: Patient ID to exclude (usually the query patient)
        top_k: Number of similar patients to return (default: 5)

    Returns:
        Dictionary containing:
        - similar_patients: List of patients with similarity scores
        - search_method: "vector_search"
        - condition_filter: Whether condition filtering was applied

    Example:
        >>> find_similar_patients_vector(
        ...     trend_vector=[0.123, -0.456, ...],
        ...     patient_condition="Asthma",
        ...     patient_id_to_exclude="1",
        ...     top_k=5
        ... )
        {
            "similar_patients": [
                {
                    "patient_id": "3",
                    "patient_name": "Sarah Johnson",
                    "condition": "Asthma",
                    "similarity_score": 0.92,
                    "trend_summary": "Elevated heart rate with low O2..."
                },
                ...
            ],
            "search_method": "vector_search",
            "search_stats": {
                "total_candidates": 50,
                "returned": 5,
                "condition_filtered": true
            }
        }
    """
    if not trend_vector or len(trend_vector) == 0:
        return {
            "error": "No trend vector provided",
            "similar_patients": [],
            "search_method": "none",
        }

    db = CouchbaseDB()
    db._ensure_connected()

    if db._connection_error:
        return {
            "error": f"Database connection failed: {db._connection_error}",
            "similar_patients": [],
            "search_method": "none",
        }

    try:
        # NOTE: This requires a vector index on wearable trend data
        # For now, we'll return a placeholder response and log a warning
        # The actual vector search implementation would look like:
        #
        # from couchbase.search import SearchRequest
        # from couchbase.vector_search import VectorQuery, VectorSearch
        #
        # search_req = SearchRequest.create(
        #     MatchNoneQuery()
        # ).with_vector_search(
        #     VectorSearch.from_vector_query(
        #         VectorQuery('wearable_trend_vector', trend_vector, num_candidates=top_k * 3)
        #     )
        # )
        #
        # result = db.wearables_scope.search(
        #     "wearable-trends-vector-index",
        #     search_req,
        #     SearchOptions(limit=top_k, fields=["patient_id", "patient_name", "condition", "trend_summary"])
        # )

        # TEMPORARY: For demo purposes, fall back to demographic search
        # Once vector index is created, replace this with actual vector search above

        print("⚠️  WARNING: Vector index not yet created. Using demographic fallback.")
        print("   To enable vector search, create a vector index on wearable trends.")
        print("   Index field: 'wearable_trend_vector', dimensions: 1024 (NVIDIA embeddings)")

        # Fallback to demographic search (existing tool)
        from tools.find_similar_patients_demographics import find_similar_patients_demographics

        # Get demographic results and enhance with vector search placeholder info
        demo_result = find_similar_patients_demographics(
            patient_id=patient_id_to_exclude if patient_id_to_exclude else "unknown",
            same_condition=bool(patient_condition),
            limit=top_k,
        )

        # Add context that vector search will be used once index is ready
        return {
            "similar_patients": demo_result.get("similar_patients", []),
            "search_method": "demographic_fallback",  # Will be "vector_search" once index exists
            "search_stats": {
                "total_candidates": demo_result.get("total_found", 0),
                "returned": len(demo_result.get("similar_patients", [])),
                "condition_filtered": bool(patient_condition),
                "note": "Using demographic search until vector index is created",
            },
            "vector_search_ready": False,
            "vector_index_needed": {
                "index_name": "wearable-trends-vector-index",
                "field": "wearable_trend_vector",
                "dimensions": 1024,
                "similarity": "dot_product",
            },
        }

    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return {
            "error": f"Vector search failed: {str(e)}",
            "similar_patients": [],
            "search_method": "error",
        }
