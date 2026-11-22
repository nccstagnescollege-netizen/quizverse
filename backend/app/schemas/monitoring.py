import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Overview & KPI Schemas
# ---------------------------------------------------------------------------
class MonitoringAlertItem(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: Optional[str] = None
    student_id: Optional[uuid.UUID] = None
    student_name: Optional[str] = None
    attempt_id: Optional[uuid.UUID] = None
    alert_type: str
    priority: str
    title: str
    details: Optional[Dict[str, Any]] = None
    is_acknowledged: bool = False
    is_resolved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LiveExaminationItem(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: Optional[str] = None
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: int = 60
    total_marks: float = 0.0
    total_questions: int = 0
    enrolled_count: int = 0
    active_count: int = 0
    submitted_count: int = 0
    disconnected_count: int = 0
    sync_issue_count: int = 0
    security_alert_count: int = 0
    lead_invigilator_name: Optional[str] = None
    invigilators_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LiveMonitoringOverviewResponse(BaseModel):
    active_examinations_count: int = 0
    total_eligible_participants: int = 0
    active_participants: int = 0
    disconnected_participants: int = 0
    sync_issue_participants: int = 0
    submitted_participants: int = 0
    pending_participants: int = 0
    critical_security_alerts: int = 0
    examinations_nearing_deadline: int = 0
    completed_examinations_today: int = 0
    recent_alerts: List[MonitoringAlertItem] = []
    active_examinations: List[LiveExaminationItem] = []


class LiveExaminationsListResponse(BaseModel):
    total: int
    items: List[LiveExaminationItem]


# ---------------------------------------------------------------------------
# Invigilator Schemas
# ---------------------------------------------------------------------------
class InvigilatorSummary(BaseModel):
    id: uuid.UUID
    invigilator_id: uuid.UUID
    name: str
    email: str
    is_lead: bool = False
    permissions: List[str] = []
    status: str = "active"
    assigned_at: datetime


class InvigilatorAssignmentCreateRequest(BaseModel):
    invigilator_id: uuid.UUID
    is_lead: bool = False
    permissions: Optional[List[str]] = Field(
        default=["view_progress", "send_announcements", "report_incidents"]
    )


class InvigilatorAssignmentResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    invigilator_id: uuid.UUID
    invigilator_name: str
    invigilator_email: str
    is_lead: bool
    permissions: List[str]
    status: str
    assigned_by_name: Optional[str] = None
    assigned_at: datetime

    class Config:
        from_attributes = True


class InvigilatorListResponse(BaseModel):
    total: int
    items: List[InvigilatorAssignmentResponse]


# ---------------------------------------------------------------------------
# Room & Participant Schemas
# ---------------------------------------------------------------------------
class ExaminationMonitoringRoomResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: Optional[str] = None
    programme_name: Optional[str] = None
    semester_name: Optional[str] = None
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: int
    total_marks: float
    total_questions: int
    enrolled_participants: int
    active_now: int
    completed_submissions: int
    disconnected_count: int
    sync_pending_count: int
    unresolved_incidents_count: int
    critical_alerts_count: int
    invigilators: List[InvigilatorSummary] = []
    timeline_summary: Dict[str, Any] = {}


class ParticipantMonitoringItem(BaseModel):
    student_id: uuid.UUID
    attempt_id: Optional[uuid.UUID] = None
    full_name: str
    register_number: Optional[str] = None
    email: str
    student_group: Optional[str] = None
    attempt_status: str  # NOT_STARTED, IN_PROGRESS, SUBMITTED, TIME_EXPIRED, TERMINATED, CANCELLED
    connection_status: str  # CONNECTED, RECONNECTING, DISCONNECTED, COMPLETED, NOT_STARTED
    last_heartbeat_at: Optional[datetime] = None
    sync_status: str  # SYNCHRONIZED, SYNC_PENDING, SYNC_FAILED, NOT_STARTED
    last_sync_at: Optional[datetime] = None
    current_question_index: Optional[int] = None
    current_section_name: Optional[str] = None
    answered_count: int = 0
    marked_for_review_count: int = 0
    unanswered_count: int = 0
    progress_percentage: float = 0.0
    time_spent_seconds: int = 0
    remaining_seconds: int = 0
    deadline_at: Optional[datetime] = None
    security_alerts_count: int = 0
    latest_security_event: Optional[str] = None
    has_active_incident: bool = False
    ip_address: Optional[str] = None
    browser: Optional[str] = None
    browser_compatibility_status: Optional[str] = "PASSED"
    fullscreen_status: Optional[str] = "ACTIVE"
    focus_loss_count: int = 0
    fullscreen_exit_count: int = 0
    incident_count: int = 0
    review_status: Optional[str] = "NONE"
    latest_incident: Optional[str] = None

    # Phase 23 - Watermark & Capture Monitoring
    watermark_status: Optional[str] = "ACTIVE"
    watermark_code: Optional[str] = None
    capture_capability: Optional[str] = "detection_limited"
    capture_signals_count: int = 0
    latest_capture_signal: Optional[str] = None

    # Phase 24 & 25 - Mobile & Desktop Security Badges
    flag_secure_active: Optional[bool] = False
    kiosk_mode_active: Optional[bool] = False
    mobile_interruptions_count: Optional[int] = 0
    root_detected: Optional[bool] = False
    is_seb_verified: Optional[bool] = False
    seb_version: Optional[str] = None
    desktop_mode: Optional[str] = "standard_browser"
    lab_device_reference: Optional[str] = None
    desktop_interruption_count: Optional[int] = 0

    # Phase 26 - Advanced AI Proctoring Fields
    proctoring_session_id: Optional[uuid.UUID] = None
    camera_status: Optional[str] = "not_required"
    microphone_status: Optional[str] = "not_required"
    face_presence_state: Optional[str] = "detected"
    head_position_state: Optional[str] = "facing_screen"
    multiple_faces_detected: bool = False
    audio_level_state: Optional[str] = "normal"
    ai_risk_score: float = 0.0
    ai_risk_level: str = "LOW"
    ai_classification: str = "NORMAL"
    proctoring_review_status: str = "NOT_REQUIRED"
    proctoring_decision: Optional[str] = None


class ParticipantMonitoringListResponse(BaseModel):
    total: int
    items: List[ParticipantMonitoringItem]


class AttemptEventItem(BaseModel):
    id: uuid.UUID
    event_type: str
    severity: str
    details: Optional[Dict[str, Any]] = None
    client_timestamp: Optional[datetime] = None
    created_at: datetime


class QuestionProgressSummary(BaseModel):
    question_index: int
    question_type: str
    is_answered: bool
    is_marked_for_review: bool
    answered_at: Optional[datetime] = None


class IncidentSummaryItem(BaseModel):
    id: uuid.UUID
    incident_code: str
    category: str
    severity: str
    status: str
    title: str
    created_at: datetime


class ExtensionHistoryItem(BaseModel):
    id: uuid.UUID
    extension_minutes: int
    previous_deadline: datetime
    new_deadline: datetime
    reason: str
    extended_by_name: Optional[str] = None
    created_at: datetime


class ParticipantDetailMonitoringResponse(BaseModel):
    participant: ParticipantMonitoringItem
    event_timeline: List[AttemptEventItem] = []
    question_progress: List[QuestionProgressSummary] = []
    incidents: List[IncidentSummaryItem] = []
    extension_history: List[ExtensionHistoryItem] = []


# ---------------------------------------------------------------------------
# Announcement Schemas
# ---------------------------------------------------------------------------
class ExaminationAnnouncementCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=2)
    announcement_type: str = Field(
        default="general",
        description="general, time_reminder, technical_notice, correction_notice, emergency, submission_reminder"
    )
    target_scope: str = Field(
        default="all_participants",
        description="all_participants, selected_participants, group"
    )
    target_participant_ids: Optional[List[str]] = None
    requires_acknowledgement: bool = False


class ExaminationAnnouncementResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_name: Optional[str] = None
    title: str
    message: str
    announcement_type: str
    target_scope: str
    target_participant_ids: Optional[List[str]] = None
    requires_acknowledgement: bool
    acknowledgement_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    total: int
    items: List[ExaminationAnnouncementResponse]


class AnnouncementAcknowledgementRequest(BaseModel):
    announcement_id: uuid.UUID
    attempt_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Incident Management Schemas
# ---------------------------------------------------------------------------
class ExaminationIncidentCreateRequest(BaseModel):
    quiz_id: Optional[uuid.UUID] = None
    student_id: Optional[uuid.UUID] = None
    attempt_id: Optional[uuid.UUID] = None
    category: str = Field(
        default="other",
        description="network_issue, synchronization_failure, access_problem, session_conflict, content_problem, timing_problem, security_concern, student_support, other"
    )
    severity: str = Field(default="medium", description="low, medium, high, critical")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", description="Incident details")
    assigned_to: Optional[uuid.UUID] = None


class IncidentNoteCreateRequest(BaseModel):
    note: str = Field(..., min_length=1)


class IncidentNoteResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExaminationIncidentUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="OPEN, ASSIGNED, UNDER_INVESTIGATION, WAITING_FOR_RESPONSE, RESOLVED, CLOSED")
    assigned_to: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None


class ExaminationIncidentResponse(BaseModel):
    id: uuid.UUID
    incident_code: str
    quiz_id: uuid.UUID
    student_id: Optional[uuid.UUID] = None
    student_name: Optional[str] = None
    attempt_id: Optional[uuid.UUID] = None
    category: str
    severity: str
    status: str
    title: str
    description: str
    reported_by: Optional[uuid.UUID] = None
    reported_by_name: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes: List[IncidentNoteResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    total: int
    items: List[ExaminationIncidentResponse]


# ---------------------------------------------------------------------------
# Emergency Interventions Schemas
# ---------------------------------------------------------------------------
class ExtendTimeRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=180, description="Minutes to extend the official examination deadline")
    target_type: str = Field(default="all", description="all, selected_student")
    student_id: Optional[uuid.UUID] = None
    reason: str = Field(default="Proctor extension", min_length=1, description="Audit reason for time extension")


class TerminateAttemptRequest(BaseModel):
    attempt_id: Optional[uuid.UUID] = None
    student_id: Optional[uuid.UUID] = None
    reason: str = Field(default="Administrative termination", min_length=1, description="Mandatory reason for manual attempt termination")


class CancelExaminationRequest(BaseModel):
    reason: str = Field(default="Administrative cancellation", min_length=1, description="Mandatory justification for emergency examination cancellation")


class RevokeSessionRequest(BaseModel):
    attempt_id: uuid.UUID
    reason: str = Field(default="Session revocation", min_length=1, description="Mandatory justification for session revocation")
    reason: str = Field(..., min_length=5, description="Mandatory justification for session revocation")


class MonitoringInterventionResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    action_type: str
    performed_by_id: Optional[uuid.UUID] = None
    performed_by_name: Optional[str] = None
    target_type: str
    target_id: Optional[str] = None
    reason: str
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterventionListResponse(BaseModel):
    total: int
    items: List[MonitoringInterventionResponse]


# ---------------------------------------------------------------------------
# Phase 31: Real-Time Live Examination Proctoring, Webcam & Audio Schemas
# ---------------------------------------------------------------------------
class MediaExaminationRoomResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    is_active: bool
    audio_broadcast_allowed: bool
    recording_enabled: bool
    recording_policy_disclosed: bool
    max_participants: int
    created_at: datetime

    class Config:
        from_attributes = True


class MediaParticipantSessionItem(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    quiz_id: uuid.UUID
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = "Student Candidate"
    candidate_email: Optional[str] = None
    attempt_id: Optional[uuid.UUID] = None
    session_token: str
    peer_id: str
    role: str
    camera_status: str
    microphone_status: str
    stream_status: str
    audio_level: str
    network_quality: str
    device_info: Optional[Dict[str, Any]] = None
    is_active: bool
    is_pinned: bool = False
    is_audio_listened: bool = False
    last_heartbeat_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MediaFeedResponse(BaseModel):
    quiz_id: uuid.UUID
    room_id: uuid.UUID
    recording_enabled: bool
    total_active_participants: int
    connected_cameras: int
    connected_microphones: int
    active_audio_listening_student_id: Optional[str] = None
    participants: List[MediaParticipantSessionItem]


class MediaSessionInitRequest(BaseModel):
    attempt_id: Optional[uuid.UUID] = None
    peer_id: str = Field(..., description="Unique WebRTC peer identifier generated by client")
    role: str = Field(default="student", description="student, invigilator, admin")
    device_info: Optional[Dict[str, Any]] = None
    camera_status: str = Field(default="Connected")
    microphone_status: str = Field(default="Connected")


class MediaSessionInitResponse(BaseModel):
    room_id: uuid.UUID
    session_id: uuid.UUID
    session_token: str
    peer_id: str
    recording_enabled: bool
    audio_broadcast_allowed: bool


class WebRTCSignalMessage(BaseModel):
    type: str = Field(..., description="offer, answer, candidate, join, leave, ping")
    sender_peer_id: str
    target_peer_id: Optional[str] = None
    sdp: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class WebRTCSignalExchangeRequest(BaseModel):
    session_token: str
    signals: List[WebRTCSignalMessage] = []


class WebRTCSignalResponse(BaseModel):
    success: bool = True
    delivered_count: int = 0
    signals: List[WebRTCSignalMessage] = []


class MediaDeviceEventCreateRequest(BaseModel):
    event_type: str = Field(
        ...,
        description="CAMERA_DISCONNECTED, MICROPHONE_DISCONNECTED, PERMISSION_REVOKED, TRACK_ENDED, STREAM_RECOVERED, AUDIO_LEVEL_CHANGE, NETWORK_DEGRADED"
    )
    previous_status: Optional[str] = None
    new_status: str
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"


class MediaDeviceEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    new_status: str
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudentMonitoringConsentRequest(BaseModel):
    attempt_id: Optional[uuid.UUID] = None
    consent_version: str = Field(default="v1.0")
    webcam_acknowledged: bool = Field(default=True)
    microphone_acknowledged: bool = Field(default=True)
    recording_acknowledged: bool = Field(
        default=False,
        description="Explicit acknowledgment that recording is disabled unless separately authorized"
    )


class StudentMonitoringConsentResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    consent_version: str
    webcam_acknowledged: bool
    microphone_acknowledged: bool
    recording_acknowledged: bool
    consented_at: datetime

    class Config:
        from_attributes = True


class ListenAudioRequest(BaseModel):
    student_id: uuid.UUID
    listen: bool = Field(default=True, description="Strictly activates audio for this student only")


class TwoWayCommunicationRequest(BaseModel):
    student_id: uuid.UUID
    comm_type: str = Field(
        default="instruction",
        description="instruction, warning, request_verification, restore_camera, restore_mic"
    )
    message: str = Field(..., min_length=1, max_length=500)


class TwoWayCommunicationResponse(BaseModel):
    success: bool = True
    recipient_id: uuid.UUID
    comm_type: str
    message: str
    delivered_at: datetime

