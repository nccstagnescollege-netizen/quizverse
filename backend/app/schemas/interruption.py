import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Interruption Event Ingestion
# ---------------------------------------------------------------------------

class InterruptionEventRequest(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    event_type: str = Field(..., description="e.g. INCOMING_CALL, APP_BACKGROUND, APP_SWITCH, NOTIFICATION_SHADE, TAB_SWITCH, FULLSCREEN_EXIT, NETWORK_OFFLINE, NETWORK_ONLINE, OS_DIALOG, BROWSER_CRASH, SEB_INTERRUPTION")
    severity_level: int = Field(1, ge=0, le=4, description="0: Info, 1: Minor, 2: Warning, 3: Serious, 4: Critical")
    duration_seconds: int = Field(0, ge=0)
    details: Optional[Dict[str, Any]] = None
    client_timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class InterruptionEventResponse(BaseModel):
    success: bool
    event_id: uuid.UUID
    action_required: str = Field("NONE", description="NONE, WARNING_DISPLAYED, EXAM_PAUSED, REVALIDATION_REQUIRED, PENDING_REVIEW")
    server_remaining_seconds: int
    message: str


# ---------------------------------------------------------------------------
# 2. Device Preparation Pre-Flight
# ---------------------------------------------------------------------------

class DevicePreparationRequest(BaseModel):
    quiz_id: uuid.UUID
    attempt_id: Optional[uuid.UUID] = None
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    is_charging: Optional[bool] = None
    network_type: Optional[str] = "unknown"
    dnd_acknowledged: bool = True
    notifications_muted_acknowledged: bool = True
    os_platform: str = Field(..., description="android, ios, windows, macos, linux, other")
    device_info: Optional[Dict[str, Any]] = None


class DevicePreparationResponse(BaseModel):
    success: bool
    can_proceed: bool
    policy: Dict[str, Any]
    recommendations: List[str]
    logged_at: datetime


# ---------------------------------------------------------------------------
# 3. Examination Session Recovery
# ---------------------------------------------------------------------------

class SessionRecoveryRequest(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    reason: str = Field("RELOAD", description="RELOAD, BROWSER_CRASH, APP_CRASH, NETWORK_RECOVERY, OS_RESTART")
    offline_answers_count: int = Field(0, ge=0)


class SessionRecoveryResponse(BaseModel):
    success: bool
    recovery_status: str = Field("RESUMED", description="RESUMED, REQUIRES_REVALIDATION, PENDING_REVIEW, EXPIRED, TERMINATED")
    recovery_token: str
    server_remaining_seconds: int
    server_deadline: datetime
    total_synced_answers: int
    interruption_policy: str
    message: str


# ---------------------------------------------------------------------------
# 4. Idempotent Answer Batch Synchronization
# ---------------------------------------------------------------------------

class AnswerSyncItem(BaseModel):
    quiz_question_id: uuid.UUID
    selected_option_ids: Optional[List[uuid.UUID]] = None
    text_response: Optional[str] = None
    time_spent_seconds: int = Field(0, ge=0)
    client_timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class AnswerBatchSyncRequest(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    answers: List[AnswerSyncItem]


class AnswerBatchSyncResponse(BaseModel):
    success: bool
    total_processed: int
    synced_count: int
    ignored_count: int
    server_time: datetime
    results: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# 5. Incident Timeline & Actions
# ---------------------------------------------------------------------------

class IncidentTimelineItemResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    event_type: str
    event_source: str = Field("CLIENT_REPORTED", description="CLIENT_REPORTED vs SERVER_VERIFIED")
    severity_level: int
    duration_seconds: int
    details: Optional[Dict[str, Any]] = None
    client_timestamp: Optional[datetime] = None
    server_timestamp: datetime


class IncidentTimelineListResponse(BaseModel):
    attempt_id: uuid.UUID
    total_events: int
    events: List[IncidentTimelineItemResponse]


class IncidentActionRequest(BaseModel):
    action: str = Field(..., description="ACKNOWLEDGE, ADD_NOTE, ASSIGN, MARK_REVIEWED, ESCALATE, AUTHORIZE_RECOVERY, REQUEST_CLARIFICATION")
    assigned_to: Optional[uuid.UUID] = None
    note: Optional[str] = None
    resolution_notes: Optional[str] = None
    reason: Optional[str] = None


class IncidentActionResponse(BaseModel):
    success: bool
    incident_id: uuid.UUID
    new_status: str
    action_performed: str
    message: str


# ---------------------------------------------------------------------------
# 6. Policy & Filtered Incident Responses
# ---------------------------------------------------------------------------

class InterruptionPolicyResponse(BaseModel):
    quiz_id: uuid.UUID
    interruption_handling_policy: str
    allow_call_recovery: bool
    max_call_interruptions: int
    call_grace_seconds: int
    require_device_prep_acknowledgment: bool
    auto_pause_on_disconnect: bool
    revalidation_code_required: bool
    network_interruption_policy: Optional[str] = "allow_sync"
    allow_interrupted_session_resume: bool = True
