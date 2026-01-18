"""
Tool to search doctor visit notes using semantic vector search.

Searches through doctor notes to find relevant information about past visits.
Uses NVIDIA embeddings and Couchbase vector search with keyword fallback.
"""

import agentc
import couchbase.options
import logging
from typing import Optional
from _shared import cluster, get_nvidia_embedding

logger = logging.getLogger(__name__)


@agentc.catalog.tool
def doc_notes_search(query: str, patient_id: Optional[str] = None, top_k: int = 3) -> dict:
    """
    Search doctor visit notes using semantic vector search.

    This tool uses NVIDIA embeddings to convert the query to a vector, then performs
    a similarity search against vectorized doctor notes in Couchbase.

    Args:
        query: The search query (e.g., 'What did I discuss with this patient about medication?')
        patient_id: Optional patient ID to filter results to a specific patient
        top_k: Number of notes to return (default: 3, max: 10)

    Returns:
        Dictionary with docnotes_search_results containing matching notes:
        {
            "docnotes_search_results": [
                {
                    "visit_date": "2024-04-21",
                    "visit_notes": "...",
                    "doctor_name": "Dr. Smith",
                    "patient_name": "James Smith",
                    "patient_id": "1",
                    "similarity_score": 0.85
                },
                ...
            ]
        }

    Example:
        >>> doc_notes_search("medication adjustments", patient_id="1", top_k=3)
        {"docnotes_search_results": [...]}
    """
    if not cluster:
        return {"docnotes_search_results": [], "error": "Database connection not available"}

    # Generate embedding for the query
    try:
        logger.info(f"Generating embedding for query: {query[:100]}...")
        embedding = get_nvidia_embedding(query)
        logger.info(f"✓ Embedding generated successfully ({len(embedding)} dimensions)")
    except Exception as e:
        # Fallback to keyword search if embedding fails
        logger.warning(f"⚠️ Embedding generation failed: {str(e)}")
        logger.warning("Falling back to keyword search...")
        return _fallback_keyword_search(query, patient_id, top_k)

    # Build vector search query
    try:
        if patient_id:
            query_str = """
                SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id,
                       APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2") AS similarity_score
                FROM `Scripps`.Notes.Doctor n
                WHERE n.patient_id = $patient_id
                ORDER BY APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2")
                LIMIT $top_k
            """
            params = {"query_vector": embedding, "patient_id": patient_id, "top_k": min(top_k, 10)}
        else:
            query_str = """
                SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id,
                       APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2") AS similarity_score
                FROM `Scripps`.Notes.Doctor n
                ORDER BY APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2")
                LIMIT $top_k
            """
            params = {"query_vector": embedding, "top_k": min(top_k, 10)}

        logger.info(f"Executing vector search for patient_id={patient_id}, top_k={top_k}")
        result_query = cluster.query(
            query_str, couchbase.options.QueryOptions(named_parameters=params)
        )
        results = list(result_query.rows())
        logger.info(f"✓ Vector search completed: found {len(results)} notes")
        return {"docnotes_search_results": results}

    except Exception as e:
        # Fallback to keyword search if vector search fails
        logger.warning(f"⚠️ Vector search failed: {str(e)}")
        logger.warning("Falling back to keyword search...")
        return _fallback_keyword_search(query, patient_id, top_k)


def _fallback_keyword_search(query: str, patient_id: Optional[str], top_k: int) -> dict:
    """Fallback to keyword-based search if vector search fails"""
    logger.info(f"Using keyword fallback search for query: {query[:100]}...")

    if not cluster:
        logger.error("Database cluster not available")
        return {"docnotes_search_results": [], "error": "Database connection not available"}

    try:
        if patient_id:
            query_str = """
                SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id
                FROM `Scripps`.Notes.Doctor n
                WHERE n.patient_id = $patient_id AND LOWER(n.visit_notes) LIKE LOWER($keyword_pattern)
                ORDER BY n.visit_date DESC
                LIMIT $top_k
            """
            params = {"patient_id": patient_id, "keyword_pattern": f"%{query}%", "top_k": top_k}
        else:
            query_str = """
                SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id
                FROM `Scripps`.Notes.Doctor n
                WHERE LOWER(n.visit_notes) LIKE LOWER($keyword_pattern)
                ORDER BY n.visit_date DESC
                LIMIT $top_k
            """
            params = {"keyword_pattern": f"%{query}%", "top_k": top_k}

        logger.info(
            f"Executing keyword search with pattern: {params.get('keyword_pattern', 'N/A')[:100]}"
        )
        result_query = cluster.query(
            query_str, couchbase.options.QueryOptions(named_parameters=params)
        )
        results = list(result_query.rows())
        logger.info(f"Keyword search completed: found {len(results)} notes")
        return {"docnotes_search_results": results}

    except Exception as e:
        logger.error(f"Keyword search failed: {str(e)}")
        return {"docnotes_search_results": [], "error": f"Search failed: {str(e)}"}
