import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==========================================
# INSTITUTIONS
# ==========================================

class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None


class InstitutionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, min_length=2, max_length=64)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class InstitutionResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    status: str
    programmes_count: int = 0
    subjects_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# PROGRAMMES
# ==========================================

class ProgrammeCreate(BaseModel):
    institution_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=64)
    degree_type: str = Field("Undergraduate", max_length=64)
    duration_years: int = Field(3, ge=1, le=10)
    total_semesters: int = Field(6, ge=1, le=20)
    description: Optional[str] = None


class ProgrammeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, min_length=2, max_length=64)
    degree_type: Optional[str] = None
    duration_years: Optional[int] = Field(None, ge=1, le=10)
    total_semesters: Optional[int] = Field(None, ge=1, le=20)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class ProgrammeResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    name: str
    code: str
    degree_type: str
    duration_years: int
    total_semesters: int
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# ACADEMIC SESSIONS
# ==========================================

class AcademicSessionCreate(BaseModel):
    session_name: str = Field(..., min_length=2, max_length=100)
    institution_id: Optional[uuid.UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: bool = False


class AcademicSessionUpdate(BaseModel):
    session_name: Optional[str] = Field(None, min_length=2, max_length=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class AcademicSessionResponse(BaseModel):
    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    session_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# PROGRAMME YEARS & SEMESTERS
# ==========================================

class ProgrammeYearResponse(BaseModel):
    id: uuid.UUID
    programme_id: uuid.UUID
    year_number: int
    year_name: str
    display_order: int

    model_config = {"from_attributes": True}


class SemesterCreate(BaseModel):
    programme_id: uuid.UUID
    programme_year_id: Optional[uuid.UUID] = None
    semester_number: int = Field(..., ge=1, le=20)
    semester_name: str = Field(..., min_length=1, max_length=100)
    display_order: int = Field(1, ge=1)


class SemesterResponse(BaseModel):
    id: uuid.UUID
    programme_id: uuid.UUID
    programme_year_id: Optional[uuid.UUID] = None
    semester_number: int
    semester_name: str
    display_order: int
    status: str

    model_config = {"from_attributes": True}


# ==========================================
# SUBJECT CATEGORIES
# ==========================================

class SubjectCategoryCreate(BaseModel):
    category_name: str = Field(..., min_length=2, max_length=100)
    category_code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class SubjectCategoryResponse(BaseModel):
    id: uuid.UUID
    category_name: str
    category_code: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ==========================================
# SUBJECTS
# ==========================================

class SubjectCreate(BaseModel):
    subject_name: str = Field(..., min_length=2, max_length=255)
    subject_code: str = Field(..., min_length=2, max_length=64)
    institution_id: Optional[uuid.UUID] = None
    subject_type: str = Field("theory", pattern="^(theory|practical|integrated|project)$")
    default_credits: int = Field(3, ge=0, le=20)
    description: Optional[str] = None
    syllabus_version: str = Field("1.0", max_length=32)


class SubjectUpdate(BaseModel):
    subject_name: Optional[str] = Field(None, min_length=2, max_length=255)
    subject_code: Optional[str] = Field(None, min_length=2, max_length=64)
    subject_type: Optional[str] = Field(None, pattern="^(theory|practical|integrated|project)$")
    default_credits: Optional[int] = Field(None, ge=0, le=20)
    description: Optional[str] = None
    syllabus_version: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class SubjectResponse(BaseModel):
    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    subject_name: str
    subject_code: str
    subject_type: str
    default_credits: int
    description: Optional[str] = None
    syllabus_version: str
    status: str
    units_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# CURRICULA & ALLOCATIONS
# ==========================================

class CurriculumCreate(BaseModel):
    programme_id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    curriculum_name: str = Field(..., min_length=2, max_length=255)
    version_code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None


class CurriculumResponse(BaseModel):
    id: uuid.UUID
    programme_id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    curriculum_name: str
    version_code: str
    is_active: bool
    description: Optional[str] = None
    status: str
    allocated_subjects_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CurriculumSubjectAllocate(BaseModel):
    curriculum_id: Optional[uuid.UUID] = None
    semester_id: uuid.UUID
    subject_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    credits: int = Field(3, ge=0, le=20)
    is_elective: bool = False
    elective_group: Optional[str] = None
    syllabus_version: str = Field("1.0", max_length=32)
    display_order: int = Field(1, ge=0)


class CurriculumSubjectResponse(BaseModel):
    id: uuid.UUID
    curriculum_id: uuid.UUID
    semester_id: uuid.UUID
    subject_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    credits: int
    is_elective: bool
    elective_group: Optional[str] = None
    syllabus_version: str
    display_order: int
    status: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ==========================================
# UNITS, CHAPTERS & TOPICS
# ==========================================

class UnitCreate(BaseModel):
    unit_name: str = Field(..., min_length=2, max_length=255)
    unit_code: str = Field(..., min_length=2, max_length=64)
    subject_id: Optional[uuid.UUID] = None
    unit_number: int = Field(1, ge=1)
    description: Optional[str] = None
    display_order: int = Field(0, ge=0)


class UnitUpdate(BaseModel):
    unit_name: Optional[str] = Field(None, min_length=2, max_length=255)
    unit_code: Optional[str] = Field(None, min_length=2, max_length=64)
    subject_id: Optional[uuid.UUID] = None
    unit_number: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class UnitResponse(BaseModel):
    id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    unit_number: int
    unit_name: str
    unit_code: str
    description: Optional[str] = None
    display_order: int
    status: str
    chapters_count: int = 0

    model_config = {"from_attributes": True}


class ChapterCreate(BaseModel):
    unit_id: uuid.UUID
    chapter_name: str = Field(..., min_length=2, max_length=255)
    chapter_code: str = Field(..., min_length=2, max_length=64)
    chapter_number: int = Field(1, ge=1)
    description: Optional[str] = None
    display_order: int = Field(0, ge=0)


class ChapterUpdate(BaseModel):
    chapter_name: Optional[str] = Field(None, min_length=2, max_length=255)
    chapter_code: Optional[str] = Field(None, min_length=2, max_length=64)
    chapter_number: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class ChapterResponse(BaseModel):
    id: uuid.UUID
    unit_id: uuid.UUID
    chapter_number: int
    chapter_name: str
    chapter_code: str
    description: Optional[str] = None
    display_order: int
    status: str
    topics_count: int = 0

    model_config = {"from_attributes": True}


class TopicCreate(BaseModel):
    chapter_id: uuid.UUID
    topic_name: str = Field(..., min_length=2, max_length=255)
    topic_code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    display_order: int = Field(0, ge=0)


class TopicUpdate(BaseModel):
    topic_name: Optional[str] = Field(None, min_length=2, max_length=255)
    topic_code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|archived|inactive)$")


class TopicResponse(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    topic_name: str
    topic_code: Optional[str] = None
    description: Optional[str] = None
    display_order: int
    status: str

    model_config = {"from_attributes": True}


# ==========================================
# ACADEMIC TREE & SCOPE ASSIGNMENT
# ==========================================

class AcademicTreeNode(BaseModel):
    id: str
    name: str
    type: str  # institution | programme | session | semester | subject | unit | chapter | topic
    code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    children: List['AcademicTreeNode'] = []

    model_config = {"from_attributes": True}


class ReorderItemsRequest(BaseModel):
    entity_type: str = Field(..., pattern="^(units|chapters|topics|curriculum_subjects)$")
    item_ids: List[uuid.UUID]


class AssignAcademicScopeRequest(BaseModel):
    admin_id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    curriculum_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
