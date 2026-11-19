from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, Path, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.student_registration_service import StudentRegistrationService
from backend.app.schemas.invitation import (
    PublicInvitationValidationResponse,
    PublicRegistrationSubmitRequest,
    PublicRegistrationReceiptResponse,
)

router = APIRouter()


@router.get("/invitations/{token}/validate", response_model=PublicInvitationValidationResponse)
def validate_invitation_token(
    token: str = Path(..., description="Cryptographically secure invitation token"),
    db: Session = Depends(get_db),
):
    """
    Public student entry point:
    Validates token hash against the database, checks active/expired/revoked/exhausted states,
    and returns registration form schema and basic quiz instructions.
    Does NOT leak internal student information.
    """
    return StudentRegistrationService.validate_public_token(db, token)


@router.post("/invitations/{token}/register", response_model=PublicRegistrationReceiptResponse, status_code=status.HTTP_201_CREATED)
def register_candidate_with_token(
    token: str = Path(..., description="Cryptographically secure invitation token"),
    req: PublicRegistrationSubmitRequest = ...,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Public candidate registration submission:
    - Atomically verifies token and quota capacity.
    - Validates required built-in and custom fields.
    - Prevents duplicate registration.
    - Upserts candidate and enrolls participant.
    - Logs usage attempt.
    - Returns registration confirmation receipt.
    """
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    return StudentRegistrationService.register_candidate(
        db=db,
        token=token,
        form_data=req.form_data,
        client_ip=client_ip,
        user_agent=user_agent,
    )
