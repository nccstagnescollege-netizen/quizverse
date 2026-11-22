import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Proctoring Policy & Configuration Schemas
# ---------------------------------------------------------------------------
class ProctoringPolicyUpdateRequest(BaseModel):
    webcam_monitoring_enabled: Optional[bool] = None
    microphone_monitoring_enabled: Optional[bool] = None
    face_presence_detection: Optional[bool] = None
    multiple_person_detection: Optional[bool] = None
    head_position_detection: Optional[bool] = None
    audio_anomaly_detection: Optional[bool] = None
    browser_activity_integration: Optional[bool] = None
    mobile_interruption_integration: Optional[bool] = None
    seb_security_integration: Optional[bool] = None
    proctoring_mandatory: Optional[bool] = None
    webcam_permission_required: Optional[bool] = None
    microphone_permission_required: Optional[bool] = None
    monitoring_interval_seconds: Optional[int] = Field(None, ge=3, le=60)
    risk_warning_threshold: Optional[int] = Field(None, ge=10, le=100)
    risk_critical_threshold: Optional[int] = Field(None, ge=20, le=100)
    human_review_required: Optional[bool] = None
    recording_enabled: Optional[bool] = None
    recording_retention_days: Optional[int] = Field(None, ge=1, le=365)


class ProctoringPolicyResponse(BaseModel):
    quiz_id: uuid.UUID
    webcam_monitoring_enabled: bool
    microphone_monitoring_enabled: bool
    face_presence_detection: bool
    multiple_person_detection: bool
    head_position_detection: bool
    audio_anomaly_detection: bool
    browser_activity_integration: bool
    mobile_interruption_integration: bool
    seb_security_integration: bool
    proctoring_mandatory: bool
    webcam_permission_required: bool
    microphone_permission_required: bool
    monitoring_interval_seconds: int
    risk_warning_threshold: int
    risk_critical_threshold: int
    human_review_required: bool
    recording_enabled: bool
    recording_retention_days: int
    privacy_disclosure: str = (
        "AI proctoring operates locally on student devices to detect camera/microphone availability, "
        "face presence, and audio activity. No biometric facial recognition templates or secret recordings "
        "are created. AI risk scoring is strictly advisory and cannot penalize students without human review."
    )


# ---------------------------------------------------------------------------
# 2. Proctoring Session Lifecycle Schemas
# ---------------------------------------------------------------------------
class ProctoringSessionInitRequest(BaseModel):
    camera_status: str = Field(default="not_required", description="granted, denied, unavailable, not_required")
    microphone_status: str = Field(default="not_required", description="granted, denied, unavailable, not_required")
    camera_label: Optional[str] = None
    microphone_label: Optional[str] = None
    lighting_condition: Optional[str] = "good"
    is_accommodated_exempt: Optional[bool] = False
    recording_consent_given: Optional[bool] = False
    client_metadata: Optional[Dict[str, Any]] = None


class ProctoringSessionResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    register_number: Optional[str] = None
    status: str
    camera_status: str
    microphone_status: str
    lighting_condition: str
    is_accommodated_exempt: bool
    face_presence_state: str
    head_position_state: str
    multiple_faces_detected: bool
    audio_level_state: str
    total_face_absent_count: int
    total_multiple_face_count: int
    total_head_movement_count: int
    total_audio_anomaly_count: int
    total_proctoring_events: int
    ai_risk_score: float
    ai_risk_level: str
    ai_classification: str
    ai_confidence: float
    risk_factors: Optional[List[Dict[str, Any]]] = None
    review_status: str
    reviewer_decision: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    recording_consent_given: bool
    started_at: datetime
    last_heartbeat_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 3. Telemetry Signals Batch Submission
# ---------------------------------------------------------------------------
class ProctoringSignalItem(BaseModel):
    event_type: str = Field(
        ...,
        description="FACE_ABSENT, MULTIPLE_FACES, HEAD_POSE_ANOMALY, AUDIO_ELEVATED, SPEECH_DETECTED, CAMERA_PERMISSION_DENIED, MIC_PERMISSION_DENIED, LIGHTING_POOR, CAMERA_INTERRUPTED"
    )
    severity: Optional[str] = "LOW"
    confidence_score: Optional[float] = 0.85
    duration_seconds: Optional[int] = 0
    details: Optional[Dict[str, Any]] = None
    occurred_at: Optional[datetime] = None


class ProctoringSignalBatchRequest(BaseModel):
    face_presence_state: Optional[str] = None
    head_position_state: Optional[str] = None
    multiple_faces_detected: Optional[bool] = None
    audio_level_state: Optional[str] = None
    lighting_condition: Optional[str] = None
    signals: List[ProctoringSignalItem] = []


class ProctoringEventItem(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    event_type: str
    severity: str
    confidence_score: float
    duration_seconds: int
    details: Optional[Dict[str, Any]] = None
    occurred_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 4. Explainable Risk Assessment Schemas
# ---------------------------------------------------------------------------
class ProctoringRiskAssessmentResponse(BaseModel):
    session_id: uuid.UUID
    attempt_id: uuid.UUID
    ai_risk_score: float  # 0.0 to 100.0
    ai_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    ai_classification: str  # NORMAL, TECHNICAL_INTERRUPTION, REQUIRES_ATTENTION, POTENTIALLY_SUSPICIOUS, CRITICAL_REVIEW
    ai_confidence: float
    risk_factors: List[Dict[str, Any]]
    recommended_action: str
    disclaimer: str = (
        "AI risk scoring is purely advisory and probabilistic. It does not constitute evidence of cheating. "
        "A human invigilator or academic authority must independently investigate before reaching any disciplinary decision."
    )


# ---------------------------------------------------------------------------
# 5. Human Decision & Incident Review Schemas
# ---------------------------------------------------------------------------
class ProctoringIncidentReviewRequest(BaseModel):
    decision: str = Field(
        ...,
        description="confirmed_concern, not_a_violation, technical_issue, inconclusive, escalated"
    )
    justification: str = Field(..., min_length=3, description="Proctor justification for the decision")
    action_taken: Optional[str] = Field(default="noted", description="warned_candidate, dismissed, escalated_to_committee, noted")


class ProctoringIncidentReviewResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    decision: str
    justification: str
    risk_score_at_review: Optional[float] = None
    classification_at_review: Optional[str] = None
    action_taken: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 6. Invigilator Dashboard & Real-Time Alerts
# ---------------------------------------------------------------------------
class ProctoringDashboardCandidateItem(BaseModel):
    session_id: uuid.UUID
    attempt_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    register_number: Optional[str] = None
    email: str
    attempt_status: str
    camera_status: str
    microphone_status: str
    lighting_condition: str
    face_presence_state: str
    head_position_state: str
    multiple_faces_detected: bool
    audio_level_state: str
    ai_risk_score: float
    ai_risk_level: str
    ai_classification: str
    review_status: str
    reviewer_decision: Optional[str] = None
    total_events: int
    last_heartbeat_at: datetime
    is_accommodated: bool


class ProctoringDashboardOverviewResponse(BaseModel):
    quiz_id: uuid.UUID
    total_proctored_candidates: int
    active_now: int
    nominal_count: int
    requires_attention_count: int
    critical_review_count: int
    unresolved_alerts_count: int
    candidates: List[ProctoringDashboardCandidateItem]


class ProctoringAlertItem(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    alert_type: str
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None
    occurred_at: datetime
    acknowledged: bool
