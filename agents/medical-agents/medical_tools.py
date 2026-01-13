import agentc
import couchbase.auth
import couchbase.cluster
import couchbase.exceptions
import couchbase.options
import dotenv
import os
import requests
import warnings
from typing import Optional
from datetime import datetime, timedelta

dotenv.load_dotenv()
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Agent Catalog imports this file once (even if both tools are requested).
# To share (and reuse) Couchbase connections, we can use a top-level variable.
try:
    cluster = couchbase.cluster.Cluster(
        os.getenv("CLUSTER_CONNECTION_STRING") or os.getenv("CB_CONN_STRING"),
        couchbase.options.ClusterOptions(
            authenticator=couchbase.auth.PasswordAuthenticator(
                username=os.getenv("CLUSTER_USERNAME") or os.getenv("CB_USERNAME"),
                password=os.getenv("CLUSTER_PASS") or os.getenv("CB_PASSWORD"),
                certpath=os.getenv("AGENT_CATALOG_CONN_ROOT_CERTIFICATE") or os.getenv("CB_CERTIFICATE"),
            )
        ),
    )
except couchbase.exceptions.CouchbaseException as e:
    print(f"""
        Could not connect to Couchbase cluster!
        This error is going to be swallowed by 'agentc index .', but you will run into issues if you decide to
        run your app!
        Make sure that all Python tools (not just the ones defined in this) are free from unwanted side-effects on
        import.
        {str(e)}
    """)


@agentc.catalog.tool
def get_patient_by_id(patient_id: str) -> dict:
    """Get complete patient information by patient ID including demographics and medical conditions."""
    query = cluster.query(
        """
            SELECT p.*
            FROM `Scripps`.People.Patients p
            WHERE p.patient_id = $patient_id
            LIMIT 1
        """,
        couchbase.options.QueryOptions(
            named_parameters={"patient_id": patient_id}
        ),
    )
    results = list(query.rows())
    return results[0] if results else {}


@agentc.catalog.tool
def search_patients_by_name(patient_name: str) -> list[dict]:
    """Search for patients by name (supports partial matching). Returns patient demographics."""
    query = cluster.query(
        """
            SELECT p.patient_id, p.patient_name, p.age, p.gender, p.medical_conditions, p.admission_date
            FROM `Scripps`.People.Patients p
            WHERE LOWER(p.patient_name) LIKE LOWER($name_pattern)
            ORDER BY p.patient_name
            LIMIT 20
        """,
        couchbase.options.QueryOptions(
            named_parameters={"name_pattern": f"%{patient_name}%"}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_patients_by_condition(medical_condition: str) -> list[dict]:
    """Find all patients with a specific medical condition. Useful for cohort analysis or condition-specific reviews."""
    query = cluster.query(
        """
            SELECT p.patient_id, p.patient_name, p.age, p.gender, p.medical_conditions, p.admission_date
            FROM `Scripps`.People.Patients p
            WHERE ANY condition IN p.medical_conditions SATISFIES LOWER(condition) LIKE LOWER($condition_pattern) END
            ORDER BY p.patient_name
            LIMIT 50
        """,
        couchbase.options.QueryOptions(
            named_parameters={"condition_pattern": f"%{medical_condition}%"}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_patient_doctor_notes(patient_id: str, days_back: int = 90) -> list[dict]:
    """Get doctor notes for a patient within a specified number of days. Default is last 90 days."""
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    query = cluster.query(
        """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.doctor_id, n.patient_name
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id AND n.visit_date >= $cutoff_date
            ORDER BY n.visit_date DESC
            LIMIT 50
        """,
        couchbase.options.QueryOptions(
            named_parameters={"patient_id": patient_id, "cutoff_date": cutoff_date}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_doctor_notes_by_date(patient_id: str, visit_date: str) -> list[dict]:
    """Get all doctor notes for a specific patient on a specific visit date (format: YYYY-MM-DD)."""
    query = cluster.query(
        """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.doctor_id, n.patient_name, n.patient_id
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id AND n.visit_date = $visit_date
            ORDER BY n.visit_date DESC
        """,
        couchbase.options.QueryOptions(
            named_parameters={"patient_id": patient_id, "visit_date": visit_date}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def search_doctor_notes_by_keyword(keyword: str, patient_id: Optional[str] = None) -> list[dict]:
    """Search doctor notes for specific keywords or phrases. Optionally filter by patient_id."""
    if patient_id:
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id AND LOWER(n.visit_notes) LIKE LOWER($keyword_pattern)
            ORDER BY n.visit_date DESC
            LIMIT 30
        """
        params = {"patient_id": patient_id, "keyword_pattern": f"%{keyword}%"}
    else:
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id
            FROM `Scripps`.Notes.Doctor n
            WHERE LOWER(n.visit_notes) LIKE LOWER($keyword_pattern)
            ORDER BY n.visit_date DESC
            LIMIT 30
        """
        params = {"keyword_pattern": f"%{keyword}%"}

    query = cluster.query(query_str, couchbase.options.QueryOptions(named_parameters=params))
    return list(query.rows())


@agentc.catalog.tool
def get_recent_wearable_data(patient_id: str, days_back: int = 7) -> list[dict]:
    """Get recent wearable device data (heart rate, steps, blood oxygen) for a patient. Default is last 7 days."""
    cutoff_timestamp = (datetime.now() - timedelta(days=days_back)).isoformat()

    # Wearables are stored in per-patient collections (Patient_1, Patient_2, etc.)
    # Extract numeric ID from patient_id if format is "patient_X"
    collection_name = patient_id if patient_id.startswith("Patient_") else f"Patient_{patient_id}"

    query = cluster.query(
        f"""
            SELECT w.timestamp, w.metrics.heart_rate, w.metrics.steps, w.blood_oxygen_level
            FROM `Scripps`.Wearables.{collection_name} w
            WHERE w.timestamp >= $cutoff_timestamp
            ORDER BY w.timestamp DESC
            LIMIT 500
        """,
        couchbase.options.QueryOptions(
            named_parameters={"cutoff_timestamp": cutoff_timestamp}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_patient_appointments(patient_id: str, days_ahead: int = 30) -> list[dict]:
    """Get upcoming and recent appointments for a patient within specified days ahead. Default is next 30 days."""
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    query = cluster.query(
        """
            SELECT a.appointment_date, a.appointment_time, a.doctor_id, a.appointment_type,
                   a.status, a.duration_minutes
            FROM `Scripps`.Calendar.Appointments a
            WHERE a.patient_id = $patient_id
              AND a.appointment_date >= $start_date
              AND a.appointment_date <= $end_date
            ORDER BY a.appointment_date, a.appointment_time
            LIMIT 50
        """,
        couchbase.options.QueryOptions(
            named_parameters={
                "patient_id": patient_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_doctor_schedule(doctor_id: str, start_date: str, end_date: str) -> list[dict]:
    """Get all appointments for a doctor within a date range (format: YYYY-MM-DD). Useful for scheduling."""
    query = cluster.query(
        """
            SELECT a.appointment_date, a.appointment_time, a.patient_id, a.appointment_type,
                   a.status, a.duration_minutes
            FROM `Scripps`.Calendar.Appointments a
            WHERE a.doctor_id = $doctor_id
              AND a.appointment_date >= $start_date
              AND a.appointment_date <= $end_date
            ORDER BY a.appointment_date, a.appointment_time
        """,
        couchbase.options.QueryOptions(
            named_parameters={
                "doctor_id": doctor_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_todays_appointments(doctor_id: str) -> list[dict]:
    """Get all appointments for a doctor today. Quick way to check daily schedule."""
    today = datetime.now().strftime("%Y-%m-%d")

    query = cluster.query(
        """
            SELECT a.appointment_date, a.appointment_time, a.patient_id, a.appointment_type,
                   a.status, a.duration_minutes
            FROM `Scripps`.Calendar.Appointments a
            WHERE a.doctor_id = $doctor_id AND a.appointment_date = $today
            ORDER BY a.appointment_time
        """,
        couchbase.options.QueryOptions(
            named_parameters={"doctor_id": doctor_id, "today": today}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def search_medical_research(query_text: str, limit: int = 5) -> list[dict]:
    """Search medical research papers using semantic vector search. Requires query to be embedded first.
    Returns relevant research papers with titles, authors, and article text."""
    # Note: This requires the query to be embedded using the NVIDIA embedding API
    # For now, this does a simple text search. Vector search integration would require
    # calling the embedding API first and passing the vector here.
    query = cluster.query(
        """
            SELECT r.title, r.author, r.article_text, r.article_citation, r.pmc_link
            FROM `Research`.Pubmed.Pulmonary r
            WHERE LOWER(r.title) LIKE LOWER($search_pattern)
               OR LOWER(r.article_text) LIKE LOWER($search_pattern)
            LIMIT $limit
        """,
        couchbase.options.QueryOptions(
            named_parameters={"search_pattern": f"%{query_text}%", "limit": limit}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def vector_search_medical_research(query_vector: list[float], limit: int = 3) -> list[dict]:
    """Search medical research papers using vector similarity search.
    Requires a 2048-dimensional embedding vector. Returns most relevant papers by cosine similarity."""
    query = cluster.query(
        """
            SELECT r.title, r.author, r.article_text, r.article_citation, r.pmc_link,
                   APPROX_VECTOR_DISTANCE(r.article_vectorized, $query_vector, "COSINE") AS distance
            FROM `Research`.Pubmed.Pulmonary r
            ORDER BY APPROX_VECTOR_DISTANCE(r.article_vectorized, $query_vector, "COSINE")
            LIMIT $limit
        """,
        couchbase.options.QueryOptions(
            named_parameters={"query_vector": query_vector, "limit": limit}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_private_messages(doctor_id: str, limit: int = 20) -> list[dict]:
    """Get recent private messages for a doctor. Useful for checking unread communications."""
    query = cluster.query(
        """
            SELECT m.from_name, m.to_name, m.subject, m.content, m.timestamp, m.read, m.priority
            FROM `Scripps`.Messages.Private m
            WHERE m.to_id = $doctor_id OR m.from_id = $doctor_id
            ORDER BY m.timestamp DESC
            LIMIT $limit
        """,
        couchbase.options.QueryOptions(
            named_parameters={"doctor_id": doctor_id, "limit": limit}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_unread_messages(doctor_id: str) -> list[dict]:
    """Get all unread private messages for a doctor. Check for urgent communications."""
    query = cluster.query(
        """
            SELECT m.from_name, m.subject, m.content, m.timestamp, m.priority
            FROM `Scripps`.Messages.Private m
            WHERE m.to_id = $doctor_id AND m.read = false
            ORDER BY m.priority DESC, m.timestamp DESC
        """,
        couchbase.options.QueryOptions(
            named_parameters={"doctor_id": doctor_id}
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_patients_with_upcoming_appointments(doctor_id: str, days_ahead: int = 3) -> list[dict]:
    """Get list of patients with upcoming appointments in the next N days. Useful for pre-visit preparation."""
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    query = cluster.query(
        """
            SELECT a.patient_id, a.appointment_date, a.appointment_time, a.appointment_type,
                   p.patient_name, p.age, p.gender, p.medical_conditions
            FROM `Scripps`.Calendar.Appointments a
            JOIN `Scripps`.People.Patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = $doctor_id
              AND a.appointment_date >= $start_date
              AND a.appointment_date <= $end_date
              AND a.status = "scheduled"
            ORDER BY a.appointment_date, a.appointment_time
        """,
        couchbase.options.QueryOptions(
            named_parameters={
                "doctor_id": doctor_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ),
    )
    return list(query.rows())


@agentc.catalog.tool
def get_patient_summary(patient_id: str) -> dict:
    """Get a comprehensive summary of a patient including demographics, recent notes, appointments, and conditions.
    This is a high-level overview tool useful for quick patient review."""

    # Get patient info
    patient_query = cluster.query(
        """
            SELECT p.patient_id, p.patient_name, p.age, p.gender, p.medical_conditions, p.admission_date
            FROM `Scripps`.People.Patients p
            WHERE p.patient_id = $patient_id
            LIMIT 1
        """,
        couchbase.options.QueryOptions(named_parameters={"patient_id": patient_id}),
    )
    patient_info = list(patient_query.rows())

    if not patient_info:
        return {"error": "Patient not found"}

    # Get recent notes (last 30 days)
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    notes_query = cluster.query(
        """
            SELECT n.visit_date, n.doctor_name, LEFT(n.visit_notes, 200) AS note_preview
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id AND n.visit_date >= $cutoff_date
            ORDER BY n.visit_date DESC
            LIMIT 5
        """,
        couchbase.options.QueryOptions(
            named_parameters={"patient_id": patient_id, "cutoff_date": cutoff_date}
        ),
    )
    recent_notes = list(notes_query.rows())

    # Get upcoming appointments
    today = datetime.now().strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    appointments_query = cluster.query(
        """
            SELECT a.appointment_date, a.appointment_time, a.appointment_type, a.status
            FROM `Scripps`.Calendar.Appointments a
            WHERE a.patient_id = $patient_id
              AND a.appointment_date >= $today
              AND a.appointment_date <= $future_date
            ORDER BY a.appointment_date
            LIMIT 5
        """,
        couchbase.options.QueryOptions(
            named_parameters={
                "patient_id": patient_id,
                "today": today,
                "future_date": future_date
            }
        ),
    )
    upcoming_appointments = list(appointments_query.rows())

    return {
        "patient": patient_info[0],
        "recent_notes": recent_notes,
        "upcoming_appointments": upcoming_appointments
    }


def get_nvidia_embedding(text: str) -> list[float]:
    """Generate a 2048-dimensional embedding vector using NVIDIA's embedding model.
    Internal helper function for vector search."""
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


@agentc.catalog.tool
def find_patient_by_id(patient_id: str) -> dict:
    """Find a patient by ID and return their demographics and medical conditions.
    Alias for get_patient_by_id for compatibility with medical_researcher prompt."""
    return get_patient_by_id(patient_id)


@agentc.catalog.tool
def find_conditions_by_patient_id(patient_id: str) -> str:
    """Get the medical conditions for a specific patient. Returns conditions as a string."""
    patient = get_patient_by_id(patient_id)
    if not patient:
        return "Patient not found"
    conditions = patient.get("medical_conditions", [])
    if isinstance(conditions, list):
        return ", ".join(conditions) if conditions else "No conditions listed"
    return str(conditions)


@agentc.catalog.tool
def paper_search(query: str, patient_id: Optional[str] = None, top_k: int = 3) -> list[dict]:
    """Search for relevant medical research papers using semantic vector search.

    Args:
        query: The search query (e.g., 'COPD treatment options', 'Asthma management')
        patient_id: Optional patient ID to include their condition in the search
        top_k: Number of papers to return (default 3)

    Returns:
        List of relevant papers with title, author, article_text, article_citation, and pmc_link
    """
    # If patient_id is provided, get their condition and enhance the query
    if patient_id:
        condition = find_conditions_by_patient_id(patient_id)
        if condition and condition != "Patient not found":
            query = f"{condition}. {query}"

    # Generate embedding for the query
    try:
        embedding = get_nvidia_embedding(query)
    except Exception:
        # Fallback to text search if embedding fails
        return search_medical_research(query, limit=top_k)

    # Perform vector search
    return vector_search_medical_research(embedding, limit=top_k)


@agentc.catalog.tool
def doc_notes_search(query: str, patient_id: Optional[str] = None, top_k: int = 3) -> dict:
    """Search doctor visit notes using semantic vector search.

    Args:
        query: The search query (e.g., 'What did I discuss with Emily regarding enzymes?')
        patient_id: Optional patient ID to filter results to a specific patient
        top_k: Number of notes to return (default 3)

    Returns:
        Dictionary with docnotes_search_results containing matching doctor notes
    """
    # Generate embedding for the query
    try:
        embedding = get_nvidia_embedding(query)
    except Exception:
        # Fallback to keyword search if embedding fails
        return {
            "docnotes_search_results": search_doctor_notes_by_keyword(query, patient_id)[:top_k]
        }

    # Build vector search query
    if patient_id:
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id,
                   APPROX_VECTOR_DISTANCE(n.visit_notes_vectorized, $query_vector, "COSINE") AS similarity_score
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id
            ORDER BY APPROX_VECTOR_DISTANCE(n.visit_notes_vectorized, $query_vector, "COSINE")
            LIMIT $top_k
        """
        params = {"query_vector": embedding, "patient_id": patient_id, "top_k": top_k}
    else:
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id,
                   APPROX_VECTOR_DISTANCE(n.visit_notes_vectorized, $query_vector, "COSINE") AS similarity_score
            FROM `Scripps`.Notes.Doctor n
            ORDER BY APPROX_VECTOR_DISTANCE(n.visit_notes_vectorized, $query_vector, "COSINE")
            LIMIT $top_k
        """
        params = {"query_vector": embedding, "top_k": top_k}

    result_query = cluster.query(
        query_str,
        couchbase.options.QueryOptions(named_parameters=params)
    )

    return {
        "docnotes_search_results": list(result_query.rows())
    }
