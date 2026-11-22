import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.monitoring import (
    MediaExaminationRoom,
    MediaParticipantSession,
    MediaDeviceStatusEvent,
    StudentMonitoringConsent,
    ExaminationIncident,
    InvigilatorActivityLog,
    ExaminationAnnouncement,
)
from backend.app.models.quiz import Quiz
from backend.app.models.student import Student
from backend.app.models.auth_rbac import Admin
from backend.app.schemas.monitoring import (
    WebRTCSignalMessage,
    WebRTCSignalResponse,
    MediaFeedResponse,
    MediaParticipantSessionItem,
    TwoWayCommunicationResponse,
)
from backend.app.services.monitoring_service import LiveMonitoringService

logger = logging.getLogger("quizverse.live_media")

# Fast in-memory WebRTC signaling buffer: room_id -> peer_id -> [WebRTCSignalMessage]
# Bounded to 50 items per peer to prevent unbounded memory growth
_SIGNAL_BUFFER: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))


class LiveMediaMonitoringService:

    @staticmethod
    def get_or_create_media_room(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Optional[Admin] = None,
    ) -> MediaExaminationRoom:
        """
        Retrieves or initializes the media examination room for the given quiz.
        Enforces RBAC scoping if an admin is provided.
        """
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Examination with ID {quiz_id} not found."
            )

        if admin:
            # Scoped check
            LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        room = db.query(MediaExaminationRoom).filter(MediaExaminationRoom.quiz_id == quiz_id).first()
        if not room:
            room = MediaExaminationRoom(
                quiz_id=quiz_id,
                is_active=True,
                audio_broadcast_allowed=False,
                recording_enabled=False,  # strictly false by default
                recording_policy_disclosed=True,
                max_participants=100,
            )
            db.add(room)
            db.commit()
            db.refresh(room)

        return room

    @staticmethod
    def initialize_media_session(
        db: Session,
        quiz_id: uuid.UUID,
        peer_id: str,
        role: str = "student",
        candidate_id: Optional[uuid.UUID] = None,
        admin_id: Optional[uuid.UUID] = None,
        attempt_id: Optional[uuid.UUID] = None,
        device_info: Optional[Dict[str, Any]] = None,
        camera_status: str = "Connected",
        microphone_status: str = "Connected",
    ) -> Dict[str, Any]:
        """
        Initializes an authenticated WebRTC media session for a student or invigilator.
        """
        room = LiveMediaMonitoringService.get_or_create_media_room(db, quiz_id)

        # Deactivate existing active sessions with the same candidate/admin/peer for this room
        query = db.query(MediaParticipantSession).filter(
            MediaParticipantSession.room_id == room.id,
            MediaParticipantSession.is_active == True,
        )
        if candidate_id:
            query = query.filter(MediaParticipantSession.candidate_id == candidate_id)
        elif admin_id:
            query = query.filter(MediaParticipantSession.admin_id == admin_id)
        else:
            query = query.filter(MediaParticipantSession.peer_id == peer_id)
        
        existing = query.all()
        for sess in existing:
            sess.is_active = False

        session_token = uuid.uuid4().hex

        new_session = MediaParticipantSession(
            room_id=room.id,
            quiz_id=quiz_id,
            candidate_id=candidate_id,
            admin_id=admin_id,
            attempt_id=attempt_id,
            session_token=session_token,
            peer_id=peer_id,
            role=role,
            camera_status=camera_status,
            microphone_status=microphone_status,
            stream_status="LIVE",
            audio_level="no_input",
            network_quality="GOOD",
            device_info=device_info,
            is_active=True,
            is_pinned=False,
            is_audio_listened=False,
            last_heartbeat_at=datetime.now(timezone.utc),
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # Announce joining to other room peers
        room_str = str(room.id)
        join_signal = {
            "type": "join",
            "sender_peer_id": peer_id,
            "target_peer_id": None,
            "metadata": {
                "role": role,
                "candidate_id": str(candidate_id) if candidate_id else None,
                "camera_status": camera_status,
                "microphone_status": microphone_status,
            }
        }
        # Push to all existing peers in this room
        for target_peer in list(_SIGNAL_BUFFER[room_str].keys()):
            if target_peer != peer_id:
                _SIGNAL_BUFFER[room_str][target_peer].append(join_signal)

        return {
            "room_id": room.id,
            "session_id": new_session.id,
            "session_token": session_token,
            "peer_id": peer_id,
            "recording_enabled": room.recording_enabled,
            "audio_broadcast_allowed": room.audio_broadcast_allowed,
        }

    @staticmethod
    def exchange_webrtc_signals(
        db: Session,
        session_token: str,
        incoming_signals: List[WebRTCSignalMessage],
    ) -> WebRTCSignalResponse:
        """
        Exchanges SDP offers, answers, and ICE candidates between candidate and invigilator peers.
        Also returns any signals buffered for this peer.
        """
        session = db.query(MediaParticipantSession).filter(
            MediaParticipantSession.session_token == session_token,
            MediaParticipantSession.is_active == True,
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired media session token."
            )

        # Update heartbeat
        session.last_heartbeat_at = datetime.now(timezone.utc)
        db.commit()

        room_str = str(session.room_id)
        sender_peer_id = session.peer_id

        delivered_count = 0
        for sig in incoming_signals:
            sig_dict = sig.model_dump()
            sig_dict["sender_peer_id"] = sender_peer_id
            target = sig.target_peer_id

            if target:
                # Direct signal to specific peer
                buf = _SIGNAL_BUFFER[room_str][target]
                if len(buf) < 50:
                    buf.append(sig_dict)
                    delivered_count += 1
            else:
                # Broadcast signal to all active peers in room except sender
                active_peers = [
                    p.peer_id for p in db.query(MediaParticipantSession.peer_id).filter(
                        MediaParticipantSession.room_id == session.room_id,
                        MediaParticipantSession.is_active == True,
                        MediaParticipantSession.peer_id != sender_peer_id,
                    ).all()
                ]
                for p_id in active_peers:
                    buf = _SIGNAL_BUFFER[room_str][p_id]
                    if len(buf) < 50:
                        buf.append(sig_dict)
                        delivered_count += 1

        # Retrieve pending signals for this peer
        pending_raw = _SIGNAL_BUFFER[room_str].get(sender_peer_id, [])
        # Drain the buffer
        _SIGNAL_BUFFER[room_str][sender_peer_id] = []

        pending_models = [WebRTCSignalMessage(**item) for item in pending_raw]

        return WebRTCSignalResponse(
            success=True,
            delivered_count=delivered_count,
            signals=pending_models,
        )

    @staticmethod
    def report_device_event(
        db: Session,
        session_token: str,
        event_type: str,
        new_status: str,
        previous_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> MediaDeviceStatusEvent:
        """
        Logs a device status change (e.g. camera disconnected, track ended, microphone mute).
        Updates the participant session state and automatically registers an incident if required.
        """
        session = db.query(MediaParticipantSession).filter(
            MediaParticipantSession.session_token == session_token,
            MediaParticipantSession.is_active == True,
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Media session not found or inactive."
            )

        prev_stat = previous_status
        if event_type in ("CAMERA_DISCONNECTED", "CAMERA_TRACK_ENDED", "CAMERA_REVOKED"):
            prev_stat = prev_stat or session.camera_status
            session.camera_status = new_status
            if new_status in ("Disconnected", "Permission denied", "Device unavailable"):
                session.stream_status = "INTERRUPTED"
                severity = "warning"
        elif event_type in ("MICROPHONE_DISCONNECTED", "MICROPHONE_TRACK_ENDED", "MICROPHONE_REVOKED"):
            prev_stat = prev_stat or session.microphone_status
            session.microphone_status = new_status
            if new_status in ("Disconnected", "Permission denied", "Device unavailable"):
                severity = "warning"
        elif event_type == "STREAM_RECOVERED":
            session.camera_status = "Connected"
            session.microphone_status = "Connected"
            session.stream_status = "LIVE"
            severity = "info"
        elif event_type == "AUDIO_LEVEL_CHANGE":
            session.audio_level = new_status

        session.last_heartbeat_at = datetime.now(timezone.utc)

        event = MediaDeviceStatusEvent(
            session_id=session.id,
            quiz_id=session.quiz_id,
            attempt_id=session.attempt_id,
            event_type=event_type,
            previous_status=prev_stat,
            new_status=new_status,
            details=details,
            severity=severity,
        )
        db.add(event)

        # If critical disconnection, create a non-punitive incident for invigilator review
        if severity in ("warning", "critical") and event_type in (
            "CAMERA_DISCONNECTED", "CAMERA_REVOKED", "MICROPHONE_DISCONNECTED", "MICROPHONE_REVOKED"
        ):
            inc_code = f"INC-MEDIA-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            incident = ExaminationIncident(
                incident_code=inc_code,
                quiz_id=session.quiz_id,
                student_id=session.candidate_id,
                attempt_id=session.attempt_id,
                category="security_concern",
                severity="medium",
                severity_level=2,
                event_source="SERVER_VERIFIED",
                recovery_state="ACTIVE_INTERRUPTED",
                status="OPEN",
                title=f"Media Device Alert: {event_type.replace('_', ' ').title()}",
                description=(
                    f"Candidate media stream reported {event_type}. "
                    f"Camera status: {session.camera_status}, Microphone status: {session.microphone_status}. "
                    "Technical interruptions are non-punitive and pending candidate recovery."
                ),
                interruption_metadata=details,
            )
            db.add(incident)

        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def record_student_consent(
        db: Session,
        quiz_id: uuid.UUID,
        student_id: uuid.UUID,
        attempt_id: Optional[uuid.UUID] = None,
        consent_version: str = "v1.0",
        webcam_acknowledged: bool = True,
        microphone_acknowledged: bool = True,
        recording_acknowledged: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> StudentMonitoringConsent:
        """
        Stores student acknowledgment and consent for authorized camera and microphone proctoring.
        Confirms recording is disabled unless separately authorized and disclosed.
        """
        consent = StudentMonitoringConsent(
            quiz_id=quiz_id,
            student_id=student_id,
            attempt_id=attempt_id,
            consent_version=consent_version,
            webcam_acknowledged=webcam_acknowledged,
            microphone_acknowledged=microphone_acknowledged,
            recording_acknowledged=recording_acknowledged,
            ip_address=ip_address,
            user_agent=user_agent,
            consented_at=datetime.now(timezone.utc),
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        return consent

    @staticmethod
    def get_live_media_feed(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
    ) -> MediaFeedResponse:
        """
        Returns real-time telemetry of all connected student camera and audio feeds.
        Marks stale sessions as Disconnected if no heartbeat in 45 seconds.
        """
        room = LiveMediaMonitoringService.get_or_create_media_room(db, quiz_id, admin)

        threshold = datetime.now(timezone.utc) - timedelta(seconds=45)

        sessions = (
            db.query(MediaParticipantSession)
            .filter(
                MediaParticipantSession.room_id == room.id,
                MediaParticipantSession.role == "student",
                MediaParticipantSession.is_active == True,
            )
            .all()
        )

        connected_cameras = 0
        connected_microphones = 0
        active_listened_id: Optional[str] = None
        participant_items: List[MediaParticipantSessionItem] = []

        for s in sessions:
            # Check staleness
            hb = s.last_heartbeat_at
            if hb and hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)

            if hb and hb < threshold:
                s.stream_status = "OFFLINE"
                s.camera_status = "Disconnected"
                s.microphone_status = "Disconnected"
                s.network_quality = "CRITICAL"

            if s.camera_status == "Connected":
                connected_cameras += 1
            if s.microphone_status == "Connected":
                connected_microphones += 1
            if s.is_audio_listened:
                active_listened_id = str(s.candidate_id) if s.candidate_id else None

            # Student details
            cand_name = "Candidate"
            cand_email = None
            if s.candidate_id:
                student = db.query(Student).filter(Student.id == s.candidate_id).first()
                if student:
                    cand_name = getattr(student, "full_name", None) or getattr(student, "name", None) or f"Candidate {str(student.id)[:8]}"
                    cand_email = student.email

            participant_items.append(
                MediaParticipantSessionItem(
                    id=s.id,
                    room_id=s.room_id,
                    quiz_id=s.quiz_id,
                    candidate_id=s.candidate_id,
                    candidate_name=cand_name,
                    candidate_email=cand_email,
                    attempt_id=s.attempt_id,
                    session_token=s.session_token,
                    peer_id=s.peer_id,
                    role=s.role,
                    camera_status=s.camera_status,
                    microphone_status=s.microphone_status,
                    stream_status=s.stream_status,
                    audio_level=s.audio_level,
                    network_quality=s.network_quality,
                    device_info=s.device_info,
                    is_active=s.is_active,
                    is_pinned=s.is_pinned,
                    is_audio_listened=s.is_audio_listened,
                    last_heartbeat_at=s.last_heartbeat_at,
                    created_at=s.created_at,
                )
            )

        db.commit()

        return MediaFeedResponse(
            quiz_id=room.quiz_id,
            room_id=room.id,
            recording_enabled=room.recording_enabled,
            total_active_participants=len(sessions),
            connected_cameras=connected_cameras,
            connected_microphones=connected_microphones,
            active_audio_listening_student_id=active_listened_id,
            participants=participant_items,
        )

    @staticmethod
    def set_audio_listening_target(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        student_id: uuid.UUID,
        listen: bool = True,
    ) -> Dict[str, Any]:
        """
        Strict Individual Audio Listening:
        When listen=True, activates audio monitoring ONLY for this student and clears all others.
        Never mixes multiple students' audio streams simultaneously.
        """
        room = LiveMediaMonitoringService.get_or_create_media_room(db, quiz_id, admin)

        # Clear audio listening on ALL sessions in this room first
        db.query(MediaParticipantSession).filter(
            MediaParticipantSession.room_id == room.id,
        ).update({"is_audio_listened": False})

        target_session = None
        if listen:
            target_session = db.query(MediaParticipantSession).filter(
                MediaParticipantSession.room_id == room.id,
                MediaParticipantSession.candidate_id == student_id,
                MediaParticipantSession.is_active == True,
            ).first()
            if target_session:
                target_session.is_audio_listened = True

        # Log invigilator action
        action_name = "LISTENED_AUDIO" if listen else "STOPPED_AUDIO_LISTENING"
        log = InvigilatorActivityLog(
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action=action_name,
            details={
                "target_student_id": str(student_id),
                "listen": listen,
                "session_id": str(target_session.id) if target_session else None,
            }
        )
        db.add(log)
        db.commit()

        return {
            "success": True,
            "target_student_id": str(student_id),
            "is_audio_listened": listen and bool(target_session),
            "message": f"Audio monitoring {'activated' if listen else 'stopped'} for student.",
        }

    @staticmethod
    def send_two_way_communication(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        student_id: uuid.UUID,
        comm_type: str,
        message: str,
    ) -> TwoWayCommunicationResponse:
        """
        Sends an authorized two-way invigilator instruction, warning, or device verification request.
        """
        room = LiveMediaMonitoringService.get_or_create_media_room(db, quiz_id, admin)

        announcement = ExaminationAnnouncement(
            quiz_id=quiz_id,
            sender_id=admin.id,
            title=f"Invigilator {comm_type.replace('_', ' ').title()}",
            message=message,
            announcement_type="technical_notice" if "camera" in comm_type or "mic" in comm_type else "warning",
            target_scope="selected_participants",
            target_participant_ids=[str(student_id)],
            requires_acknowledgement=True,
        )
        db.add(announcement)

        # Log activity
        log = InvigilatorActivityLog(
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action="SENT_DIRECT_COMMUNICATION",
            details={
                "target_student_id": str(student_id),
                "comm_type": comm_type,
                "message": message,
            }
        )
        db.add(log)
        db.commit()

        return TwoWayCommunicationResponse(
            success=True,
            recipient_id=student_id,
            comm_type=comm_type,
            message=message,
            delivered_at=datetime.now(timezone.utc),
        )
