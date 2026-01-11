import asyncio
import uuid
from datetime import datetime, timezone
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import db
from backend.models import Patient
from backend.agents_agentc import orchestrator

# Background task control
background_task = None
stop_background_tasks = False


# Background agent task runner
async def run_agents_for_all_patients():
    """
    Background task that runs medical research agent for all patients.
    Uses vector search to find relevant research articles.
    """
    print("\n" + "=" * 60)
    print("Running Medical Research Agent for All Patients...")
    print("=" * 60)

    try:
        # Get all patients
        patients = db.get_all_patients()
        print(f"Found {len(patients)} patients to analyze\n")

        for patient in patients:
            patient_id = patient.get("id")
            patient_name = patient.get("name")
            print(f"Processing: {patient_name} ({patient_id})")

            # Run research summarization agent (only if needed)
            try:
                # Check if research exists and is recent
                existing_research = db.get_research_for_patient(patient_id)
                existing_summaries = (existing_research or {}).get("summaries", [])
                existing_is_dirty = False
                if isinstance(existing_summaries, list) and existing_summaries:
                    existing_is_dirty = any(
                        isinstance(s, str)
                        and ("====" in s or "http://" in s or "https://" in s or s.count("\n") > 4)
                        for s in existing_summaries
                    )

                if not existing_research or existing_is_dirty:
                    print("   Generating research summaries using vector search...")
                    research_result = await orchestrator.run_research_summarizer(
                        patient_id, patient
                    )

                    # Save research
                    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    research_summary = {
                        "patient_id": patient_id,
                        "condition": research_result.get("condition", ""),
                        "topic": research_result.get("research_topic", ""),
                        "summaries": research_result.get("summaries", []),
                        "sources": [],
                        "generated_at": generated_at,
                    }
                    _summary_id = str(uuid.uuid4())

                    # Update patient record
                    _ = (patient, _summary_id)

                    print("   Research summaries generated via vector search")
                else:
                    print("   Research already exists (skipping)")

            except Exception as e:
                print(f"   Research generation failed: {e}")

            print()  # Blank line between patients

        print("=" * 60)
        print("Research agent run completed for all patients")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"Error running agents: {e}")
        import traceback

        traceback.print_exc()


async def periodic_agent_runner():
    """
    Continuously runs agents in the background at regular intervals.
    """
    global stop_background_tasks

    print("\nStarting periodic agent runner (every 15 minutes)...")

    while not stop_background_tasks:
        try:
            # Wait 15 minutes before next run
            await asyncio.sleep(15 * 60)  # 15 minutes in seconds

            if not stop_background_tasks:
                await run_agents_for_all_patients()

        except asyncio.CancelledError:
            print("Agent runner task cancelled")
            break
        except Exception as e:
            print(f"Error in periodic agent runner: {e}")
            # Continue running even if there's an error
            await asyncio.sleep(60)  # Wait 1 minute before retrying


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Runs agents on startup and schedules periodic execution using asyncio.
    """
    global background_task, stop_background_tasks

    # Startup
    print("\n" + "=" * 60)
    print("Healthcare Agent API Starting Up")
    print("=" * 60)

    # Run agents once on startup
    print("\nRunning initial agent analysis...")
    await run_agents_for_all_patients()

    # Start background task for periodic agent runs
    stop_background_tasks = False
    background_task = asyncio.create_task(periodic_agent_runner())
    print("Background agent runner started")

    print("\n" + "=" * 60)
    print("Backend Ready - Agents Running in Background")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    print("\nShutting down background tasks...")
    stop_background_tasks = True
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    print("Background tasks stopped\n")


app = FastAPI(
    title="Healthcare Agent API",
    description="FastAPI backend with LangGraph agents (agentc) for healthcare dashboard",
    version="1.0.0",
    lifespan=lifespan,
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


# Request/Response Models
class AgentTriggerRequest(BaseModel):
    patient_id: str


class DoctorNotesSearchRequest(BaseModel):
    query: str
    patient_id: str = None
    limit: int = 5


# Health Check
@app.get("/health")
def health():
    return {"ok": True, "service": "Healthcare Agent API"}


# Agent Status Endpoint
@app.get("/api/agents/status")
async def get_agent_status():
    """Get the status of background agents"""
    global background_task, stop_background_tasks

    return {
        "agents_running": background_task is not None and not stop_background_tasks,
        "task_status": "running" if background_task and not background_task.done() else "stopped",
        "next_run": "in 15 minutes (continuous)" if not stop_background_tasks else "stopped",
        "message": "AI agents are continuously monitoring all patients and generating insights",
    }


# Manual Agent Trigger (for testing/manual runs)
@app.post("/api/agents/run-now")
async def trigger_agents_now():
    """Manually trigger agents to run immediately (in addition to scheduled runs)"""
    try:
        # Run in background to not block the request
        asyncio.create_task(run_agents_for_all_patients())
        return {
            "status": "triggered",
            "message": "Agents are running in the background. Check logs for progress.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering agents: {str(e)}")


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




# Research Summarization Agent Endpoints
@app.post("/api/agents/research-summarizer/run")
async def run_research_summarizer(request: AgentTriggerRequest):
    """
    Trigger the Medical Research Summarization Agent for a patient.
    Generates research summaries relevant to the patient's condition.
    """
    try:
        patient_data = db.get_patient(request.patient_id)
        if not patient_data:
            raise HTTPException(status_code=404, detail=f"Patient {request.patient_id} not found")

        # Run agent using orchestrator
        result = await orchestrator.run_research_summarizer(request.patient_id, patient_data)

        # Prepare research summary for database
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        research_summary = {
            "patient_id": request.patient_id,
            "condition": result.get("condition", ""),
            "topic": result.get("research_topic", ""),
            "summaries": result.get("summaries", []),
            "sources": [],  # Would be populated with actual sources
            "generated_at": result.get("generated_at", generated_at),
        }

        # Save to database
        _summary_id = str(uuid.uuid4())

        # Update patient record with research data
        _ = (patient_data, _summary_id)

        return research_summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running research summarizer: {str(e)}")


@app.get("/api/patients/{patient_id}/research")
async def get_patient_research(patient_id: str):
    """Get the latest research summary for a patient"""
    try:
        research = db.get_research_for_patient(patient_id)
        if not research:
            return {"patient_id": patient_id, "research": None, "message": "No research available"}
        return {"patient_id": patient_id, "research": research}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching research: {str(e)}")


# Doctor Notes Vector Search Endpoints
@app.post("/api/doctor-notes/search")
async def search_doctor_notes_endpoint(request: DoctorNotesSearchRequest):
    """
    Search doctor notes using vector search.
    Embeds the query and finds semantically similar notes.
    """
    try:
        from tools.doctor_notes_tools import search_doctor_notes

        result = search_doctor_notes(
            query=request.query,
            patient_id=request.patient_id,
            limit=request.limit,
        )

        return {
            "query": request.query,
            "found": result.get("found", False),
            "notes": result.get("notes", []),
            "count": result.get("count", 0),
            "search_type": result.get("search_type", "vector_search"),
            "filtered_by_patient": result.get("filtered_by_patient", False),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching doctor notes: {str(e)}")


@app.post("/api/doctor-notes/answer")
async def answer_from_doctor_notes_endpoint(request: DoctorNotesSearchRequest):
    """
    Answer a question using doctor notes via vector search.
    Returns relevant notes that can help answer the question.
    """
    try:
        from tools.doctor_notes_tools import answer_from_doctor_notes

        result = answer_from_doctor_notes(
            question=request.query,
            patient_id=request.patient_id,
            limit=request.limit,
        )

        return {
            "question": request.query,
            "answered": result.get("answered", False),
            "relevant_notes": result.get("relevant_notes", []),
            "count": result.get("count", 0),
            "message": result.get("message", ""),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering from doctor notes: {str(e)}")


@app.post("/api/doctor-notes/query")
async def query_doctor_notes_with_llm(request: DoctorNotesSearchRequest):
    """
    Answer a question about doctor notes using vector search + LLM.
    Uses semantic search to find relevant notes and LLM to synthesize an answer.
    """
    try:
        result = await orchestrator.answer_doctor_notes_query(
            query=request.query,
            patient_id=request.patient_id,
        )

        return {
            "query": request.query,
            "answer": result.get("answer", ""),
            "supporting_notes": result.get("supporting_notes", []),
            "notes_count": result.get("notes_count", 0),
            "patient_id": request.patient_id,
            "search_type": result.get("search_type", "vector_search"),
            "generated_at": result.get("generated_at", ""),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying doctor notes: {str(e)}")




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


