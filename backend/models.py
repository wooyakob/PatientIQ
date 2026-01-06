from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class SentimentLevel(str, Enum):
    AMAZING = "amazing"
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    TERRIBLE = "terrible"


class WearableData(BaseModel):
    heart_rate: List[int] = Field(default_factory=list, description="7-day heart rate readings")
    step_count: List[int] = Field(default_factory=list, description="7-day step count readings")


class DoctorNote(BaseModel):
    id: str
    date: str
    time: str
    content: str


class Patient(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    condition: str
    avatar: str
    last_visit: str
    next_appointment: str
    wearable_data: WearableData
    sentiment: SentimentLevel
    private_notes: str
    research_topic: str
    research_content: List[str]
    doctor_notes: List[DoctorNote] = Field(default_factory=list, description="Doctor notes (fetched separately)")


class WearableAlert(BaseModel):
    patient_id: str
    alert_type: str
    message: str
    severity: str  # low, medium, high, critical
    timestamp: datetime
    metrics: dict


class ResearchSummary(BaseModel):
    patient_id: str
    condition: str
    topic: str
    summaries: List[str]
    sources: List[str]
    generated_at: datetime


class MessageRoute(BaseModel):
    id: str
    original_message: str
    routed_to: List[str]  # List of doctor/staff IDs
    priority: str
    timestamp: datetime


class QuestionnaireSummary(BaseModel):
    patient_id: str
    appointment_date: str
    summary: str
    key_points: List[str]
    generated_at: datetime
