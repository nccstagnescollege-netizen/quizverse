import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ImportJobSummaryResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_format: str
    file_size_bytes: int
    template_version: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    warning_rows: int
    duplicate_rows: int
    imported_rows: int
    skipped_rows: int
    import_policy: str
    duplicate_strategy: str
    summary_metadata: Optional[Dict[str, Any]] = None
    error_summary: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportRowResponse(BaseModel):
    id: uuid.UUID
    row_number: int
    raw_data: Dict[str, Any]
    parsed_data: Optional[Dict[str, Any]] = None
    validation_status: str
    is_duplicate: bool
    duplicate_question_id: Optional[uuid.UUID] = None
    imported_question_id: Optional[uuid.UUID] = None
    errors: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class ImportJobPreviewResponse(BaseModel):
    job: ImportJobSummaryResponse
    rows: List[ImportRowResponse]
    total_rows_previewed: int


class ImportConfirmRequest(BaseModel):
    policy: str = Field("import_valid", pattern="^(import_valid|all_or_nothing)$")
    duplicate_strategy: str = Field("skip", pattern="^(skip|import_as_new|update_existing)$")


class ExportQuestionsRequest(BaseModel):
    export_format: str = Field("xlsx", pattern="^(xlsx|csv)$")
    export_mode: str = Field("question_only", pattern="^(question_only|administrative_answer_key)$")
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    status: Optional[str] = None
