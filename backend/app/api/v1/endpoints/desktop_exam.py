import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Header, Request, Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin, enforce_quiz_access
from backend.app.services.desktop_security_service import DesktopSecurityService
from backend.app.schemas.desktop_security import (
    SEBConfigCreateRequest,
    SEBConfigResponse,
    SEBRevokeRequest,
    DesktopSessionVerifyRequest,
    DesktopSessionVerifyResponse,
    DesktopHeartbeatRequest,
    DesktopHeartbeatResponse,
    DesktopInterruptionRequest,
    DesktopInterruptionResponse,
    ComputerLabCreateRequest,
    ComputerLabUpdateRequest,
    ComputerLabResponse,
    LabDeviceCreateRequest,
    LabDeviceUpdateRequest,
    LabDeviceResponse,
    LabReadinessAuditResponse,
)

router = APIRouter()


# -----------------------------------------------------------------
# SEB Configuration Endpoints
# -----------------------------------------------------------------

@router.post(
    "/quizzes/{quiz_id}/seb-config",
    response_model=SEBConfigResponse,
    summary="Create or update Safe Exam Browser configuration profile for a quiz",
)
def create_seb_config(
    quiz_id: uuid.UUID = Path(..., description="Target quiz UUID"),
    req: SEBConfigCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    enforce_quiz_access(db, admin, quiz_id, required_level="editor")
    return DesktopSecurityService.create_or_update_seb_config(
        db=db,
        quiz_id=quiz_id,
        req=req,
        admin_id=admin.id,
    )


@router.get(
    "/quizzes/{quiz_id}/seb-config",
    response_model=Optional[SEBConfigResponse],
    summary="Get active Safe Exam Browser configuration profile for a quiz",
)
def get_seb_config(
    quiz_id: uuid.UUID = Path(..., description="Target quiz UUID"),
    db: Session = Depends(get_db),
):
    cfg = DesktopSecurityService.get_seb_config_by_quiz_id(db=db, quiz_id=quiz_id)
    return cfg


@router.get(
    "/quizzes/{quiz_id}/seb-config/download",
    summary="Download the XML property list (.seb) configuration file for Safe Exam Browser",
)
def download_seb_file(
    quiz_id: uuid.UUID = Path(..., description="Target quiz UUID"),
    version: Optional[int] = Query(None, description="Specific configuration version number"),
    db: Session = Depends(get_db),
):
    xml_content, filename = DesktopSecurityService.get_seb_xml(db=db, quiz_id=quiz_id, version=version)
    return Response(
        content=xml_content,
        media_type="application/seb",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.post(
    "/quizzes/{quiz_id}/seb-config/revoke",
    response_model=SEBConfigResponse,
    summary="Revoke an active Safe Exam Browser configuration profile",
)
def revoke_seb_config(
    quiz_id: uuid.UUID = Path(..., description="Target quiz UUID"),
    req: SEBRevokeRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    enforce_quiz_access(db, admin, quiz_id, required_level="editor")
    return DesktopSecurityService.revoke_seb_config(
        db=db,
        quiz_id=quiz_id,
        req=req,
        admin_id=admin.id,
    )


# -----------------------------------------------------------------
# Desktop Examination Session Verification & Heartbeats
# -----------------------------------------------------------------

@router.post(
    "/verify-session",
    response_model=DesktopSessionVerifyResponse,
    summary="Verify desktop examination environment, SEB headers, and lab workstation",
)
def verify_desktop_session(
    req: DesktopSessionVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_seb_ck_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    x_seb_req_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
):
    # Extract client IP and headers
    client_ip = request.client.host if request.client else None
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0].strip()

    ua = req.user_agent or request.headers.get("user-agent", "")
    
    # Merge headers into request if not already populated in payload
    if not req.config_key_hash and x_seb_ck_hash:
        req.config_key_hash = x_seb_ck_hash
    if not req.request_hash and x_seb_req_hash:
        req.request_hash = x_seb_req_hash
    if not req.user_agent:
        req.user_agent = ua

    return DesktopSecurityService.verify_desktop_session(
        db=db,
        req=req,
        ip_address=client_ip,
    )


@router.post(
    "/heartbeat",
    response_model=DesktopHeartbeatResponse,
    summary="Desktop examination client heartbeat ping",
)
def desktop_heartbeat(
    req: DesktopHeartbeatRequest,
    db: Session = Depends(get_db),
):
    return DesktopSecurityService.record_desktop_heartbeat(db=db, req=req)


@router.post(
    "/interruption",
    response_model=DesktopInterruptionResponse,
    summary="Record a desktop security interruption event (SEB quit attempt, focus loss, window blur)",
)
def desktop_interruption(
    req: DesktopInterruptionRequest,
    db: Session = Depends(get_db),
):
    return DesktopSecurityService.record_desktop_interruption(db=db, req=req)


# -----------------------------------------------------------------
# Institutional Computer Lab Management (Admin RBAC)
# -----------------------------------------------------------------

@router.get(
    "/labs",
    response_model=List[ComputerLabResponse],
    summary="List registered institutional computer laboratories",
)
def list_labs(
    institution_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.list_computer_labs(
        db=db,
        institution_id=institution_id,
        status_filter=status_filter,
    )


@router.post(
    "/labs",
    response_model=ComputerLabResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new computer laboratory",
)
def create_lab(
    req: ComputerLabCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.create_computer_lab(db=db, req=req)


@router.get(
    "/labs/{lab_id}",
    response_model=ComputerLabResponse,
    summary="Get computer lab details",
)
def get_lab(
    lab_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.get_computer_lab(db=db, lab_id=lab_id)


@router.put(
    "/labs/{lab_id}",
    response_model=ComputerLabResponse,
    summary="Update computer lab information",
)
def update_lab(
    lab_id: uuid.UUID = Path(...),
    req: ComputerLabUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.update_computer_lab(db=db, lab_id=lab_id, req=req)


@router.delete(
    "/labs/{lab_id}",
    summary="Delete a computer laboratory",
)
def delete_lab(
    lab_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.delete_computer_lab(db=db, lab_id=lab_id)


# -----------------------------------------------------------------
# Lab Devices & Workstations
# -----------------------------------------------------------------

@router.get(
    "/labs/{lab_id}/devices",
    response_model=List[LabDeviceResponse],
    summary="List workstations assigned to a computer lab",
)
def list_devices(
    lab_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.list_lab_devices(db=db, lab_id=lab_id)


@router.post(
    "/labs/{lab_id}/devices",
    response_model=LabDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new workstation in a computer lab",
)
def register_device(
    lab_id: uuid.UUID = Path(...),
    req: LabDeviceCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.register_lab_device(db=db, lab_id=lab_id, req=req)


@router.put(
    "/labs/{lab_id}/devices/{device_id}",
    response_model=LabDeviceResponse,
    summary="Update workstation device settings or compatibility status",
)
def update_device(
    lab_id: uuid.UUID = Path(...),
    device_id: uuid.UUID = Path(...),
    req: LabDeviceUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.update_lab_device(db=db, device_id=device_id, req=req)


@router.delete(
    "/labs/{lab_id}/devices/{device_id}",
    summary="Remove a workstation from a computer lab",
)
def delete_device(
    lab_id: uuid.UUID = Path(...),
    device_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.delete_lab_device(db=db, device_id=device_id)


@router.get(
    "/labs/{lab_id}/readiness",
    response_model=LabReadinessAuditResponse,
    summary="Audit computer lab SEB readiness and compatibility score",
)
def audit_lab_readiness(
    lab_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return DesktopSecurityService.audit_lab_readiness(db=db, lab_id=lab_id)
