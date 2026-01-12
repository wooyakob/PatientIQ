from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class SentimentLevel(str, Enum):
    amazing = "amazing"
    good = "good"
    neutral = "neutral"
    poor = "poor"
    terrible = "terrible"


class WearableData(BaseModel):
    timestamps: List[str] = Field(default_factory=list, description="Wearable entry timestamps (daily, last 30 days)")
    heart_rate: List[int] = Field(default_factory=list, description="Daily heart rate readings (last 30 days)")
    step_count: List[int] = Field(default_factory=list, description="Daily step count readings (last 30 days)")


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
    doctor_notes: List[DoctorNote] = Field(
        default_factory=list, description="Doctor notes (fetched separately)"
    )


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

class Message(BaseModel):
    id: str
    message_type: str  # "private" or "public"
    from_id: str
    from_name: str
    to_id: str = None  # For private messages
    to_name: str = None  # For private messages
    subject: str
    content: str
    timestamp: datetime
    read: bool = False
    priority: str = "normal"  # normal, high, urgent


class Appointment(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    appointment_date: str  # ISO format YYYY-MM-DD
    appointment_time: str  # HH:MM format
    appointment_type: str  # follow-up, consultation, emergency, routine
    status: str  # scheduled, completed, cancelled, no-show
    duration_minutes: int = 30
