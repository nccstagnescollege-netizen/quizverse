import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class SEBConfiguration(Base):
    """
    Stores Safe Exam Browser (.seb) configuration profiles for quizzes,
    including cryptographic ConfigKey, BrowserExamKey, password hashes,
    and generated XML Property List configurations.
    """
    __tablename__ = "seb_configurations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1, server_default=text("1"))
    config_name = Column(String(128), nullable=False, default="Default SEB Profile")
    
    # Cryptographic & Verification Keys
    config_key = Column(String(128), nullable=False, index=True)  # SHA-256 hash of canonical XML plist
    browser_exam_key = Column(String(128), nullable=True)  # Optional BEK for strict client validation
    
    # Configuration Rules & XML
    config_data = Column(JSONType, nullable=False)  # Key-value JSON representation of SEB settings
    encrypted_xml = Column(Text, nullable=False)  # Apple XML Property List (.seb contents)
    
    # Security Passwords (hashed with SHA-256 / bcrypt)
    config_password_hash = Column(String(255), nullable=True)  # Hash of administrative/config unlock password
    quit_password_hash = Column(String(255), nullable=True)  # Hash of examination quit password
    
    # Policy Enforcement Flags
    status = Column(String(32), nullable=False, default="published", server_default=text("'published'"))  # draft, published, revoked
    is_mandatory = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    allow_quit = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    min_seb_version = Column(String(32), nullable=False, default="3.0.0", server_default=text("'3.0.0'"))
    allow_reload = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    enable_url_filter = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    browser_view_mode = Column(Integer, nullable=False, default=1, server_default=text("1"))  # 1 = Fullscreen Kiosk
    
    # Audit & Lifecycle
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    # Relationships
    quiz = relationship("Quiz")
    creator = relationship("Admin")
    sessions = relationship("DesktopExamSession", back_populates="seb_config")

    __table_args__ = (
        UniqueConstraint("quiz_id", "version_number", name="uq_quiz_seb_version"),
    )


class ComputerLab(Base):
    """
    Manages institutional computer laboratories and workstation pools
    for supervised in-person desktop examinations.
    """
    __tablename__ = "computer_labs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    campus_name = Column(String(128), nullable=False, default="Main Campus")
    lab_name = Column(String(128), nullable=False)  # e.g., "Turing Computing Lab 301"
    room_number = Column(String(64), nullable=True)  # e.g., "Room 301-B"
    total_workstations = Column(Integer, nullable=False, default=0, server_default=text("0"))
    network_subnet = Column(String(64), nullable=True)  # e.g. "192.168.10.0/24" for lab IP scoping
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, maintenance, inactive
    contact_person = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    institution = relationship("Institution")
    devices = relationship("LabDevice", back_populates="lab", cascade="all, delete-orphan")


class LabDevice(Base):
    """
    Tracks individual workstations within a computer lab, their operating system,
    installed Safe Exam Browser versions, and audit readiness status.
    """
    __tablename__ = "lab_devices"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    lab_id = Column(Uuid, ForeignKey("computer_labs.id", ondelete="CASCADE"), nullable=False, index=True)
    device_reference = Column(String(64), nullable=False)  # e.g., "LAB-01-PC-14"
    os_platform = Column(String(32), nullable=False, default="windows", server_default=text("'windows'"))  # windows, macos
    os_version = Column(String(64), nullable=True)  # e.g., "Windows 11 Pro 23H2"
    seb_version = Column(String(32), nullable=True)  # e.g., "3.7.0"
    ip_address = Column(String(64), nullable=True)
    mac_address_masked = Column(String(64), nullable=True)
    compatibility_status = Column(String(32), nullable=False, default="ready", server_default=text("'ready'"))  # ready, update_required, incompatible, unverified
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    metadata_info = Column(JSONType, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    lab = relationship("ComputerLab", back_populates="devices")
    sessions = relationship("DesktopExamSession", back_populates="lab_device")

    __table_args__ = (
        UniqueConstraint("lab_id", "device_reference", name="uq_lab_device_reference"),
    )


class DesktopExamSession(Base):
    """
    Active desktop examination session tracking Safe Exam Browser verification headers,
    heartbeats, interruption counts, and workstation associations.
    """
    __tablename__ = "desktop_exam_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    seb_config_id = Column(Uuid, ForeignKey("seb_configurations.id", ondelete="SET NULL"), nullable=True, index=True)
    lab_device_id = Column(Uuid, ForeignKey("lab_devices.id", ondelete="SET NULL"), nullable=True, index=True)

    session_mode = Column(String(32), nullable=False, default="seb_enforced", server_default=text("'seb_enforced'"))  # seb_enforced, seb_voluntary, standard_browser
    is_seb_verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    seb_version = Column(String(32), nullable=True)
    os_platform = Column(String(32), nullable=True)  # windows, macos, linux, unknown
    config_key_hash = Column(String(128), nullable=True)
    request_hash = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, interrupted, terminated, completed
    interruption_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    session_metadata = Column(JSONType, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt")
    student = relationship("Student")
    quiz = relationship("Quiz")
    seb_config = relationship("SEBConfiguration", back_populates="sessions")
    lab_device = relationship("LabDevice", back_populates="sessions")
