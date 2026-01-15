"""
Tool to search medical research papers using semantic vector search.

Combines patient condition context with search query for better results.
Uses NVIDIA embeddings and Couchbase vector search.
"""

import agentc
import couchbase.options
from typing import Optional
from _shared import cluster, get_nvidia_embedding


@agentc.catalog.tool
def paper_search(query: str, patient_id: Optional[str] = None, top_k: int = 3) -> list[dict]:
    """
    Search for relevant medical research papers using semantic vector search.

    This tool uses NVIDIA embeddings to convert the query to a vector, then performs
    a similarity search against vectorized medical papers in Couchbase.

    If a patient_id is provided, the patient's conditions are automatically added
    to the search query for more relevant results.

    Args:
        query: The search query (e.g., 'COPD treatment options', 'Asthma management')
        patient_id: Optional patient ID to include their condition in the search
        top_k: Number of papers to return (default: 3, max: 10)

    Returns:
        List of relevant papers, each containing:
        - title: Paper title
        - author: Author names
        - article_text: Full or partial article text
        - article_citation: Citation information
        - pmc_link: PubMed Central link (if available)

    Example:
        >>> paper_search("treatment options for COPD", patient_id="1", top_k=3)
        [
            {
                "title": "Current Treatment Approaches for COPD",
                "author": "Smith J, et al.",
                "article_text": "...",
                "article_citation": "NEJM 2024;380:123-145",
                "pmc_link": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC..."
            },
            ...
        ]
    """
    if not cluster:
        return [{"error": "Database connection not available"}]

    # Enhance query with patient condition if provided
    enhanced_query = query
    if patient_id:
        # Get patient conditions directly
        try:
            cond_query = cluster.query(
                """
                SELECT p.medical_conditions
                FROM `Scripps`.People.Patients p
                WHERE p.patient_id = $patient_id
                LIMIT 1
                """,
                couchbase.options.QueryOptions(named_parameters={"patient_id": patient_id}),
            )
            cond_results = list(cond_query.rows())
            if cond_results:
                conditions = cond_results[0].get("medical_conditions", [])
                if isinstance(conditions, list) and conditions:
                    condition_str = ", ".join(conditions)
                    enhanced_query = f"{condition_str}. {query}"
        except Exception:
            # If condition lookup fails, just use original query
            pass

    # Generate embedding for the query
    try:
        embedding = get_nvidia_embedding(enhanced_query)
    except Exception:
        # Fallback to text search if embedding fails
        return _fallback_text_search(query, top_k)

    # Perform vector search
    try:
        result = cluster.query(
            """
            SELECT r.title, r.author, r.article_text, r.article_citation, r.pmc_link,
                   APPROX_VECTOR_DISTANCE(r.article_vectorized, $query_vector, "COSINE") AS distance
            FROM `Research`.Pubmed.Pulmonary r
            ORDER BY APPROX_VECTOR_DISTANCE(r.article_vectorized, $query_vector, "COSINE")
            LIMIT $limit
            """,
            couchbase.options.QueryOptions(
                named_parameters={"query_vector": embedding, "limit": min(top_k, 10)}
            ),
        )
        return list(result.rows())
    except Exception as e:
        return [{"error": f"Vector search failed: {str(e)}"}]


def _fallback_text_search(query: str, limit: int) -> list[dict]:
    """Fallback to text-based search if vector search fails"""
    if not cluster:
        return [{"error": "Database connection not available"}]

    try:
        result = cluster.query(
            """
            SELECT r.title, r.author, r.article_text, r.article_citation, r.pmc_link
            FROM `Research`.Pubmed.Pulmonary r
            WHERE LOWER(r.title) LIKE LOWER($search_pattern)
               OR LOWER(r.article_text) LIKE LOWER($search_pattern)
            LIMIT $limit
            """,
            couchbase.options.QueryOptions(
                named_parameters={"search_pattern": f"%{query}%", "limit": limit}
            ),
        )
        return list(result.rows())
    except Exception as e:
        return [{"error": f"Text search failed: {str(e)}"}]
