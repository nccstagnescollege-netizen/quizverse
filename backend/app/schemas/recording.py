import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class QuizRecordingSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quiz_id: uuid.UUID
    recording_storage_enabled: bool = False
    webcam_recording_enabled: bool = False
    microphone_recording_enabled: bool = False
    recording_quality: str = "standard"
    recording_retention_days: int = 30
    allow_invigilator_recording_access: bool = True
    allow_admin_recording_download: bool = True
    estimated_storage_mb_per_hour: float = 120.0


class QuizRecordingSettingsUpdateRequest(BaseModel):
    recording_storage_enabled: Optional[bool] = None
    webcam_recording_enabled: Optional[bool] = None
    microphone_recording_enabled: Optional[bool] = None
    recording_quality: Optional[str] = Field(None, description="standard, high, bandwidth_optimized")
    recording_retention_days: Optional[int] = Field(None, ge=1, le=365)
    allow_invigilator_recording_access: Optional[bool] = None
    allow_admin_recording_download: Optional[bool] = None


class StorageEstimateRequest(BaseModel):
    duration_minutes: int = Field(default=60, ge=1, le=720)
    student_count: int = Field(default=50, ge=1, le=5000)
    recording_quality: str = Field(default="standard")


class StorageEstimateResponse(BaseModel):
    student_count: int
    duration_minutes: int
    recording_quality: str
    estimated_mb_total: float
    estimated_gb_total: float
    storage_warning: Optional[str] = None


class StartRecordingRequest(BaseModel):
    session_id: Optional[uuid.UUID] = None
    webcam_recorded: bool = True
    microphone_recorded: bool = True
    recording_quality: str = "standard"


class StopRecordingRequest(BaseModel):
    reason: str = Field(default="submission", description="submission, timeout, admin_terminate, manual_stop")


class ExamRecordingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    quiz_id: uuid.UUID
    quiz_title: Optional[str] = None
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    attempt_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    bucket_name: str = "quiz-recordings"
    storage_object_path: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: str = "video/webm"
    file_size_bytes: int = 0
    duration_seconds: int = 0
    recording_status: str = "NOT_STARTED"
    webcam_recorded: bool = False
    microphone_recorded: bool = False
    recording_quality: str = "standard"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None
    checksum: Optional[str] = None
    retention_expires_at: Optional[datetime] = None
    created_at: datetime


class ExamRecordingListResponse(BaseModel):
    total: int
    items: List[ExamRecordingItem]


class SignedPlaybackUrlResponse(BaseModel):
    recording_id: uuid.UUID
    playback_url: str
    expires_in_seconds: int = 3600
    file_name: str
    mime_type: str
    duration_seconds: int = 0
    student_name: Optional[str] = None
    quiz_title: Optional[str] = None


class SignedDownloadUrlResponse(BaseModel):
    recording_id: uuid.UUID
    download_url: str
    expires_in_seconds: int = 3600
    file_name: str
    file_size_bytes: int = 0


class SuperAdminStorageStatsResponse(BaseModel):
    total_recordings: int
    total_storage_bytes: int
    total_storage_mb: float
    total_storage_gb: float
    completed_count: int
    recording_count: int
    failed_count: int
    expired_count: int
    storage_by_quiz: List[Dict[str, Any]]
    storage_by_institution: List[Dict[str, Any]]


class RecordingCleanupResponse(BaseModel):
    deleted_count: int
    freed_bytes: int
    freed_mb: float
    recordings_cleared: List[uuid.UUID]
