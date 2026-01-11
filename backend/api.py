from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import db
from backend.models import Patient


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


@app.get("/api/messages/public")
async def get_public_messages(limit: int = 50):
    """Get public messages for all Scripps staff"""
    try:
        messages = db.get_public_messages(limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching public messages: {str(e)}")


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
async def get_doctor_appointments(
    doctor_id: str, start_date: str = None, end_date: str = None
):
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
        raise HTTPException(
            status_code=500, detail=f"Error updating appointment status: {str(e)}"
        )


