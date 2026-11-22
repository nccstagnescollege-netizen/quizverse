import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.monitoring_service import LiveMonitoringService
from backend.app.schemas.monitoring import (
    LiveMonitoringOverviewResponse,
    LiveExaminationsListResponse,
    ExaminationMonitoringRoomResponse,
    ParticipantMonitoringListResponse,
    ParticipantDetailMonitoringResponse,
    InvigilatorAssignmentCreateRequest,
    InvigilatorAssignmentResponse,
    InvigilatorListResponse,
    ExaminationAnnouncementCreateRequest,
    ExaminationAnnouncementResponse,
    AnnouncementListResponse,
    ExaminationIncidentCreateRequest,
    ExaminationIncidentUpdateRequest,
    IncidentNoteCreateRequest,
    IncidentNoteResponse,
    ExaminationIncidentResponse,
    IncidentListResponse,
    MonitoringAlertItem,
    ExtendTimeRequest,
    TerminateAttemptRequest,
    CancelExaminationRequest,
    MonitoringInterventionResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Live Overview
# ---------------------------------------------------------------------------
@router.get("/overview", response_model=LiveMonitoringOverviewResponse)
def get_live_overview(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns platform or scope-wide real-time examination monitoring KPIs,
    connection health breakdown, recent security alerts, and active examinations.
    """
    return LiveMonitoringService.get_live_overview(db, admin)


# ---------------------------------------------------------------------------
# 2. Active Examinations List
# ---------------------------------------------------------------------------
@router.get("/examinations", response_model=LiveExaminationsListResponse)
def list_active_examinations(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns list of active/scheduled examinations with live participant counters,
    disconnection warnings, and invigilator assignments.
    """
    return LiveMonitoringService.list_active_examinations(
        db=db,
        admin=admin,
        status_filter=status_filter,
        search=search,
    )


# ---------------------------------------------------------------------------
# 3. Individual Examination Monitoring Room
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}", response_model=ExaminationMonitoringRoomResponse)
def get_examination_room(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns full room overview, countdown timings, participant breakdown,
    assigned invigilators, and real-time activity metrics.
    """
    return LiveMonitoringService.get_examination_room(db, admin, quiz_id)


# ---------------------------------------------------------------------------
# 4. Live Participant Table
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/participants", response_model=ParticipantMonitoringListResponse)
def list_room_participants(
    quiz_id: uuid.UUID = Path(...),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    connection_filter: Optional[str] = Query(None, alias="connection"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns live table of participants with server-authoritative progress %,
    heartbeat connection state, sync status, and remaining time.
    """
    return LiveMonitoringService.list_room_participants(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        search=search,
        status_filter=status_filter,
        connection_filter=connection_filter,
    )


# ---------------------------------------------------------------------------
# 5. Individual Participant Deep Telemetry
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/participants/{participant_id}", response_model=ParticipantDetailMonitoringResponse)
def get_participant_detail(
    quiz_id: uuid.UUID = Path(...),
    participant_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns detailed participant attempt telemetry, events timeline,
    question progress summary (without leaking keys), and extension history.
    """
    return LiveMonitoringService.get_participant_detail(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        participant_id=participant_id,
    )


# ---------------------------------------------------------------------------
# 6. Invigilator Management
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/invigilators", response_model=InvigilatorListResponse)
def list_invigilators(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.list_invigilators(db, admin, quiz_id)


@router.post("/examinations/{quiz_id}/invigilators", response_model=InvigilatorAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_invigilator(
    quiz_id: uuid.UUID = Path(...),
    req: InvigilatorAssignmentCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.assign_invigilator(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        invigilator_id=req.invigilator_id,
        is_lead=req.is_lead,
        permissions=req.permissions,
    )


@router.delete("/examinations/{quiz_id}/invigilators/{assignment_id}")
def revoke_invigilator(
    quiz_id: uuid.UUID = Path(...),
    assignment_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.revoke_invigilator(db, admin, quiz_id, assignment_id)


# ---------------------------------------------------------------------------
# 7. Examination Announcements
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/announcements", response_model=AnnouncementListResponse)
def list_announcements(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.list_announcements(db, admin, quiz_id)


@router.post("/examinations/{quiz_id}/announcements", response_model=ExaminationAnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    quiz_id: uuid.UUID = Path(...),
    req: ExaminationAnnouncementCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.create_announcement(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        title=req.title,
        message=req.message,
        announcement_type=req.announcement_type,
        target_scope=req.target_scope,
        target_participant_ids=req.target_participant_ids,
        requires_acknowledgement=req.requires_acknowledgement,
    )


# ---------------------------------------------------------------------------
# 8. Live Incident Management
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/incidents", response_model=IncidentListResponse)
def list_incidents(
    quiz_id: uuid.UUID = Path(...),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.list_incidents(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        status_filter=status_filter,
        severity_filter=severity_filter,
    )


@router.post("/examinations/{quiz_id}/incidents", response_model=ExaminationIncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    quiz_id: uuid.UUID = Path(...),
    req: ExaminationIncidentCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    target_quiz_id = req.quiz_id or quiz_id
    desc = req.description if (req.description and req.description.strip()) else req.title
    return LiveMonitoringService.create_incident(
        db=db,
        admin=admin,
        quiz_id=target_quiz_id,
        title=req.title,
        description=desc,
        category=req.category or "other",
        severity=req.severity or "medium",
        student_id=req.student_id,
        attempt_id=req.attempt_id,
        assigned_to=req.assigned_to,
    )


@router.patch("/examinations/{quiz_id}/incidents/{incident_id}", response_model=ExaminationIncidentResponse)
def update_incident(
    quiz_id: uuid.UUID = Path(...),
    incident_id: uuid.UUID = Path(...),
    req: ExaminationIncidentUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.update_incident(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        incident_id=incident_id,
        status_val=req.status,
        assigned_to=req.assigned_to,
        resolution_notes=req.resolution_notes,
    )


@router.post("/examinations/{quiz_id}/incidents/{incident_id}/notes", response_model=IncidentNoteResponse, status_code=status.HTTP_201_CREATED)
def add_incident_note(
    quiz_id: uuid.UUID = Path(...),
    incident_id: uuid.UUID = Path(...),
    req: IncidentNoteCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.add_incident_note(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        incident_id=incident_id,
        note=req.note,
    )


# ---------------------------------------------------------------------------
# 9. Unified Alert Center
# ---------------------------------------------------------------------------
@router.get("/alerts", response_model=List[MonitoringAlertItem])
def list_alerts(
    quiz_id: Optional[uuid.UUID] = Query(None),
    priority: Optional[str] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.list_alerts(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        priority=priority,
        is_resolved=is_resolved,
    )


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.acknowledge_alert(db, admin, alert_id)


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.resolve_alert(db, admin, alert_id)


# ---------------------------------------------------------------------------
# 10. Emergency Interventions
# ---------------------------------------------------------------------------
@router.post("/examinations/{quiz_id}/extend-time", response_model=MonitoringInterventionResponse)
def extend_examination_time(
    quiz_id: uuid.UUID = Path(...),
    req: ExtendTimeRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.extend_examination_time(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        minutes=req.minutes,
        target_type=req.target_type,
        student_id=req.student_id,
        reason=req.reason,
    )


@router.post("/examinations/{quiz_id}/terminate-attempt", response_model=MonitoringInterventionResponse)
def terminate_attempt(
    quiz_id: uuid.UUID = Path(...),
    req: TerminateAttemptRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.terminate_attempt(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        attempt_id=req.attempt_id,
        student_id=req.student_id,
        reason=req.reason or "Administrative termination",
    )


@router.post("/examinations/{quiz_id}/cancel", response_model=MonitoringInterventionResponse)
def cancel_examination(
    quiz_id: uuid.UUID = Path(...),
    req: CancelExaminationRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return LiveMonitoringService.cancel_examination(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        reason=req.reason,
    )
