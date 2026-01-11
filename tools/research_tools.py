"""
Tools for managing medical research summaries in the healthcare agent system.
Uses vector search with Couchbase AI Services embedding model.
"""

import os
import requests
import agentc
from datetime import datetime
from couchbase.options import QueryOptions


def _get_db():
    from backend.database import db

    return db


def _generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings using Couchbase AI Services Model Service.

    Args:
        text: Text to embed

    Returns:
        List of embedding floats (2048 dimensions)
    """
    endpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
    model_id = os.getenv("EMBEDDING_MODEL_ID")
    token = os.getenv("EMBEDDING_MODEL_TOKEN")

    if not all([endpoint, model_id, token]):
        raise ValueError("Missing embedding model configuration in environment variables")

    url = f"{endpoint}/v1/models/{model_id}:generateEmbedding"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract embedding from response
        if "embedding" in data:
            return data["embedding"]
        elif "embeddings" in data and len(data["embeddings"]) > 0:
            return data["embeddings"][0]
        else:
            raise ValueError(f"Unexpected response format: {data}")

    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding: {e}")


@agentc.catalog.tool
def fetch_research_articles(
    condition: str,
    limit: int = 5,
    max_chars: int = 1800,
) -> dict:
    """
    Fetch research article excerpts relevant to a medical condition using vector search.

    This tool:
    1. Embeds the doctor's query using Couchbase AI Services (2048 dimensions)
    2. Performs vector search on Research.Pubmed.Pulmonary collection
    3. Uses hyperscale index: hyperscale_pubmed_vectorized_article_vectorized
    4. Searches against article_vectorized field

    Args:
        condition: Medical condition or doctor's query (e.g. "Bronchiectasis treatment")
        limit: Max number of excerpts to return
        max_chars: Max characters per excerpt

    Returns:
        Dict containing a list of excerpts.
    """

    c = str(condition or "").strip()
    if not c:
        return {"found": False, "condition": "", "excerpts": [], "message": "Missing condition"}

    try:
        # Generate embedding for the query
        query_embedding = _generate_embedding(c)

        db = _get_db()

        # Hyperscale vector search query
        # Using the hyperscale_pubmed_vectorized_article_vectorized index
        index_name = os.getenv("HYPERSCALE_RESEARCH", "hyperscale_pubmed_vectorized_article_vectorized")

        query = f"""
            SELECT p.article_text, p.title, p.abstract,
                   SEARCH_SCORE() AS score
            FROM `Research`.`Pubmed`.`Pulmonary` p
            WHERE SEARCH(p, {{
                "query": {{
                    "match_none": {{}}
                }},
                "knn": [{{
                    "field": "article_vectorized",
                    "vector": $query_vector,
                    "k": $limit
                }}]
            }}, {{"index": "{index_name}"}})
            ORDER BY score DESC
            LIMIT $limit
        """

        rows = list(
            db.cluster.query(
                query,
                QueryOptions(named_parameters={
                    "query_vector": query_embedding,
                    "limit": int(limit)
                }),
            )
        )

    except Exception as e:
        return {
            "found": False,
            "condition": c,
            "excerpts": [],
            "message": f"Vector search failed: {e}",
        }

    excerpts: list[str] = []
    for r in rows:
        text = str(r.get("article_text") or "")
        if not text:
            continue
        if max_chars and len(text) > int(max_chars):
            text = text[: int(max_chars)].rstrip() + "…"
        excerpts.append(text)

    return {
        "found": bool(excerpts),
        "condition": c,
        "excerpts": excerpts,
        "count": len(excerpts),
        "search_type": "vector_search",
    }


@agentc.catalog.tool
def save_research_summary(
    summary_id: str,
    patient_id: str,
    condition: str,
    topic: str,
    summaries: list[str],
    sources: list[str] = None,
) -> dict:
    """
    Save a medical research summary to the database.

    Args:
        summary_id: Unique identifier for the summary
        patient_id: Patient the research is for
        condition: Patient's medical condition
        topic: Research topic title
        summaries: List of research summary paragraphs
        sources: Optional list of source citations

    Returns:
        Dictionary with success status
    """
    return {
        "success": True,
        "summary_id": summary_id,
        "message": "Research summary saving is disabled",
    }


@agentc.catalog.tool
def get_patient_research(patient_id: str) -> dict:
    """
    Retrieve the latest research summary for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        Dictionary containing the latest research summary, or None if not found
    """
    db = _get_db()
    research = db.get_research_for_patient(patient_id)
    if not research:
        return {"found": False, "message": "No research summary found"}
    return {"found": True, "research": research}
