import uuid
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
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class QuestionImportJob(Base):
    __tablename__ = "question_import_jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    uploaded_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_format = Column(String(16), nullable=False)  # "csv", "xlsx"
    file_size_bytes = Column(Integer, nullable=False, default=0)
    file_checksum = Column(String(64), nullable=True)
    template_version = Column(String(32), nullable=False, default="v1.0")
    status = Column(String(32), nullable=False, default="uploaded", server_default=text("'uploaded'"))
    # uploaded, validating, validation_completed, awaiting_confirmation, importing, completed, completed_with_errors, failed, cancelled

    total_rows = Column(Integer, nullable=False, default=0)
    valid_rows = Column(Integer, nullable=False, default=0)
    invalid_rows = Column(Integer, nullable=False, default=0)
    warning_rows = Column(Integer, nullable=False, default=0)
    duplicate_rows = Column(Integer, nullable=False, default=0)
    imported_rows = Column(Integer, nullable=False, default=0)
    skipped_rows = Column(Integer, nullable=False, default=0)

    import_policy = Column(String(32), nullable=False, default="import_valid")  # import_valid, all_or_nothing
    duplicate_strategy = Column(String(32), nullable=False, default="skip")  # skip, import_as_new, update_existing
    column_mapping = Column(JSONType, nullable=True)
    summary_metadata = Column(JSONType, nullable=True)  # distributions by question_type, difficulty, subject
    error_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    uploader = relationship("Admin", foreign_keys=[uploaded_by])
    rows = relationship("QuestionImportRow", back_populates="job", cascade="all, delete-orphan", order_by="QuestionImportRow.row_number")


class QuestionImportRow(Base):
    __tablename__ = "question_import_rows"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    job_id = Column(Uuid, ForeignKey("question_import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSONType, nullable=False)
    parsed_data = Column(JSONType, nullable=True)
    validation_status = Column(String(32), nullable=False, default="valid")  # valid, invalid, warning, duplicate, skipped, imported
    is_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_question_id = Column(Uuid, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    imported_question_id = Column(Uuid, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    errors = Column(JSONType, nullable=True)  # list of {"column": "...", "message": "..."}
    warnings = Column(JSONType, nullable=True)  # list of str
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    job = relationship("QuestionImportJob", back_populates="rows")
    duplicate_question = relationship("Question", foreign_keys=[duplicate_question_id])
    imported_question = relationship("Question", foreign_keys=[imported_question_id])


class QuestionExportJob(Base):
    __tablename__ = "question_export_jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    requested_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    export_format = Column(String(16), nullable=False)  # "csv", "xlsx"
    export_mode = Column(String(32), nullable=False, default="question_only")  # question_only, administrative_answer_key
    filters_applied = Column(JSONType, nullable=True)
    total_questions = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="completed")  # processing, completed, failed
    file_path = Column(String(512), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    requester = relationship("Admin", foreign_keys=[requested_by])
