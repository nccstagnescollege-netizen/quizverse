from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin, require_permission
from backend.app.schemas.quiz_publishing import (
    QuizConfigurationResponse,
    QuizConfigurationUpdateRequest,
    QuizScheduleUpdateRequest,
    QuizScoringUpdateRequest,
    QuizNavigationUpdateRequest,
    QuizAccessUpdateRequest,
    QuizResultVisibilityUpdateRequest,
    QuizSecurityUpdateRequest,
    QuizValidationReport,
    QuizPublishRequest,
    QuizScheduleRequest,
    QuizUnpublishRequest,
    QuizArchiveRequest,
    QuizPublishingHistoryItem,
    QuizManagementItem,
    QuizFinalReviewResponse,
)
from backend.app.services import quiz_publishing_service as pub_service
from backend.app.services import quiz_validation_service as val_service

router = APIRouter()


@router.get("/manage", response_model=List[QuizManagementItem])
def list_quizzes_for_management(
    status: Optional[str] = Query(None, description="Filter by quiz status"),
    creation_mode: Optional[str] = Query(None, description="Filter by creation mode: manual, generator, import"),
    search: Optional[str] = Query(None, description="Search by title or slug"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List quizzes accessible to the administrator with publishing status and metrics."""
    return pub_service.get_quizzes_management_list(
        db, admin, status_filter=status, creation_mode_filter=creation_mode, search=search
    )


@router.get("/{quiz_id}/configuration", response_model=QuizConfigurationResponse)
def get_quiz_configuration(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve full configuration settings for an examination."""
    return pub_service.get_quiz_configuration(db, quiz_id, admin)


@router.patch("/{quiz_id}/configuration", response_model=QuizConfigurationResponse)
def update_quiz_configuration(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizConfigurationUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update all or subset of quiz configuration fields."""
    return pub_service.update_quiz_configuration(db, quiz_id, payload, admin)


@router.patch("/{quiz_id}/schedule", response_model=QuizConfigurationResponse)
def update_quiz_schedule_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizScheduleUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update examination schedule and availability timings."""
    patch_req = QuizConfigurationUpdateRequest(
        timezone=payload.timezone,
        availability_mode=payload.availability_mode,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reading_time_minutes=payload.reading_time_minutes,
        late_entry_minutes=payload.late_entry_minutes,
        grace_period_minutes=payload.grace_period_minutes,
        timer_type=payload.timer_type,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.patch("/{quiz_id}/scoring", response_model=QuizConfigurationResponse)
def update_quiz_scoring_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizScoringUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update scoring, negative marking, and passing criteria."""
    patch_req = QuizConfigurationUpdateRequest(
        passing_criteria_type=payload.passing_criteria_type,
        passing_marks=payload.passing_marks,
        passing_percentage=payload.passing_percentage,
        negative_marking_type=payload.negative_marking_type,
        fixed_negative_marks=payload.fixed_negative_marks,
        partial_marking_enabled=payload.partial_marking_enabled,
        rounding_precision=payload.rounding_precision,
        evaluation_method=payload.evaluation_method,
        require_manual_evaluation=payload.require_manual_evaluation,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.patch("/{quiz_id}/navigation", response_model=QuizConfigurationResponse)
def update_quiz_navigation_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizNavigationUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update student question navigation rules."""
    patch_req = QuizConfigurationUpdateRequest(
        navigation_mode=payload.navigation_mode,
        allow_previous_nav=payload.allow_previous_nav,
        allow_answer_change=payload.allow_answer_change,
        allow_mark_for_review=payload.allow_mark_for_review,
        allow_skip_questions=payload.allow_skip_questions,
        show_question_palette=payload.show_question_palette,
        show_answered_stats=payload.show_answered_stats,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.patch("/{quiz_id}/access", response_model=QuizConfigurationResponse)
def update_quiz_access_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizAccessUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update candidate registration and access constraints."""
    patch_req = QuizConfigurationUpdateRequest(
        registration_required=payload.registration_required,
        account_required=payload.account_required,
        max_attempts=payload.max_attempts,
        one_attempt_per_student=payload.one_attempt_per_student,
        allow_multiple_devices=payload.allow_multiple_devices,
        require_invitation=payload.require_invitation,
        restricted_student_groups=payload.restricted_student_groups,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.patch("/{quiz_id}/result-visibility", response_model=QuizConfigurationResponse)
def update_quiz_result_visibility_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizResultVisibilityUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update score and answer-key release policies."""
    patch_req = QuizConfigurationUpdateRequest(
        result_release_policy=payload.result_release_policy,
        show_score_immediately=payload.show_score_immediately,
        show_correct_answers=payload.show_correct_answers,
        show_answer_keys=payload.show_answer_keys,
        show_explanations=payload.show_explanations,
        show_section_breakdown=payload.show_section_breakdown,
        show_final_status_pass_fail=payload.show_final_status_pass_fail,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.patch("/{quiz_id}/security", response_model=QuizConfigurationResponse)
def update_quiz_security_settings(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizSecurityUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Update exam deterrence and monitoring policies."""
    patch_req = QuizConfigurationUpdateRequest(
        log_focus_loss=payload.log_focus_loss,
        log_copy_paste=payload.log_copy_paste,
        enforce_fullscreen=payload.enforce_fullscreen,
        watermark_enabled=payload.watermark_enabled,
        concurrent_session_block=payload.concurrent_session_block,
        suspicious_activity_flagging=payload.suspicious_activity_flagging,
    )
    return pub_service.update_quiz_configuration(db, quiz_id, patch_req, admin)


@router.post("/{quiz_id}/validate", response_model=QuizValidationReport)
def run_quiz_validation(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Execute complete backend validation against content, scoring, and schedules."""
    return val_service.validate_quiz_for_publishing(db, quiz_id, admin)


@router.get("/{quiz_id}/validation-report", response_model=QuizValidationReport)
def get_validation_report(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve existing validation results or generate fresh report."""
    return val_service.validate_quiz_for_publishing(db, quiz_id, admin)


@router.get("/{quiz_id}/final-preview", response_model=QuizFinalReviewResponse)
def get_final_examination_review(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve pre-publishing final review summary, validation status, and configuration."""
    return pub_service.get_final_review(db, quiz_id, admin)


@router.post("/{quiz_id}/publish")
def publish_examination(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: Optional[QuizPublishRequest] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Officially publish an examination after strict validation and freeze immutable version."""
    return pub_service.publish_quiz(db, quiz_id, admin, payload)


@router.post("/{quiz_id}/schedule")
def schedule_examination(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizScheduleRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Configure examination schedule window and mark as scheduled."""
    return pub_service.schedule_quiz(db, quiz_id, payload, admin)


@router.post("/{quiz_id}/unpublish")
def unpublish_examination(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: QuizUnpublishRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Revert published or scheduled examination back to draft revision."""
    return pub_service.unpublish_quiz(db, quiz_id, admin, payload.reason)


@router.post("/{quiz_id}/archive")
def archive_examination(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    payload: Optional[QuizArchiveRequest] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """Archive examination to retire from active catalog."""
    reason = payload.reason if payload else None
    return pub_service.archive_quiz(db, quiz_id, admin, reason)


@router.get("/{quiz_id}/publishing-history", response_model=List[QuizPublishingHistoryItem])
def get_quiz_publishing_history(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve audit trail of publishing, scheduling, and lifecycle transitions."""
    return pub_service.get_publishing_history(db, quiz_id, admin)
