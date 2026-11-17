import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class QuizCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int = Field(60, ge=1, le=600)
    passing_percentage: Decimal = Field(Decimal("40.00"), ge=0, le=100)
    max_attempts: int = Field(1, ge=1)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_results_immediately: bool = True
    show_correct_answers: bool = False
    allow_review: bool = True
    status: str = Field("draft", pattern="^(draft|scheduled|published|archived)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class QuizUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    passing_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_attempts: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, pattern="^(draft|scheduled|published|archived)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class QuizResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: Decimal
    passing_percentage: Decimal
    max_attempts: int
    status: str
    created_by: Optional[uuid.UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuizListResponse(BaseModel):
    quizzes: List[QuizResponse]
    total: int
