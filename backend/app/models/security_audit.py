import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=True, index=True)
    details = Column(JSONType, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="audit_logs")


class ExaminationSecurityPolicy(Base):
    __tablename__ = "examination_security_policies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)  # Null = Platform Default Policy
    policy_scope = Column(String(32), nullable=False, default="quiz", server_default=text("'quiz'"))  # platform, quiz

    # Browser Monitoring Policies
    track_tab_switch = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    track_focus_loss = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    require_fullscreen = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    track_fullscreen_exit = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    block_copy_paste = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    track_copy_paste = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    block_context_menu = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    track_page_reload = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Watermark
    enable_watermark = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    watermark_pattern = Column(String(255), nullable=False, default="QUIZVERSE | {student_name} | {masked_reg} | {attempt_id}", server_default=text("'QUIZVERSE | {student_name} | {masked_reg} | {attempt_id}'"))

    # Thresholds
    max_tab_switches_warning = Column(Integer, nullable=False, default=2, server_default=text("2"))
    max_tab_switches_critical = Column(Integer, nullable=False, default=5, server_default=text("5"))
    max_focus_losses_warning = Column(Integer, nullable=False, default=3, server_default=text("3"))
    max_fullscreen_exits_warning = Column(Integer, nullable=False, default=2, server_default=text("2"))

    # Session & Integrity Controls
    single_session_enforced = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    allow_session_recovery = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    randomize_question_order = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    randomize_option_order = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Transparency & Student Notice
    student_notice_text = Column(Text, nullable=True)
    student_acknowledgement_required = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Phase 22 - Advanced Browser Lockdown Controls
    fullscreen_exit_policy = Column(String(32), nullable=False, default="warning_only", server_default=text("'warning_only'"))  # warning_only, record_incident, pause_exam, flag_review
    max_focus_loss_count = Column(Integer, nullable=False, default=5, server_default=text("5"))
    disable_copy = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    disable_paste = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    disable_context_menu = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    print_restrictions = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    navigation_warning = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    network_interruption_policy = Column(String(32), nullable=False, default="buffer_and_resume", server_default=text("'buffer_and_resume'"))  # buffer_and_resume, pause_on_disconnect
    require_invigilator_review = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
    watermark_opacity = Column(Numeric(3, 2), nullable=False, default=0.06, server_default=text("0.06"))
    watermark_font_size = Column(Integer, nullable=False, default=12, server_default=text("12"))
    watermark_rotation_deg = Column(Integer, nullable=False, default=-25, server_default=text("-25"))
    watermark_spacing_px = Column(Integer, nullable=False, default=140, server_default=text("140"))
    watermark_update_interval_sec = Column(Integer, nullable=False, default=30, server_default=text("30"))
    watermark_mask_student_id = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    watermark_show_timestamp = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    watermark_show_exam_id = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    watermark_custom_text = Column(String(255), nullable=True)
    require_watermark_validation = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    block_screen_capture_api = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    track_screenshot_signals = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    track_screen_recording_signals = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    creator = relationship("Admin")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_category = Column(String(64), nullable=False, default="GENERAL", server_default=text("'GENERAL'"), index=True)  # TAB_SWITCH, FOCUS_LOSS, FULLSCREEN, CLIPBOARD, CONTEXT_MENU, SESSION, NAVIGATION
    severity = Column(String(32), nullable=False, default="LOW", server_default=text("'LOW'"), index=True)  # LOW, MEDIUM, HIGH, INFO
    event_name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    event_metadata = Column(JSONType, nullable=True)
    sequence_number = Column(Integer, nullable=False, default=1, server_default=text("1"))
    session_id = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    student = relationship("Student")
    quiz = relationship("Quiz")
    attempt = relationship("ExaminationAttempt", back_populates="security_events")


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False, index=True)  # REPEATED_TAB_SWITCH, FULLSCREEN_EXIT_EXCEEDED, FREQUENT_CLIPBOARD_ATTEMPT, CONCURRENT_SESSION_ATTEMPT, UNUSUAL_ACTIVITY
    severity = Column(String(32), nullable=False, default="LOW", server_default=text("'LOW'"), index=True)  # LOW, MEDIUM, HIGH
    occurrences_count = Column(Integer, nullable=False, default=1, server_default=text("1"))
    first_observed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_observed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    status = Column(String(32), nullable=False, default="UNREVIEWED", server_default=text("'UNREVIEWED'"), index=True)  # UNREVIEWED, UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED
    resolution_reason = Column(Text, nullable=True)
    reviewed_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="security_alerts")
    quiz = relationship("Quiz")
    student = relationship("Student")
    reviewer = relationship("Admin")
    notes = relationship("SecurityInvestigationNote", back_populates="alert", cascade="all, delete-orphan", order_by="SecurityInvestigationNote.created_at")


class SecurityInvestigationNote(Base):
    __tablename__ = "security_investigation_notes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(Uuid, ForeignKey("security_alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    note_text = Column(Text, nullable=False)
    action_taken = Column(String(64), nullable=False, default="NOTE_ADDED", server_default=text("'NOTE_ADDED'"))  # NOTE_ADDED, MARKED_UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="investigation_notes")
    alert = relationship("SecurityAlert", back_populates="notes")
    admin = relationship("Admin")


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(Uuid, nullable=True, index=True)
    user_type = Column(String(32), nullable=False, default="guest", server_default=text("'guest'"))  # admin, student, guest
    endpoint = Column(String(512), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())


class BrowserCompatibilityRecord(Base):
    __tablename__ = "browser_compatibility_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(128), nullable=True)

    browser_name = Column(String(64), nullable=False)
    browser_version = Column(String(64), nullable=False)
    os_name = Column(String(64), nullable=False)
    os_version = Column(String(64), nullable=False)
    device_type = Column(String(32), nullable=False, default="desktop", server_default=text("'desktop'"))

    is_secure_context = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    javascript_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    fullscreen_supported = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    visibility_api_supported = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    storage_available = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    screen_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    screen_height = Column(Integer, nullable=False, default=0, server_default=text("0"))
    viewport_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    viewport_height = Column(Integer, nullable=False, default=0, server_default=text("0"))

    network_online = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    network_downlink = Column(Numeric(6, 2), nullable=True)
    network_rtt = Column(Integer, nullable=True)
    is_seb_detected = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    checks_summary = Column(JSONType, nullable=True)
    overall_status = Column(String(32), nullable=False, default="PASSED", server_default=text("'PASSED'"))
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")


class WatermarkSession(Base):
    __tablename__ = "watermark_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    watermark_code = Column(String(32), nullable=False, unique=True, index=True)
    watermark_text = Column(String(512), nullable=False)
    student_display_name = Column(String(255), nullable=False)
    student_masked_identifier = Column(String(128), nullable=False)
    institution_name = Column(String(255), nullable=False, default="QUIZVERSE", server_default=text("'QUIZVERSE'"))

    opacity = Column(Numeric(3, 2), nullable=False, default=0.06, server_default=text("0.06"))
    font_size = Column(Integer, nullable=False, default=12, server_default=text("12"))
    rotation_deg = Column(Integer, nullable=False, default=-25, server_default=text("-25"))
    spacing_px = Column(Integer, nullable=False, default=140, server_default=text("140"))
    update_interval_sec = Column(Integer, nullable=False, default=30, server_default=text("30"))

    issued_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_verified_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    verification_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    is_valid = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    tamper_flag = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    metadata_json = Column(JSONType, nullable=True)

    # Relationships
    attempt = relationship("ExaminationAttempt")
    quiz = relationship("Quiz")
    student = relationship("Student")


class CaptureCapabilityReport(Base):
    __tablename__ = "capture_capability_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    screen_capture_api_supported = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    screenshot_shortcut_supported = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_media_active = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    detection_tier = Column(String(32), nullable=False, default="detection_limited", server_default=text("'detection_limited'"))  # detection_supported, detection_limited, unsupported
    browser_vendor = Column(String(64), nullable=False, default="Unknown", server_default=text("'Unknown'"))
    os_platform = Column(String(64), nullable=False, default="Unknown", server_default=text("'Unknown'"))
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt")
    quiz = relationship("Quiz")
    student = relationship("Student")
