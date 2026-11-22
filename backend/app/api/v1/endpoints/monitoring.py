import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status, Header, Request, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.monitoring_service import LiveMonitoringService
from backend.app.services.live_media_monitoring_service import LiveMediaMonitoringService
from backend.app.services.student_exam_service import StudentExamService
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
    MediaFeedResponse,
    MediaSessionInitRequest,
    MediaSessionInitResponse,
    WebRTCSignalExchangeRequest,
    WebRTCSignalResponse,
    MediaDeviceEventCreateRequest,
    MediaDeviceEventResponse,
    StudentMonitoringConsentRequest,
    StudentMonitoringConsentResponse,
    ListenAudioRequest,
    TwoWayCommunicationRequest,
    TwoWayCommunicationResponse,
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


# ---------------------------------------------------------------------------
# Phase 31: Real-Time Live Examination Proctoring, Webcam & Microphone Monitoring
# ---------------------------------------------------------------------------
@router.get("/examinations/{quiz_id}/media-feed", response_model=MediaFeedResponse)
def get_live_media_feed(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns live telemetry of all connected student webcam and microphone streams
    for the specified examination room. Includes active audio listening indicators.
    """
    return LiveMediaMonitoringService.get_live_media_feed(db=db, quiz_id=quiz_id, admin=admin)


@router.post("/examinations/{quiz_id}/media-session", response_model=MediaSessionInitResponse)
def initialize_media_session(
    quiz_id: uuid.UUID = Path(...),
    req: MediaSessionInitRequest = ...,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
):
    """
    Initializes an authenticated WebRTC media session for a candidate or invigilator.
    Authenticates via candidate session token or administrator bearer token.
    """
    candidate_id = None
    admin_id = None
    attempt_id = req.attempt_id

    # Try student verification first
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()

    if raw_token:
        try:
            cand_sess = StudentExamService.verify_session_token(raw_token)
            candidate_id = uuid.UUID(str(cand_sess["student_id"])) if "student_id" in cand_sess else None
            if "attempt_id" in cand_sess:
                attempt_id = uuid.UUID(str(cand_sess["attempt_id"]))
        except Exception:
            # Check if it is an admin token
            try:
                from backend.app.services.auth_service import verify_access_token
                token_data = verify_access_token(raw_token)
                admin_id = uuid.UUID(token_data.sub)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for media session initialization."
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials."
        )

    res = LiveMediaMonitoringService.initialize_media_session(
        db=db,
        quiz_id=quiz_id,
        peer_id=req.peer_id,
        role=req.role,
        candidate_id=candidate_id,
        admin_id=admin_id,
        attempt_id=attempt_id,
        device_info=req.device_info,
        camera_status=req.camera_status,
        microphone_status=req.microphone_status,
    )
    return res


@router.post("/webrtc/signal", response_model=WebRTCSignalResponse)
def exchange_webrtc_signals(
    req: WebRTCSignalExchangeRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Lightweight, high-speed WebRTC signaling bridge:
    Transfers SDP offers, answers, and ICE candidates between candidate and invigilator peers.
    """
    return LiveMediaMonitoringService.exchange_webrtc_signals(
        db=db,
        session_token=req.session_token,
        incoming_signals=req.signals,
    )


@router.post("/media-events", response_model=MediaDeviceEventResponse)
def report_media_device_event(
    req: MediaDeviceEventCreateRequest = ...,
    x_media_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Reports hardware device events (camera/microphone disconnected, permission revoked, track ended).
    Updates stream status and triggers non-punitive invigilator alert if disconnected.
    """
    token = x_media_session_token or session_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing media session token."
        )

    return LiveMediaMonitoringService.report_device_event(
        db=db,
        session_token=token,
        event_type=req.event_type,
        new_status=req.new_status,
        previous_status=req.previous_status,
        details=req.details,
        severity=req.severity,
    )


@router.post("/examinations/{quiz_id}/consent", response_model=StudentMonitoringConsentResponse)
def record_student_consent(
    quiz_id: uuid.UUID = Path(...),
    req: StudentMonitoringConsentRequest = ...,
    request: Request = None,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
):
    """
    Stores student acknowledgment and consent for webcam & microphone monitoring before exam room entry.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to record proctoring consent."
        )

    cand_sess = StudentExamService.verify_session_token(raw_token)
    student_id = uuid.UUID(str(cand_sess["student_id"]))
    attempt_id = req.attempt_id or (uuid.UUID(str(cand_sess["attempt_id"])) if "attempt_id" in cand_sess else None)

    client_ip = request.client.host if request and request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Browser") if request else "Browser"

    return LiveMediaMonitoringService.record_student_consent(
        db=db,
        quiz_id=quiz_id,
        student_id=student_id,
        attempt_id=attempt_id,
        consent_version=req.consent_version,
        webcam_acknowledged=req.webcam_acknowledged,
        microphone_acknowledged=req.microphone_acknowledged,
        recording_acknowledged=req.recording_acknowledged,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.post("/examinations/{quiz_id}/listen-audio")
def set_audio_listening_target(
    quiz_id: uuid.UUID = Path(...),
    req: ListenAudioRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Individual Student Audio Listening Control:
    Activates audio monitoring ONLY for the selected student's microphone feed.
    Strictly mutes/clears all other candidate feeds to avoid simultaneous audio playback.
    """
    return LiveMediaMonitoringService.set_audio_listening_target(
        db=db,
        quiz_id=quiz_id,
        admin=admin,
        student_id=req.student_id,
        listen=req.listen,
    )


@router.post("/examinations/{quiz_id}/two-way-communication", response_model=TwoWayCommunicationResponse)
def send_two_way_communication(
    quiz_id: uuid.UUID = Path(...),
    req: TwoWayCommunicationRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Sends an authorized invigilator instruction, warning, or device verification request to an individual student.
    """
    return LiveMediaMonitoringService.send_two_way_communication(
        db=db,
        quiz_id=quiz_id,
        admin=admin,
        student_id=req.student_id,
        comm_type=req.comm_type,
        message=req.message,
    )

