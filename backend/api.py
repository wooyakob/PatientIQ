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
    Background task that runs AI agents for all patients.
    This analyzes patient data and generates insights automatically.
    """
    print("\n" + "=" * 60)
    print("Running AI Agents for All Patients...")
    print("=" * 60)

    try:
        # Get all patients
        patients = db.get_all_patients()
        print(f"Found {len(patients)} patients to analyze\n")

        for patient in patients:
            patient_id = patient.get("id")
            patient_name = patient.get("name")
            print(f"Processing: {patient_name} ({patient_id})")

            # Run wearable monitoring agent
            try:
                print("   Analyzing wearable data...")
                wearable_result = await orchestrator.run_wearable_monitor(patient_id, patient)

                # Save alerts
                alerts = wearable_result.get("alerts", [])
                for alert in alerts:
                    alert_id = alert.get("id", str(uuid.uuid4()))
                    db.save_wearable_alert(alert_id, alert)

                if alerts:
                    print(f"   Generated {len(alerts)} alert(s)")
                else:
                    print("   No alerts needed")

            except Exception as e:
                print(f"   Wearable analysis failed: {e}")

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
                    print("   Generating research summaries...")
                    research_result = await orchestrator.run_research_summarizer(patient_id, patient)

                    # Save research
                    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    research_summary = {
                        "patient_id": patient_id,
                        "condition": research_result.get("condition", ""),
                        "topic": research_result.get("research_topic", ""),
                        "summaries": research_result.get("summaries", []),
                        "sources": [],
                        "generated_at": generated_at
                    }
                    db.save_research_summary(str(uuid.uuid4()), research_summary)

                    # Update patient record
                    patient["research_topic"] = research_summary["topic"]
                    patient["research_content"] = research_summary["summaries"]
                    db.upsert_patient(patient_id, patient)

                    print("   Research summaries generated")
                else:
                    print("   Research already exists (skipping)")

            except Exception as e:
                print(f"   Research generation failed: {e}")

            print()  # Blank line between patients

        print("=" * 60)
        print("Agent run completed for all patients")
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
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AgentTriggerRequest(BaseModel):
    patient_id: str


class MessageRouteRequest(BaseModel):
    announcement: str
    staff_directory: List[dict] = []


class QuestionnaireRequest(BaseModel):
    patient_id: str
    questionnaire_responses: dict
    appointment_date: str


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
        "message": "AI agents are continuously monitoring all patients and generating insights"
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
            "message": "Agents are running in the background. Check logs for progress."
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


# Wearable Monitoring Agent Endpoints
@app.post("/api/agents/wearable-monitor/run")
async def run_wearable_monitor(request: AgentTriggerRequest):
    """
    Trigger the Wearable Data Monitoring Agent for a patient.
    Analyzes wearable data and generates alerts if needed.
    """
    try:
        patient_data = db.get_patient(request.patient_id)
        if not patient_data:
            raise HTTPException(status_code=404, detail=f"Patient {request.patient_id} not found")

        # Run agent using orchestrator
        result = await orchestrator.run_wearable_monitor(request.patient_id, patient_data)

        # Save alerts to database
        alerts = result.get("alerts", [])
        for alert in alerts:
            db.save_wearable_alert(alert["id"], alert)

        return {
            "patient_id": request.patient_id,
            "analysis": result.get("analysis", ""),
            "alerts": alerts,
            "alert_count": len(alerts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running wearable monitor: {str(e)}")


@app.get("/api/patients/{patient_id}/alerts")
async def get_patient_alerts(patient_id: str):
    """Get all alerts for a patient"""
    try:
        alerts = db.get_alerts_for_patient(patient_id)
        return {"patient_id": patient_id, "alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


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
            "generated_at": result.get("generated_at", generated_at)
        }

        # Save to database
        summary_id = str(uuid.uuid4())
        db.save_research_summary(summary_id, research_summary)

        # Update patient record with research data
        patient_data["research_topic"] = research_summary["topic"]
        patient_data["research_content"] = research_summary["summaries"]
        db.upsert_patient(request.patient_id, patient_data)

        return research_summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error running research summarizer: {str(e)}"
        )


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


# Message Routing Agent Endpoints
@app.post("/api/agents/message-router/run")
async def run_message_router(request: MessageRouteRequest):
    """
    Trigger the Message Board Routing Agent.
    Analyzes announcements and routes to relevant staff members.
    """
    try:
        # Run agent using orchestrator
        result = await orchestrator.run_message_router(
            request.announcement,
            request.staff_directory
        )

        # Save routes to database
        routes = result.get("routes", [])
        for route in routes:
            db.save_message_route(route["id"], route)

        return {
            "announcement": request.announcement,
            "routes": routes,
            "recipients": result.get("recipients", []),
            "priority": result.get("priority", "medium")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running message router: {str(e)}")


# Questionnaire Summarization Agent Endpoints
@app.post("/api/agents/questionnaire-summarizer/run")
async def run_questionnaire_summarizer(request: QuestionnaireRequest):
    """
    Trigger the Medical Questionnaire Summarization Agent.
    Summarizes patient questionnaire responses before appointments.
    """
    try:
        patient_data = db.get_patient(request.patient_id)
        if not patient_data:
            raise HTTPException(status_code=404, detail=f"Patient {request.patient_id} not found")

        # Run agent using orchestrator
        result = await orchestrator.run_questionnaire_summarizer(
            request.patient_id,
            patient_data,
            request.questionnaire_responses,
            request.appointment_date
        )

        # Prepare summary for database
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        summary_data = {
            "patient_id": request.patient_id,
            "appointment_date": request.appointment_date,
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "generated_at": result.get("generated_at", generated_at),
        }

        # Save to database
        summary_id = str(uuid.uuid4())
        db.save_questionnaire_summary(summary_id, summary_data)

        return summary_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error running questionnaire summarizer: {str(e)}"
        )


@app.get("/api/patients/{patient_id}/questionnaire")
async def get_patient_questionnaire(patient_id: str):
    """Get the latest questionnaire summary for a patient"""
    try:
        questionnaire = db.get_questionnaire_for_patient(patient_id)
        if not questionnaire:
            return {
                "patient_id": patient_id,
                "questionnaire": None,
                "message": "No questionnaire available"
            }
        return {"patient_id": patient_id, "questionnaire": questionnaire}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questionnaire: {str(e)}")


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


# Batch Agent Run Endpoint
@app.post("/api/agents/run-all")
async def run_all_agents(request: AgentTriggerRequest):
    """
    Trigger all applicable agents for a patient.
    This is useful for periodic updates or when loading patient dashboard.
    """
    try:
        patient_data = db.get_patient(request.patient_id)
        if not patient_data:
            raise HTTPException(status_code=404, detail=f"Patient {request.patient_id} not found")

        results = {}

        # Run wearable monitoring
        try:
            wearable_result = await orchestrator.run_wearable_monitor(
                request.patient_id, patient_data
            )
            results["wearable"] = {
                "status": "success",
                "alerts": wearable_result.get("alerts", [])
            }
            # Save alerts
            for alert in wearable_result.get("alerts", []):
                db.save_wearable_alert(alert["id"], alert)
        except Exception as e:
            results["wearable"] = {"status": "error", "error": str(e)}

        # Run research summarization
        try:
            research_result = await orchestrator.run_research_summarizer(
                request.patient_id, patient_data
            )
            results["research"] = {
                "status": "success",
                "topic": research_result.get("research_topic", ""),
                "summaries": research_result.get("summaries", [])
            }
            # Save research
            research_summary = {
                "patient_id": request.patient_id,
                "condition": research_result.get("condition", ""),
                "topic": research_result.get("research_topic", ""),
                "summaries": research_result.get("summaries", []),
                "sources": [],
                "generated_at": datetime.now().isoformat()
            }
            db.save_research_summary(str(uuid.uuid4()), research_summary)
            # Update patient
            patient_data["research_topic"] = research_summary["topic"]
            patient_data["research_content"] = research_summary["summaries"]
            db.upsert_patient(request.patient_id, patient_data)
        except Exception as e:
            results["research"] = {"status": "error", "error": str(e)}

        return {
            "patient_id": request.patient_id,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running agents: {str(e)}")