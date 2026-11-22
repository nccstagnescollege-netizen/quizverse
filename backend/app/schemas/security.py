"""
Pydantic Schemas for Phase 14 Advanced Examination Security & Anti-Cheating System.
Covers policy management, transparent student notices, secure event logging,
risk assessments, security alerts, and investigation timelines.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# 1. Security Policies
# ---------------------------------------------------------------------------

class SecurityPolicyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    track_tab_switch: bool = Field(True, description="Detect when browser tab or page visibility changes")
    track_focus_loss: bool = Field(True, description="Detect window blur and focus changes")
    require_fullscreen: bool = Field(False, description="Whether full-screen mode is required to start/continue")
    track_fullscreen_exit: bool = Field(True, description="Record full-screen exit events")
    block_copy_paste: bool = Field(False, description="Block clipboard copy/paste in question text")
    track_copy_paste: bool = Field(True, description="Log copy, paste, and cut attempts")
    block_context_menu: bool = Field(True, description="Disable right-click context menu")
    track_page_reload: bool = Field(True, description="Monitor browser reloads & navigation")
    enable_watermark: bool = Field(True, description="Render subtle anti-screenshot dynamic watermark")
    watermark_pattern: str = Field(
        "QUIZVERSE | {student_name} | {masked_reg} | {attempt_id}",
        description="Template for dynamic watermark rendering"
    )
    max_tab_switches_warning: int = Field(2, ge=1, le=50, description="Warning threshold for tab switching")
    max_tab_switches_critical: int = Field(5, ge=1, le=100, description="Alert threshold for tab switching")
    max_focus_losses_warning: int = Field(3, ge=1, le=50, description="Warning threshold for focus loss")
    max_fullscreen_exits_warning: int = Field(2, ge=1, le=50, description="Warning threshold for fullscreen exit")
    single_session_enforced: bool = Field(True, description="Restrict candidate to exactly one active session")
    allow_session_recovery: bool = Field(True, description="Allow reconnecting from another tab after confirmation")
    randomize_question_order: bool = Field(True, description="Randomize question sequence per attempt")
    randomize_option_order: bool = Field(True, description="Randomize option order for multiple-choice questions")
    student_notice_text: Optional[str] = Field(None, description="Custom transparent security notice text")
    student_acknowledgement_required: bool = Field(True, description="Require candidate to accept policy before starting")

    # Phase 22 - Advanced Browser Lockdown Controls
    fullscreen_exit_policy: str = Field("warning_only", description="warning_only, record_incident, pause_exam, flag_review")
    max_focus_loss_count: int = Field(5, ge=1, le=100, description="Maximum permitted focus loss incidents before alert")
    disable_copy: bool = Field(True, description="Prohibit clipboard copy within exam interface")
    disable_paste: bool = Field(True, description="Prohibit clipboard paste into exam inputs unless permitted")
    disable_context_menu: bool = Field(True, description="Prohibit browser right-click context menu")
    print_restrictions: bool = Field(True, description="Interdict print attempts and mask print viewports")
    navigation_warning: bool = Field(True, description="Trigger beforeunload and history traps against accidental navigation")
    network_interruption_policy: str = Field("buffer_and_resume", description="buffer_and_resume, pause_on_disconnect")
    require_invigilator_review: bool = Field(True, description="Require human invigilator review before any academic penalty")

    # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
    watermark_opacity: float = Field(0.06, ge=0.01, le=1.0, description="Watermark opacity")
    watermark_font_size: int = Field(12, ge=8, le=36, description="Watermark font size in pt/px")
    watermark_rotation_deg: int = Field(-25, ge=-90, le=90, description="Watermark rotation angle")
    watermark_spacing_px: int = Field(140, ge=40, le=400, description="Grid spacing in pixels")
    watermark_update_interval_sec: int = Field(30, ge=5, le=300, description="Timestamp rotation interval")
    watermark_mask_student_id: bool = Field(True, description="Mask register numbers for student privacy")
    watermark_show_timestamp: bool = Field(True, description="Include live server-synced timestamp")
    watermark_show_exam_id: bool = Field(True, description="Include exam attempt reference")
    watermark_custom_text: Optional[str] = Field(None, description="Optional institution prefix or watermark banner")
    require_watermark_validation: bool = Field(False, description="Verify active watermark rendering")
    block_screen_capture_api: bool = Field(True, description="Interdict Screen Capture MediaDevices requests")
    track_screenshot_signals: bool = Field(True, description="Log PrintScreen and Snipping Tool keyboard combos")
    track_screen_recording_signals: bool = Field(True, description="Monitor screen capture API invocations")


class SecurityPolicyCreateRequest(SecurityPolicyBase):
    quiz_id: Optional[UUID] = Field(None, description="Quiz ID for override; null for platform default")


class SecurityPolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    track_tab_switch: Optional[bool] = None
    track_focus_loss: Optional[bool] = None
    require_fullscreen: Optional[bool] = None
    track_fullscreen_exit: Optional[bool] = None
    block_copy_paste: Optional[bool] = None
    track_copy_paste: Optional[bool] = None
    block_context_menu: Optional[bool] = None
    track_page_reload: Optional[bool] = None
    enable_watermark: Optional[bool] = None
    watermark_pattern: Optional[str] = None
    max_tab_switches_warning: Optional[int] = None
    max_tab_switches_critical: Optional[int] = None
    max_focus_losses_warning: Optional[int] = None
    max_fullscreen_exits_warning: Optional[int] = None
    single_session_enforced: Optional[bool] = None
    allow_session_recovery: Optional[bool] = None
    randomize_question_order: Optional[bool] = None
    randomize_option_order: Optional[bool] = None
    student_notice_text: Optional[str] = None
    student_acknowledgement_required: Optional[bool] = None

    # Phase 22 - Advanced Browser Lockdown Controls
    fullscreen_exit_policy: Optional[str] = None
    max_focus_loss_count: Optional[int] = None
    disable_copy: Optional[bool] = None
    disable_paste: Optional[bool] = None
    disable_context_menu: Optional[bool] = None
    print_restrictions: Optional[bool] = None
    navigation_warning: Optional[bool] = None
    network_interruption_policy: Optional[str] = None
    require_invigilator_review: Optional[bool] = None

    # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
    watermark_opacity: Optional[float] = None
    watermark_font_size: Optional[int] = None
    watermark_rotation_deg: Optional[int] = None
    watermark_spacing_px: Optional[int] = None
    watermark_update_interval_sec: Optional[int] = None
    watermark_mask_student_id: Optional[bool] = None
    watermark_show_timestamp: Optional[bool] = None
    watermark_show_exam_id: Optional[bool] = None
    watermark_custom_text: Optional[str] = None
    require_watermark_validation: Optional[bool] = None
    block_screen_capture_api: Optional[bool] = None
    track_screenshot_signals: Optional[bool] = None
    track_screen_recording_signals: Optional[bool] = None


class SecurityPolicyResponse(SecurityPolicyBase):
    id: UUID
    quiz_id: Optional[UUID] = None
    policy_scope: str = "quiz"
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# 2. Student Security Notice & Transparency
# ---------------------------------------------------------------------------

class SecurityNoticeResponse(BaseModel):
    quiz_id: UUID
    quiz_title: str
    track_tab_switch: bool
    track_focus_loss: bool
    require_fullscreen: bool
    track_fullscreen_exit: bool
    block_copy_paste: bool
    track_copy_paste: bool
    block_context_menu: bool
    enable_watermark: bool
    student_acknowledgement_required: bool
    notice_text: str
    watermark_text: Optional[str] = None
    candidate_name: Optional[str] = None
    masked_identifier: Optional[str] = None


class SecurityNoticeAcknowledgeRequest(BaseModel):
    acknowledged: bool = Field(..., description="Confirmation that student read and accepted monitoring notice")


class SecurityNoticeAcknowledgeResponse(BaseModel):
    success: bool
    attempt_id: UUID
    acknowledged_at: datetime
    message: str


# ---------------------------------------------------------------------------
# 3. Security Event Collection (Student Interface -> Server)
# ---------------------------------------------------------------------------

class SecurityEventItem(BaseModel):
    event_category: str = Field(..., description="TAB_SWITCH, FOCUS_LOSS, FULLSCREEN, CLIPBOARD, CONTEXT_MENU, NAVIGATION")
    event_name: str = Field(..., description="e.g. TAB_HIDDEN, TAB_VISIBLE, WINDOW_FOCUS_LOST, FULLSCREEN_EXIT, COPY_ATTEMPT")
    client_timestamp: Optional[datetime] = None
    duration_ms: Optional[int] = None
    sequence_number: Optional[int] = None
    event_metadata: Optional[Dict[str, Any]] = None


class SecurityEventSubmitRequest(BaseModel):
    events: List[SecurityEventItem] = Field(..., min_length=1, max_length=50)


class SecurityEventSubmitResponse(BaseModel):
    success: bool
    recorded_count: int
    current_risk_score: float
    current_risk_level: str
    active_alerts_count: int
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# 4. Security Alerts & Investigation
# ---------------------------------------------------------------------------

class SecurityAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    quiz_id: UUID
    quiz_title: Optional[str] = None
    student_id: UUID
    student_name: Optional[str] = None
    masked_identifier: Optional[str] = None
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH
    occurrences_count: int
    first_observed_at: datetime
    last_observed_at: datetime
    status: str  # UNREVIEWED, UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED
    resolution_reason: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SecurityAlertListResponse(BaseModel):
    alerts: List[SecurityAlertResponse]
    total: int
    unreviewed_count: int
    medium_or_high_count: int


class SecurityAlertUpdateRequest(BaseModel):
    status: str = Field(..., description="UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED")
    resolution_reason: Optional[str] = Field(None, description="Administrative rationale for the resolution")


class InvestigationNoteCreateRequest(BaseModel):
    note_text: str = Field(..., min_length=1, max_length=2000)
    action_taken: str = Field("NOTE_ADDED", description="NOTE_ADDED, MARKED_UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED")
    alert_id: Optional[UUID] = None


class InvestigationNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    alert_id: Optional[UUID] = None
    admin_id: Optional[UUID] = None
    admin_name: Optional[str] = None
    note_text: str
    action_taken: str
    created_at: datetime


class InvestigationTimelineItemResponse(BaseModel):
    id: UUID
    event_category: str
    event_name: str
    severity: str
    description: Optional[str] = None
    client_timestamp: Optional[datetime] = None
    server_timestamp: datetime
    duration_ms: Optional[int] = None
    sequence_number: int
    metadata: Optional[Dict[str, Any]] = None


class InvestigationDetailResponse(BaseModel):
    attempt_id: UUID
    quiz_id: UUID
    quiz_title: str
    student_id: UUID
    student_name: str
    masked_identifier: str
    attempt_status: str
    started_at: datetime
    deadline_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    submission_reason: Optional[str] = None
    risk_score: float
    risk_level: str
    total_events_count: int
    timeline: List[InvestigationTimelineItemResponse]
    alerts: List[SecurityAlertResponse]
    notes: List[InvestigationNoteResponse]


# ---------------------------------------------------------------------------
# 5. Security Analytics Dashboard
# ---------------------------------------------------------------------------

class SecurityDashboardSummaryResponse(BaseModel):
    total_active_attempts: int
    total_security_events: int
    low_severity_events: int
    medium_severity_events: int
    high_severity_events: int
    unreviewed_alerts: int
    resolved_alerts: int
    attempts_under_investigation: int
    session_conflicts_count: int
    event_categories_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    recent_alerts: List[SecurityAlertResponse]


# ---------------------------------------------------------------------------
# 6. Data Retention Controls
# ---------------------------------------------------------------------------

class SecurityRetentionPurgeRequest(BaseModel):
    retention_days: int = Field(90, ge=14, le=1825, description="Purge non-investigated events older than N days")
    preserve_under_investigation: bool = Field(True, description="Keep attempts that have unresolved alerts or investigation notes")


class SecurityRetentionPurgeResponse(BaseModel):
    success: bool
    purged_events_count: int
    retention_cutoff_date: datetime
    preserved_investigations_count: int
    message: str


# ---------------------------------------------------------------------------
# 7. Browser Security Compatibility & Pre-Flight Lockdown (Phase 22)
# ---------------------------------------------------------------------------

class BrowserCompatibilityCheckItem(BaseModel):
    key: str
    title: str
    status: str  # passed, warning, unsupported, action_required
    details: Optional[str] = None
    message: Optional[str] = None
    is_mandatory: bool = False


class BrowserCompatibilitySubmitRequest(BaseModel):
    browser_name: str
    browser_version: str
    os_name: str
    os_version: str
    device_type: str = "desktop"
    is_secure_context: bool = True
    javascript_enabled: bool = True
    fullscreen_supported: bool = True
    visibility_api_supported: bool = True
    storage_available: bool = True
    screen_width: int
    screen_height: int
    viewport_width: int
    viewport_height: int
    network_online: bool = True
    network_downlink: Optional[float] = None
    network_rtt: Optional[int] = None
    is_seb_detected: bool = False
    checks: List[BrowserCompatibilityCheckItem] = []
    overall_status: str = "PASSED"
    attempt_id: Optional[UUID] = None


class BrowserCompatibilityResponse(BaseModel):
    success: bool
    record_id: Optional[UUID] = None
    overall_status: str
    can_proceed: bool
    message: str
    unsupported_notice: str = "Note: Standard web browsers cannot prevent operating-system screenshots, screen recording, external cameras, or second devices."
    checks: List[BrowserCompatibilityCheckItem] = []


# ---------------------------------------------------------------------------
# 8. Dynamic Watermark & Anti-Capture Signals (Phase 23)
# ---------------------------------------------------------------------------

class WatermarkSessionResponse(BaseModel):
    watermark_code: str
    watermark_text: str
    student_display_name: str
    student_masked_identifier: str
    institution_name: str
    opacity: float
    font_size: int
    rotation_deg: int
    spacing_px: int
    update_interval_sec: int
    issued_at: datetime
    server_time: datetime
    is_valid: bool
    model_config = ConfigDict(from_attributes=True)


class WatermarkVerificationRequest(BaseModel):
    watermark_code: str
    rendered_text: Optional[str] = None
    client_timestamp: Optional[datetime] = None


class WatermarkVerificationResponse(BaseModel):
    valid: bool
    watermark_code: str
    server_time: datetime
    message: str


class CaptureCapabilitySubmitRequest(BaseModel):
    screen_capture_api_supported: bool = False
    screenshot_shortcut_supported: bool = True
    display_media_active: bool = False
    detection_tier: str = "detection_limited"  # detection_supported, detection_limited, unsupported
    browser_vendor: str = "Unknown"
    os_platform: str = "Unknown"
    notes: Optional[str] = None


class CaptureCapabilityResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    detection_tier: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CaptureSignalSubmitRequest(BaseModel):
    signal_type: str  # SCREENSHOT_KEY_COMBO, PRINT_SCREEN_KEY, DISPLAY_MEDIA_STARTED, BLUR_CAPTURE_CORRELATION
    detection_source: str  # keyboard_shortcut, media_devices_api, window_blur_correlation
    confidence_level: str = "low"  # low, medium, high
    client_timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class CaptureSignalResponse(BaseModel):
    success: bool
    signal_id: Optional[UUID] = None
    event_category: str
    message: str
    requires_human_review: bool = True

