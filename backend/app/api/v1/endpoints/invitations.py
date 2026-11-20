from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, Query, Path, Response, Request, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin
from backend.app.services.invitation_service import InvitationService
from backend.app.services.student_registration_service import StudentRegistrationService
from backend.app.schemas.invitation import (
    InvitationCreateRequest,
    InvitationUpdateRequest,
    InvitationResponse,
    InvitationListResponse,
    InvitationUsageResponse,
    ParticipantItemResponse,
    ParticipantListResponse,
    ParticipantStatusUpdateRequest,
    BatchParticipantStatusUpdateRequest,
    RegistrationFormCreateUpdateRequest,
    RegistrationFormResponse,
    EligibleQuizResponse,
)

router = APIRouter()


@router.get("/eligible-quizzes", response_model=List[EligibleQuizResponse])
def get_eligible_quizzes(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List quizzes published or scheduled that are eligible for invitation generation."""
    return InvitationService.get_eligible_quizzes(db, admin)


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    req: InvitationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Generate a unique cryptographic invitation token and QR code for an eligible quiz.
    Stores only the SHA-256 hash. Returns the raw token and QR representations in this response only.
    """
    return InvitationService.create_invitation(db, admin, req, request=request)


@router.get("", response_model=InvitationListResponse)
def list_invitations(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, scheduled, expired, revoked, exhausted, all)"),
    type: Optional[str] = Query(None, description="Filter by invitation type"),
    search: Optional[str] = Query(None, description="Search by name, quiz title, or target email"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List invitations with real-time status evaluation and RBAC isolation."""
    return InvitationService.list_invitations(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        status_filter=status,
        invitation_type=type,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/participants", response_model=ParticipantListResponse)
def list_all_participants(
    quiz_id: Optional[uuid.UUID] = Query(None, description="Filter by quiz ID"),
    status: Optional[str] = Query(None, description="Filter by participant status"),
    search: Optional[str] = Query(None, description="Search by candidate name or email"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List participants across accessible quizzes with status and metrics."""
    return InvitationService.get_participants(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        status_filter=status,
        search=search,
        page=page,
        limit=limit,
    )


@router.patch("/participants/{participant_id}/status", response_model=ParticipantItemResponse)
def update_participant_status(
    participant_id: uuid.UUID = Path(..., description="Participant ID"),
    req: ParticipantStatusUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Approve, reject, or revoke a student participant registration."""
    return InvitationService.update_participant_status(
        db=db,
        admin=admin,
        participant_id=participant_id,
        new_status=req.status,
        rejection_reason=req.rejection_reason,
        internal_notes=req.internal_notes,
    )


@router.post("/participants/batch-status", response_model=Dict[str, Any])
def batch_update_participant_status(
    req: BatchParticipantStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Batch approve, reject, or revoke registrations."""
    count = 0
    for pid in req.participant_ids:
        try:
            InvitationService.update_participant_status(
                db=db,
                admin=admin,
                participant_id=pid,
                new_status=req.status,
                rejection_reason=req.rejection_reason,
            )
            count += 1
        except Exception:
            pass

    return {
        "success": True,
        "updated_count": count,
        "status": req.status,
    }


@router.get("/quizzes/{quiz_id}/registration-form", response_model=RegistrationFormResponse)
def get_quiz_registration_form(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Get active registration form configuration for a quiz (or provisions default)."""
    return StudentRegistrationService.get_quiz_registration_form(db, quiz_id)


@router.post("/quizzes/{quiz_id}/registration-form", response_model=RegistrationFormResponse)
def save_quiz_registration_form(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    req: RegistrationFormCreateUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Save or update registration form configuration. Automatically creates a new version."""
    return StudentRegistrationService.save_quiz_registration_form(db, admin, quiz_id, req)


@router.get("/{invitation_id}", response_model=InvitationResponse)
def get_invitation_detail(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Get invitation detail with access restrictions and status."""
    return InvitationService.get_invitation(db, admin, invitation_id)


@router.patch("/{invitation_id}", response_model=InvitationResponse)
def update_invitation(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    req: InvitationUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Update allowed settings of an active invitation."""
    return InvitationService.update_invitation(db, admin, invitation_id, req)


@router.post("/{invitation_id}/revoke", response_model=Dict[str, Any])
def revoke_invitation(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Revoke an invitation link immediately. Permanently prevents future redemptions and QR scans."""
    return InvitationService.revoke_invitation(db, admin, invitation_id)


@router.get("/{invitation_id}/usage", response_model=InvitationUsageResponse)
def get_invitation_usage(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve usage analytics, redemptions log, and remaining capacity."""
    return InvitationService.get_invitation_usage(db, admin, invitation_id)


@router.get("/{invitation_id}/participants", response_model=ParticipantListResponse)
def get_invitation_participants(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search candidates"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List registered participants for a specific invitation link."""
    return InvitationService.get_participants(
        db=db,
        admin=admin,
        invitation_id=invitation_id,
        status_filter=status,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/{invitation_id}/export")
def export_invitation_participants_csv(
    invitation_id: uuid.UUID = Path(..., description="Invitation Link ID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Export invitation participants list as a downloadable CSV file."""
    csv_content = InvitationService.export_participants_csv(db, admin, invitation_id=invitation_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=participants_{invitation_id}.csv"
        }
    )
