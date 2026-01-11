import os
import re
import threading
from datetime import date, datetime, timedelta
from typing import List, Optional
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, QueryOptions
from couchbase.exceptions import DocumentNotFoundException

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class CouchbaseDB:
    """
    Couchbase database utility for healthcare agent application.

    Uses bucket/scope/collection hierarchy:
    - ckodb bucket
      - People scope (Patient, Doctor collections)
      - Research scope (pubmed collection)
      - Wearables scope (Watch, 
      - Notes scope (Patient, Doctor collections)

    """

    def __init__(self):
        # Store connection parameters but don't connect yet (lazy initialization)
        self.endpoint = os.getenv("CLUSTER_CONNECTION_STRING")
        self.username = os.getenv("CLUSTER_USERNAME", "ac")
        self.password = os.getenv("CLUSTER_PASS")
        self.bucket_name = os.getenv("COUCHBASE_BUCKET", "Scripps")

        # Connection state
        self.cluster = None
        self.bucket = None
        self.patients_collection = None
        self._connection_attempted = False
        self._connection_error = None

    def _ensure_connected(self):
        """Lazy initialization - connect to database on first use"""
        if self._connection_attempted:
            return

        self._connection_attempted = True

        if not self.endpoint or not self.username or not self.password:
            self._connection_error = RuntimeError(
                "Missing required environment variables. "
                "Please set CLUSTER_CONNECTION_STRING, CLUSTER_USERNAME, and CLUSTER_PASS"
            )
            print(f"Database connection error: {self._connection_error}")
            return

        try:
            print(f"Connecting to Couchbase at {self.endpoint}...")
            auth = PasswordAuthenticator(self.username, self.password)
            options = ClusterOptions(auth)
            options.apply_profile("wan_development")

            self.cluster = Cluster(self.endpoint, options)
            self.cluster.wait_until_ready(timedelta(seconds=10))

            self.bucket = self.cluster.bucket(self.bucket_name)

            # Initialize scopes and collections
            # People scope - for patients and doctors
            self.people_scope = self.bucket.scope("People")
            self.patients_collection = self.people_scope.collection("Patients")
            self.doctors_collection = self.people_scope.collection("Doctors")

            # Wearables scope - per-patient collections (Patient_1..Patient_5)
            self.wearables_scope = self.bucket.scope("Wearables")

            # Notes scope - for patient and doctor notes
            self.notes_scope = self.bucket.scope("Notes")
            self.patient_notes_collection = self.notes_scope.collection("Patient")
            self.doctor_notes_collection = self.notes_scope.collection("Doctor")

            # Messages scope - for private and public messages
            self.messages_scope = self.bucket.scope("Messages")
            self.private_messages_collection = self.messages_scope.collection("Private")
            self.public_messages_collection = self.messages_scope.collection("Public")

            # Calendar scope - for appointments
            self.calendar_scope = self.bucket.scope("Calendar")
            self.appointments_collection = self.calendar_scope.collection("Appointments")

            print(f"Connected to Couchbase cluster. Using bucket: {self.bucket_name}")
            print("Initialized scopes: People, Wearables, Notes, Messages, Calendar")

        except Exception as e:
            self._connection_error = e
            print(f"Warning: Could not connect to Couchbase: {e}")
            print("   Please verify the cluster is running and accessible.")
            print(
                "   Expected structure: Scripps bucket with People/Notes/Wearables scopes"
            )

    def _check_connection(self):
        """Check if database is connected"""
        self._ensure_connected()

        if self._connection_error:
            raise RuntimeError(
                f"Database connection failed: {self._connection_error}. "
                f"Please verify the Couchbase cluster is running and accessible."
            )

        if not self.patients_collection:
            raise RuntimeError(
                f"Bucket '{self.bucket_name}' not available. "
                f"Please verify Scripps bucket exists with proper scopes/collections."
            )

    def _initials(self, name: str) -> str:
        parts = [p for p in (name or "").split() if p]
        if not parts:
            return "??"
        if len(parts) == 1:
            return (parts[0][:2]).upper()
        return (parts[0][:1] + parts[-1][:1]).upper()

    def _parse_date(self, value: str) -> Optional[date]:
        try:
            return date.fromisoformat(value)
        except Exception:
            return None

    def _sentiment_from_text(self, text: str) -> str:
        t = (text or "").lower()
        if any(w in t for w in ("terrible", "panic", "cannot", "can't", "worse", "urgent")):
            return "terrible"
        if any(w in t for w in ("anxious", "drained", "fatig", "worried", "tight", "short of breath")):
            return "poor"
        if any(w in t for w in ("motivated", "better", "helped", "coping", "steady", "improv")):
            return "good"
        return "neutral"

    def _wearables_keyspace_for_patient_id(self, patient_id: str) -> Optional[str]:
        if not re.fullmatch(r"\d+", str(patient_id or "")):
            return None
        return f"`{self.bucket_name}`.`Wearables`.`Patient_{patient_id}`"

    def _get_wearable_summary(self, patient_id: str) -> dict:
        keyspace = self._wearables_keyspace_for_patient_id(patient_id)
        if not keyspace:
            return {"heart_rate": [0] * 7, "step_count": [0] * 7}

        query = f"""
            SELECT w.metrics.heart_rate AS heart_rate,
                   w.metrics.steps AS steps
            FROM {keyspace} w
            ORDER BY w.timestamp DESC
            LIMIT 7
        """
        try:
            rows = list(self.cluster.query(query))
        except Exception:
            rows = []

        heart_rates = [int(r.get("heart_rate") or 0) for r in rows]
        step_counts = [int(r.get("steps") or 0) for r in rows]

        heart_rates.reverse()
        step_counts.reverse()

        if len(heart_rates) < 7:
            heart_rates = ([0] * (7 - len(heart_rates))) + heart_rates
        if len(step_counts) < 7:
            step_counts = ([0] * (7 - len(step_counts))) + step_counts

        return {"heart_rate": heart_rates[:7], "step_count": step_counts[:7]}

    def _get_latest_patient_private_note(self, patient_id: str) -> str:
        query = f"""
            SELECT n.visit_notes AS note
            FROM `{self.bucket_name}`.`Notes`.`Patient` n
            WHERE n.patient_id = $patient_id
            ORDER BY n.visit_date DESC
            LIMIT 1
        """
        try:
            rows = list(
                self.cluster.query(
                    query, QueryOptions(named_parameters={"patient_id": patient_id})
                )
            )
        except Exception:
            return ""
        if not rows:
            return ""
        return str(rows[0].get("note") or "")

    def _get_research_snippets(self, limit: int = 2, max_chars: int = 700) -> List[str]:
        query = """
            SELECT p.article_text AS article_text
            FROM `Research`.`Pubmed`.`Pulmonary` p
            LIMIT $limit
        """
        try:
            rows = list(self.cluster.query(query, QueryOptions(named_parameters={"limit": limit})))
        except Exception:
            return []

        snippets: List[str] = []
        for r in rows:
            text = str(r.get("article_text") or "")
            if max_chars and len(text) > max_chars:
                text = text[:max_chars].rstrip() + "…"
            if text:
                snippets.append(text)
        return snippets

    def _get_research_snippets_for_condition(
        self, condition: str, limit: int = 3, max_chars: int = 900
    ) -> List[str]:
        c = str(condition or "").strip().lower()
        if not c:
            return self._get_research_snippets(limit=limit, max_chars=max_chars)

        pattern = f"%{c}%"
        query = """
            SELECT p.article_text AS article_text
            FROM `Research`.`Pubmed`.`Pulmonary` p
            WHERE LOWER(IFMISSINGORNULL(p.article_text, '')) LIKE $pattern
               OR LOWER(IFMISSINGORNULL(p.title, '')) LIKE $pattern
               OR LOWER(IFMISSINGORNULL(p.abstract, '')) LIKE $pattern
            LIMIT $limit
        """
        try:
            rows = list(
                self.cluster.query(
                    query,
                    QueryOptions(named_parameters={"pattern": pattern, "limit": int(limit)}),
                )
            )
        except Exception:
            return []

        snippets: List[str] = []
        for r in rows:
            text = str(r.get("article_text") or "")
            if max_chars and len(text) > max_chars:
                text = text[:max_chars].rstrip() + "…"
            if text:
                snippets.append(text)
        return snippets

    def _patient_doc_to_api(self, p: dict) -> dict:
        patient_id = str(p.get("patient_id") or p.get("id") or "")
        patient_name = str(p.get("patient_name") or p.get("name") or "")
        condition = str(p.get("medical_conditions") or p.get("condition") or "")

        admission_date = str(p.get("admission_date") or "")
        last_visit = admission_date
        next_appointment = admission_date
        parsed = self._parse_date(admission_date)
        if parsed:
            next_appointment = (parsed + timedelta(days=30)).isoformat()

        try:
            age = int(p.get("age") or 0)
        except Exception:
            age = 0

        wearable_data = self._get_wearable_summary(patient_id)
        private_notes = self._get_latest_patient_private_note(patient_id)

        research_topic = f"Pulmonary research for {condition}" if condition else "Pulmonary research"
        research_content: List[str] = []
        try:
            existing = self.get_research_for_patient(patient_id)
        except Exception:
            existing = None

        if isinstance(existing, dict) and existing.get("document_type") == "research_summary":
            research_topic = str(existing.get("topic") or research_topic)
            summaries = existing.get("summaries")
            if isinstance(summaries, list):
                research_content = [str(s) for s in summaries if isinstance(s, str)]

        if not research_content:
            research_content = self._get_research_snippets_for_condition(condition, limit=3, max_chars=700)

        return {
            "id": patient_id,
            "name": patient_name,
            "age": age,
            "gender": str(p.get("gender") or ""),
            "condition": condition,
            "avatar": self._initials(patient_name),
            "last_visit": last_visit,
            "next_appointment": next_appointment,
            "wearable_data": wearable_data,
            "sentiment": self._sentiment_from_text(private_notes),
            "private_notes": private_notes,
            "research_topic": research_topic,
            "research_content": research_content,
        }

    def get_patient(self, patient_id: str) -> Optional[dict]:
        """Retrieve a patient by ID from People.Patient collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT p.*
                FROM `{self.bucket_name}`.`People`.`Patients` p
                WHERE p.patient_id = $patient_id
                LIMIT 1
            """
            rows = list(
                self.cluster.query(
                    query, QueryOptions(named_parameters={"patient_id": patient_id})
                )
            )
            if not rows:
                return None
            return self._patient_doc_to_api(rows[0])
        except DocumentNotFoundException:
            return None
        except Exception:
            return None

    def get_all_patients(self) -> List[dict]:
        """Retrieve all patients from People.Patient collection"""
        self._check_connection()
        try:
            # Query the Patient collection in People scope
            query = f"""
                SELECT p.*
                FROM `{self.bucket_name}`.`People`.`Patients` p
            """
            result = self.cluster.query(query)
            return [self._patient_doc_to_api(row) for row in result]
        except Exception as e:
            print(f"Error fetching patients: {e}")
            return []

    def upsert_patient(self, patient_id: str, patient_data: dict) -> bool:
        """Insert or update a patient in People.Patient collection"""
        self._check_connection()
        try:
            # Remove type field if present (not needed with scope/collection structure)
            patient_data.pop("type", None)
            # Store with the same field names as the seeded dataset for compatibility.
            to_store = dict(patient_data)
            to_store["patient_id"] = str(patient_data.get("patient_id") or patient_data.get("id") or patient_id)
            to_store["patient_name"] = str(patient_data.get("patient_name") or patient_data.get("name") or "")
            if "medical_conditions" not in to_store and ("condition" in patient_data):
                to_store["medical_conditions"] = patient_data.get("condition")
            self.patients_collection.upsert(str(patient_id), to_store)
            return True
        except Exception as e:
            print(f"Error upserting patient: {e}")
            return False

    def save_wearable_alert(self, alert_id: str, alert_data: dict) -> bool:
        """Save a wearable data alert to Wearables.Watch collection"""
        self._check_connection()
        try:
            alert_data.pop("type", None)
            alert_data["document_type"] = "wearable_alert"
            self.doctor_notes_collection.upsert(alert_id, alert_data)
            return True
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False

    def get_alerts_for_patient(self, patient_id: str) -> List[dict]:
        """Get all alerts for a specific patient from Wearables.Watch collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT a.*
                FROM `{self.bucket_name}`.`Notes`.`Doctor` a
                WHERE a.patient_id = $patient_id
                AND a.document_type = 'wearable_alert'
                ORDER BY a.timestamp DESC
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"patient_id": patient_id})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            return []

    def save_research_summary(self, summary_id: str, summary_data: dict) -> bool:
        """Save a research summary to Research.pubmed collection"""
        self._check_connection()
        try:
            summary_data.pop("type", None)
            summary_data["document_type"] = "research_summary"
            self.doctor_notes_collection.upsert(summary_id, summary_data)
            return True
        except Exception as e:
            print(f"Error saving research summary: {e}")
            return False

    def get_research_for_patient(self, patient_id: str) -> Optional[dict]:
        """Get latest research summary for a patient from Research.pubmed collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT r.*
                FROM `{self.bucket_name}`.`Notes`.`Doctor` r
                WHERE r.patient_id = $patient_id
                AND r.document_type = 'research_summary'
                ORDER BY r.generated_at DESC
                LIMIT 1
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"patient_id": patient_id})
            )
            rows = list(result)
            return rows[0] if rows else None
        except Exception as e:
            print(f"Error fetching research: {e}")
            return None

    def save_message_route(self, route_id: str, route_data: dict) -> bool:
        """Save a message routing record to Notes.Doctor collection"""
        self._check_connection()
        try:
            route_data.pop("type", None)
            self.doctor_notes_collection.upsert(route_id, route_data)
            return True
        except Exception as e:
            print(f"Error saving message route: {e}")
            return False

    # NOTE: Questionnaires scope collection names TBD
    # Temporarily saving to Notes.Doctor until collection is confirmed

    def save_questionnaire_summary(self, summary_id: str, summary_data: dict) -> bool:
        """
        Save a questionnaire summary.
        TODO: Update to use Questionnaires scope once collection name is confirmed.
        Currently saving to Notes.Doctor collection.
        """
        self._check_connection()
        try:
            summary_data.pop("type", None)
            # Temporary: Save to Notes.Doctor until Questionnaires collection is defined
            summary_data["document_type"] = "questionnaire_summary"
            self.doctor_notes_collection.upsert(summary_id, summary_data)
            return True
        except Exception as e:
            print(f"Error saving questionnaire summary: {e}")
            return False

    def get_questionnaire_for_patient(self, patient_id: str) -> Optional[dict]:
        """
        Get latest questionnaire summary for a patient.
        TODO: Update to use Questionnaires scope once collection name is confirmed.
        Currently reading from Notes.Doctor collection.
        """
        self._check_connection()
        try:
            query = f"""
                SELECT n.*
                FROM `{self.bucket_name}`.`Notes`.`Doctor` n
                WHERE n.patient_id = '{patient_id}'
                AND n.document_type = 'questionnaire_summary'
                ORDER BY n.generated_at DESC
                LIMIT 1
            """
            result = self.cluster.query(query)
            rows = list(result)
            return rows[0] if rows else None
        except Exception as e:
            print(f"Error fetching questionnaire: {e}")
            return None

    def save_doctor_note(self, note_id: str, note_data: dict) -> bool:
        """Save a doctor note to Notes.Doctor collection"""
        self._check_connection()
        try:
            note_data.pop("type", None)
            self.doctor_notes_collection.upsert(note_id, note_data)
            return True
        except Exception as e:
            print(f"Error saving doctor note: {e}")
            return False

    def get_doctor_notes_for_patient(self, patient_id: str) -> List[dict]:
        """Get all doctor notes for a patient from Notes.Doctor collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT META(n).id AS id,
                       n.visit_date AS date,
                       '' AS time,
                       n.visit_notes AS content
                FROM `{self.bucket_name}`.`Notes`.`Doctor` n
                WHERE n.patient_id = $patient_id
                ORDER BY n.visit_date DESC
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"patient_id": patient_id})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching doctor notes: {e}")
            return []

    def save_patient_note(self, note_id: str, note_data: dict) -> bool:
        """Save a patient note to Notes.Patient collection"""
        self._check_connection()
        try:
            note_data.pop("type", None)
            self.patient_notes_collection.upsert(note_id, note_data)
            return True
        except Exception as e:
            print(f"Error saving patient note: {e}")
            return False

    def get_patient_notes_for_patient(self, patient_id: str) -> List[dict]:
        """Get all patient notes for a patient from Notes.Patient collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT META(n).id AS id,
                       n.visit_date AS date,
                       '' AS time,
                       n.visit_notes AS content
                FROM `{self.bucket_name}`.`Notes`.`Patient` n
                WHERE n.patient_id = $patient_id
                ORDER BY n.visit_date DESC
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"patient_id": patient_id})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching patient notes: {e}")
            return []

    # Messages Methods

    def get_private_messages(self, doctor_id: str, limit: int = 50) -> List[dict]:
        """Get private messages for a specific doctor from Messages.Private collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT m.*
                FROM `{self.bucket_name}`.`Messages`.`Private` m
                WHERE m.to_id = $doctor_id
                ORDER BY m.timestamp DESC
                LIMIT $limit
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"doctor_id": doctor_id, "limit": limit})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching private messages: {e}")
            return []

    def get_public_messages(self, limit: int = 50) -> List[dict]:
        """Get public messages for all Scripps staff from Messages.Public collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT m.*
                FROM `{self.bucket_name}`.`Messages`.`Public` m
                ORDER BY m.timestamp DESC
                LIMIT $limit
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"limit": limit})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching public messages: {e}")
            return []

    def save_private_message(self, message_id: str, message_data: dict) -> bool:
        """Save a private message to Messages.Private collection"""
        self._check_connection()
        try:
            message_data.pop("type", None)
            message_data["message_type"] = "private"
            self.private_messages_collection.upsert(message_id, message_data)
            return True
        except Exception as e:
            print(f"Error saving private message: {e}")
            return False

    def save_public_message(self, message_id: str, message_data: dict) -> bool:
        """Save a public message to Messages.Public collection"""
        self._check_connection()
        try:
            message_data.pop("type", None)
            message_data["message_type"] = "public"
            self.public_messages_collection.upsert(message_id, message_data)
            return True
        except Exception as e:
            print(f"Error saving public message: {e}")
            return False

    def mark_message_as_read(self, message_id: str, is_private: bool = True) -> bool:
        """Mark a message as read"""
        self._check_connection()
        try:
            collection = self.private_messages_collection if is_private else self.public_messages_collection
            message = collection.get(message_id)
            message_data = message.content_as[dict]
            message_data["read"] = True
            collection.upsert(message_id, message_data)
            return True
        except Exception as e:
            print(f"Error marking message as read: {e}")
            return False

    # Calendar/Appointments Methods

    def get_appointments_for_doctor(
        self, doctor_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[dict]:
        """Get appointments for a specific doctor from Calendar.Appointments collection"""
        self._check_connection()
        try:
            if start_date and end_date:
                query = f"""
                    SELECT a.*
                    FROM `{self.bucket_name}`.`Calendar`.`Appointments` a
                    WHERE a.doctor_id = $doctor_id
                    AND a.appointment_date >= $start_date
                    AND a.appointment_date <= $end_date
                    ORDER BY a.appointment_date, a.appointment_time
                """
                result = self.cluster.query(
                    query,
                    QueryOptions(
                        named_parameters={
                            "doctor_id": doctor_id,
                            "start_date": start_date,
                            "end_date": end_date,
                        }
                    ),
                )
            else:
                query = f"""
                    SELECT a.*
                    FROM `{self.bucket_name}`.`Calendar`.`Appointments` a
                    WHERE a.doctor_id = $doctor_id
                    ORDER BY a.appointment_date, a.appointment_time
                """
                result = self.cluster.query(
                    query, QueryOptions(named_parameters={"doctor_id": doctor_id})
                )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching appointments: {e}")
            return []

    def get_appointments_for_patient(self, patient_id: str) -> List[dict]:
        """Get appointments for a specific patient from Calendar.Appointments collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT a.*
                FROM `{self.bucket_name}`.`Calendar`.`Appointments` a
                WHERE a.patient_id = $patient_id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
            """
            result = self.cluster.query(
                query, QueryOptions(named_parameters={"patient_id": patient_id})
            )
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching patient appointments: {e}")
            return []

    def save_appointment(self, appointment_id: str, appointment_data: dict) -> bool:
        """Save an appointment to Calendar.Appointments collection"""
        self._check_connection()
        try:
            appointment_data.pop("type", None)
            self.appointments_collection.upsert(appointment_id, appointment_data)
            return True
        except Exception as e:
            print(f"Error saving appointment: {e}")
            return False

    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        """Update the status of an appointment"""
        self._check_connection()
        try:
            appointment = self.appointments_collection.get(appointment_id)
            appointment_data = appointment.content_as[dict]
            appointment_data["status"] = status
            self.appointments_collection.upsert(appointment_id, appointment_data)
            return True
        except Exception as e:
            print(f"Error updating appointment status: {e}")
            return False


# Global database instance
_db_instance = None
_db_lock = threading.Lock()


def _get_db_instance():
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = CouchbaseDB()
    return _db_instance


class _DBProxy:
    def __getattr__(self, name):
        return getattr(_get_db_instance(), name)


db = _DBProxy()
