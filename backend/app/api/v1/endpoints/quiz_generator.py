import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin
from backend.app.schemas.quiz_generator import (
    PreflightCheckRequest,
    PreflightCheckResponse,
    GeneratePaperRequest,
    GenerationSessionResponse,
    ReplaceQuestionRequest,
    ReplacementCandidateItem,
    ReorderQuestionsRequest,
    UpdateQuestionSettingsRequest,
    RegeneratePaperRequest,
    SaveAsDraftRequest,
    SaveAsDraftResponse,
)
from backend.app.services.quiz_generator_service import (
    get_academic_cascading_options,
    get_subject_syllabus_hierarchy,
    preflight_availability_check,
    generate_question_paper,
    get_generation_session,
    list_generation_history,
    get_replacement_candidates,
    replace_question_in_session,
    reorder_questions_in_session,
    update_question_settings_in_session,
    regenerate_unlocked_questions,
    save_generation_as_draft,
)

router = APIRouter()


@router.get("/academic-options", response_model=Dict[str, Any])
def api_get_academic_options(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns cascading academic options (Institutions, Programmes, Sessions, Semesters, Subjects, Units)
    filtered by the administrator's assigned academic scope.
    """
    return get_academic_cascading_options(db, admin)


@router.get("/syllabus-hierarchy/{subject_id}", response_model=Dict[str, Any])
def api_get_syllabus_hierarchy(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns the hierarchical syllabus tree (Units -> Chapters -> Topics) for a given subject.
    """
    return get_subject_syllabus_hierarchy(db, admin, subject_id)


@router.post("/check-availability", response_model=PreflightCheckResponse)
def api_check_availability(
    req: PreflightCheckRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Audits the Question Bank for question availability across difficulty and unit quotas.
    Returns exact shortage breakdowns without silently substituting questions.
    """
    return preflight_availability_check(db, admin, req)


@router.post("/generate", response_model=GenerationSessionResponse)
def api_generate_question_paper(
    req: GeneratePaperRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Automatically generates an examination question paper from eligible Question Bank records.
    Creates immutable question snapshots and persists a generation session.
    """
    return generate_question_paper(db, admin, req)


@router.get("/sessions", response_model=List[Dict[str, Any]])
def api_list_generation_sessions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists past generation sessions for history review.
    """
    return list_generation_history(db, admin, limit=limit)


@router.get("/sessions/{generation_id}", response_model=GenerationSessionResponse)
def api_get_generation_session(
    generation_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves the generated questions and settings for an active generation session.
    """
    return get_generation_session(db, admin, generation_id)


@router.get("/sessions/{generation_id}/candidates/{question_id}", response_model=List[ReplacementCandidateItem])
def api_get_replacement_candidates(
    generation_id: uuid.UUID,
    question_id: uuid.UUID,
    match_difficulty: bool = Query(True),
    match_type: bool = Query(True),
    match_topic: bool = Query(False),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Finds alternative candidate questions from the Question Bank matching constraints without duplicating questions.
    """
    return get_replacement_candidates(
        db, admin, generation_id, question_id,
        match_difficulty=match_difficulty,
        match_type=match_type,
        match_topic=match_topic,
    )


@router.post("/sessions/{generation_id}/replace", response_model=GenerationSessionResponse)
def api_replace_question(
    generation_id: uuid.UUID,
    req: ReplaceQuestionRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Replaces a specific question in the paper with an approved alternative.
    """
    return replace_question_in_session(db, admin, generation_id, req)


@router.patch("/sessions/{generation_id}/reorder", response_model=GenerationSessionResponse)
def api_reorder_questions(
    generation_id: uuid.UUID,
    req: ReorderQuestionsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Reorders the sequence of questions in the generated paper.
    """
    return reorder_questions_in_session(db, admin, generation_id, req.question_ids_order)


@router.patch("/sessions/{generation_id}/question-settings", response_model=GenerationSessionResponse)
def api_update_question_settings(
    generation_id: uuid.UUID,
    req: UpdateQuestionSettingsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Updates custom marks, negative marks, or locked status for a specific question.
    """
    return update_question_settings_in_session(
        db, admin, generation_id, req.question_id,
        marks=req.marks,
        negative_marks=req.negative_marks,
        is_locked=req.is_locked,
    )


@router.post("/sessions/{generation_id}/regenerate", response_model=GenerationSessionResponse)
def api_regenerate_paper(
    generation_id: uuid.UUID,
    req: RegeneratePaperRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Regenerates unlocked questions using a new randomization seed while preserving locked questions.
    """
    return regenerate_unlocked_questions(
        db, admin, generation_id,
        preserve_locked=req.preserve_locked,
        new_seed=req.new_seed,
    )


@router.post("/sessions/{generation_id}/save-draft", response_model=SaveAsDraftResponse)
def api_save_generation_draft(
    generation_id: uuid.UUID,
    req: Optional[SaveAsDraftRequest] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Saves the generated paper into the authoritative quizzes & quiz_questions database tables with status 'draft'.
    """
    override_data = req.model_dump(exclude_unset=True) if req else None
    return save_generation_as_draft(db, admin, generation_id, override_settings=override_data)
