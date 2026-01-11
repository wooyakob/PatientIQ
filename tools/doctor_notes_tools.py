"""
Tools for searching doctor notes using vector search with Couchbase AI Services.
Uses the same embedding model as research search (2048 dimensions).
"""

import os
import requests
import agentc
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
def search_doctor_notes(
    query: str,
    patient_id: str = None,
    limit: int = 5,
    max_chars: int = 1800,
) -> dict:
    """
    Search doctor notes using vector search.

    This tool:
    1. Embeds the doctor's query using Couchbase AI Services (2048 dimensions)
    2. Performs vector search on Scripps.Notes.Doctor collection
    3. Uses hyperscale index: hyperscale_doctor_notes_vectorized_all_notes_vectorized
    4. Searches against all_notes_vectorized field

    Args:
        query: Doctor's question or search query (e.g. "patient progress on medication")
        patient_id: Optional patient ID to filter results
        limit: Max number of notes to return
        max_chars: Max characters per note

    Returns:
        Dict containing a list of relevant doctor notes.
    """

    q = str(query or "").strip()
    if not q:
        return {"found": False, "query": "", "notes": [], "message": "Missing query"}

    try:
        # Generate embedding for the query
        query_embedding = _generate_embedding(q)

        db = _get_db()

        # Hyperscale vector search query
        # Using the hyperscale_doctor_notes_vectorized_all_notes_vectorized index
        index_name = os.getenv("HYPERSCALE_DOCTOR_NOTES", "hyperscale_doctor_notes_vectorized_all_notes_vectorized")

        # Build query with optional patient filter
        where_clause = ""
        named_params = {
            "query_vector": query_embedding,
            "limit": int(limit)
        }

        if patient_id:
            where_clause = f"AND n.patient_id = $patient_id"
            named_params["patient_id"] = str(patient_id)

        query_sql = f"""
            SELECT n.visit_notes, n.visit_date, n.patient_id, n.doctor_id,
                   META(n).id AS note_id,
                   SEARCH_SCORE() AS score
            FROM `{db.bucket_name}`.`Notes`.`Doctor` n
            WHERE SEARCH(n, {{
                "query": {{
                    "match_none": {{}}
                }},
                "knn": [{{
                    "field": "all_notes_vectorized",
                    "vector": $query_vector,
                    "k": $limit
                }}]
            }}, {{"index": "{index_name}"}})
            {where_clause}
            ORDER BY score DESC
            LIMIT $limit
        """

        rows = list(
            db.cluster.query(
                query_sql,
                QueryOptions(named_parameters=named_params),
            )
        )

    except Exception as e:
        return {
            "found": False,
            "query": q,
            "notes": [],
            "message": f"Vector search failed: {e}",
        }

    notes: list[dict] = []
    for r in rows:
        note = {
            "note_id": r.get("note_id", ""),
            "visit_notes": str(r.get("visit_notes") or ""),
            "visit_date": r.get("visit_date", ""),
            "patient_id": r.get("patient_id", ""),
            "doctor_id": r.get("doctor_id", ""),
            "relevance_score": r.get("score", 0.0),
        }

        # Truncate notes if needed
        if max_chars and len(note["visit_notes"]) > int(max_chars):
            note["visit_notes"] = note["visit_notes"][: int(max_chars)].rstrip() + "…"

        notes.append(note)

    return {
        "found": bool(notes),
        "query": q,
        "notes": notes,
        "count": len(notes),
        "search_type": "vector_search",
        "filtered_by_patient": bool(patient_id),
    }


@agentc.catalog.tool
def answer_from_doctor_notes(
    question: str,
    patient_id: str = None,
    limit: int = 5,
) -> dict:
    """
    Answer a question using doctor notes via vector search.

    This tool:
    1. Searches doctor notes using vector search
    2. Returns relevant notes that can answer the question
    3. Optionally filters by patient ID

    Args:
        question: Question to answer (e.g. "How is the patient responding to treatment?")
        patient_id: Optional patient ID to filter results
        limit: Max number of notes to retrieve

    Returns:
        Dict containing relevant notes and context for answering the question.
    """

    result = search_doctor_notes(
        query=question,
        patient_id=patient_id,
        limit=limit,
        max_chars=2000,
    )

    if not result.get("found"):
        return {
            "answered": False,
            "question": question,
            "message": "No relevant doctor notes found",
            "notes": [],
        }

    return {
        "answered": True,
        "question": question,
        "relevant_notes": result.get("notes", []),
        "count": result.get("count", 0),
        "message": f"Found {result.get('count', 0)} relevant notes",
    }
