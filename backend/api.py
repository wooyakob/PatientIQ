"""FastAPI application.

## Endpoints

- **GET** `/health`
- **GET** `/api/patients`
- **GET** `/api/patients/{patient_id}`
- **POST** `/api/patients/{patient_id}/summary`
- **POST** `/api/conditions/summary`
- **GET** `/api/patients/{patient_id}/wearables`
- **GET** `/api/patients/{patient_id}/wearables/summary`
- **POST** `/api/patients`
- **GET** `/api/patients/{patient_id}/doctor-notes`
- **POST** `/api/patients/{patient_id}/doctor-notes/search`
- **POST** `/api/doctor-notes`
- **DELETE** `/api/doctor-notes/{note_id}`
- **GET** `/api/patients/{patient_id}/patient-notes`
- **GET** `/api/messages/private/{doctor_id}`
- **POST** `/api/messages/private`
- **GET** `/api/messages/public`
- **POST** `/api/messages/public`
- **POST** `/api/messages/private/{message_id}/read`
- **POST** `/api/messages/public/{message_id}/read`
- **GET** `/api/appointments/doctor/{doctor_id}`
- **GET** `/api/appointments/patient/{patient_id}`
- **POST** `/api/appointments/{appointment_id}/status`
- **GET** `/api/questionnaires/pre-visit/{patient_id}`
- **GET** `/api/questionnaires/pre-visit/{patient_id}/summary`
- **POST** `/api/questionnaires/pre-visit/status`
- **GET** `/api/patients/{patient_id}/research`
- **POST** `/api/patients/{patient_id}/research/ask`
- **POST** `/api/research/answers`
- **PATCH** `/api/research/answers/{answer_id}/rating`
- **POST** `/api/research/tavily/search`
- **POST** `/api/research/pubmed/search`
- **POST** `/api/research/papers/add`
"""

import json
import logging
import sys
import time
import uuid
import os
import hashlib
import asyncio
import requests
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.database import db
from backend.models import (
    Patient,
    WearableData,
    WearablesSummary,
    QuestionnaireSummary,
    DoctorNotesSummary,
)

import agentc
import importlib.util
import langchain_core.messages

from backend.utils.llm_client import chat_completion_text
from backend.utils.embedding_client import embedding_vector
from tools._shared import get_nvidia_embedding


def _load_agent_module(agent_name: str, module_file: str = "graph.py"):
    """
    Load an agent module with proper isolation to avoid naming conflicts.

    Args:
        agent_name: Name of the agent directory (e.g., 'pulmonary_research_agent')
        module_file: Name of the module file to load (default: 'graph.py')

    Returns:
        Loaded module
    """
    agent_dir = str(Path(__file__).parent.parent / "agents" / agent_name)
    module_path = Path(agent_dir) / module_file

    # Use unique module name to avoid conflicts
    unique_module_name = f"{agent_name}_{module_file.replace('.py', '')}"

    spec = importlib.util.spec_from_file_location(unique_module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load agent module spec from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_module_name] = module
    original_sys_path = list(sys.path)
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path = original_sys_path
        # Don't clean up the unique module - keep it in sys.modules

    return module


def _trim_to_last_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    last_dot = text.rfind(".")
    last_bang = text.rfind("!")
    last_q = text.rfind("?")
    last_end = max(last_dot, last_bang, last_q)

    if last_end == -1:
        return text

    return text[: last_end + 1].strip()


def _redact_pii(value: Any) -> Any:
    keys_to_drop = {
        "patient_email",
        "patient_cell",
        "email",
        "phone",
        "insurance_number",
        "emergency_contacts",
    }

    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if str(k) in keys_to_drop:
                continue
            out[str(k)] = _redact_pii(v)
        return out

    if isinstance(value, list):
        return [_redact_pii(v) for v in value]

    if isinstance(value, str):
        s = value
        s = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[REDACTED]", s, flags=re.I)
        s = re.sub(r"\b\d{3}[- .]?\d{3}[- .]?\d{4}\b", "[REDACTED]", s)
        return s

    return value


def _strip_html_to_text(html: str) -> str:
    h = str(html or "")
    if not h.strip():
        return ""
    h = re.sub(r"(?is)<script.*?>.*?</script>", " ", h)
    h = re.sub(r"(?is)<style.*?>.*?</style>", " ", h)
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", h)
    if paras:
        text = "\n\n".join([re.sub(r"(?is)<.*?>", " ", p) for p in paras])
    else:
        text = re.sub(r"(?is)<.*?>", " ", h)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_research_papers(papers: Any) -> List[Dict[str, Any]]:
    if not isinstance(papers, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for p in papers:
        if not isinstance(p, dict):
            continue

        paper = dict(p)
        citation = paper.get("article_citation")
        title = paper.get("title")

        resolved = None
        try:
            resolved = db.get_research_paper_pmc_link(article_citation=citation, title=title)
        except Exception:
            resolved = None

        if isinstance(resolved, str) and resolved.strip():
            paper["pmc_link"] = resolved.strip()

        normalized.append(paper)

    return normalized


# Import PulmonaryResearcher from pulmonary_research_agent/graph.py
pulmonary_graph = _load_agent_module("pulmonary_research_agent", "graph.py")
PulmonaryResearcher = pulmonary_graph.PulmonaryResearcher

# Import DocNotesSearcher from docnotes_search_agent/graph.py
docnotes_graph = _load_agent_module("docnotes_search_agent", "graph.py")
DocNotesSearcher = docnotes_graph.DocNotesSearcher

# Import PrevisitSummarizer from previsit_summary_agent/graph.py
previsit_graph = _load_agent_module("previsit_summary_agent", "graph.py")
PrevisitSummarizer = previsit_graph.PrevisitSummarizer

# Initialize catalog and agents at module level
_catalog = agentc.Catalog()
_root_span = _catalog.Span(name="CKO-Backend")
_pulmonary_researcher = PulmonaryResearcher(catalog=_catalog)
_docnotes_searcher = DocNotesSearcher(catalog=_catalog)
_previsit_summarizer = PrevisitSummarizer(catalog=_catalog)

logger = logging.getLogger("cko")
logger.setLevel(logging.INFO)


def _now_utc_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


app = FastAPI(
    title="Healthcare API",
    description="FastAPI backend for healthcare dashboard",
    version="1.0.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "Unhandled exception request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    try:
        response.headers["X-Request-ID"] = request_id
    except Exception:
        pass

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        getattr(response, "status_code", "?"),
        duration_ms,
    )
    return response


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    expected = (os.getenv("API_KEY") or "").strip()
    if not expected:
        return await call_next(request)
    if request.url.path == "/health":
        return await call_next(request)
    provided = (request.headers.get("x-api-key") or "").strip()
    if provided != expected:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o
        for o in (
            (os.getenv("CORS_ALLOW_ORIGINS") or "")
            or "http://localhost:8080,http://localhost:5173,http://localhost:3000"
        ).split(",")
        if o.strip()
    ],
    allow_credentials=("*" not in (os.getenv("CORS_ALLOW_ORIGINS") or "")),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "service": "Healthcare API"}


# Patient Endpoints
@app.get("/api/patients", response_model=List[Patient])
async def get_patients():
    """Get all patients"""
    try:
        logger.info("get_patients")
        patients = db.get_all_patients()
        return patients
    except Exception as e:
        logger.exception("Error fetching patients")
        raise HTTPException(status_code=500, detail=f"Error fetching patients: {str(e)}")


@app.get("/api/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a specific patient by ID"""
    try:
        logger.info("get_patient patient_id=%s", patient_id)
        patient = db.get_patient(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
        return patient
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching patient patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error fetching patient: {str(e)}")


@app.post("/api/patients/{patient_id}/summary")
async def summarize_patient(patient_id: str):
    """Summarize a patient's raw demographic/profile fields in a single paragraph."""
    try:
        logger.info("summarize_patient patient_id=%s", patient_id)
        patient = db.get_patient_raw(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        questionnaire = None
        try:
            questionnaire = await get_pre_visit_questionnaire(patient_id)
        except Exception:
            questionnaire = None

        patient_redacted = _redact_pii(patient)
        questionnaire_redacted = _redact_pii(questionnaire) if questionnaire else None

        prompt = (
            "You are a clinical assistant. Write ONE paragraph summarizing the patient's profile and, if available, "
            "their pre-visit questionnaire. Capture key conditions, symptoms, functional impact, exposures, and follow-up needs. "
            "Be factual, concise, and avoid speculation. Do not mention that you are an AI. "
            "Use ONLY the facts present in the provided JSON. Do NOT infer, estimate, or modify numeric values (e.g., age, weight, height). "
            "If a value is missing, state it is not provided rather than guessing. "
            "Do NOT include any email addresses, phone numbers, insurance numbers, emergency contacts, or other personal contact information. "
            "End with a period.\n\n"
            f"Patient JSON:\n{json.dumps(patient_redacted, ensure_ascii=False)}\n\n"
            f"Pre-visit questionnaire JSON (if present):\n{json.dumps(questionnaire_redacted, ensure_ascii=False)}"
        )

        text, _raw = await chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.0,
        )

        summary = _trim_to_last_sentence(text)
        return {"patient_id": str(patient_id), "patient": patient_redacted, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error summarizing patient patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error summarizing patient: {str(e)}")


@app.post("/api/conditions/summary")
async def summarize_condition(payload: dict = Body(...)):
    """Summarize a medical condition in a single paragraph (no agents)."""
    try:
        condition = str(payload.get("condition") or "").strip()
        if not condition:
            raise HTTPException(status_code=400, detail="condition is required")

        logger.info("summarize_condition condition=%s", condition)

        prompt = (
            "Write a single-paragraph clinical overview of the condition below for a busy clinician. "
            "Include typical presentation and high-level management considerations. "
            "Keep it concise (under ~90 words) and end with a period. "
            "Do not mention that you are an AI.\n\n"
            f"Condition: {condition}"
        )

        text, _raw = await chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=260,
            temperature=0.2,
        )

        summary = _trim_to_last_sentence(text)
        return {"condition": condition, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error summarizing condition")
        raise HTTPException(status_code=500, detail=f"Error summarizing condition: {str(e)}")


@app.get("/api/patients/{patient_id}/wearables", response_model=WearableData)
async def get_patient_wearables(patient_id: str, days: int = 30):
    """Get wearable data (daily entries) for a patient"""
    try:
        logger.info("get_patient_wearables patient_id=%s days=%s", patient_id, days)
        return db.get_wearables_for_patient(patient_id, days=days)
    except Exception as e:
        logger.exception("Error fetching wearable data patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error fetching wearable data: {str(e)}")


@app.get("/api/patients/{patient_id}/wearables/summary", response_model=WearablesSummary)
async def get_patient_wearables_summary(patient_id: str, days: int = 30):
    """Generate a one-paragraph summary of the last N days of wearable data."""
    try:
        logger.info("get_patient_wearables_summary patient_id=%s days=%s", patient_id, days)

        try:
            days_i = int(days)
        except Exception:
            days_i = 30
        if days_i <= 0:
            days_i = 30
        if days_i > 60:
            days_i = 60

        wearable_data = db.get_wearables_for_patient(patient_id, days=days_i)
        patient = None
        try:
            patient = db.get_patient(patient_id)
        except Exception:
            patient = None

        heart_rate = list((wearable_data or {}).get("heart_rate") or [])
        step_count = list((wearable_data or {}).get("step_count") or [])
        timestamps = list((wearable_data or {}).get("timestamps") or [])
        num_points = min(len(heart_rate), len(step_count), len(timestamps))

        series = []
        for i in range(num_points):
            series.append(
                {
                    "date": str(timestamps[i]),
                    "heart_rate": int(heart_rate[i] or 0),
                    "steps": int(step_count[i] or 0),
                }
            )

        patient_name = str((patient or {}).get("name") or "")
        prompt = (
            "You are a clinical assistant. Summarize the patient's last "
            f"{days_i} days of wearable data (heart rate and steps) in ONE paragraph. "
            "Identify meaningful patterns and trends with concrete examples (e.g., early period vs late period, "
            "increasing steps over last 5 days, sustained elevation in heart rate). "
            "Be factual and concise. Do not mention that you are an AI. End with a period.\n\n"
            f"Patient: {patient_name or patient_id}\n"
            f"Data points: {num_points}\n"
            f"Time series JSON (chronological): {json.dumps(series, ensure_ascii=False)}"
        )

        text, _raw = await chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.2,
        )
        summary = _trim_to_last_sentence(text)
        return {"patient_id": str(patient_id), "days": int(days_i), "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating wearables summary patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error generating wearables summary: {str(e)}")


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


@app.get("/api/patients/{patient_id}/doctor-notes/summary", response_model=DoctorNotesSummary)
async def get_patient_doctor_notes_summary(patient_id: str, max_notes: int = 20):
    """Generate a one-paragraph summary of a patient's doctor notes."""
    try:
        logger.info(
            "get_patient_doctor_notes_summary patient_id=%s max_notes=%s", patient_id, max_notes
        )

        try:
            max_notes_i = int(max_notes)
        except Exception:
            max_notes_i = 20
        if max_notes_i <= 0:
            max_notes_i = 20
        if max_notes_i > 50:
            max_notes_i = 50

        notes = db.get_doctor_notes_for_patient(patient_id) or []
        note_count = len(notes)

        patient = None
        try:
            patient = db.get_patient(patient_id)
        except Exception:
            patient = None
        patient_name = str((patient or {}).get("name") or "")

        notes_for_prompt = []
        for n in notes[:max_notes_i]:
            content = str(n.get("content") or "")
            if len(content) > 800:
                content = content[:800].rstrip() + "…"
            notes_for_prompt.append({"date": str(n.get("date") or ""), "content": content})

        prompt = (
            "You are a clinical assistant. Summarize the patient's doctor visit notes in ONE paragraph. "
            "Focus on the most important clinical themes: key symptoms, diagnoses, treatments/med changes, "
            "test results, plans, and follow-up. Be factual, concise, and avoid speculation. "
            "Do not mention that you are an AI. End with a period.\n\n"
            f"Patient: {patient_name or patient_id}\n"
            f"Total notes available: {note_count}\n"
            f"Notes JSON (most recent first, truncated): {json.dumps(notes_for_prompt, ensure_ascii=False)}"
        )

        text, _raw = await chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=240,
            temperature=0.2,
        )
        summary = _trim_to_last_sentence(text)
        return {
            "patient_id": str(patient_id),
            "note_count": int(note_count),
            "summary": summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating doctor notes summary patient_id=%s", patient_id)
        raise HTTPException(
            status_code=500, detail=f"Error generating doctor notes summary: {str(e)}"
        )


@app.post("/api/patients/{patient_id}/doctor-notes/search")
async def search_patient_doctor_notes(request: Request, patient_id: str, payload: dict = Body(...)):
    """
    Search doctor notes for a patient using semantic search.

    Args:
        patient_id: The patient's ID
        payload: JSON with 'question' field

    Returns:
        Dictionary with patient info, relevant notes, and answer
    """
    try:
        question = payload.get("question", "")
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        doctor_name = str(payload.get("doctor_name") or "Tiffany Mitchell")
        patient_name = str(payload.get("patient_name") or "").strip()
        if not patient_name:
            try:
                patient = db.get_patient(patient_id)
                patient_name = str((patient or {}).get("name") or "").strip()
            except Exception:
                patient_name = ""

        timestamp = _now_utc_iso_z()
        question_id = f"dq_{int(datetime.now().timestamp() * 1000)}"
        question_doc = {
            "question_asked": question,
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "timestamp": timestamp,
        }
        try:
            db.save_doctors_question(question_id, question_doc)
        except Exception as e:
            logger.warning("Warning: Failed to save doctors question: %s", e)

        logger.info(
            "search_patient_doctor_notes patient_id=%s question_len=%s patient_name=%s",
            patient_id,
            len(question),
            patient_name,
        )

        # Use the doc notes search agent directly
        state = DocNotesSearcher.build_starting_state(patient_id=patient_id, question=question)
        if patient_name:
            state["patient_name"] = patient_name

        # Add the question as a human message in JSON format
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "patient_name": "{patient_name or ""}", "question": "{question}"}}'
            )
        )

        # Invoke the agent
        logger.info("Invoking DocNotesSearcher agent for patient_id=%s", patient_id)
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        search_span = _root_span.new(
            name="DocNotesSearcher.invoke",
            agent="docnotes_search_agent",
            endpoint="POST /api/patients/{patient_id}/doctor-notes/search",
            patient_id=str(patient_id),
            request_id=str(request_id or ""),
        )
        agent_result = DocNotesSearcher(catalog=_catalog, span=search_span).invoke(input=state)

        # Format response
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name"),
            "question": agent_result.get("question", question),
            "notes": agent_result.get("notes", []),
            "answer": agent_result.get("answer", ""),
        }
        logger.info(
            "DocNotesSearcher completed - found %s notes, answer_len=%s",
            len(result.get("notes", [])),
            len(result.get("answer", "")),
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        authoritative_patient_name = (patient_name or str(result.get("patient_name") or "")).strip()
        if authoritative_patient_name:
            result["patient_name"] = authoritative_patient_name

        answer_text = str(result.get("answer") or "")
        if answer_text:
            if authoritative_patient_name:
                answer_text = answer_text.replace("[patient_name]", authoritative_patient_name)
                if authoritative_patient_name.lower() != "john doe":
                    answer_text = answer_text.replace("John Doe", authoritative_patient_name)
            if doctor_name:
                answer_text = answer_text.replace("[doctor_name]", doctor_name)
            result["answer"] = answer_text

        answer_id = f"ad_{int(datetime.now().timestamp() * 1000)}"
        referenced_visit_notes = result.get("notes", [])
        answer_doc = {
            "question_asked": question,
            "patient_name": str(result.get("patient_name") or ""),
            "doctor_name": doctor_name,
            "timestamp": timestamp,
            "answer_provided": str(result.get("answer") or ""),
            "referenced_visit_notes": referenced_visit_notes,
        }
        try:
            db.save_answers_doctors(answer_id, answer_doc)
        except Exception as e:
            logger.warning("Warning: Failed to save answers_doctors: %s", e)

        result["referenced_visit_notes"] = referenced_visit_notes

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error searching notes patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error searching notes: {str(e)}")


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
            try:
                vec = await embedding_vector(str(note.get("visit_notes") or ""))
                if vec:
                    db.upsert_doctor_note_embedding(note_id, vec)
            except Exception as e:
                logger.warning(
                    "Warning: Failed to vectorize doctor note note_id=%s patient_id=%s: %s",
                    note_id,
                    str(note.get("patient_id") or ""),
                    e,
                )

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
    """Send a private message to a doctor/staff member."""
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
    """Send a public message visible to all staff."""
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
    """Fetch the pre-visit questionnaire JSON for a patient."""
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


@app.get("/api/questionnaires/pre-visit/{patient_id}/summary", response_model=QuestionnaireSummary)
async def get_pre_visit_questionnaire_summary(patient_id: str):
    """Generate a one-paragraph summary of a patient's pre-visit questionnaire."""
    try:
        questionnaire = await get_pre_visit_questionnaire(patient_id)
        if not isinstance(questionnaire, dict):
            raise HTTPException(status_code=500, detail="Invalid questionnaire format")

        patient_name = str(questionnaire.get("patient_name") or "").strip()
        date_completed = str(questionnaire.get("date_completed") or "").strip()

        questionnaire_redacted = _redact_pii(questionnaire)

        prompt = (
            "You are a clinical assistant. Write ONE paragraph summarizing the patient's pre-visit questionnaire. "
            "Capture the key symptoms, severity, functional impact, relevant exposures, and any red flags or follow-up needs. "
            "Be factual and concise. Do not mention that you are an AI. "
            "Do NOT include any email addresses, phone numbers, insurance numbers, emergency contacts, or other personal contact information. "
            "End with a period.\n\n"
            f"Patient: {patient_name or patient_id}\n"
            f"Date completed: {date_completed or 'unknown'}\n"
            f"Questionnaire JSON: {json.dumps(questionnaire_redacted, ensure_ascii=False)}"
        )

        text, _raw = await chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=240,
            temperature=0.2,
        )

        summary = _trim_to_last_sentence(text)
        return {"patient_id": str(patient_id), "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error generating pre-visit questionnaire summary patient_id=%s", patient_id
        )
        raise HTTPException(
            status_code=500, detail=f"Error generating questionnaire summary: {str(e)}"
        )


@app.post("/api/questionnaires/pre-visit/status")
async def get_pre_visit_questionnaire_status(payload: Dict[str, Any] = Body(...)):
    """Bulk-check existence/completion status for multiple patients' pre-visit questionnaires."""
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


@app.get("/api/patients/{patient_id}/previsit-summary")
async def get_previsit_summary(request: Request, patient_id: str):
    """
    Generate a comprehensive pre-visit summary for a patient using AI.

    Uses hybrid approach:
    - OpenAI (gpt-4o-mini) for tool calling to gather data
    - Mistral for clinical summarization

    Args:
        patient_id: The patient's ID

    Returns:
        Structured pre-visit summary with clinical overview, medications, allergies, symptoms, and concerns
    """
    try:
        logger.info("Generating pre-visit summary for patient_id=%s", patient_id)

        # Build starting state for the agent
        state = PrevisitSummarizer.build_starting_state(patient_id=patient_id)

        # Add initial message
        state["messages"].append(
            langchain_core.messages.HumanMessage(content=f'{{"patient_id": "{patient_id}"}}')
        )

        # Create span for tracing
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        summary_span = _root_span.new(
            name="PrevisitSummarizer.invoke",
            agent="previsit_summary_agent",
            endpoint="GET /api/patients/{patient_id}/previsit-summary",
            patient_id=str(patient_id),
            request_id=str(request_id or ""),
        )

        # Invoke the agent
        logger.info("Invoking PrevisitSummarizer agent for patient_id=%s", patient_id)
        agent_result = PrevisitSummarizer(catalog=_catalog, span=summary_span).invoke(input=state)

        # Build response
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name", "Unknown"),
            "clinical_summary": agent_result.get("clinical_summary", ""),
            "current_medications": agent_result.get("current_medications", []),
            "allergies": agent_result.get(
                "allergies", {"drug": [], "food": [], "environmental": []}
            ),
            "key_symptoms": agent_result.get("key_symptoms", []),
            "patient_concerns": agent_result.get("patient_concerns", []),
            "recent_note_summary": agent_result.get("recent_note_summary", ""),
        }

        logger.info(
            "PrevisitSummarizer completed - %s medications, %s symptoms, %s concerns",
            len(result.get("current_medications", [])),
            len(result.get("key_symptoms", [])),
            len(result.get("patient_concerns", [])),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating pre-visit summary for patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error generating pre-visit summary: {str(e)}")


# Medical Research Agent Endpoints
@app.get("/api/patients/{patient_id}/research")
async def get_patient_research(request: Request, patient_id: str, question: Optional[str] = None):
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

        logger.info(
            "get_patient_research patient_id=%s question_len=%s",
            patient_id,
            len(question),
        )

        # Use the pulmonary research agent directly
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message in JSON format
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        # Invoke the agent
        logger.info("Invoking PulmonaryResearcher agent for patient_id=%s", patient_id)
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        research_span = _root_span.new(
            name="PulmonaryResearcher.invoke",
            agent="pulmonary_research_agent",
            endpoint="GET /api/patients/{patient_id}/research",
            patient_id=str(patient_id),
            request_id=str(request_id or ""),
        )
        agent_result = PulmonaryResearcher(catalog=_catalog, span=research_span).invoke(input=state)

        papers = _normalize_research_papers(agent_result.get("papers", []))

        # Format response
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name"),
            "condition": agent_result.get("condition", ""),
            "question": agent_result.get("question", question),
            "papers": papers,
            "answer": agent_result.get("answer", ""),
        }
        logger.info(
            "PulmonaryResearcher completed - found %s papers, answer_len=%s",
            len(result.get("papers", [])),
            len(result.get("answer", "")),
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching research patient_id=%s", patient_id)
        raise HTTPException(status_code=500, detail=f"Error fetching research: {str(e)}")


@app.post("/api/patients/{patient_id}/research/ask")
async def ask_research_question(request: Request, patient_id: str, payload: dict = Body(...)):
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
            logger.warning("Warning: Failed to save question: %s", e)

        # Use the pulmonary research agent directly with the specific question
        state = PulmonaryResearcher.build_starting_state(patient_id=patient_id, question=question)

        # Add the question as a human message in JSON format
        state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
            )
        )

        # Invoke the agent
        logger.info(
            "Invoking PulmonaryResearcher agent for patient_id=%s question_id=%s",
            patient_id,
            question_id,
        )
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        research_span = _root_span.new(
            name="PulmonaryResearcher.ask.invoke",
            agent="pulmonary_research_agent",
            endpoint="POST /api/patients/{patient_id}/research/ask",
            patient_id=str(patient_id),
            question_id=str(question_id),
            request_id=str(request_id or ""),
        )
        agent_result = PulmonaryResearcher(catalog=_catalog, span=research_span).invoke(input=state)

        papers = _normalize_research_papers(agent_result.get("papers", []))

        # Format response
        result = {
            "patient_id": agent_result.get("patient_id", patient_id),
            "patient_name": agent_result.get("patient_name"),
            "condition": agent_result.get("condition", ""),
            "question": agent_result.get("question", question),
            "papers": papers,
            "answer": agent_result.get("answer", ""),
        }
        logger.info(
            "PulmonaryResearcher completed - found %s papers, answer_len=%s",
            len(result.get("papers", [])),
            len(result.get("answer", "")),
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # Add question_id to result
        result["question_id"] = question_id

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing research question patient_id=%s", patient_id)
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


@app.post("/api/research/tavily/search")
async def search_tavily_research(payload: dict = Body(...)):
    """Search latest medical research using Tavily web search API."""
    try:
        query = payload.get("query", "").strip()
        max_results = payload.get("max_results", 3)

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        if max_results <= 0:
            max_results = 3
        if max_results > 10:
            max_results = 10

        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise HTTPException(status_code=503, detail="Tavily API not configured")

        # Call Tavily API
        url = "https://api.tavily.com/search"
        headers = {"Authorization": f"Bearer {tavily_api_key}", "Content-Type": "application/json"}
        payload_data = {
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_raw_content": True,
        }

        response = await asyncio.to_thread(
            requests.post, url, headers=headers, json=payload_data, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Transform results to paper schema
        papers = []
        for result in data.get("results", []):
            # Extract domain from URL for author field
            domain = result.get("url", "").split("//")[-1].split("/")[0]

            paper = {
                "title": result.get("title", "Untitled"),
                "author": domain,
                "article_text": result.get("raw_content", result.get("content", ""))[:5000],
                "article_citation": result.get("url", ""),
                "pmc_link": result.get("url", ""),
                "source_type": "tavily",
                "score": result.get("score", 0),
            }
            papers.append(paper)

        logger.info(f"Tavily search returned {len(papers)} results for query: {query}")
        return {"results": papers}

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.exception("Tavily API error")
        raise HTTPException(status_code=502, detail=f"Tavily API error: {str(e)}")
    except Exception as e:
        logger.exception("Error searching Tavily")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/api/research/pubmed/search")
async def search_pubmed_research(payload: dict = Body(...)):
    """Search PubMed (optionally including PMC full text) and return normalized paper results."""
    try:
        query = str(payload.get("query") or "").strip()
        max_results = int(payload.get("max_results", 3) or 3)
        days_back = payload.get("days_back")
        include_pmc_full_text = bool(payload.get("include_pmc_full_text", True))

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        if max_results <= 0:
            max_results = 3
        if max_results > 10:
            max_results = 10

        esearch_params = {
            "db": "pubmed",
            "term": query,
            "sort": "date",
            "retmode": "json",
            "retmax": str(max_results),
        }
        if days_back is not None:
            try:
                days_i = int(days_back)
            except Exception:
                days_i = 0
            if days_i > 0:
                esearch_params["datetype"] = "pdat"
                esearch_params["reldate"] = str(days_i)

        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        esearch_resp = await asyncio.to_thread(
            requests.get, esearch_url, params=esearch_params, timeout=30
        )
        esearch_resp.raise_for_status()
        esearch = esearch_resp.json()
        pmids = list(((esearch.get("esearchresult") or {}).get("idlist") or []))

        if not pmids:
            return {"results": []}

        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        esummary_resp = await asyncio.to_thread(
            requests.get,
            esummary_url,
            params={"db": "pubmed", "id": ",".join(pmids), "retmode": "json"},
            timeout=30,
        )
        esummary_resp.raise_for_status()
        esummary = esummary_resp.json()
        result_map = esummary.get("result") or {}

        papers: List[Dict[str, Any]] = []
        for pmid in pmids:
            item = result_map.get(str(pmid)) or {}
            title = str(item.get("title") or "").strip() or "Untitled"
            source = str(item.get("source") or "").strip()
            pubdate = str(item.get("pubdate") or "").strip()
            authors = item.get("authors") or []
            author_names = []
            for a in authors:
                if isinstance(a, dict) and a.get("name"):
                    author_names.append(str(a.get("name")))
            author_str = " ".join(author_names).strip() or "Unknown"

            pmc_link = ""
            try:
                elink_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
                elink_resp = await asyncio.to_thread(
                    requests.get,
                    elink_url,
                    params={
                        "dbfrom": "pubmed",
                        "db": "pmc",
                        "linkname": "pubmed_pmc",
                        "id": str(pmid),
                        "retmode": "xml",
                    },
                    timeout=30,
                )
                elink_resp.raise_for_status()
                root = ET.fromstring(elink_resp.text)
                pmc_id = None
                for linksetdb in root.findall(".//LinkSetDb"):
                    linkname = linksetdb.findtext("LinkName") or ""
                    if linkname.strip() != "pubmed_pmc":
                        continue
                    id_text = linksetdb.findtext("Link/Id")
                    if id_text and str(id_text).strip().isdigit():
                        pmc_id = str(id_text).strip()
                        break
                if pmc_id:
                    pmc_link = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/"
            except Exception:
                pmc_link = ""

            abstract_text = ""
            try:
                efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                efetch_resp = await asyncio.to_thread(
                    requests.get,
                    efetch_url,
                    params={"db": "pubmed", "id": str(pmid), "retmode": "xml"},
                    timeout=30,
                )
                efetch_resp.raise_for_status()
                root = ET.fromstring(efetch_resp.text)
                parts = []
                for at in root.findall(".//AbstractText"):
                    if at.text and str(at.text).strip():
                        parts.append(str(at.text).strip())
                abstract_text = "\n\n".join(parts).strip()
            except Exception:
                abstract_text = ""

            article_text = abstract_text
            if pmc_link and include_pmc_full_text:
                try:
                    pmc_resp = await asyncio.to_thread(requests.get, pmc_link, timeout=30)
                    pmc_resp.raise_for_status()
                    extracted = _strip_html_to_text(pmc_resp.text)
                    if extracted:
                        article_text = extracted
                except Exception:
                    article_text = abstract_text

            article_text = (article_text or "").strip()
            if len(article_text) > 5000:
                article_text = article_text[:5000]

            pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{urllib.parse.quote_plus(str(pmid))}/"
            citation = " ".join([p for p in [source, pubdate, f"PMID:{pmid}"] if p]).strip()

            papers.append(
                {
                    "author": author_str,
                    "title": title,
                    "article_text": article_text,
                    "article_citation": citation or pubmed_url,
                    "pmc_link": pmc_link or pubmed_url,
                    "source_type": "pubmed",
                    "pubmed_url": pubmed_url,
                    "pmid": str(pmid),
                }
            )

        return {"results": papers}
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.exception("PubMed API error")
        raise HTTPException(status_code=502, detail=f"PubMed API error: {str(e)}")
    except Exception as e:
        logger.exception("Error searching PubMed")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/api/research/papers/add")
async def add_research_paper(payload: dict = Body(...)):
    """Add a research paper to database with automatic vectorization."""
    try:
        # Validate required fields
        title = payload.get("title", "").strip()
        article_text = payload.get("article_text", "").strip()
        article_citation = payload.get("article_citation", "").strip()

        if not all([title, article_text, article_citation]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: title, article_text, article_citation",
            )

        # Check for duplicate by URL
        existing = db.check_paper_exists(article_citation)
        if existing:
            raise HTTPException(status_code=409, detail="Paper already exists in database")

        # Generate unique paper ID
        timestamp = int(datetime.now().timestamp())
        url_hash = hashlib.md5(article_citation.encode()).hexdigest()[:8]
        paper_id = f"tavily_{timestamp}_{url_hash}"

        # Build paper document
        paper_doc = {
            "paper_id": paper_id,
            "title": title,
            "author": payload.get("author", "Unknown"),
            "article_text": article_text,
            "article_citation": article_citation,
            "pmc_link": payload.get("pmc_link", article_citation),
            "source_type": payload.get("source_type", "tavily"),
            "added_at": datetime.now().isoformat(),
            "added_by": "Tiffany Mitchell",
        }

        # Vectorize article_text
        vectorized = False
        try:
            logger.info(f"Vectorizing paper: {paper_id}")
            embedding = get_nvidia_embedding(article_text)
            paper_doc["article_text_vectorized"] = embedding
            vectorized = True
            logger.info(f"Successfully vectorized paper: {paper_id}")
        except Exception as e:
            logger.warning(f"Vectorization failed for {paper_id}: {e}")
            # Continue without vector - paper still searchable via text

        # Save to database
        success = db.save_research_paper(paper_id, paper_doc)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save paper to database")

        logger.info(f"Added paper {paper_id} (vectorized={vectorized})")
        return {
            "message": "Paper added successfully",
            "paper_id": paper_id,
            "vectorized": vectorized,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error adding paper")
        raise HTTPException(status_code=500, detail=f"Error adding paper: {str(e)}")
