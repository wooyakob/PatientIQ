import os
from datetime import timedelta
from typing import List, Optional
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
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
      - Wearables scope (Watch, Phone collections)
      - Notes scope (Patient, Doctor collections)
      - Questionnaires scope (collection names TBD)
    """

    def __init__(self):
        endpoint = os.getenv("CLUSTER_CONNECTION_STRING")
        username = os.getenv("CLUSTER_NAME")
        password = os.getenv("CLUSTER_PASS")

        if not endpoint or not username or not password:
            raise RuntimeError(
                "Missing required environment variables. "
                "Please set CLUSTER_CONNECTION_STRING, CLUSTER_NAME, and CLUSTER_PASS"
            )

        auth = PasswordAuthenticator(username, password)
        options = ClusterOptions(auth)
        options.apply_profile("wan_development")

        self.cluster = Cluster(endpoint, options)
        self.cluster.wait_until_ready(timedelta(seconds=5))

        # Use ckodb bucket with scopes and collections
        self.bucket_name = os.getenv("COUCHBASE_BUCKET", "ckodb")

        try:
            self.bucket = self.cluster.bucket(self.bucket_name)

            # Initialize scopes and collections
            # People scope - for patients and doctors
            self.people_scope = self.bucket.scope("People")
            self.patients_collection = self.people_scope.collection("Patient")
            self.doctors_collection = self.people_scope.collection("Doctor")

            # Research scope - for research summaries
            self.research_scope = self.bucket.scope("Research")
            self.pubmed_collection = self.research_scope.collection("pubmed")

            # Wearables scope - for wearable data and alerts
            self.wearables_scope = self.bucket.scope("Wearables")
            self.watch_collection = self.wearables_scope.collection("Watch")
            self.phone_collection = self.wearables_scope.collection("Phone")

            # Notes scope - for patient and doctor notes
            self.notes_scope = self.bucket.scope("Notes")
            self.patient_notes_collection = self.notes_scope.collection("Patient")
            self.doctor_notes_collection = self.notes_scope.collection("Doctor")

            # Questionnaires scope - collection names TBD
            # self.questionnaires_scope = self.bucket.scope("Questionnaires")
            # self.patient_questionnaires_collection = self.questionnaires_scope.collection("Patient")

            print(f"Connected to Couchbase cluster. Using bucket: {self.bucket_name}")
            print("Initialized scopes: People, Research, Wearables, Notes")

        except Exception as e:
            print(f"Warning: Could not access bucket '{self.bucket_name}': {e}")
            print(f"   Please verify the bucket exists in Couchbase Capella.")
            print(f"   Expected structure: ckodb bucket with People/Research/Wearables/Notes/Questionnaires scopes")
            # Set to None so we can check later
            self.bucket = None
            self.patients_collection = None

    def _check_connection(self):
        """Check if database is connected"""
        if not self.patients_collection:
            raise RuntimeError(
                f"Bucket '{self.bucket_name}' not available. "
                f"Please verify ckodb bucket exists with proper scopes/collections."
            )

    # ==================== PATIENT OPERATIONS ====================

    def get_patient(self, patient_id: str) -> Optional[dict]:
        """Retrieve a patient by ID from People.Patient collection"""
        self._check_connection()
        try:
            result = self.patients_collection.get(patient_id)
            return result.content_as[dict]
        except DocumentNotFoundException:
            return None

    def get_all_patients(self) -> List[dict]:
        """Retrieve all patients from People.Patient collection"""
        self._check_connection()
        try:
            # Query the Patient collection in People scope
            query = f"""
                SELECT p.*
                FROM `{self.bucket_name}`.`People`.`Patient` p
            """
            result = self.cluster.query(query)
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching patients: {e}")
            return []

    def upsert_patient(self, patient_id: str, patient_data: dict) -> bool:
        """Insert or update a patient in People.Patient collection"""
        self._check_connection()
        try:
            # Remove type field if present (not needed with scope/collection structure)
            patient_data.pop("type", None)
            self.patients_collection.upsert(patient_id, patient_data)
            return True
        except Exception as e:
            print(f"Error upserting patient: {e}")
            return False

    # ==================== WEARABLE ALERTS ====================

    def save_wearable_alert(self, alert_id: str, alert_data: dict) -> bool:
        """Save a wearable data alert to Wearables.Watch collection"""
        self._check_connection()
        try:
            alert_data.pop("type", None)
            self.watch_collection.upsert(alert_id, alert_data)
            return True
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False

    def get_alerts_for_patient(self, patient_id: str) -> List[dict]:
        """Get all alerts for a specific patient from Wearables.Watch collection"""
        self._check_connection()
        try:
            query = f"""
                SELECT w.*
                FROM `{self.bucket_name}`.`Wearables`.`Watch` w
                WHERE w.patient_id = '{patient_id}'
                ORDER BY w.timestamp DESC
            """
            result = self.cluster.query(query)
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            return []

    # ==================== RESEARCH SUMMARIES ====================

    def save_research_summary(self, summary_id: str, summary_data: dict) -> bool:
        """Save a research summary to Research.pubmed collection"""
        self._check_connection()
        try:
            summary_data.pop("type", None)
            self.pubmed_collection.upsert(summary_id, summary_data)
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
                FROM `{self.bucket_name}`.`Research`.`pubmed` r
                WHERE r.patient_id = '{patient_id}'
                ORDER BY STR_TO_MILLIS(r.generated_at) DESC
                LIMIT 1
            """
            result = self.cluster.query(query)
            rows = list(result)
            return rows[0] if rows else None
        except Exception as e:
            print(f"Error fetching research: {e}")
            return None

    # ==================== MESSAGE ROUTING ====================

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

    # ==================== QUESTIONNAIRE SUMMARIES ====================
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

    # ==================== DOCTOR NOTES ====================

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
                SELECT n.*
                FROM `{self.bucket_name}`.`Notes`.`Doctor` n
                WHERE n.patient_id = '{patient_id}'
                ORDER BY n.date DESC, n.time DESC
            """
            result = self.cluster.query(query)
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching doctor notes: {e}")
            return []

    # ==================== PATIENT NOTES ====================

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
                SELECT n.*
                FROM `{self.bucket_name}`.`Notes`.`Patient` n
                WHERE n.patient_id = '{patient_id}'
                ORDER BY n.created_at DESC
            """
            result = self.cluster.query(query)
            return [row for row in result]
        except Exception as e:
            print(f"Error fetching patient notes: {e}")
            return []


# Global database instance
db = CouchbaseDB()
