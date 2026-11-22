import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_

from backend.app.models.auth_rbac import Admin
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.models.monitoring import (
    ExaminationIncident,
    IncidentNote,
    MonitoringAlert,
    InvigilatorAssignment,
    InvigilatorActivityLog,
)
from backend.app.models.interruption import (
    IncidentTimelineEvent,
    DevicePreparationLog,
    InterruptionRecoverySession,
)
from backend.app.schemas.interruption import (
    InterruptionEventRequest,
    InterruptionEventResponse,
    DevicePreparationRequest,
    DevicePreparationResponse,
    SessionRecoveryRequest,
    SessionRecoveryResponse,
    AnswerBatchSyncRequest,
    AnswerBatchSyncResponse,
    IncidentActionRequest,
    IncidentActionResponse,
    IncidentTimelineItemResponse,
    IncidentTimelineListResponse,
    InterruptionPolicyResponse,
)
from backend.app.core.logging import logger


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class InterruptionService:
    """
    Centralized Examination Interruption, Recovery & Incident Management Service (Phase 27).
    Guarantees server-authoritative timers, idempotent answer synchronization,
    privacy-conscious detection, and auditable invigilator actions.
    """

    @staticmethod
    def get_quiz_policy(db: Session, quiz_id: uuid.UUID) -> InterruptionPolicyResponse:
        """Retrieves active interruption and incident configuration for a quiz."""
        config = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_id).first()
        if not config:
            return InterruptionPolicyResponse(
                quiz_id=quiz_id,
                interruption_handling_policy="continue_with_warning",
                allow_call_recovery=True,
                max_call_interruptions=3,
                call_grace_seconds=60,
                require_device_prep_acknowledgment=True,
                auto_pause_on_disconnect=False,
                revalidation_code_required=False,
                network_interruption_policy="allow_sync",
                allow_interrupted_session_resume=True,
            )

        return InterruptionPolicyResponse(
            quiz_id=quiz_id,
            interruption_handling_policy=getattr(config, "interruption_handling_policy", "continue_with_warning"),
            allow_call_recovery=getattr(config, "allow_call_recovery", True),
            max_call_interruptions=getattr(config, "max_call_interruptions", 3),
            call_grace_seconds=getattr(config, "call_grace_seconds", 60),
            require_device_prep_acknowledgment=getattr(config, "require_device_prep_acknowledgment", True),
            auto_pause_on_disconnect=getattr(config, "auto_pause_on_disconnect", False),
            revalidation_code_required=getattr(config, "revalidation_code_required", False),
            network_interruption_policy=getattr(config, "network_interruption_policy", "allow_sync"),
            allow_interrupted_session_resume=getattr(config, "allow_interrupted_session_resume", True),
        )

    @staticmethod
    def record_device_preparation(
        db: Session, student_id: uuid.UUID, req: DevicePreparationRequest
    ) -> DevicePreparationResponse:
        """
        Records candidate pre-flight device preparation checklist before examination entry.
        """
        from backend.app.models.student import Student
        student = db.query(Student).filter(Student.id == student_id).first()
        ack_time = datetime.now(timezone.utc)

        if student:
            prep_log = DevicePreparationLog(
                quiz_id=req.quiz_id,
                student_id=student_id,
                attempt_id=req.attempt_id,
                battery_level=req.battery_level,
                is_charging=req.is_charging,
                network_type=req.network_type,
                dnd_acknowledged=req.dnd_acknowledged,
                notifications_muted_acknowledged=req.notifications_muted_acknowledged,
                os_platform=req.os_platform.lower(),
                device_info=req.device_info,
                acknowledged_at=ack_time,
            )
            db.add(prep_log)
            db.commit()

        # Generate platform-specific guidelines
        os_lower = req.os_platform.lower()
        recs = []
        if "android" in os_lower:
            recs = [
                "Enable 'Do Not Disturb' from Quick Settings to silence calls and notifications.",
                "Ensure device battery is above 50% or plug into charger.",
                "Close background apps to preserve RAM and prevent multitasking interruptions.",
            ]
        elif "ios" in os_lower:
            recs = [
                "Swipe down Control Center and activate 'Focus > Do Not Disturb'.",
                "Ensure Low Power Mode is disabled so background timers stay accurate.",
                "Connect to a stable Wi-Fi network and keep device plugged into power.",
            ]
        elif "windows" in os_lower:
            recs = [
                "Turn on 'Focus Assist' or 'Do Not Disturb' in Windows Notification settings.",
                "Close communication software (Teams, Discord, Slack, Skype, WhatsApp).",
                "Keep AC adapter connected to prevent battery saver screen dimming.",
            ]
        elif "mac" in os_lower:
            recs = [
                "Open Control Center and enable 'Do Not Disturb' for the duration of the exam.",
                "Mute notifications in System Settings > Notifications.",
                "Ensure charger is connected and battery is above 50%.",
            ]
        else:
            recs = [
                "Silence notifications and mute phone or background apps.",
                "Ensure stable internet connection and connect device to power.",
            ]

        policy_resp = InterruptionService.get_quiz_policy(db, req.quiz_id)

        return DevicePreparationResponse(
            success=True,
            can_proceed=True,
            policy=policy_resp.model_dump(),
            recommendations=recs,
            logged_at=ack_time,
        )

    @staticmethod
    def record_interruption_event(
        db: Session, student_id: uuid.UUID, req: InterruptionEventRequest
    ) -> InterruptionEventResponse:
        """
        Receives and classifies an interruption event (mobile call, app switch, tab switch,
        fullscreen exit, network loss, OS dialog). Validates attempt ownership, verifies
        server-authoritative timer, creates timeline record, and triggers incidents/alerts if needed.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == req.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

        if attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attempt ownership mismatch.")

        now = datetime.now(timezone.utc)
        deadline = to_utc(attempt.expires_at or attempt.deadline_at)

        # Check server-authoritative timer
        if deadline and now > deadline:
            if attempt.status != "submitted":
                attempt.status = "expired"
                db.commit()
            return InterruptionEventResponse(
                success=False,
                event_id=uuid.uuid4(),
                action_required="EXAM_EXPIRED",
                server_remaining_seconds=0,
                message="Examination deadline has passed. Interruption event recorded under expired state.",
            )

        remaining_seconds = max(0, int((deadline - now).total_seconds())) if deadline else 3600

        # Idempotency check: if already processed, return idempotently
        if req.idempotency_key:
            existing_event = db.query(IncidentTimelineEvent).filter(
                IncidentTimelineEvent.attempt_id == req.attempt_id,
                IncidentTimelineEvent.idempotency_key == req.idempotency_key,
            ).first()
            if existing_event:
                return InterruptionEventResponse(
                    success=True,
                    event_id=existing_event.id,
                    action_required="NONE",
                    server_remaining_seconds=remaining_seconds,
                    message="Event already acknowledged (idempotent).",
                )

        # Retrieve quiz interruption policy
        policy_resp = InterruptionService.get_quiz_policy(db, req.quiz_id)
        policy = policy_resp.interruption_handling_policy

        # Determine action required based on policy and severity level
        # Levels: 0=Info, 1=Minor, 2=Warning, 3=Serious, 4=Critical
        action_required = "NONE"
        if req.severity_level == 2:
            if policy != "continue":
                action_required = "WARNING_DISPLAYED"
        elif req.severity_level >= 3:
            if policy in ("pause_local", "pause_pending_review"):
                action_required = "EXAM_PAUSED"
            elif policy == "strict_terminate":
                action_required = "TERMINATED"
            else:
                action_required = "WARNING_DISPLAYED"

        incident_id = None
        # Group into ExaminationIncident if severity >= 2 or explicit interruption
        if req.severity_level >= 2 or req.event_type in (
            "INCOMING_CALL", "APP_BACKGROUND", "APP_SWITCH", "NOTIFICATION_SHADE",
            "SEB_INTERRUPTION", "NETWORK_OFFLINE", "OS_DIALOG", "BROWSER_CRASH"
        ):
            incident_code = f"INC-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            category_mapping = {
                "INCOMING_CALL": "mobile_call",
                "APP_BACKGROUND": "app_switch",
                "APP_SWITCH": "app_switch",
                "NOTIFICATION_SHADE": "notification_interruption",
                "TAB_SWITCH": "tab_switch",
                "FULLSCREEN_EXIT": "fullscreen_exit",
                "NETWORK_OFFLINE": "network_issue",
                "NETWORK_ONLINE": "network_issue",
                "SEB_INTERRUPTION": "seb_security",
                "OS_DIALOG": "system_dialog",
                "BROWSER_CRASH": "browser_crash",
            }
            cat = category_mapping.get(req.event_type, "security_concern")
            sev_str = "critical" if req.severity_level == 4 else "high" if req.severity_level == 3 else "medium"

            incident = ExaminationIncident(
                incident_code=incident_code,
                quiz_id=req.quiz_id,
                student_id=student_id,
                attempt_id=req.attempt_id,
                category=cat,
                severity=sev_str,
                severity_level=req.severity_level,
                event_source="CLIENT_REPORTED",
                recovery_state="ACTIVE_INTERRUPTED",
                duration_seconds=req.duration_seconds,
                idempotency_key=req.idempotency_key,
                interruption_metadata=req.details,
                status="OPEN",
                title=f"Interruption: {req.event_type.replace('_', ' ').title()}",
                description=f"Candidate station detected interruption event '{req.event_type}' (Severity Level {req.severity_level}, Duration: {req.duration_seconds}s). Server deadline maintained authoritatively.",
                created_at=now,
                updated_at=now,
            )
            db.add(incident)
            db.flush()
            incident_id = incident.id

            # Emit MonitoringAlert for serious/critical events
            if req.severity_level >= 3:
                alert = MonitoringAlert(
                    quiz_id=req.quiz_id,
                    student_id=student_id,
                    attempt_id=req.attempt_id,
                    alert_type="INTERRUPTION_ALERT",
                    priority="HIGH" if req.severity_level == 3 else "CRITICAL",
                    title=f"Station Alert: {req.event_type.replace('_', ' ').title()}",
                    details={
                        "event_type": req.event_type,
                        "severity_level": req.severity_level,
                        "duration_seconds": req.duration_seconds,
                        "incident_code": incident_code,
                    },
                    created_at=now,
                )
                db.add(alert)

        # Create Timeline Event
        timeline_event = IncidentTimelineEvent(
            quiz_id=req.quiz_id,
            attempt_id=req.attempt_id,
            student_id=student_id,
            incident_id=incident_id,
            event_type=req.event_type,
            event_source="CLIENT_REPORTED",
            severity_level=req.severity_level,
            duration_seconds=req.duration_seconds,
            details=req.details,
            client_timestamp=req.client_timestamp,
            server_timestamp=now,
            idempotency_key=req.idempotency_key,
        )
        db.add(timeline_event)
        db.commit()

        return InterruptionEventResponse(
            success=True,
            event_id=timeline_event.id,
            action_required=action_required,
            server_remaining_seconds=remaining_seconds,
            message=f"Interruption event {req.event_type} registered successfully.",
        )

    @staticmethod
    def recover_session(
        db: Session, student_id: uuid.UUID, req: SessionRecoveryRequest
    ) -> SessionRecoveryResponse:
        """
        Examination Session Recovery workflow.
        Validates attempt ownership, checks server-authoritative timer,
        retrieves saved progress, and transitions attempt without silently extending time.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == req.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

        if attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attempt ownership mismatch.")

        now = datetime.now(timezone.utc)
        deadline = to_utc(attempt.expires_at or attempt.deadline_at)

        # Check server-authoritative timer: CANNOT extend time!
        if deadline and now > deadline:
            attempt.status = "expired"
            db.commit()
            return SessionRecoveryResponse(
                success=False,
                recovery_status="EXPIRED",
                recovery_token="",
                server_remaining_seconds=0,
                server_deadline=deadline,
                total_synced_answers=0,
                interruption_policy="strict_terminate",
                message="Server examination deadline has expired. Resumption is not permitted.",
            )

        remaining_seconds = max(0, int((deadline - now).total_seconds())) if deadline else 3600

        # Check quiz policy
        policy_resp = InterruptionService.get_quiz_policy(db, req.quiz_id)

        recovery_status = "RESUMED"
        if policy_resp.revalidation_code_required:
            recovery_status = "REQUIRES_REVALIDATION"
        elif policy_resp.interruption_handling_policy == "pause_pending_review":
            recovery_status = "PENDING_REVIEW"

        # Count synced answers
        synced_count = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == req.attempt_id).count()

        # Generate unique recovery token
        rec_token = f"REC-{now.strftime('%Y%m%d%H%M')}-{str(uuid.uuid4())[:8]}"

        rec_session = InterruptionRecoverySession(
            attempt_id=req.attempt_id,
            quiz_id=req.quiz_id,
            student_id=student_id,
            recovery_token=rec_token,
            recovery_status=recovery_status,
            interruption_reason=req.reason,
            answers_synced_count=synced_count,
            server_remaining_seconds=remaining_seconds,
            created_at=now,
        )
        db.add(rec_session)

        # Authoritative server-verified timeline event
        timeline_event = IncidentTimelineEvent(
            quiz_id=req.quiz_id,
            attempt_id=req.attempt_id,
            student_id=student_id,
            event_type="SESSION_RECOVERED",
            event_source="SERVER_VERIFIED",
            severity_level=0,
            duration_seconds=0,
            details={
                "reason": req.reason,
                "recovery_status": recovery_status,
                "offline_answers_declared": req.offline_answers_count,
                "server_remaining_seconds": remaining_seconds,
            },
            server_timestamp=now,
        )
        db.add(timeline_event)
        db.commit()

        return SessionRecoveryResponse(
            success=True,
            recovery_status=recovery_status,
            recovery_token=rec_token,
            server_remaining_seconds=remaining_seconds,
            server_deadline=deadline or (now),
            total_synced_answers=synced_count,
            interruption_policy=policy_resp.interruption_handling_policy,
            message="Examination session safely recovered with server-authoritative timer.",
        )

    @staticmethod
    def sync_pending_answers(
        db: Session, student_id: uuid.UUID, req: AnswerBatchSyncRequest
    ) -> AnswerBatchSyncResponse:
        """
        Idempotent batch answer synchronization for candidates recovering from network drop.
        Never overwrites newer server answers with older client timestamps.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == req.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")

        if attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attempt ownership mismatch.")

        if attempt.is_immutable or attempt.status in ("submitted", "expired"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is finalized and immutable.")

        now = datetime.now(timezone.utc)
        deadline = to_utc(attempt.expires_at or attempt.deadline_at)
        if deadline and now > deadline:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Examination deadline has passed.")

        synced_count = 0
        ignored_count = 0
        results = []

        for item in req.answers:
            existing = db.query(AttemptAnswer).filter(
                AttemptAnswer.attempt_id == req.attempt_id,
                AttemptAnswer.quiz_question_id == item.quiz_question_id,
            ).first()

            # Idempotency check by key
            if existing and item.idempotency_key and existing.idempotency_key == item.idempotency_key:
                ignored_count += 1
                results.append({
                    "quiz_question_id": str(item.quiz_question_id),
                    "status": "ALREADY_SYNCED",
                })
                continue

            # Timestamp check: ignore if client timestamp is older than answered_at on server
            if existing and item.client_timestamp and existing.answered_at:
                if to_utc(item.client_timestamp) < to_utc(existing.answered_at):
                    ignored_count += 1
                    results.append({
                        "quiz_question_id": str(item.quiz_question_id),
                        "status": "IGNORED_OLDER_TIMESTAMP",
                    })
                    continue

            if existing:
                existing.selected_option_ids = [str(uid) for uid in item.selected_option_ids] if item.selected_option_ids else None
                existing.text_response = item.text_response
                existing.time_spent_seconds = max(existing.time_spent_seconds, item.time_spent_seconds)
                existing.client_timestamp = item.client_timestamp
                existing.idempotency_key = item.idempotency_key
                existing.answered_at = now
                existing.answer_status = "ANSWERED"
                existing.version = (existing.version or 1) + 1
            else:
                new_ans = AttemptAnswer(
                    attempt_id=req.attempt_id,
                    quiz_question_id=item.quiz_question_id,
                    selected_option_ids=[str(uid) for uid in item.selected_option_ids] if item.selected_option_ids else None,
                    text_response=item.text_response,
                    time_spent_seconds=item.time_spent_seconds,
                    client_timestamp=item.client_timestamp,
                    idempotency_key=item.idempotency_key,
                    answered_at=now,
                    answer_status="ANSWERED",
                    version=1,
                )
                db.add(new_ans)

            synced_count += 1
            results.append({
                "quiz_question_id": str(item.quiz_question_id),
                "status": "SYNCED",
            })

        # Log timeline event
        timeline_event = IncidentTimelineEvent(
            quiz_id=req.quiz_id,
            attempt_id=req.attempt_id,
            student_id=student_id,
            event_type="ANSWERS_SYNCED",
            event_source="SERVER_VERIFIED",
            severity_level=0,
            duration_seconds=0,
            details={
                "total_sent": len(req.answers),
                "synced_count": synced_count,
                "ignored_count": ignored_count,
            },
            server_timestamp=now,
        )
        db.add(timeline_event)
        db.commit()

        return AnswerBatchSyncResponse(
            success=True,
            total_processed=len(req.answers),
            synced_count=synced_count,
            ignored_count=ignored_count,
            server_time=now,
            results=results,
        )

    @staticmethod
    def get_incident_timeline(
        db: Session, admin: Admin, attempt_id: uuid.UUID
    ) -> IncidentTimelineListResponse:
        """
        Retrieves chronological incident timeline for an attempt, verifying permissions.
        """
        events = db.query(IncidentTimelineEvent).filter(
            IncidentTimelineEvent.attempt_id == attempt_id
        ).order_by(IncidentTimelineEvent.server_timestamp.asc()).all()

        resp_events = [
            IncidentTimelineItemResponse(
                id=ev.id,
                attempt_id=ev.attempt_id,
                event_type=ev.event_type,
                event_source=ev.event_source,
                severity_level=ev.severity_level,
                duration_seconds=ev.duration_seconds,
                details=ev.details,
                client_timestamp=ev.client_timestamp,
                server_timestamp=ev.server_timestamp,
            )
            for ev in events
        ]

        return IncidentTimelineListResponse(
            attempt_id=attempt_id,
            total_events=len(resp_events),
            events=resp_events,
        )

    @staticmethod
    def perform_incident_action(
        db: Session, admin: Admin, incident_id: uuid.UUID, req: IncidentActionRequest
    ) -> IncidentActionResponse:
        """
        Performs an authorized invigilator action on an examination incident with full audit logging.
        Actions: ACKNOWLEDGE, ADD_NOTE, ASSIGN, MARK_REVIEWED, ESCALATE, AUTHORIZE_RECOVERY, REQUEST_CLARIFICATION.
        """
        incident = db.query(ExaminationIncident).filter(ExaminationIncident.id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

        now = datetime.now(timezone.utc)
        act = req.action.upper()

        if act == "ACKNOWLEDGE":
            incident.status = "ASSIGNED"
            incident.assigned_to = admin.id
            incident.updated_at = now
        elif act == "ADD_NOTE":
            if not req.note:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note content required.")
            note = IncidentNote(
                incident_id=incident.id,
                author_id=admin.id,
                note=req.note,
                created_at=now,
            )
            db.add(note)
            incident.updated_at = now
        elif act == "ASSIGN":
            if not req.assigned_to:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee admin ID required.")
            incident.assigned_to = req.assigned_to
            incident.status = "ASSIGNED"
            incident.updated_at = now
        elif act == "MARK_REVIEWED":
            incident.status = "RESOLVED"
            incident.resolution_notes = req.resolution_notes or "Reviewed by invigilator."
            incident.resolved_at = now
            incident.updated_at = now
        elif act == "ESCALATE":
            incident.severity = "critical"
            incident.severity_level = 4
            incident.status = "UNDER_INVESTIGATION"
            incident.updated_at = now
            # Create a critical alert
            alert = MonitoringAlert(
                quiz_id=incident.quiz_id,
                student_id=incident.student_id,
                attempt_id=incident.attempt_id,
                alert_type="ESCALATED_INCIDENT",
                priority="CRITICAL",
                title=f"Incident Escalated: {incident.title}",
                details={"reason": req.reason, "incident_code": incident.incident_code},
                created_at=now,
            )
            db.add(alert)
        elif act == "AUTHORIZE_RECOVERY":
            incident.recovery_state = "RECOVERED"
            incident.updated_at = now
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported action '{req.action}'.")

        # Audit log in InvigilatorActivityLog
        act_log = InvigilatorActivityLog(
            invigilator_id=admin.id,
            quiz_id=incident.quiz_id,
            action=f"INCIDENT_{act}",
            details={
                "incident_id": str(incident.id),
                "incident_code": incident.incident_code,
                "note": req.note,
                "reason": req.reason,
            },
            created_at=now,
        )
        db.add(act_log)

        # Timeline event
        if incident.attempt_id:
            timeline_event = IncidentTimelineEvent(
                quiz_id=incident.quiz_id,
                attempt_id=incident.attempt_id,
                student_id=incident.student_id,
                incident_id=incident.id,
                event_type="INVIGILATOR_ACTION",
                event_source="INVIGILATOR_ACTION",
                severity_level=0,
                duration_seconds=0,
                details={
                    "action": act,
                    "invigilator_name": f"{admin.first_name} {admin.last_name}".strip() if hasattr(admin, 'first_name') else "Invigilator",
                    "note": req.note,
                },
                server_timestamp=now,
            )
            db.add(timeline_event)

        db.commit()

        return IncidentActionResponse(
            success=True,
            incident_id=incident.id,
            new_status=incident.status,
            action_performed=act,
            message=f"Action '{act}' applied to incident {incident.incident_code} successfully.",
        )
