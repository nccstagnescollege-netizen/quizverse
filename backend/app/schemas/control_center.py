import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Security Overview Dashboard Schemas
# ---------------------------------------------------------------------------

class SecurityOverviewStatsResponse(BaseModel):
    active_examinations_count: int = 0
    active_attempts_count: int = 0
    connected_students_count: int = 0
    interrupted_students_count: int = 0
    open_incidents_count: int = 0
    critical_incidents_count: int = 0
    awaiting_action_incidents_count: int = 0
    seb_active_count: int = 0
    native_mobile_active_count: int = 0
    standard_browser_count: int = 0
    proctoring_sessions_count: int = 0
    pending_recovery_count: int = 0
    last_refresh_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# 2. Security System Health Schemas
# ---------------------------------------------------------------------------

class SecurityHealthItem(BaseModel):
    component: str
    status: str  # OPERATIONAL, DEGRADED, UNAVAILABLE, NOT_CONFIGURED
    latency_ms: Optional[float] = None
    details: Optional[str] = None
    last_checked: datetime = Field(default_factory=datetime.utcnow)


class SecurityHealthResponse(BaseModel):
    overall_status: str  # HEALTHY, DEGRADED, CRITICAL
    checks: List[SecurityHealthItem]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# 3. Policy Template & Validation Schemas
# ---------------------------------------------------------------------------

class SecurityPolicyTemplateResponse(BaseModel):
    id: uuid.UUID
    template_name: str
    code: str
    description: Optional[str] = None
    is_system_template: bool
    configuration_payload: Dict[str, Any]
    required_capabilities: Optional[List[str]] = None
    platform_limitations: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class SecurityPolicyTemplateCreateRequest(BaseModel):
    template_name: str
    code: str
    description: Optional[str] = None
    configuration_payload: Dict[str, Any]
    required_capabilities: Optional[List[str]] = None
    platform_limitations: Optional[List[str]] = None


class PolicyValidationRequest(BaseModel):
    configuration_payload: Dict[str, Any]
    target_quiz_id: Optional[uuid.UUID] = None


class PolicyValidationResponse(BaseModel):
    is_valid: bool
    conflicts: List[str]
    warnings: List[str]
    recommendations: List[str]
    supported_platforms: List[str]
    unsupported_platforms: List[str]


class PolicyAssignRequest(BaseModel):
    quiz_id: uuid.UUID
    template_code_or_id: str
    custom_overrides: Optional[Dict[str, Any]] = None


class PolicyAssignResponse(BaseModel):
    success: bool
    quiz_id: uuid.UUID
    template_assigned: str
    applied_configuration: Dict[str, Any]
    audit_event_id: uuid.UUID


# ---------------------------------------------------------------------------
# 4. Device Compatibility Matrix Schemas
# ---------------------------------------------------------------------------

class CapabilityItem(BaseModel):
    feature_name: str
    description: str
    standard_browser: str  # SUPPORTED, LIMITED, UNAVAILABLE
    seb_desktop: str
    android_native: str
    ios_browser: str
    technical_boundary_note: str


class DeviceCapabilityMatrixResponse(BaseModel):
    platforms: List[str]
    capabilities: List[CapabilityItem]
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DeviceCheckRequest(BaseModel):
    quiz_id: uuid.UUID
    os_name: str
    os_version: Optional[str] = None
    browser_name: str
    browser_version: Optional[str] = None
    is_native_app: bool = False
    is_seb: bool = False
    has_camera: bool = False
    has_microphone: bool = False


class DeviceCheckResponse(BaseModel):
    can_enter: bool
    security_mode: str
    compatibility_level: str  # FULL, LIMITED, INCOMPATIBLE
    reasons: List[str]
    recommended_actions: List[str]


# ---------------------------------------------------------------------------
# 5. Live Monitoring & Incident Management Schemas
# ---------------------------------------------------------------------------

class LiveExamSessionItem(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    student_id: uuid.UUID
    student_name: str
    student_identifier: Optional[str] = None
    status: str
    device_category: str
    browser_or_app: str
    security_mode: str
    connection_status: str  # ONLINE, DEGRADED, OFFLINE
    last_heartbeat_at: Optional[datetime] = None
    server_remaining_seconds: int
    watermark_code: Optional[str] = None
    proctoring_risk_score: Optional[int] = None
    proctoring_risk_level: Optional[str] = None
    incident_count: int
    critical_incident_count: int


class LiveExamSessionListResponse(BaseModel):
    total_active: int
    sessions: List[LiveExamSessionItem]


class IncidentReviewActionRequest(BaseModel):
    action: str  # ASSIGN, REVIEW, RESOLVE, ESCALATE, DISMISS
    assigned_to_admin_id: Optional[uuid.UUID] = None
    note: Optional[str] = None
    resolution_reason: Optional[str] = None
    is_false_positive: bool = False


# ---------------------------------------------------------------------------
# 6. Security Action Orchestration Schemas
# ---------------------------------------------------------------------------

class SecurityActionExecuteRequest(BaseModel):
    action_type: str  # SEND_WARNING, FLAG_ATTEMPT, PAUSE_EXAM, PERMIT_RECOVERY, REVOKE_SESSION, TERMINATE_ATTEMPT
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    reason: str
    confirmation_code: Optional[str] = None


class SecurityActionExecuteResponse(BaseModel):
    success: bool
    action_type: str
    attempt_id: uuid.UUID
    previous_status: str
    new_status: str
    message: str
    audit_event_id: uuid.UUID


# ---------------------------------------------------------------------------
# 7. Alert Management Schemas
# ---------------------------------------------------------------------------

class SecurityAlertRuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    quiz_id: Optional[uuid.UUID] = None
    event_category: str
    min_severity: int
    notification_channels: List[str]
    deduplication_window_seconds: int
    rate_limit_per_hour: int
    escalation_delay_seconds: int
    is_enabled: bool


class SecurityAlertRuleCreateRequest(BaseModel):
    name: str
    quiz_id: Optional[uuid.UUID] = None
    event_category: str = "all"
    min_severity: int = 2
    notification_channels: List[str] = ["in_app"]
    deduplication_window_seconds: int = 300
    rate_limit_per_hour: int = 20
    escalation_delay_seconds: int = 600
    is_enabled: bool = True


# ---------------------------------------------------------------------------
# 8. Security Analytics & Audit Schemas
# ---------------------------------------------------------------------------

class SecurityReportMetricsResponse(BaseModel):
    total_events_count: int
    incident_category_breakdown: Dict[str, int]
    incident_severity_breakdown: Dict[str, int]
    security_mode_distribution: Dict[str, int]
    network_interruption_rate: float
    examination_recovery_rate: float
    false_positive_rate: float
    timeline_distribution: List[Dict[str, Any]]


class SecurityAuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_role: str
    actor_name: str
    action: str
    target_type: str
    target_id: Optional[str] = None
    reason: Optional[str] = None
    outcome: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


class PrivacyRetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    data_category: str
    retention_days: int
    purpose_of_collection: str
    anonymization_procedure: Optional[str] = None
    requires_explicit_consent: bool
    is_locked: bool
    updated_at: datetime


class PrivacyRetentionUpdateRequest(BaseModel):
    retention_days: int
    purpose_of_collection: Optional[str] = None
    anonymization_procedure: Optional[str] = None
