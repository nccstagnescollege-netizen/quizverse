import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin
from backend.app.services.evaluation_service import EvaluationService
from backend.app.schemas.evaluation import (
    GradingCriterionCreate,
    GradingCriterionResponse,
    GradingRubricCreate,
    GradingRubricUpdate,
    GradingRubricResponse,
    GradingRubricVersionResponse,
    GradingAssignmentCreate,
    GradingAssignmentResponse,
    ManualGradingWorkspaceResponse,
    SaveManualEvaluationRequest,
    ModerationEvaluationItem,
    ModerationActionRequest,
    EvaluationJobResponse,
    EvaluationTaskItem,
    ResultListItemResponse,
    ResultListResponse,
    ResultDetailResponse,
    ResultApproveRequest,
    ResultPublishRequest,
    BatchResultApproveRequest,
    BatchResultPublishRequest,
    ResultOverrideRequest,
    StudentResultResponse,
)

evaluations_router = APIRouter()
grading_router = APIRouter()
results_router = APIRouter()


# ====================================================================
# 1. EVALUATION JOBS & TASKS ROUTER (/evaluations)
# ====================================================================

@evaluations_router.post("/attempts/{attempt_id}/start", response_model=EvaluationJobResponse)
def start_attempt_evaluation(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Trigger or restart authoritative evaluation job for an examination attempt."""
    EvaluationService.run_evaluation(db, attempt_id, triggered_by=admin)
    return EvaluationService.get_evaluation_status(db, attempt_id, admin)


@evaluations_router.get("/attempts/{attempt_id}/status", response_model=EvaluationJobResponse)
def get_attempt_evaluation_status(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Get real-time evaluation job status and processed question counts."""
    return EvaluationService.get_evaluation_status(db, attempt_id, admin)


@evaluations_router.post("/attempts/{attempt_id}/retry", response_model=EvaluationJobResponse)
def retry_attempt_evaluation(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retry an evaluation job without duplicating existing evaluations."""
    EvaluationService.retry_evaluation(db, attempt_id, admin)
    return EvaluationService.get_evaluation_status(db, attempt_id, admin)


@evaluations_router.get("/tasks", response_model=List[EvaluationTaskItem])
def list_manual_grading_tasks(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List manual evaluation tasks assigned to the current evaluator/admin."""
    return EvaluationService.list_manual_tasks(db, admin, quiz_id=quiz_id)


# Moderation endpoints under /evaluations/moderation
@evaluations_router.get("/moderation", response_model=List[ModerationEvaluationItem])
def list_moderation_queue(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List flagged or pending evaluations awaiting moderation review."""
    return EvaluationService.list_moderation_evaluations(db, admin, quiz_id=quiz_id)


@evaluations_router.post("/moderation/{evaluation_id}/action")
def process_moderation_decision(
    evaluation_id: uuid.UUID = Path(..., description="Question Evaluation ID"),
    req: ModerationActionRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Approve, return, or override marks for an evaluated question."""
    ev = EvaluationService.process_moderation_action(db, evaluation_id, req, admin)
    return {
        "success": True,
        "evaluation_id": ev.id,
        "moderation_status": ev.moderation_status,
        "marks_awarded": float(ev.marks_awarded),
    }


# ====================================================================
# 2. MANUAL GRADING WORKSPACE & RUBRICS ROUTER (/grading)
# ====================================================================

@grading_router.get("/workspaces/{attempt_id}", response_model=ManualGradingWorkspaceResponse)
def get_manual_grading_workspace(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Load candidate answers, rubrics, and feedback fields for manual grading workspace."""
    return EvaluationService.get_manual_grading_workspace(db, attempt_id, admin)


@grading_router.post("/evaluations/{evaluation_id}/save")
def save_manual_question_score(
    evaluation_id: uuid.UUID = Path(..., description="Question Evaluation ID"),
    req: SaveManualEvaluationRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Save manual score, criterion breakdown, and feedback for a response."""
    ev = EvaluationService.save_manual_evaluation(db, evaluation_id, req, admin)
    return {
        "success": True,
        "evaluation_id": ev.id,
        "marks_awarded": float(ev.marks_awarded),
        "is_flagged_for_moderation": ev.is_flagged_for_moderation,
    }


@grading_router.get("/assignments", response_model=List[GradingAssignmentResponse])
def list_grading_assignments(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List evaluator assignments."""
    return EvaluationService.list_grading_assignments(db, admin, quiz_id=quiz_id)


@grading_router.post("/assignments", response_model=GradingAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_grading_assignment(
    req: GradingAssignmentCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Assign an evaluator to a quiz, section, or student group."""
    return EvaluationService.create_grading_assignment(db, admin, req)


# Rubric endpoints
@grading_router.get("/rubrics", response_model=List[GradingRubricResponse])
def list_rubrics(
    subject_id: Optional[uuid.UUID] = Query(None, description="Filter by subject"),
    search: Optional[str] = Query(None, description="Search rubric title"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List grading rubrics and criteria."""
    return EvaluationService.list_rubrics(db, admin, subject_id=subject_id, search=search)


@grading_router.post("/rubrics", response_model=GradingRubricResponse, status_code=status.HTTP_201_CREATED)
def create_rubric(
    req: GradingRubricCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Create a new grading rubric with criteria."""
    return EvaluationService.create_rubric(db, admin, req)


@grading_router.patch("/rubrics/{rubric_id}", response_model=GradingRubricResponse)
def update_rubric(
    rubric_id: uuid.UUID = Path(..., description="Rubric ID"),
    req: GradingRubricUpdate = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Update rubric and archive previous version in history."""
    return EvaluationService.update_rubric(db, admin, rubric_id, req)


# ====================================================================
# 3. RESULTS MANAGEMENT & PUBLICATION ROUTER (/results)
# ====================================================================

@results_router.get("", response_model=ResultListResponse)
def list_examination_results(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    search: Optional[str] = Query(None, description="Search candidate name or email"),
    is_published: Optional[bool] = Query(None, description="Filter published state"),
    is_approved: Optional[bool] = Query(None, description="Filter approved state"),
    is_passed: Optional[bool] = Query(None, description="Filter pass/fail state"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List examination results with filters, scores, and approval state."""
    return EvaluationService.list_results(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        search=search,
        is_published=is_published,
        is_approved=is_approved,
        is_passed=is_passed,
        page=page,
        limit=limit,
    )


@results_router.get("/{result_id}", response_model=ResultDetailResponse)
def get_examination_result_detail(
    result_id: uuid.UUID = Path(..., description="Examination Result ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Get full question-wise and section-wise result details with audit history."""
    return EvaluationService.get_result_detail(db, result_id, admin)


@results_router.post("/{result_id}/approve")
def approve_result(
    result_id: uuid.UUID = Path(..., description="Examination Result ID"),
    req: Optional[ResultApproveRequest] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Approve an individual examination result."""
    res = EvaluationService.approve_result(db, result_id, admin, approval_notes=req.approval_notes if req else None)
    return {
        "success": True,
        "result_id": res.id,
        "is_approved": res.is_approved,
        "approved_at": res.approved_at,
    }


@results_router.post("/batch-approve")
def batch_approve_results(
    req: BatchResultApproveRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Batch approve all completed results for a quiz."""
    count = EvaluationService.batch_approve_results(db, req.quiz_id, admin, approval_notes=req.approval_notes)
    return {
        "success": True,
        "quiz_id": req.quiz_id,
        "approved_count": count,
    }


@results_router.post("/{result_id}/publish")
def publish_result(
    result_id: uuid.UUID = Path(..., description="Examination Result ID"),
    req: Optional[ResultPublishRequest] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Publish an approved examination result to the candidate."""
    publish_flag = req.publish if req else True
    res = EvaluationService.publish_result(db, result_id, admin, publish=publish_flag)
    return {
        "success": True,
        "result_id": res.id,
        "is_published": res.is_published,
        "published_at": res.published_at,
    }


@results_router.post("/batch-publish")
def batch_publish_results(
    req: BatchResultPublishRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Batch publish all approved results for a quiz."""
    count = EvaluationService.batch_publish_results(db, req.quiz_id, admin, publish=req.publish)
    return {
        "success": True,
        "quiz_id": req.quiz_id,
        "published_count": count,
    }


@results_router.post("/{result_id}/override")
def override_result_score(
    result_id: uuid.UUID = Path(..., description="Examination Result ID"),
    req: ResultOverrideRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Administrative mark override with immutable audit history."""
    res = EvaluationService.override_result(db, result_id, admin, new_score=req.new_score, reason=req.reason)
    return {
        "success": True,
        "result_id": res.id,
        "new_score": float(res.score),
        "new_percentage": float(res.percentage),
        "is_passed": res.is_passed,
        "result_version": res.result_version,
    }


@results_router.get("/student/{attempt_id}", response_model=StudentResultResponse)
def get_student_examination_result(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    db: Session = Depends(get_db),
):
    """
    Candidate result endpoint:
    Enforces Phase 10 visibility policy (immediate, after close, after approval, never).
    Protects sensitive answer keys and internal notes.
    """
    return EvaluationService.get_student_result(db, attempt_id)
