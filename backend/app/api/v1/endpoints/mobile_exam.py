import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Header, Request
from sqlalchemy.orm import Session
import jwt

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import require_permission
from backend.app.services.mobile_security_service import MobileSecurityService
from backend.app.schemas.mobile_security import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    MobileCompatibilityCheckRequest,
    MobileCompatibilityCheckResponse,
    MobileExamSessionInitRequest,
    MobileExamSessionResponse,
    MobileInterruptionSubmitRequest,
    MobileInterruptionSubmitResponse,
    MobileRecoveryRequest,
    MobileRecoveryResponse,
    MobileQuizSecurityPolicyResponse,
    DeviceListItemResponse,
)

router = APIRouter()


def get_current_mobile_student_session(
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Extracts and validates candidate examination session JWT token or student auth token.
    Returns payload dictionary containing 'sub' (student UUID) and attempt/quiz identifiers.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing mobile examination session token.",
        )

    try:
        secret = settings.effective_jwt_secret
        algo = getattr(settings, "JWT_ALGORITHM", "HS256")
        payload = jwt.decode(raw_token, secret, algorithms=[algo], options={"verify_aud": False})
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid examination token: missing subject identity.",
            )
        return payload
    except (jwt.PyJWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired mobile examination token.",
        )


# ---------------------------------------------------------------------------
# 1. Device Registration Endpoints
# ---------------------------------------------------------------------------

@router.post("/devices/register", response_model=DeviceRegisterResponse)
def register_mobile_device(
    request: Request,
    req: DeviceRegisterRequest,
    session: Dict[str, Any] = Depends(get_current_mobile_student_session),
    db: Session = Depends(get_db),
):
    """
    Registers or updates candidate mobile device reference.
    Enforces device trust status and blocks restricted hardware devices.
    """
    student_id = uuid.UUID(session["sub"])
    ip = request.client.host if request.client else None
    return MobileSecurityService.register_device(
        db=db,
        student_id=student_id,
        req=req,
        ip_address=ip,
    )


# ---------------------------------------------------------------------------
# 2. Mobile Device Compatibility Verification
# ---------------------------------------------------------------------------

@router.post("/compatibility", response_model=MobileCompatibilityCheckResponse)
def check_mobile_compatibility(
    req: MobileCompatibilityCheckRequest,
    session: Dict[str, Any] = Depends(get_current_mobile_student_session),
    db: Session = Depends(get_db),
):
    """
    Verifies mobile platform compatibility, FLAG_SECURE status,
    root/jailbreak risk signals, and lock-task kiosk readiness.
    """
    student_id = uuid.UUID(session["sub"])
    return MobileSecurityService.verify_mobile_compatibility(
        db=db,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 3. Mobile Examination Session Management
# ---------------------------------------------------------------------------

@router.post("/attempts/{attempt_id}/session", response_model=MobileExamSessionResponse)
def init_mobile_session(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: MobileExamSessionInitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_mobile_student_session),
    db: Session = Depends(get_db),
):
    """
    Initializes or activates a native mobile examination session.
    Protects against simultaneous device hijacking and activates server timer authority.
    """
    student_id = uuid.UUID(session["sub"])
    return MobileSecurityService.init_mobile_exam_session(
        db=db,
        attempt_id=attempt_id,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 4. Mobile Lifecycle & Interruption Telemetry
# ---------------------------------------------------------------------------

@router.post("/attempts/{attempt_id}/interruptions", response_model=MobileInterruptionSubmitResponse)
def submit_mobile_interruption(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: MobileInterruptionSubmitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_mobile_student_session),
    db: Session = Depends(get_db),
):
    """
    Submits mobile lifecycle interruptions (calls, backgrounding, OS dialogs).
    Integrates with unified anti-cheating risk scoring engine.
    Zero-disqualification guarantee: Never auto-fails students without human invigilation.
    """
    student_id = uuid.UUID(session["sub"])
    return MobileSecurityService.record_interruption(
        db=db,
        attempt_id=attempt_id,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 5. Mobile Session Recovery
# ---------------------------------------------------------------------------

@router.post("/attempts/{attempt_id}/recover", response_model=MobileRecoveryResponse)
def recover_mobile_session(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: MobileRecoveryRequest = ...,
    session: Dict[str, Any] = Depends(get_current_mobile_student_session),
    db: Session = Depends(get_db),
):
    """
    Restores interrupted examination sessions.
    Guarantees: Server-authoritative timer deadline is preserved without time extensions.
    """
    student_id = uuid.UUID(session["sub"])
    return MobileSecurityService.recover_exam_session(
        db=db,
        attempt_id=attempt_id,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 6. Policy & Device Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/quizzes/{quiz_id}/mobile-policy", response_model=MobileQuizSecurityPolicyResponse)
def get_quiz_mobile_policy(
    quiz_id: uuid.UUID = Path(..., description="Quiz ID"),
    db: Session = Depends(get_db),
):
    """
    Retrieves quiz-specific mobile security policies.
    """
    return MobileSecurityService.get_quiz_mobile_policy(db, quiz_id)


@router.get("/devices/student/{student_id}", response_model=List[DeviceListItemResponse])
def get_student_devices(
    student_id: uuid.UUID = Path(..., description="Student UUID"),
    admin: Admin = Depends(require_permission("examination.monitor")),
    db: Session = Depends(get_db),
):
    """
    Invigilator endpoint: Lists all registered mobile devices for a student.
    """
    return MobileSecurityService.get_student_devices(db, student_id)


@router.patch("/devices/{device_id}/status", response_model=DeviceListItemResponse)
def update_device_status(
    device_id: uuid.UUID = Path(..., description="Registered Device UUID"),
    is_trusted: Optional[bool] = Query(None),
    is_blocked: Optional[bool] = Query(None),
    block_reason: Optional[str] = Query(None),
    admin: Admin = Depends(require_permission("quiz.edit")),
    db: Session = Depends(get_db),
):
    """
    Administrator endpoint: Trust or block registered student mobile hardware.
    """
    return MobileSecurityService.update_device_status(
        db=db,
        device_id=device_id,
        is_trusted=is_trusted,
        is_blocked=is_blocked,
        block_reason=block_reason,
    )
