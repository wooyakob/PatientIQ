from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class SentimentLevel(str, Enum):
    positive = "positive"
    neutral = "neutral"
    mixed = "mixed"
    negative = "negative"


class WearableData(BaseModel):
    timestamps: List[str] = Field(
        default_factory=list, description="Wearable entry timestamps (daily, last 30 days)"
    )
    heart_rate: List[int] = Field(
        default_factory=list, description="Daily heart rate readings (last 30 days)"
    )
    step_count: List[int] = Field(
        default_factory=list, description="Daily step count readings (last 30 days)"
    )


class WearablesSummary(BaseModel):
    patient_id: str
    days: int
    summary: str


class QuestionnaireSummary(BaseModel):
    patient_id: str
    summary: str


class DoctorNotesSummary(BaseModel):
    patient_id: str
    note_count: int
    summary: str


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
    sentiment_rating: str = ""
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


# Wearable Analytics Models


class WearableAnalyticsRequest(BaseModel):
    """Request model for wearable analytics agent"""

    patient_id: str = Field(..., description="Patient ID to analyze")
    question: str = Field(
        default="Analyze wearable data and provide clinical insights",
        description="Specific question or analysis request",
    )
    days: int = Field(default=30, description="Number of days of data to analyze", ge=1, le=90)


class WearableMetricTrend(BaseModel):
    """Trend analysis for a single metric"""

    metric_name: str
    average: float
    minimum: float
    maximum: float
    std_dev: float
    threshold: float = None
    days_above_threshold: int = None
    days_below_threshold: int = None


class WearableAlertDetail(BaseModel):
    """Detailed alert from trend analysis"""

    metric: str
    severity: str  # critical, high, medium, low
    priority: int
    message: str
    values: List[float] = Field(default_factory=list)
    threshold: float = None
    clinical_significance: str


class SimilarPatient(BaseModel):
    """Information about a demographically similar patient"""

    patient_id: str
    patient_name: str
    age: int = None
    gender: str = None
    medical_conditions: str = None
    similarity_score: int
    matching_criteria: List[str] = Field(default_factory=list)
    age_difference_years: float = None


class CohortMetric(BaseModel):
    """Statistical metrics for cohort comparison"""

    mean: float
    std: float
    median: float = None
    min: float = None
    max: float = None
    cohort_size: int


class CohortOutlier(BaseModel):
    """Outlier detection result"""

    metric: str
    metric_key: str
    patient_value: float
    cohort_mean: float
    cohort_std: float
    difference: float
    difference_percent: float
    std_deviations: float
    percentile: int
    unit: str
    significance: str  # concerning, highly concerning, favorable, highly favorable
    interpretation: str


class ResearchPaper(BaseModel):
    """Research paper with relevance to symptoms"""

    title: str
    author: str
    article_citation: str = None
    pmc_link: str = None
    article_text: str = None
    relevance_score: float = None
    key_findings: List[str] = Field(default_factory=list)
    matched_condition: str = None


class TrendAnalysisResult(BaseModel):
    """Complete trend analysis results"""

    alerts: List[WearableAlertDetail]
    trends: dict  # Flexible dict for various metric trends
    summary: str
    recommendations: List[str] = Field(default_factory=list)
    alert_counts: dict = None
    data_points_analyzed: int
    analysis_period_days: int


class CohortComparisonResult(BaseModel):
    """Complete cohort comparison results"""

    patient_metrics: dict
    cohort_metrics: dict
    percentile_rankings: dict
    outliers: List[CohortOutlier] = Field(default_factory=list)
    comparison_summary: str
    cohort_size: int
    analysis_date: str = None


class WearableAnalyticsResponse(BaseModel):
    """Complete response from wearable analytics agent"""

    patient_id: str
    patient_name: str
    patient_condition: str
    question: str
    wearable_data: List[dict] = Field(
        default_factory=list, description="Summary of wearable data analyzed"
    )
    similar_patients: List[SimilarPatient] = Field(default_factory=list)
    trend_analysis: TrendAnalysisResult = None
    cohort_comparison: CohortComparisonResult = None
    research_papers: List[ResearchPaper] = Field(default_factory=list)
    alerts: List[WearableAlertDetail] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    answer: str = Field(..., description="Comprehensive clinical summary")
    generated_at: datetime = Field(default_factory=datetime.now)
    analysis_duration_seconds: float = None
