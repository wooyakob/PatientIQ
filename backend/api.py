import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import db
from backend.models import Patient, WearableData

# Add agents path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "medical-agents"))
# Use catalog-integrated version with tracing
from pulmonary_research_agent import run_pulmonary_research

app = FastAPI(
    title="Healthcare API",
    description="FastAPI backend for healthcare dashboard",
    version="1.0.0",
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
    ],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health")
def health():
    return {"ok": True, "service": "Healthcare API"}


# Patient Endpoints
@app.get("/api/patients", response_model=List[Patient])
async def get_patients():
    """Get all patients"""
    try:
        patients = db.get_all_patients()
        return patients
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching patients: {str(e)}")


@app.get("/api/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a specific patient by ID"""
    try:
        patient = db.get_patient(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
        return patient
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching patient: {str(e)}")


@app.get("/api/patients/{patient_id}/wearables", response_model=WearableData)
async def get_patient_wearables(patient_id: str, days: int = 30):
    """Get wearable data (daily entries) for a patient"""
    try:
        return db.get_wearables_for_patient(patient_id, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wearable data: {str(e)}")


@app.post("/api/patients")
async def create_or_update_patient(patient: Patient):
    """Create or update a patient"""
    try:
        patient_dict = patient.model_dump()
        success = db.upsert_patient(patient.id, patient_dict)
        if success:
            return {"message": "Patient saved successfully", "patient_id": patient.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save patient")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving patient: {str(e)}")


# Doctor Notes Endpoints
@app.get("/api/patients/{patient_id}/doctor-notes")
async def get_patient_doctor_notes(patient_id: str):
    """Get all doctor notes for a patient"""
    try:
        notes = db.get_doctor_notes_for_patient(patient_id)
        return {"patient_id": patient_id, "notes": notes, "count": len(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching doctor notes: {str(e)}")


@app.post("/api/doctor-notes")
async def save_doctor_note(note: dict):
    """Save a doctor note"""
    try:
        # Validate required fields
        required_fields = [
            "visit_date",
            "doctor_name",
            "doctor_id",
            "visit_notes",
            "patient_name",
            "patient_id",
        ]
        missing_fields = [
            field for field in required_fields if field not in note or not note[field]
        ]

        if missing_fields:
            raise HTTPException(
                status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Generate note ID using patient_id and timestamp
        note_id = (
            f"note_{note['patient_id']}_{note['visit_date']}_{int(datetime.now().timestamp())}"
        )

        success = db.save_doctor_note(note_id, note)
        if success:
            return {"message": "Doctor note saved successfully", "note_id": note_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save doctor note")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving doctor note: {str(e)}")


@app.delete("/api/doctor-notes/{note_id}")
async def delete_doctor_note(note_id: str):
    """Delete a doctor note"""
    try:
        success = db.delete_doctor_note(note_id)
        if success:
            return {"message": "Doctor note deleted successfully", "note_id": note_id}
        else:
            raise HTTPException(status_code=404, detail="Note not found or failed to delete")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting doctor note: {str(e)}")


# Patient Notes Endpoints
@app.get("/api/patients/{patient_id}/patient-notes")
async def get_patient_notes(patient_id: str):
    """Get all patient notes (private notes) for a patient"""
    try:
        notes = db.get_patient_notes_for_patient(patient_id)
        return {"patient_id": patient_id, "notes": notes, "count": len(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching patient notes: {str(e)}")


# Messages Endpoints
@app.get("/api/messages/private/{doctor_id}")
async def get_private_messages(doctor_id: str, limit: int = 50):
    """Get private messages for a specific doctor"""
    try:
        messages = db.get_private_messages(doctor_id, limit)
        return {"doctor_id": doctor_id, "messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching private messages: {str(e)}")


@app.post("/api/messages/private")
async def send_private_message(payload: dict):
    try:
        to_id = str(payload.get("to_id") or "").strip()
        to_name = str(payload.get("to_name") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        content = str(payload.get("content") or "").strip()

        if not to_id or not to_name or not subject or not content:
            raise HTTPException(
                status_code=400, detail="Missing required fields: to_id, to_name, subject, content"
            )

        # For now, enforce that private messages sent from the UI are from Tiffany Mitchell.
        message_id = f"msg_private_{int(datetime.now().timestamp())}"
        message = {
            "id": message_id,
            "message_type": "private",
            "from_id": "1",
            "from_name": "Tiffany Mitchell",
            "to_id": to_id,
            "to_name": to_name,
            "subject": subject,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "read": False,
            "priority": str(payload.get("priority") or "normal"),
        }

        success = db.save_private_message(message_id, message)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send private message")
        return {"message": "Private message sent", "id": message_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending private message: {str(e)}")


@app.get("/api/messages/public")
async def get_public_messages(limit: int = 50):
    """Get public messages for all Scripps staff"""
    try:
        messages = db.get_public_messages(limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching public messages: {str(e)}")


@app.post("/api/messages/public")
async def send_public_message(payload: dict):
    try:
        subject = str(payload.get("subject") or "").strip()
        content = str(payload.get("content") or "").strip()

        if not subject or not content:
            raise HTTPException(status_code=400, detail="Missing required fields: subject, content")

        message_id = f"msg_public_{int(datetime.now().timestamp())}"
        message = {
            "id": message_id,
            "message_type": "public",
            "from_id": "1",
            "from_name": "Tiffany Mitchell",
            "to_name": "All Scripps Staff",
            "subject": subject,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "read": False,
            "priority": str(payload.get("priority") or "normal"),
        }

        success = db.save_public_message(message_id, message)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send public message")
        return {"message": "Public message sent", "id": message_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending public message: {str(e)}")


@app.post("/api/messages/private/{message_id}/read")
async def mark_private_message_read(message_id: str):
    """Mark a private message as read"""
    try:
        success = db.mark_message_as_read(message_id, is_private=True)
        if success:
            return {"message": "Message marked as read", "message_id": message_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to mark message as read")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking message as read: {str(e)}")


@app.post("/api/messages/public/{message_id}/read")
async def mark_public_message_read(message_id: str):
    """Mark a public message as read"""
    try:
        success = db.mark_message_as_read(message_id, is_private=False)
        if success:
            return {"message": "Message marked as read", "message_id": message_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to mark message as read")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking message as read: {str(e)}")


# Calendar/Appointments Endpoints
@app.get("/api/appointments/doctor/{doctor_id}")
async def get_doctor_appointments(doctor_id: str, start_date: str = None, end_date: str = None):
    """Get appointments for a specific doctor, optionally filtered by date range"""
    try:
        appointments = db.get_appointments_for_doctor(doctor_id, start_date, end_date)
        return {"doctor_id": doctor_id, "appointments": appointments, "count": len(appointments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching appointments: {str(e)}")


@app.get("/api/appointments/patient/{patient_id}")
async def get_patient_appointments(patient_id: str):
    """Get appointments for a specific patient"""
    try:
        appointments = db.get_appointments_for_patient(patient_id)
        return {"patient_id": patient_id, "appointments": appointments, "count": len(appointments)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching patient appointments: {str(e)}"
        )


@app.post("/api/appointments/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, status: str):
    """Update the status of an appointment"""
    try:
        valid_statuses = ["scheduled", "completed", "cancelled", "no-show"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )
        success = db.update_appointment_status(appointment_id, status)
        if success:
            return {
                "message": "Appointment status updated",
                "appointment_id": appointment_id,
                "status": status,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update appointment status")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating appointment status: {str(e)}")


@app.get("/api/questionnaires/pre-visit/{patient_id}")
async def get_pre_visit_questionnaire(patient_id: str):
    try:
        root = Path(__file__).resolve().parent.parent
        path = (
            root
            / "data"
            / "questionnaires"
            / f"patient_{patient_id}"
            / "pre_visit_questionnaire.json"
        )

        if not path.exists():
            raise HTTPException(status_code=404, detail="Pre-visit questionnaire not found")

        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            if len(data) == 0:
                raise HTTPException(status_code=404, detail="Pre-visit questionnaire not found")
            data = data[0]

        if not isinstance(data, dict):
            raise HTTPException(status_code=500, detail="Invalid questionnaire format")

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questionnaire: {str(e)}")


@app.post("/api/questionnaires/pre-visit/status")
async def get_pre_visit_questionnaire_status(payload: Dict[str, Any] = Body(...)):
    try:
        patient_ids = payload.get("patient_ids")
        if not isinstance(patient_ids, list):
            raise HTTPException(status_code=400, detail="patient_ids must be a list")

        root = Path(__file__).resolve().parent.parent
        statuses = []
        for pid in patient_ids:
            patient_id = str(pid)
            path = (
                root
                / "data"
                / "questionnaires"
                / f"patient_{patient_id}"
                / "pre_visit_questionnaire.json"
            )
            if not path.exists():
                statuses.append(
                    {
                        "patient_id": patient_id,
                        "exists": False,
                        "completed": False,
                        "date_completed": None,
                    }
                )
                continue

            date_completed = None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    date_completed = data[0].get("date_completed")
                elif isinstance(data, dict):
                    date_completed = data.get("date_completed")
            except (json.JSONDecodeError, IOError) as e:
                # Log the specific error e
                _ = e
                date_completed = None

            completed = bool(date_completed)

            statuses.append(
                {
                    "patient_id": patient_id,
                    "exists": True,
                    "completed": completed,
                    "date_completed": date_completed,
                }
            )

        return {"statuses": statuses}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching questionnaire status: {str(e)}"
        )


# Medical Research Agent Endpoints
@app.get("/api/patients/{patient_id}/research")
async def get_patient_research(patient_id: str, question: Optional[str] = None):
    """
    Get medical research relevant to a patient's condition.

    Args:
        patient_id: The patient's ID
        question: Optional specific question (if not provided, uses default question about treatment options)

    Returns:
        Dictionary with patient info, condition, papers, and clinical summary
    """
    try:
        # Default question if none provided
        if not question:
            question = "What are evidence-based treatment options and practical next steps for this patient's condition?"

        # Run the pulmonary research agent
        result = run_pulmonary_research(patient_id, question)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching research: {str(e)}")


@app.post("/api/patients/{patient_id}/research/ask")
async def ask_research_question(patient_id: str, payload: dict = Body(...)):
    """
    Ask a specific question about a patient's condition and get research-based answers.
    Also saves the question to Research.Pubmed.questions collection.

    Args:
        patient_id: The patient's ID
        payload: JSON with 'question' field

    Returns:
        Dictionary with patient info, condition, papers, answer, and question_id
    """
    try:
        question = payload.get("question", "").strip()

        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        # Save question to database
        question_id = f"q_{int(datetime.now().timestamp() * 1000)}"
        question_doc = {
            "question_id": question_id,
            "question_asked": question,
            "doctor_name": "Tiffany Mitchell",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            db.save_research_question(question_id, question_doc)
        except Exception as e:
            # Log but don't fail if question save fails
            print(f"Warning: Failed to save question: {e}")

        # Run the pulmonary research agent with the specific question
        result = run_pulmonary_research(patient_id, question)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # Add question_id to result
        result["question_id"] = question_id

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.post("/api/research/answers")
async def save_research_answer(payload: dict = Body(...)):
    """
    Save a research answer with optional rating.

    Args:
        payload: JSON with question_asked, answer_provided, answer_rating (optional)

    Returns:
        Success message with answer_id
    """
    try:
        question_asked = payload.get("question_asked", "").strip()
        answer_provided = payload.get("answer_provided", "").strip()
        answer_rating = payload.get("answer_rating")  # Optional, 1-5

        if not question_asked or not answer_provided:
            raise HTTPException(
                status_code=400, detail="question_asked and answer_provided are required"
            )

        if answer_rating is not None:
            if not isinstance(answer_rating, int) or answer_rating < 1 or answer_rating > 5:
                raise HTTPException(
                    status_code=400, detail="answer_rating must be an integer between 1 and 5"
                )

        # Save answer to database
        answer_id = f"a_{int(datetime.now().timestamp() * 1000)}"
        answer_doc = {
            "answer_id": answer_id,
            "question_asked": question_asked,
            "answer_provided": answer_provided,
            "answer_rating": answer_rating,
            "timestamp": datetime.now().isoformat(),
        }

        success = db.save_research_answer(answer_id, answer_doc)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save answer")

        return {"message": "Answer saved successfully", "answer_id": answer_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving answer: {str(e)}")


@app.patch("/api/research/answers/{answer_id}/rating")
async def update_answer_rating(answer_id: str, payload: dict = Body(...)):
    """
    Update the rating for a research answer.

    Args:
        answer_id: The answer's ID
        payload: JSON with 'rating' field (1-5)

    Returns:
        Success message
    """
    try:
        rating = payload.get("rating")

        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be an integer between 1 and 5")

        success = db.update_answer_rating(answer_id, rating)

        if not success:
            raise HTTPException(status_code=404, detail="Answer not found or update failed")

        return {"message": "Rating updated successfully", "answer_id": answer_id, "rating": rating}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating rating: {str(e)}")
