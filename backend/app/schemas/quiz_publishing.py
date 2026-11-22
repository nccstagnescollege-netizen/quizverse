from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# Configuration Schemas
# -------------------------------------------------------------

class QuizConfigurationBase(BaseModel):
    timezone: str = "UTC"
    availability_mode: str = "immediate"  # immediate, scheduled, restricted
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reading_time_minutes: int = 0
    accommodations_extra_minutes: int = 0
    late_entry_minutes: Optional[int] = None
    early_access_minutes: Optional[int] = None
    grace_period_minutes: int = 5
    timer_type: str = "per_student"  # per_student, server_window

    shuffle_questions: bool = True
    shuffle_options: bool = True
    question_grouping: str = "preserve_order"  # preserve_order, randomize_within_sections, fixed
    question_selection_mode: str = "all_questions"  # all_questions, section_rules

    passing_criteria_type: str = "percentage"  # percentage, fixed_marks
    passing_marks: Optional[Decimal] = None
    passing_percentage: Decimal = Decimal("40.00")
    negative_marking_type: str = "none"  # none, fixed, question_specific
    fixed_negative_marks: Decimal = Decimal("0.00")
    partial_marking_enabled: bool = False
    rounding_precision: int = 2
    evaluation_method: str = "automatic"  # automatic, manual, mixed
    require_manual_evaluation: bool = False

    navigation_mode: str = "free"  # free, sequential
    allow_previous_nav: bool = True
    allow_answer_change: bool = True
    allow_mark_for_review: bool = True
    allow_skip_questions: bool = True
    show_question_palette: bool = True
    show_answered_stats: bool = True

    manual_submission_allowed: bool = True
    auto_submit_on_timeout: bool = True
    submission_confirmation_modal: bool = True
    submit_unanswered_questions: bool = True
    allow_attempt_reentry_on_disconnect: bool = True
    reentry_grace_minutes: int = 15

    registration_required: bool = False
    account_required: bool = False
    max_attempts: int = 1
    one_attempt_per_student: bool = True
    allow_multiple_devices: bool = False
    require_invitation: bool = False
    restricted_student_groups: List[str] = Field(default_factory=list)

    result_release_policy: str = "immediate"  # immediate, after_close, after_manual_eval, after_admin_approval, never
    show_score_immediately: bool = True
    show_correct_answers: bool = False
    show_answer_keys: bool = False
    show_explanations: bool = False
    show_section_breakdown: bool = True
    show_final_status_pass_fail: bool = True

    log_focus_loss: bool = True
    log_copy_paste: bool = True
    enforce_fullscreen: bool = False
    watermark_enabled: bool = False
    concurrent_session_block: bool = True
    suspicious_activity_flagging: bool = True

    # Phase 22 - Advanced Browser Lockdown Controls
    fullscreen_exit_policy: str = "warning_only"  # warning_only, record_incident, pause_exam, flag_review
    max_focus_loss_count: int = 5
    disable_copy: bool = True
    disable_paste: bool = True
    disable_context_menu: bool = True
    print_restrictions: bool = True
    navigation_warning: bool = True
    network_interruption_policy: str = "buffer_and_resume"  # buffer_and_resume, pause_on_disconnect
    require_invigilator_review: bool = True

    # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
    watermark_opacity: float = 0.06
    watermark_font_size: int = 12
    watermark_rotation_deg: int = -25
    watermark_spacing_px: int = 140
    watermark_update_interval_sec: int = 30
    watermark_mask_student_id: bool = True
    watermark_show_timestamp: bool = True
    watermark_show_exam_id: bool = True
    watermark_custom_text: Optional[str] = None
    require_watermark_validation: bool = False
    block_screen_capture_api: bool = True
    track_screenshot_signals: bool = True
    track_screen_recording_signals: bool = True

    # Phase 24 - Mobile Device Security & Native Examination Controls
    require_native_app: bool = False
    android_secure_mode: bool = True
    ios_secure_mode: bool = True
    require_kiosk_mode: bool = False
    min_android_version: int = 26
    min_ios_version: str = "15.0"
    mobile_interruption_policy: str = "allow_with_event"
    allow_device_recovery: bool = True
    block_rooted_devices: bool = False


class QuizConfigurationResponse(QuizConfigurationBase):
    id: uuid.UUID
    quiz_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuizConfigurationUpdateRequest(BaseModel):
    timezone: Optional[str] = None
    availability_mode: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reading_time_minutes: Optional[int] = None
    accommodations_extra_minutes: Optional[int] = None
    late_entry_minutes: Optional[int] = None
    early_access_minutes: Optional[int] = None
    grace_period_minutes: Optional[int] = None
    timer_type: Optional[str] = None

    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    question_grouping: Optional[str] = None
    question_selection_mode: Optional[str] = None

    passing_criteria_type: Optional[str] = None
    passing_marks: Optional[Decimal] = None
    passing_percentage: Optional[Decimal] = None
    negative_marking_type: Optional[str] = None
    fixed_negative_marks: Optional[Decimal] = None
    partial_marking_enabled: Optional[bool] = None
    rounding_precision: Optional[int] = None
    evaluation_method: Optional[str] = None
    require_manual_evaluation: Optional[bool] = None

    navigation_mode: Optional[str] = None
    allow_previous_nav: Optional[bool] = None
    allow_answer_change: Optional[bool] = None
    allow_mark_for_review: Optional[bool] = None
    allow_skip_questions: Optional[bool] = None
    show_question_palette: Optional[bool] = None
    show_answered_stats: Optional[bool] = None

    manual_submission_allowed: Optional[bool] = None
    auto_submit_on_timeout: Optional[bool] = None
    submission_confirmation_modal: Optional[bool] = None
    submit_unanswered_questions: Optional[bool] = None
    allow_attempt_reentry_on_disconnect: Optional[bool] = None
    reentry_grace_minutes: Optional[int] = None

    registration_required: Optional[bool] = None
    account_required: Optional[bool] = None
    max_attempts: Optional[int] = None
    one_attempt_per_student: Optional[bool] = None
    allow_multiple_devices: Optional[bool] = None
    require_invitation: Optional[bool] = None
    restricted_student_groups: Optional[List[str]] = None

    result_release_policy: Optional[str] = None
    show_score_immediately: Optional[bool] = None
    show_correct_answers: Optional[bool] = None
    show_answer_keys: Optional[bool] = None
    show_explanations: Optional[bool] = None
    show_section_breakdown: Optional[bool] = None
    show_final_status_pass_fail: Optional[bool] = None

    log_focus_loss: Optional[bool] = None
    log_copy_paste: Optional[bool] = None
    enforce_fullscreen: Optional[bool] = None
    watermark_enabled: Optional[bool] = None
    concurrent_session_block: Optional[bool] = None
    suspicious_activity_flagging: Optional[bool] = None

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

    # Phase 24 - Mobile Device Security & Native Examination Controls
    require_native_app: Optional[bool] = None
    android_secure_mode: Optional[bool] = None
    ios_secure_mode: Optional[bool] = None
    require_kiosk_mode: Optional[bool] = None
    min_android_version: Optional[int] = None
    min_ios_version: Optional[str] = None
    mobile_interruption_policy: Optional[str] = None
    allow_device_recovery: Optional[bool] = None
    block_rooted_devices: Optional[bool] = None


# -------------------------------------------------------------
# Dedicated Subsection Update Schemas
# -------------------------------------------------------------

class QuizScheduleUpdateRequest(BaseModel):
    timezone: Optional[str] = "UTC"
    availability_mode: str = "immediate"  # immediate, scheduled, restricted
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reading_time_minutes: int = 0
    late_entry_minutes: Optional[int] = None
    grace_period_minutes: int = 5
    timer_type: str = "per_student"


class QuizScoringUpdateRequest(BaseModel):
    passing_criteria_type: str = "percentage"
    passing_marks: Optional[Decimal] = None
    passing_percentage: Decimal = Decimal("40.00")
    negative_marking_type: str = "none"  # none, fixed, question_specific
    fixed_negative_marks: Decimal = Decimal("0.00")
    partial_marking_enabled: bool = False
    rounding_precision: int = 2
    evaluation_method: str = "automatic"
    require_manual_evaluation: bool = False


class QuizNavigationUpdateRequest(BaseModel):
    navigation_mode: str = "free"  # free, sequential
    allow_previous_nav: bool = True
    allow_answer_change: bool = True
    allow_mark_for_review: bool = True
    allow_skip_questions: bool = True
    show_question_palette: bool = True
    show_answered_stats: bool = True


class QuizAccessUpdateRequest(BaseModel):
    registration_required: bool = False
    account_required: bool = False
    max_attempts: int = 1
    one_attempt_per_student: bool = True
    allow_multiple_devices: bool = False
    require_invitation: bool = False
    restricted_student_groups: List[str] = Field(default_factory=list)


class QuizResultVisibilityUpdateRequest(BaseModel):
    result_release_policy: str = "immediate"  # immediate, after_close, after_manual_eval, after_admin_approval, never
    show_score_immediately: bool = True
    show_correct_answers: bool = False
    show_answer_keys: bool = False
    show_explanations: bool = False
    show_section_breakdown: bool = True
    show_final_status_pass_fail: bool = True


class QuizSecurityUpdateRequest(BaseModel):
    log_focus_loss: bool = True
    log_copy_paste: bool = True
    enforce_fullscreen: bool = False
    watermark_enabled: bool = False
    concurrent_session_block: bool = True
    suspicious_activity_flagging: bool = True

    # Phase 22 - Advanced Browser Lockdown Controls
    fullscreen_exit_policy: str = "warning_only"  # warning_only, record_incident, pause_exam, flag_review
    max_focus_loss_count: int = 5
    disable_copy: bool = True
    disable_paste: bool = True
    disable_context_menu: bool = True
    print_restrictions: bool = True
    navigation_warning: bool = True
    network_interruption_policy: str = "buffer_and_resume"  # buffer_and_resume, pause_on_disconnect
    require_invigilator_review: bool = True

    # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
    watermark_opacity: float = 0.06
    watermark_font_size: int = 12
    watermark_rotation_deg: int = -25
    watermark_spacing_px: int = 140
    watermark_update_interval_sec: int = 30
    watermark_mask_student_id: bool = True
    watermark_show_timestamp: bool = True
    watermark_show_exam_id: bool = True
    watermark_custom_text: Optional[str] = None
    require_watermark_validation: bool = False
    block_screen_capture_api: bool = True
    track_screenshot_signals: bool = True
    track_screen_recording_signals: bool = True

    # Phase 24 - Mobile Device Security & Native Examination Controls
    require_native_app: bool = False
    android_secure_mode: bool = True
    ios_secure_mode: bool = True
    require_kiosk_mode: bool = False
    min_android_version: int = 26
    min_ios_version: str = "15.0"
    mobile_interruption_policy: str = "allow_with_event"
    allow_device_recovery: bool = True
    block_rooted_devices: bool = False


# -------------------------------------------------------------
# Validation Report Schema
# -------------------------------------------------------------

class ValidationCheckItem(BaseModel):
    category: str  # content, academic, scoring, schedule, permissions
    name: str
    passed: bool
    level: str = "error"  # error, warning, info
    message: str


class QuizValidationReport(BaseModel):
    quiz_id: uuid.UUID
    is_valid: bool
    can_publish: bool
    checks: List[ValidationCheckItem]
    summary: Dict[str, Any]
    scoring_summary: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_at: datetime


# -------------------------------------------------------------
# Publishing & Lifecycle Action Schemas
# -------------------------------------------------------------

class QuizPublishRequest(BaseModel):
    change_log: Optional[str] = None
    force_immediate: bool = False


class QuizScheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    change_log: Optional[str] = None


class QuizUnpublishRequest(BaseModel):
    reason: str


class QuizArchiveRequest(BaseModel):
    reason: Optional[str] = None


class QuizPublishingHistoryItem(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    from_status: str
    to_status: str
    action: str
    performed_by: Optional[uuid.UUID] = None
    performer_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Management Dashboard & Review Schemas
# -------------------------------------------------------------

class QuizManagementItem(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    programme_name: Optional[str] = None
    creator_id: Optional[uuid.UUID] = None
    creator_name: Optional[str] = None
    creation_mode: str  # manual, generator, import
    duration_minutes: int
    total_questions: int
    maximum_marks: float
    passing_percentage: float
    status: str
    published_version: int
    availability_mode: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_scheduled: bool
    created_at: datetime
    updated_at: datetime


class QuizFinalReviewResponse(BaseModel):
    quiz: Dict[str, Any]
    sections_count: int
    questions_count: int
    total_obtainable_marks: float
    maximum_possible_marks: float
    configuration: Dict[str, Any]
    validation: QuizValidationReport
    can_publish: bool
