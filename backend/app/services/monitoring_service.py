import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, and_
from fastapi import HTTPException, status

from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
    AttemptEvent,
    AttemptSession,
)
from backend.app.models.security_audit import (
    SecurityEvent,
    SecurityAlert,
    BrowserCompatibilityRecord,
    WatermarkSession,
    CaptureCapabilityReport,
)
from backend.app.models.academic import Subject, Programme, Semester
from backend.app.models.monitoring import (
    InvigilatorAssignment,
    InvigilatorActivityLog,
    ExaminationAnnouncement,
    AnnouncementAcknowledgement,
    ExaminationIncident,
    IncidentNote,
    MonitoringAlert,
    MonitoringIntervention,
    ExaminationExtensionHistory,
)
from backend.app.models.proctoring import ProctoringSession
from backend.app.schemas.monitoring import (
    LiveMonitoringOverviewResponse,
    LiveExaminationItem,
    LiveExaminationsListResponse,
    ExaminationMonitoringRoomResponse,
    ParticipantMonitoringItem,
    ParticipantMonitoringListResponse,
    ParticipantDetailMonitoringResponse,
    InvigilatorSummary,
    InvigilatorAssignmentResponse,
    InvigilatorListResponse,
    ExaminationAnnouncementResponse,
    AnnouncementListResponse,
    ExaminationIncidentResponse,
    IncidentListResponse,
    IncidentNoteResponse,
    MonitoringAlertItem,
    MonitoringInterventionResponse,
    InterventionListResponse,
    AttemptEventItem,
    QuestionProgressSummary,
    IncidentSummaryItem,
    ExtensionHistoryItem,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_super_admin(admin: Admin) -> bool:
    if getattr(admin, "is_super_admin", False):
        return True
    for r in getattr(admin, "roles", []):
        r_name = getattr(r, "role_name", getattr(r, "name", ""))
        if "super" in r_name.lower():
            return True
    role = getattr(admin, "role", None)
    if isinstance(role, str) and "super" in role.lower():
        return True
    if hasattr(role, "name") and "super" in role.name.lower():
        return True
    return False


class LiveMonitoringService:

    # -------------------------------------------------------------------------
    # RBAC Permission Verification
    # -------------------------------------------------------------------------
    @staticmethod
    def check_monitoring_access(db: Session, admin: Admin, quiz_id: uuid.UUID) -> Tuple[bool, bool, List[str]]:
        """
        Verify if the admin/invigilator has access to monitor the quiz.
        Returns: (has_access, is_lead, permissions)
        """
        if is_super_admin(admin):
            return True, True, [
                "view_progress", "send_announcements", "report_incidents",
                "request_intervention", "manage_invigilators", "extend_time",
                "terminate_attempt", "cancel_exam"
            ]

        # Check if Admin owns the quiz
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        if quiz.created_by == admin.id:
            return True, True, [
                "view_progress", "send_announcements", "report_incidents",
                "request_intervention", "manage_invigilators", "extend_time",
                "terminate_attempt", "cancel_exam"
            ]

        # Check if Admin is assigned to the quiz via AdminQuizAssignment
        assignment = db.query(AdminQuizAssignment).filter(
            AdminQuizAssignment.quiz_id == quiz_id,
            AdminQuizAssignment.admin_id == admin.id,
        ).first()
        if assignment:
            return True, True, [
                "view_progress", "send_announcements", "report_incidents",
                "request_intervention", "manage_invigilators", "extend_time",
                "terminate_attempt", "cancel_exam"
            ]

        # Check if assigned as invigilator
        invig = db.query(InvigilatorAssignment).filter(
            InvigilatorAssignment.quiz_id == quiz_id,
            InvigilatorAssignment.invigilator_id == admin.id,
            InvigilatorAssignment.status == "active",
        ).first()

        if invig:
            perms = invig.permissions or ["view_progress", "send_announcements", "report_incidents"]
            return True, invig.is_lead, perms

        raise HTTPException(status_code=403, detail="You do not have invigilation or monitoring access to this examination")

    @staticmethod
    def check_intervention_permission(db: Session, admin: Admin, quiz_id: uuid.UUID) -> bool:
        """
        Intervention controls (time extension, exam cancel, terminate attempt)
        require Super Admin, Quiz Owner, or Lead Invigilator.
        """
        has_access, is_lead, perms = LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)
        if is_super_admin(admin):
            return True

        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if quiz and quiz.created_by == admin.id:
            return True

        if is_lead or "extend_time" in perms or "request_intervention" in perms:
            return True

        raise HTTPException(
            status_code=403,
            detail="Emergency intervention actions require Super Admin, Quiz Creator, or Lead Invigilator privileges"
        )

    # -------------------------------------------------------------------------
    # 1. Live Monitoring Overview
    # -------------------------------------------------------------------------
    @staticmethod
    def get_live_overview(db: Session, admin: Admin) -> LiveMonitoringOverviewResponse:
        now = datetime.now(timezone.utc)
        is_super = is_super_admin(admin)

        # Base quizzes query
        quizzes_query = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.configuration),
        ).filter(Quiz.status.in_(["published", "scheduled"]))

        if not is_super:
            assigned_quiz_ids = [
                r[0] for r in db.query(AdminQuizAssignment.quiz_id).filter(AdminQuizAssignment.admin_id == admin.id).all()
            ]
            invig_quiz_ids = [
                r[0] for r in db.query(InvigilatorAssignment.quiz_id).filter(
                    InvigilatorAssignment.invigilator_id == admin.id,
                    InvigilatorAssignment.status == "active"
                ).all()
            ]
            quizzes_query = quizzes_query.filter(
                or_(
                    Quiz.created_by == admin.id,
                    Quiz.id.in_(assigned_quiz_ids),
                    Quiz.id.in_(invig_quiz_ids),
                )
            )

        quizzes = quizzes_query.all()
        quiz_ids = [q.id for q in quizzes]

        if not quiz_ids:
            return LiveMonitoringOverviewResponse(
                active_examinations_count=0,
                total_eligible_participants=0,
                active_participants=0,
                disconnected_participants=0,
                sync_issue_participants=0,
                submitted_participants=0,
                pending_participants=0,
                critical_security_alerts=0,
                examinations_nearing_deadline=0,
                completed_examinations_today=0,
                recent_alerts=[],
                active_examinations=[],
            )

        # Total enrolled participants
        total_eligible = db.query(func.count(QuizParticipant.id)).filter(
            QuizParticipant.quiz_id.in_(quiz_ids),
            QuizParticipant.status.in_(["enrolled", "approved", "active"]),
        ).scalar() or 0

        # Attempts in progress
        in_progress_attempts = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id.in_(quiz_ids),
            ExaminationAttempt.status == "in_progress",
        ).all()
        active_participants = len(in_progress_attempts)

        # Disconnected participants (heartbeat > 60s ago or missing)
        disconnected_participants = 0
        sync_issues = 0
        for att in in_progress_attempts:
            hb = _ensure_utc(att.last_heartbeat_at)
            if hb is None:
                st = _ensure_utc(att.started_at)
                if st and (now - st).total_seconds() > 60:
                    disconnected_participants += 1
            elif (now - hb).total_seconds() > 60:
                disconnected_participants += 1

        # Submitted count
        submitted_participants = db.query(func.count(ExaminationAttempt.id)).filter(
            ExaminationAttempt.quiz_id.in_(quiz_ids),
            ExaminationAttempt.status.in_(["submitted", "evaluated"]),
        ).scalar() or 0

        pending_participants = max(0, total_eligible - (active_participants + submitted_participants))

        # Critical security alerts
        critical_alerts_count = db.query(func.count(MonitoringAlert.id)).filter(
            MonitoringAlert.quiz_id.in_(quiz_ids),
            MonitoringAlert.priority.in_(["CRITICAL", "HIGH"]),
            MonitoringAlert.is_resolved == False,
        ).scalar() or 0

        # Examinations nearing deadline (within 15 minutes of quiz end_time)
        nearing_deadline_count = 0
        for q in quizzes:
            cfg = q.configuration
            if cfg and cfg.end_time:
                end_t = _ensure_utc(cfg.end_time)
                if end_t and now < end_t <= now + timedelta(minutes=15):
                    nearing_deadline_count += 1

        # Completed exams today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today_count = db.query(func.count(Quiz.id)).filter(
            Quiz.id.in_(quiz_ids),
            Quiz.status == "completed",
            Quiz.updated_at >= today_start,
        ).scalar() or 0

        # Recent alerts
        alerts_records = db.query(MonitoringAlert).options(
            joinedload(MonitoringAlert.quiz),
            joinedload(MonitoringAlert.student),
        ).filter(
            MonitoringAlert.quiz_id.in_(quiz_ids)
        ).order_by(desc(MonitoringAlert.created_at)).limit(10).all()

        recent_alerts = []
        for a in alerts_records:
            st_name = None
            if a.student:
                st_name = a.student.full_name or a.student.email
            recent_alerts.append(MonitoringAlertItem(
                id=a.id,
                quiz_id=a.quiz_id,
                quiz_title=a.quiz.title if a.quiz else "Examination",
                student_id=a.student_id,
                student_name=st_name,
                attempt_id=a.attempt_id,
                alert_type=a.alert_type,
                priority=a.priority,
                title=a.title,
                details=a.details,
                is_acknowledged=a.is_acknowledged,
                is_resolved=a.is_resolved,
                created_at=_ensure_utc(a.created_at),
            ))

        # Active examinations items
        active_exam_items = LiveMonitoringService._build_exam_items(db, quizzes[:10])

        return LiveMonitoringOverviewResponse(
            active_examinations_count=len(quizzes),
            total_eligible_participants=total_eligible,
            active_participants=active_participants,
            disconnected_participants=disconnected_participants,
            sync_issue_participants=sync_issues,
            submitted_participants=submitted_participants,
            pending_participants=pending_participants,
            critical_security_alerts=critical_alerts_count,
            examinations_nearing_deadline=nearing_deadline_count,
            completed_examinations_today=completed_today_count,
            recent_alerts=recent_alerts,
            active_examinations=active_exam_items,
        )

    # -------------------------------------------------------------------------
    # 2. Active Examinations List & Filters
    # -------------------------------------------------------------------------
    @staticmethod
    def list_active_examinations(
        db: Session,
        admin: Admin,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> LiveExaminationsListResponse:
        is_super = is_super_admin(admin)

        query = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.configuration),
        )

        if not is_super:
            assigned_quiz_ids = [
                r[0] for r in db.query(AdminQuizAssignment.quiz_id).filter(AdminQuizAssignment.admin_id == admin.id).all()
            ]
            invig_quiz_ids = [
                r[0] for r in db.query(InvigilatorAssignment.quiz_id).filter(
                    InvigilatorAssignment.invigilator_id == admin.id,
                    InvigilatorAssignment.status == "active"
                ).all()
            ]
            query = query.filter(
                or_(
                    Quiz.created_by == admin.id,
                    Quiz.id.in_(assigned_quiz_ids),
                    Quiz.id.in_(invig_quiz_ids),
                )
            )

        if status_filter and status_filter.lower() != "all":
            query = query.filter(Quiz.status == status_filter.lower())
        else:
            query = query.filter(Quiz.status.in_(["published", "scheduled", "in_progress"]))

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(or_(Quiz.title.ilike(term), Quiz.description.ilike(term)))

        quizzes = query.order_by(desc(Quiz.updated_at)).all()
        items = LiveMonitoringService._build_exam_items(db, quizzes)

        return LiveExaminationsListResponse(total=len(items), items=items)

    @staticmethod
    def _build_exam_items(db: Session, quizzes: List[Quiz]) -> List[LiveExaminationItem]:
        now = datetime.now(timezone.utc)
        items = []

        for q in quizzes:
            cfg = q.configuration
            start_t = _ensure_utc(cfg.start_time) if cfg else None
            end_t = _ensure_utc(cfg.end_time) if cfg else None
            dur = q.duration_minutes or (cfg.duration_minutes if cfg else 60)

            total_q = sum(len(sec.questions) for sec in q.sections) if hasattr(q, "sections") and q.sections else 0

            # Participant counts
            enrolled = db.query(func.count(QuizParticipant.id)).filter(
                QuizParticipant.quiz_id == q.id,
                QuizParticipant.status.in_(["enrolled", "approved", "active"]),
            ).scalar() or 0

            # Attempts breakdown
            attempts = db.query(ExaminationAttempt).filter(ExaminationAttempt.quiz_id == q.id).all()
            active_cnt = sum(1 for a in attempts if a.status == "in_progress")
            sub_cnt = sum(1 for a in attempts if a.status in ["submitted", "evaluated"])

            # Disconnected attempts
            disc_cnt = 0
            for a in attempts:
                if a.status == "in_progress":
                    hb = _ensure_utc(a.last_heartbeat_at)
                    if hb is None:
                        st = _ensure_utc(a.started_at)
                        if st and (now - st).total_seconds() > 60:
                            disc_cnt += 1
                    elif (now - hb).total_seconds() > 60:
                        disc_cnt += 1

            # Alerts count
            alerts_cnt = db.query(func.count(MonitoringAlert.id)).filter(
                MonitoringAlert.quiz_id == q.id,
                MonitoringAlert.is_resolved == False,
            ).scalar() or 0

            # Invigilators
            invig_assignments = db.query(InvigilatorAssignment).options(
                joinedload(InvigilatorAssignment.invigilator)
            ).filter(
                InvigilatorAssignment.quiz_id == q.id,
                InvigilatorAssignment.status == "active",
            ).all()

            lead_name = None
            for inv in invig_assignments:
                if inv.is_lead and inv.invigilator:
                    lead_name = inv.invigilator.full_name or inv.invigilator.email
                    break

            items.append(LiveExaminationItem(
                id=q.id,
                title=q.title,
                subject_name=q.subject.subject_name if q.subject else None,
                status=q.status,
                start_time=start_t,
                end_time=end_t,
                duration_minutes=dur,
                total_marks=float(q.total_marks or 0.0),
                total_questions=total_q,
                enrolled_count=enrolled,
                active_count=active_cnt,
                submitted_count=sub_cnt,
                disconnected_count=disc_cnt,
                sync_issue_count=0,
                security_alert_count=alerts_cnt,
                lead_invigilator_name=lead_name,
                invigilators_count=len(invig_assignments),
                created_at=_ensure_utc(q.created_at),
            ))

        return items

    # -------------------------------------------------------------------------
    # 3. Individual Examination Monitoring Room
    # -------------------------------------------------------------------------
    @staticmethod
    def get_examination_room(db: Session, admin: Admin, quiz_id: uuid.UUID) -> ExaminationMonitoringRoomResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        quiz = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.programme),
            joinedload(Quiz.semester),
            joinedload(Quiz.configuration),
            joinedload(Quiz.sections),
        ).filter(Quiz.id == quiz_id).first()

        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        cfg = quiz.configuration
        dur = quiz.duration_minutes or (cfg.duration_minutes if cfg else 60)
        start_t = _ensure_utc(cfg.start_time) if cfg else None
        end_t = _ensure_utc(cfg.end_time) if cfg else None
        total_q = sum(len(s.questions) for s in quiz.sections) if quiz.sections else 0

        # Counts
        enrolled = db.query(func.count(QuizParticipant.id)).filter(
            QuizParticipant.quiz_id == quiz.id,
            QuizParticipant.status.in_(["enrolled", "approved", "active"]),
        ).scalar() or 0

        attempts = db.query(ExaminationAttempt).filter(ExaminationAttempt.quiz_id == quiz.id).all()
        active_now = sum(1 for a in attempts if a.status == "in_progress")
        submitted = sum(1 for a in attempts if a.status in ["submitted", "evaluated"])

        disconnected = 0
        for a in attempts:
            if a.status == "in_progress":
                hb = _ensure_utc(a.last_heartbeat_at)
                if hb is None:
                    st = _ensure_utc(a.started_at)
                    if st and (now - st).total_seconds() > 60:
                        disconnected += 1
                elif (now - hb).total_seconds() > 60:
                    disconnected += 1

        unresolved_incidents = db.query(func.count(ExaminationIncident.id)).filter(
            ExaminationIncident.quiz_id == quiz.id,
            ExaminationIncident.status.in_(["OPEN", "ASSIGNED", "UNDER_INVESTIGATION"]),
        ).scalar() or 0

        crit_alerts = db.query(func.count(MonitoringAlert.id)).filter(
            MonitoringAlert.quiz_id == quiz.id,
            MonitoringAlert.priority.in_(["CRITICAL", "HIGH"]),
            MonitoringAlert.is_resolved == False,
        ).scalar() or 0

        # Invigilators
        invig_assignments = db.query(InvigilatorAssignment).options(
            joinedload(InvigilatorAssignment.invigilator)
        ).filter(
            InvigilatorAssignment.quiz_id == quiz.id,
            InvigilatorAssignment.status == "active",
        ).all()

        invigilators_list = []
        for inv in invig_assignments:
            if inv.invigilator:
                invigilators_list.append(InvigilatorSummary(
                    id=inv.id,
                    invigilator_id=inv.invigilator_id,
                    name=inv.invigilator.full_name or inv.invigilator.email,
                    email=inv.invigilator.email,
                    is_lead=inv.is_lead,
                    permissions=inv.permissions or [],
                    status=inv.status,
                    assigned_at=_ensure_utc(inv.assigned_at),
                ))

        # Time series / timeline summary
        timeline_summary = {
            "enrolled": enrolled,
            "active_now": active_now,
            "completed": submitted,
            "disconnected": disconnected,
            "server_time": now.isoformat(),
        }

        # Subject / Programme / Semester names
        subj_name = quiz.subject.subject_name if quiz.subject else None
        prog_name = quiz.programme.name if quiz.programme else None
        sem_name = getattr(quiz.semester, "semester_name", None) if quiz.semester else None

        return ExaminationMonitoringRoomResponse(
            id=quiz.id,
            title=quiz.title,
            subject_name=subj_name,
            programme_name=prog_name,
            semester_name=sem_name,
            status=quiz.status,
            start_time=start_t,
            end_time=end_t,
            duration_minutes=dur,
            total_marks=float(quiz.total_marks or 0.0),
            total_questions=total_q,
            enrolled_participants=enrolled,
            active_now=active_now,
            completed_submissions=submitted,
            disconnected_count=disconnected,
            sync_pending_count=0,
            unresolved_incidents_count=unresolved_incidents,
            critical_alerts_count=crit_alerts,
            invigilators=invigilators_list,
            timeline_summary=timeline_summary,
        )

    # -------------------------------------------------------------------------
    # 4. Live Participant Monitoring Table
    # -------------------------------------------------------------------------
    @staticmethod
    def list_room_participants(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        connection_filter: Optional[str] = None,
    ) -> ParticipantMonitoringListResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        quiz = db.query(Quiz).options(joinedload(Quiz.sections)).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        total_q = sum(len(s.questions) for s in quiz.sections) if quiz.sections else 1

        # Fetch enrolled participants with student profiles
        participants = db.query(QuizParticipant).options(
            joinedload(QuizParticipant.student).joinedload(Student.profile)
        ).filter(
            QuizParticipant.quiz_id == quiz_id,
            QuizParticipant.status.in_(["enrolled", "approved", "active"]),
        ).all()

        student_ids = [p.student_id for p in participants if p.student_id]

        # Fetch all attempts for these students
        attempts = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id == quiz_id,
            ExaminationAttempt.student_id.in_(student_ids),
        ).all()
        attempt_by_student = {a.student_id: a for a in attempts}

        # Fetch answer counts per attempt
        attempt_ids = [a.id for a in attempts]
        answers_data = {}
        if attempt_ids:
            ans_counts = db.query(
                AttemptAnswer.attempt_id,
                func.count(AttemptAnswer.id).label("cnt")
            ).filter(
                AttemptAnswer.attempt_id.in_(attempt_ids)
            ).group_by(AttemptAnswer.attempt_id).all()
            for row in ans_counts:
                answers_data[row[0]] = {
                    "answered": row[1] or 0,
                    "review": 0,
                }

        # Fetch security events & browser lockdown telemetry per attempt
        security_counts = {}
        focus_counts = {}
        fullscreen_counts = {}
        compat_statuses = {}
        inc_counts = {}
        review_statuses = {}

        if attempt_ids:
            sec_rows = db.query(
                SecurityEvent.attempt_id,
                func.count(SecurityEvent.id)
            ).filter(
                SecurityEvent.attempt_id.in_(attempt_ids)
            ).group_by(SecurityEvent.attempt_id).all()
            for r in sec_rows:
                security_counts[r[0]] = r[1] or 0

            focus_rows = db.query(
                SecurityEvent.attempt_id,
                func.count(SecurityEvent.id)
            ).filter(
                SecurityEvent.attempt_id.in_(attempt_ids),
                SecurityEvent.event_name.in_(["WINDOW_FOCUS_LOST", "WINDOW_BLUR", "PAGE_HIDDEN", "TAB_HIDDEN", "TAB_SWITCH"])
            ).group_by(SecurityEvent.attempt_id).all()
            for r in focus_rows:
                focus_counts[r[0]] = r[1] or 0

            fs_rows = db.query(
                SecurityEvent.attempt_id,
                func.count(SecurityEvent.id)
            ).filter(
                SecurityEvent.attempt_id.in_(attempt_ids),
                SecurityEvent.event_name == "FULLSCREEN_EXIT"
            ).group_by(SecurityEvent.attempt_id).all()
            for r in fs_rows:
                fullscreen_counts[r[0]] = r[1] or 0

            compat_rows = db.query(
                BrowserCompatibilityRecord.attempt_id,
                BrowserCompatibilityRecord.overall_status,
            ).filter(
                BrowserCompatibilityRecord.attempt_id.in_(attempt_ids)
            ).order_by(BrowserCompatibilityRecord.created_at.desc()).all()
            for r in compat_rows:
                if r[0] not in compat_statuses:
                    compat_statuses[r[0]] = r[1]

            inc_rows = db.query(
                ExaminationIncident.attempt_id,
                func.count(ExaminationIncident.id),
                func.max(ExaminationIncident.status)
            ).filter(
                ExaminationIncident.attempt_id.in_(attempt_ids)
            ).group_by(ExaminationIncident.attempt_id).all()
            for r in inc_rows:
                inc_counts[r[0]] = r[1] or 0
                review_statuses[r[0]] = r[2] or "NEW"

            # Phase 23 Watermark & Capture Telemetry
            wm_sessions: Dict[uuid.UUID, WatermarkSession] = {}
            capture_tiers: Dict[uuid.UUID, str] = {}
            capture_signal_counts: Dict[uuid.UUID, int] = {}
            latest_capture_signals: Dict[uuid.UUID, str] = {}

            wm_rows = db.query(WatermarkSession).filter(WatermarkSession.attempt_id.in_(attempt_ids)).all()
            for w in wm_rows:
                wm_sessions[w.attempt_id] = w

            # Phase 26 Advanced AI Proctoring Sessions
            proct_sessions: Dict[uuid.UUID, ProctoringSession] = {}
            p_rows = db.query(ProctoringSession).filter(ProctoringSession.attempt_id.in_(attempt_ids)).all()
            for p in p_rows:
                proct_sessions[p.attempt_id] = p

            cap_rows = db.query(
                CaptureCapabilityReport.attempt_id,
                CaptureCapabilityReport.detection_tier
            ).filter(CaptureCapabilityReport.attempt_id.in_(attempt_ids)).order_by(CaptureCapabilityReport.created_at.desc()).all()
            for c in cap_rows:
                if c[0] not in capture_tiers:
                    capture_tiers[c[0]] = c[1]

            sig_rows = db.query(
                SecurityEvent.attempt_id,
                func.count(SecurityEvent.id),
                func.max(SecurityEvent.event_name)
            ).filter(
                SecurityEvent.attempt_id.in_(attempt_ids),
                SecurityEvent.event_name.in_([
                    "SCREENSHOT_SIGNAL_DETECTED",
                    "SCREEN_RECORDING_SIGNAL_DETECTED",
                    "CAPTURE_API_ACTIVITY",
                    "PRINT_RESTRICTION_TRIGGERED",
                ])
            ).group_by(SecurityEvent.attempt_id).all()
            for s in sig_rows:
                capture_signal_counts[s[0]] = s[1] or 0
                latest_capture_signals[s[0]] = s[2] or "SCREENSHOT_SIGNAL_DETECTED"

        items: List[ParticipantMonitoringItem] = []

        for part in participants:
            stu = part.student
            if not stu:
                continue

            att = attempt_by_student.get(stu.id)

            # Liveness & Connection Status
            conn_status = "NOT_STARTED"
            sync_status = "NOT_STARTED"
            att_status = "NOT_STARTED"
            last_hb = None
            remaining_sec = 0
            time_spent = 0
            answered_cnt = 0
            review_cnt = 0
            progress_pct = 0.0
            deadline_at = None
            alerts_cnt = 0
            latest_sec_ev = None
            has_incident = False
            ip_addr = None
            browser_info = None

            if att:
                att_status = (att.status or "in_progress").upper()
                last_hb = _ensure_utc(att.last_heartbeat_at)
                deadline_at = _ensure_utc(att.deadline_at or att.expires_at)
                ip_addr = att.ip_address
                browser_info = att.user_agent

                # Time calculations
                time_spent = att.time_spent_seconds or 0
                if deadline_at:
                    remaining_sec = max(0, int((deadline_at - now).total_seconds()))

                # Connection State
                if att.status in ["submitted", "evaluated"]:
                    conn_status = "COMPLETED"
                    sync_status = "SYNCHRONIZED"
                else:
                    if last_hb is None:
                        st_time = _ensure_utc(att.started_at)
                        diff_s = (now - st_time).total_seconds() if st_time else 0
                    else:
                        diff_s = (now - last_hb).total_seconds()

                    if diff_s <= 30:
                        conn_status = "CONNECTED"
                        sync_status = "SYNCHRONIZED"
                    elif diff_s <= 60:
                        conn_status = "RECONNECTING"
                        sync_status = "SYNC_PENDING"
                    else:
                        conn_status = "DISCONNECTED"
                        sync_status = "SYNC_PENDING"

                # Answer counts
                a_info = answers_data.get(att.id, {"answered": 0, "review": 0})
                answered_cnt = a_info["answered"]
                review_cnt = a_info["review"]
                progress_pct = round((answered_cnt / max(1, total_q)) * 100, 1)

                alerts_cnt = security_counts.get(att.id, 0)
                if alerts_cnt > 0:
                    latest_sec_ev = "Security event recorded"

            reg_num = getattr(stu, "register_number", None)
            if not reg_num and stu.profile:
                reg_num = getattr(stu.profile, "student_identifier", getattr(stu.profile, "register_number", None))

            st_group = (
                part.registration_data.get("student_group")
                if (part.registration_data and isinstance(part.registration_data, dict))
                else None
            ) or (getattr(stu.profile, "student_group", None) if stu.profile else None)

            item = ParticipantMonitoringItem(
                student_id=stu.id,
                attempt_id=att.id if att else None,
                full_name=stu.full_name or stu.email,
                register_number=reg_num,
                email=stu.email,
                student_group=st_group,
                attempt_status=att_status,
                connection_status=conn_status,
                last_heartbeat_at=last_hb,
                sync_status=sync_status,
                last_sync_at=last_hb,
                current_question_index=None,
                current_section_name=None,
                answered_count=answered_cnt,
                marked_for_review_count=review_cnt,
                unanswered_count=max(0, total_q - answered_cnt),
                progress_percentage=progress_pct,
                time_spent_seconds=time_spent,
                remaining_seconds=remaining_sec,
                deadline_at=deadline_at,
                security_alerts_count=alerts_cnt,
                latest_security_event=latest_sec_ev,
                has_active_incident=has_incident,
                ip_address=ip_addr,
                browser=browser_info,
                browser_compatibility_status=compat_statuses.get(att.id, "PASSED") if att else "NOT_CHECKED",
                fullscreen_status="EXITED" if (att and fullscreen_counts.get(att.id, 0) > 0) else ("ACTIVE" if att else "NOT_REQUIRED"),
                focus_loss_count=focus_counts.get(att.id, 0) if att else 0,
                fullscreen_exit_count=fullscreen_counts.get(att.id, 0) if att else 0,
                incident_count=inc_counts.get(att.id, 0) if att else 0,
                review_status=review_statuses.get(att.id, "NONE") if att else "NONE",
                latest_incident=f"Incident recorded: {review_statuses.get(att.id, 'NEW')}" if (att and inc_counts.get(att.id, 0) > 0) else None,
                # Phase 23 Watermark & Capture Telemetry
                watermark_status="ACTIVE" if (att and att.id in wm_sessions and wm_sessions[att.id].is_valid) else ("NOT_RENDERED" if att else "DISABLED"),
                watermark_code=wm_sessions[att.id].watermark_code if (att and att.id in wm_sessions) else None,
                capture_capability=capture_tiers.get(att.id, "detection_limited") if att else "detection_limited",
                capture_signals_count=capture_signal_counts.get(att.id, 0) if att else 0,
                latest_capture_signal=latest_capture_signals.get(att.id, None) if att else None,
                # Phase 26 Advanced AI Proctoring Telemetry
                proctoring_session_id=proct_sessions[att.id].id if (att and att.id in proct_sessions) else None,
                camera_status=proct_sessions[att.id].camera_status if (att and att.id in proct_sessions) else "not_required",
                microphone_status=proct_sessions[att.id].microphone_status if (att and att.id in proct_sessions) else "not_required",
                face_presence_state=proct_sessions[att.id].face_presence_state if (att and att.id in proct_sessions) else "detected",
                head_position_state=proct_sessions[att.id].head_position_state if (att and att.id in proct_sessions) else "facing_screen",
                multiple_faces_detected=proct_sessions[att.id].multiple_faces_detected if (att and att.id in proct_sessions) else False,
                audio_level_state=proct_sessions[att.id].audio_level_state if (att and att.id in proct_sessions) else "normal",
                ai_risk_score=float(proct_sessions[att.id].ai_risk_score or 0.0) if (att and att.id in proct_sessions) else 0.0,
                ai_risk_level=proct_sessions[att.id].ai_risk_level if (att and att.id in proct_sessions) else "LOW",
                ai_classification=proct_sessions[att.id].ai_classification if (att and att.id in proct_sessions) else "NORMAL",
                proctoring_review_status=proct_sessions[att.id].review_status if (att and att.id in proct_sessions) else "NOT_REQUIRED",
                proctoring_decision=proct_sessions[att.id].reviewer_decision if (att and att.id in proct_sessions) else None,
            )

            # Apply Search Filter
            if search and search.strip():
                term = search.strip().lower()
                matches = (
                    term in item.full_name.lower() or
                    term in (item.register_number or "").lower() or
                    term in item.email.lower()
                )
                if not matches:
                    continue

            # Apply Status Filter
            if status_filter and status_filter.upper() != "ALL":
                if item.attempt_status != status_filter.upper():
                    continue

            # Apply Connection Filter
            if connection_filter and connection_filter.upper() != "ALL":
                if item.connection_status != connection_filter.upper():
                    continue

            items.append(item)

        return ParticipantMonitoringListResponse(total=len(items), items=items)

    # -------------------------------------------------------------------------
    # 5. Individual Participant Deep Telemetry
    # -------------------------------------------------------------------------
    @staticmethod
    def get_participant_detail(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        participant_id: uuid.UUID,  # student_id
    ) -> ParticipantDetailMonitoringResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        quiz = db.query(Quiz).options(joinedload(Quiz.sections)).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        total_q = sum(len(s.questions) for s in quiz.sections) if quiz.sections else 1

        student = db.query(Student).options(joinedload(Student.profile)).filter(Student.id == participant_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Candidate not found")

        attempt = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id == quiz_id,
            ExaminationAttempt.student_id == participant_id,
        ).order_by(desc(ExaminationAttempt.created_at)).first()

        # Build base participant item
        conn_status = "NOT_STARTED"
        sync_status = "NOT_STARTED"
        att_status = "NOT_STARTED"
        last_hb = None
        remaining_sec = 0
        time_spent = 0
        answered_cnt = 0
        deadline_at = None

        if attempt:
            att_status = (attempt.status or "in_progress").upper()
            last_hb = _ensure_utc(attempt.last_heartbeat_at)
            deadline_at = _ensure_utc(attempt.deadline_at or attempt.expires_at)
            time_spent = attempt.time_spent_seconds or 0
            if deadline_at:
                remaining_sec = max(0, int((deadline_at - now).total_seconds()))

            if attempt.status in ["submitted", "evaluated"]:
                conn_status = "COMPLETED"
                sync_status = "SYNCHRONIZED"
            else:
                diff_s = (now - last_hb).total_seconds() if last_hb else 9999
                if diff_s <= 30:
                    conn_status = "CONNECTED"
                    sync_status = "SYNCHRONIZED"
                elif diff_s <= 60:
                    conn_status = "RECONNECTING"
                    sync_status = "SYNC_PENDING"
                else:
                    conn_status = "DISCONNECTED"
                    sync_status = "SYNC_PENDING"

        # Question progress (WITHOUT revealing correct keys or marks)
        q_progress: List[QuestionProgressSummary] = []
        if attempt:
            answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
            answered_cnt = len(answers)
            for idx, ans in enumerate(answers, 1):
                q_progress.append(QuestionProgressSummary(
                    question_index=idx,
                    question_type="objective",
                    is_answered=ans.answer_status == "ANSWERED" or bool(ans.selected_option_ids or ans.text_response),
                    is_marked_for_review=bool(ans.is_flagged_for_review),
                    answered_at=_ensure_utc(ans.answered_at),
                ))

        # Events Timeline
        events_timeline: List[AttemptEventItem] = []
        if attempt:
            events = db.query(AttemptEvent).filter(
                AttemptEvent.attempt_id == attempt.id
            ).order_by(desc(AttemptEvent.occurred_at)).limit(50).all()

            for ev in events:
                meta = ev.event_metadata if isinstance(ev.event_metadata, dict) else {}
                sev = meta.get("severity", "MEDIUM") if meta else "MEDIUM"
                events_timeline.append(AttemptEventItem(
                    id=ev.id,
                    event_type=ev.event_type,
                    severity=sev,
                    details=meta,
                    client_timestamp=_ensure_utc(ev.occurred_at),
                    created_at=_ensure_utc(ev.occurred_at),
                ))

        # Incidents
        incidents_list: List[IncidentSummaryItem] = []
        inc_records = db.query(ExaminationIncident).filter(
            ExaminationIncident.quiz_id == quiz_id,
            ExaminationIncident.student_id == participant_id,
        ).order_by(desc(ExaminationIncident.created_at)).all()

        for inc in inc_records:
            incidents_list.append(IncidentSummaryItem(
                id=inc.id,
                incident_code=inc.incident_code,
                category=inc.category,
                severity=inc.severity,
                status=inc.status,
                title=inc.title,
                created_at=_ensure_utc(inc.created_at),
            ))

        # Extensions
        extension_list: List[ExtensionHistoryItem] = []
        if attempt:
            ext_records = db.query(ExaminationExtensionHistory).options(
                joinedload(ExaminationExtensionHistory.extender)
            ).filter(
                ExaminationExtensionHistory.attempt_id == attempt.id
            ).order_by(desc(ExaminationExtensionHistory.created_at)).all()

            for ext in ext_records:
                ext_name = ext.extender.full_name if ext.extender else "Administrator"
                extension_list.append(ExtensionHistoryItem(
                    id=ext.id,
                    extension_minutes=ext.extension_minutes,
                    previous_deadline=_ensure_utc(ext.previous_deadline),
                    new_deadline=_ensure_utc(ext.new_deadline),
                    reason=ext.reason,
                    extended_by_name=ext_name,
                    created_at=_ensure_utc(ext.created_at),
                ))

        reg_num = getattr(student, "register_number", None)
        if not reg_num and student.profile:
            reg_num = getattr(student.profile, "student_identifier", getattr(student.profile, "register_number", None))

        st_group = getattr(student.profile, "student_group", None) if student.profile else None

        p_sess = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == attempt.id).first() if attempt else None

        participant_item = ParticipantMonitoringItem(
            student_id=student.id,
            attempt_id=attempt.id if attempt else None,
            full_name=student.full_name or student.email,
            register_number=reg_num,
            email=student.email,
            student_group=st_group,
            attempt_status=att_status,
            connection_status=conn_status,
            last_heartbeat_at=last_hb,
            sync_status=sync_status,
            last_sync_at=last_hb,
            current_question_index=None,
            current_section_name=None,
            answered_count=answered_cnt,
            marked_for_review_count=0,
            unanswered_count=max(0, total_q - answered_cnt),
            progress_percentage=round((answered_cnt / max(1, total_q)) * 100, 1),
            time_spent_seconds=time_spent,
            remaining_seconds=remaining_sec,
            deadline_at=deadline_at,
            security_alerts_count=len(events_timeline),
            latest_security_event=events_timeline[0].event_type if events_timeline else None,
            has_active_incident=len(incidents_list) > 0,
            ip_address=attempt.ip_address if attempt else None,
            browser=attempt.user_agent if attempt else None,
            browser_compatibility_status="PASSED",
            fullscreen_status="EXITED" if any(e.event_type == "FULLSCREEN_EXIT" for e in events_timeline) else ("ACTIVE" if attempt else "NOT_REQUIRED"),
            focus_loss_count=sum(1 for e in events_timeline if e.event_type in ["WINDOW_FOCUS_LOST", "WINDOW_BLUR", "TAB_HIDDEN", "PAGE_HIDDEN"]),
            fullscreen_exit_count=sum(1 for e in events_timeline if e.event_type == "FULLSCREEN_EXIT"),
            incident_count=len(incidents_list),
            review_status=incidents_list[0].status if incidents_list else "NONE",
            latest_incident=incidents_list[0].title if incidents_list else None,
            # Phase 26 Advanced AI Proctoring Telemetry
            proctoring_session_id=p_sess.id if p_sess else None,
            camera_status=p_sess.camera_status if p_sess else "not_required",
            microphone_status=p_sess.microphone_status if p_sess else "not_required",
            face_presence_state=p_sess.face_presence_state if p_sess else "detected",
            head_position_state=p_sess.head_position_state if p_sess else "facing_screen",
            multiple_faces_detected=p_sess.multiple_faces_detected if p_sess else False,
            audio_level_state=p_sess.audio_level_state if p_sess else "normal",
            ai_risk_score=float(p_sess.ai_risk_score or 0.0) if p_sess else 0.0,
            ai_risk_level=p_sess.ai_risk_level if p_sess else "LOW",
            ai_classification=p_sess.ai_classification if p_sess else "NORMAL",
            proctoring_review_status=p_sess.review_status if p_sess else "NOT_REQUIRED",
            proctoring_decision=p_sess.reviewer_decision if p_sess else None,
        )

        return ParticipantDetailMonitoringResponse(
            participant=participant_item,
            event_timeline=events_timeline,
            question_progress=q_progress,
            incidents=incidents_list,
            extension_history=extension_list,
        )

    # -------------------------------------------------------------------------
    # 6. Invigilator Assignment & Management
    # -------------------------------------------------------------------------
    @staticmethod
    def assign_invigilator(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        invigilator_id: uuid.UUID,
        is_lead: bool = False,
        permissions: Optional[List[str]] = None,
    ) -> InvigilatorAssignmentResponse:
        LiveMonitoringService.check_intervention_permission(db, admin, quiz_id)

        target_admin = db.query(Admin).filter(Admin.id == invigilator_id).first()
        if not target_admin:
            raise HTTPException(status_code=404, detail="Target administrator/invigilator not found")

        existing = db.query(InvigilatorAssignment).filter(
            InvigilatorAssignment.quiz_id == quiz_id,
            InvigilatorAssignment.invigilator_id == invigilator_id,
        ).first()

        default_perms = permissions or ["view_progress", "send_announcements", "report_incidents"]
        if is_lead and "extend_time" not in default_perms:
            default_perms.append("extend_time")

        if existing:
            existing.status = "active"
            existing.is_lead = is_lead
            existing.permissions = default_perms
            existing.assigned_by = admin.id
            db.commit()
            db.refresh(existing)
            assignment = existing
        else:
            assignment = InvigilatorAssignment(
                id=uuid.uuid4(),
                quiz_id=quiz_id,
                invigilator_id=invigilator_id,
                is_lead=is_lead,
                permissions=default_perms,
                status="active",
                assigned_by=admin.id,
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)

        # Log action
        LiveMonitoringService.log_invigilator_activity(
            db=db,
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action="ASSIGNED_INVIGILATOR",
            details={"assigned_invigilator_id": str(invigilator_id), "is_lead": is_lead},
        )

        return InvigilatorAssignmentResponse(
            id=assignment.id,
            quiz_id=assignment.quiz_id,
            invigilator_id=assignment.invigilator_id,
            invigilator_name=target_admin.full_name or target_admin.email,
            invigilator_email=target_admin.email,
            is_lead=assignment.is_lead,
            permissions=assignment.permissions or [],
            status=assignment.status,
            assigned_by_name=admin.full_name or admin.email,
            assigned_at=_ensure_utc(assignment.assigned_at),
        )

    @staticmethod
    def list_invigilators(db: Session, admin: Admin, quiz_id: uuid.UUID) -> InvigilatorListResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        assignments = db.query(InvigilatorAssignment).options(
            joinedload(InvigilatorAssignment.invigilator),
            joinedload(InvigilatorAssignment.assigner),
        ).filter(
            InvigilatorAssignment.quiz_id == quiz_id,
            InvigilatorAssignment.status == "active",
        ).all()

        items = []
        for a in assignments:
            if not a.invigilator:
                continue
            items.append(InvigilatorAssignmentResponse(
                id=a.id,
                quiz_id=a.quiz_id,
                invigilator_id=a.invigilator_id,
                invigilator_name=a.invigilator.full_name or a.invigilator.email,
                invigilator_email=a.invigilator.email,
                is_lead=a.is_lead,
                permissions=a.permissions or [],
                status=a.status,
                assigned_by_name=a.assigner.full_name if a.assigner else None,
                assigned_at=_ensure_utc(a.assigned_at),
            ))

        return InvigilatorListResponse(total=len(items), items=items)

    @staticmethod
    def revoke_invigilator(db: Session, admin: Admin, quiz_id: uuid.UUID, assignment_id: uuid.UUID) -> Dict[str, Any]:
        LiveMonitoringService.check_intervention_permission(db, admin, quiz_id)

        assignment = db.query(InvigilatorAssignment).filter(
            InvigilatorAssignment.id == assignment_id,
            InvigilatorAssignment.quiz_id == quiz_id,
        ).first()

        if not assignment:
            raise HTTPException(status_code=404, detail="Invigilator assignment not found")

        assignment.status = "revoked"
        db.commit()

        LiveMonitoringService.log_invigilator_activity(
            db=db,
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action="REVOKED_INVIGILATOR",
            details={"assignment_id": str(assignment_id)},
        )

        return {"message": "Invigilator assignment successfully revoked", "id": str(assignment_id)}

    @staticmethod
    def log_invigilator_activity(
        db: Session,
        invigilator_id: uuid.UUID,
        quiz_id: uuid.UUID,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        log = InvigilatorActivityLog(
            id=uuid.uuid4(),
            invigilator_id=invigilator_id,
            quiz_id=quiz_id,
            action=action,
            details=details,
            ip_address=ip_address,
        )
        db.add(log)
        db.commit()

    # -------------------------------------------------------------------------
    # 7. Examination Announcements & Communication
    # -------------------------------------------------------------------------
    @staticmethod
    def create_announcement(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        title: str,
        message: str,
        announcement_type: str = "general",
        target_scope: str = "all_participants",
        target_participant_ids: Optional[List[str]] = None,
        requires_acknowledgement: bool = False,
    ) -> ExaminationAnnouncementResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        announcement = ExaminationAnnouncement(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            sender_id=admin.id,
            title=title.strip(),
            message=message.strip(),
            announcement_type=announcement_type,
            target_scope=target_scope,
            target_participant_ids=target_participant_ids,
            requires_acknowledgement=requires_acknowledgement,
        )
        db.add(announcement)
        db.commit()
        db.refresh(announcement)

        # Log invigilator activity
        LiveMonitoringService.log_invigilator_activity(
            db=db,
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action="SENT_ANNOUNCEMENT",
            details={"announcement_id": str(announcement.id), "title": title, "type": announcement_type},
        )

        return ExaminationAnnouncementResponse(
            id=announcement.id,
            quiz_id=announcement.quiz_id,
            sender_id=announcement.sender_id,
            sender_name=admin.full_name or admin.email,
            title=announcement.title,
            message=announcement.message,
            announcement_type=announcement_type,
            target_scope=target_scope,
            target_participant_ids=target_participant_ids,
            requires_acknowledgement=requires_acknowledgement,
            acknowledgement_count=0,
            created_at=_ensure_utc(announcement.created_at),
        )

    @staticmethod
    def list_announcements(db: Session, admin: Admin, quiz_id: uuid.UUID) -> AnnouncementListResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        announcements = db.query(ExaminationAnnouncement).options(
            joinedload(ExaminationAnnouncement.sender),
            joinedload(ExaminationAnnouncement.acknowledgements),
        ).filter(
            ExaminationAnnouncement.quiz_id == quiz_id
        ).order_by(desc(ExaminationAnnouncement.created_at)).all()

        items = []
        for ann in announcements:
            items.append(ExaminationAnnouncementResponse(
                id=ann.id,
                quiz_id=ann.quiz_id,
                sender_id=ann.sender_id,
                sender_name=ann.sender.full_name if ann.sender else "System Announcement",
                title=ann.title,
                message=ann.message,
                announcement_type=ann.announcement_type,
                target_scope=ann.target_scope,
                target_participant_ids=ann.target_participant_ids,
                requires_acknowledgement=ann.requires_acknowledgement,
                acknowledgement_count=len(ann.acknowledgements) if ann.acknowledgements else 0,
                created_at=_ensure_utc(ann.created_at),
            ))

        return AnnouncementListResponse(total=len(items), items=items)

    @staticmethod
    def acknowledge_announcement(
        db: Session,
        student_id: uuid.UUID,
        announcement_id: uuid.UUID,
        attempt_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        existing = db.query(AnnouncementAcknowledgement).filter(
            AnnouncementAcknowledgement.announcement_id == announcement_id,
            AnnouncementAcknowledgement.student_id == student_id,
        ).first()

        if existing:
            return {"message": "Already acknowledged", "acknowledged_at": existing.acknowledged_at.isoformat()}

        ack = AnnouncementAcknowledgement(
            id=uuid.uuid4(),
            announcement_id=announcement_id,
            student_id=student_id,
            attempt_id=attempt_id,
        )
        db.add(ack)
        db.commit()

        return {"message": "Announcement successfully acknowledged", "acknowledged_at": ack.acknowledged_at.isoformat()}

    # -------------------------------------------------------------------------
    # 8. Live Incident Management
    # -------------------------------------------------------------------------
    @staticmethod
    def create_incident(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        title: str,
        description: str,
        category: str,
        severity: str = "medium",
        student_id: Optional[uuid.UUID] = None,
        attempt_id: Optional[uuid.UUID] = None,
        assigned_to: Optional[uuid.UUID] = None,
    ) -> ExaminationIncidentResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        rand_code = secrets.token_hex(2).upper()
        incident_code = f"INC-{date_str}-{rand_code}"

        incident = ExaminationIncident(
            id=uuid.uuid4(),
            incident_code=incident_code,
            quiz_id=quiz_id,
            student_id=student_id,
            attempt_id=attempt_id,
            category=category,
            severity=severity.lower(),
            status="OPEN",
            title=title.strip(),
            description=description.strip(),
            reported_by=admin.id,
            assigned_to=assigned_to,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        # Trigger monitoring alert if high or critical
        if severity.lower() in ["high", "critical"]:
            alert = MonitoringAlert(
                id=uuid.uuid4(),
                quiz_id=quiz_id,
                student_id=student_id,
                attempt_id=attempt_id,
                alert_type="UNRESOLVED_INCIDENT",
                priority=severity.upper(),
                title=f"Incident {incident_code}: {title}",
                details={"incident_id": str(incident.id), "category": category},
            )
            db.add(alert)
            db.commit()

        # Log invigilator activity
        LiveMonitoringService.log_invigilator_activity(
            db=db,
            invigilator_id=admin.id,
            quiz_id=quiz_id,
            action="REPORTED_INCIDENT",
            details={"incident_code": incident_code, "severity": severity},
        )

        st_name = None
        if student_id:
            stu = db.query(Student).filter(Student.id == student_id).first()
            if stu:
                st_name = stu.full_name or stu.email

        assignee_name = None
        if assigned_to:
            assignee = db.query(Admin).filter(Admin.id == assigned_to).first()
            if assignee:
                assignee_name = assignee.full_name or assignee.email

        return ExaminationIncidentResponse(
            id=incident.id,
            incident_code=incident.incident_code,
            quiz_id=incident.quiz_id,
            student_id=incident.student_id,
            student_name=st_name,
            attempt_id=incident.attempt_id,
            category=incident.category,
            severity=incident.severity,
            status=incident.status,
            title=incident.title,
            description=incident.description,
            reported_by=incident.reported_by,
            reported_by_name=admin.full_name or admin.email,
            assigned_to=incident.assigned_to,
            assigned_to_name=assignee_name,
            resolution_notes=incident.resolution_notes,
            resolved_at=_ensure_utc(incident.resolved_at),
            notes=[],
            created_at=_ensure_utc(incident.created_at),
            updated_at=_ensure_utc(incident.updated_at),
        )

    @staticmethod
    def update_incident(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        incident_id: uuid.UUID,
        status_val: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
        resolution_notes: Optional[str] = None,
    ) -> ExaminationIncidentResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        incident = db.query(ExaminationIncident).options(
            joinedload(ExaminationIncident.reporter),
            joinedload(ExaminationIncident.assignee),
            joinedload(ExaminationIncident.student),
            joinedload(ExaminationIncident.notes).joinedload(IncidentNote.author),
        ).filter(
            ExaminationIncident.id == incident_id,
            ExaminationIncident.quiz_id == quiz_id,
        ).first()

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        if status_val:
            incident.status = status_val.upper()
            if status_val.upper() in ["RESOLVED", "CLOSED"]:
                incident.resolved_at = datetime.now(timezone.utc)

        if assigned_to is not None:
            incident.assigned_to = assigned_to

        if resolution_notes:
            incident.resolution_notes = resolution_notes.strip()

        db.commit()
        db.refresh(incident)

        notes_resp = [
            IncidentNoteResponse(
                id=n.id,
                incident_id=n.incident_id,
                author_id=n.author_id,
                author_name=n.author.full_name if n.author else "Administrator",
                note=n.note,
                created_at=_ensure_utc(n.created_at),
            )
            for n in incident.notes
        ]

        st_name = incident.student.full_name if incident.student else None

        return ExaminationIncidentResponse(
            id=incident.id,
            incident_code=incident.incident_code,
            quiz_id=incident.quiz_id,
            student_id=incident.student_id,
            student_name=st_name,
            attempt_id=incident.attempt_id,
            category=incident.category,
            severity=incident.severity,
            status=incident.status,
            title=incident.title,
            description=incident.description,
            reported_by=incident.reported_by,
            reported_by_name=incident.reporter.full_name if incident.reporter else None,
            assigned_to=incident.assigned_to,
            assigned_to_name=incident.assignee.full_name if incident.assignee else None,
            resolution_notes=incident.resolution_notes,
            resolved_at=_ensure_utc(incident.resolved_at),
            notes=notes_resp,
            created_at=_ensure_utc(incident.created_at),
            updated_at=_ensure_utc(incident.updated_at),
        )

    @staticmethod
    def add_incident_note(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        incident_id: uuid.UUID,
        note: str,
    ) -> IncidentNoteResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        incident = db.query(ExaminationIncident).filter(
            ExaminationIncident.id == incident_id,
            ExaminationIncident.quiz_id == quiz_id,
        ).first()

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        inc_note = IncidentNote(
            id=uuid.uuid4(),
            incident_id=incident_id,
            author_id=admin.id,
            note=note.strip(),
        )
        db.add(inc_note)
        db.commit()
        db.refresh(inc_note)

        return IncidentNoteResponse(
            id=inc_note.id,
            incident_id=inc_note.incident_id,
            author_id=inc_note.author_id,
            author_name=admin.full_name or admin.email,
            note=inc_note.note,
            created_at=_ensure_utc(inc_note.created_at),
        )

    @staticmethod
    def list_incidents(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
    ) -> IncidentListResponse:
        LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)

        query = db.query(ExaminationIncident).options(
            joinedload(ExaminationIncident.reporter),
            joinedload(ExaminationIncident.assignee),
            joinedload(ExaminationIncident.student),
            joinedload(ExaminationIncident.notes).joinedload(IncidentNote.author),
        ).filter(ExaminationIncident.quiz_id == quiz_id)

        if status_filter and status_filter.upper() != "ALL":
            query = query.filter(ExaminationIncident.status == status_filter.upper())

        if severity_filter and severity_filter.lower() != "all":
            query = query.filter(ExaminationIncident.severity == severity_filter.lower())

        incidents = query.order_by(desc(ExaminationIncident.created_at)).all()

        items = []
        for inc in incidents:
            notes_resp = [
                IncidentNoteResponse(
                    id=n.id,
                    incident_id=n.incident_id,
                    author_id=n.author_id,
                    author_name=n.author.full_name if n.author else "Administrator",
                    note=n.note,
                    created_at=_ensure_utc(n.created_at),
                )
                for n in inc.notes
            ]
            items.append(ExaminationIncidentResponse(
                id=inc.id,
                incident_code=inc.incident_code,
                quiz_id=inc.quiz_id,
                student_id=inc.student_id,
                student_name=inc.student.full_name if inc.student else None,
                attempt_id=inc.attempt_id,
                category=inc.category,
                severity=inc.severity,
                status=inc.status,
                title=inc.title,
                description=inc.description,
                reported_by=inc.reported_by,
                reported_by_name=inc.reporter.full_name if inc.reporter else None,
                assigned_to=inc.assigned_to,
                assigned_to_name=inc.assignee.full_name if inc.assignee else None,
                resolution_notes=inc.resolution_notes,
                resolved_at=_ensure_utc(inc.resolved_at),
                notes=notes_resp,
                created_at=_ensure_utc(inc.created_at),
                updated_at=_ensure_utc(inc.updated_at),
            ))

        return IncidentListResponse(total=len(items), items=items)

    # -------------------------------------------------------------------------
    # 9. Emergency Interventions
    # -------------------------------------------------------------------------
    @staticmethod
    def extend_examination_time(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        minutes: int,
        target_type: str = "all",
        student_id: Optional[uuid.UUID] = None,
        reason: str = "Technical accommodation",
    ) -> MonitoringInterventionResponse:
        """
        Extends examination time with official server deadline updates.
        Updates attempts' deadline_at and expires_at, and creates an audit trail.
        """
        LiveMonitoringService.check_intervention_permission(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        # Find eligible attempts
        query = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id == quiz_id,
            ExaminationAttempt.status == "in_progress",
        )
        if target_type == "selected_student" and student_id:
            query = query.filter(ExaminationAttempt.student_id == student_id)

        target_attempts = query.all()
        if not target_attempts:
            raise HTTPException(status_code=400, detail="No active in-progress attempts found to extend")

        added_delta = timedelta(minutes=minutes)
        previous_states = []
        new_states = []

        for att in target_attempts:
            prev_deadline = _ensure_utc(att.deadline_at or att.expires_at)
            new_deadline = prev_deadline + added_delta

            previous_states.append({
                "attempt_id": str(att.id),
                "student_id": str(att.student_id),
                "deadline": prev_deadline.isoformat(),
            })

            att.deadline_at = new_deadline
            att.expires_at = new_deadline
            att.extra_time_seconds = (att.extra_time_seconds or 0) + (minutes * 60)

            new_states.append({
                "attempt_id": str(att.id),
                "student_id": str(att.student_id),
                "deadline": new_deadline.isoformat(),
            })

            # Record history entry
            history = ExaminationExtensionHistory(
                id=uuid.uuid4(),
                quiz_id=quiz_id,
                attempt_id=att.id,
                extended_by=admin.id,
                extension_minutes=minutes,
                previous_deadline=prev_deadline,
                new_deadline=new_deadline,
                reason=reason.strip(),
            )
            db.add(history)

        # Record intervention audit
        intervention = MonitoringIntervention(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            action_type="EXTEND_TIME",
            performed_by=admin.id,
            target_type=target_type,
            target_id=str(student_id) if student_id else "all",
            reason=reason.strip(),
            previous_state={"attempts": previous_states},
            new_state={"attempts": new_states, "added_minutes": minutes},
        )
        db.add(intervention)

        # Broadcast announcement to candidates
        ann_msg = f"Examination time extended by {minutes} minutes. New deadline applied automatically. Reason: {reason}"
        LiveMonitoringService.create_announcement(
            db=db,
            admin=admin,
            quiz_id=quiz_id,
            title=f"Time Extension (+{minutes} mins)",
            message=ann_msg,
            announcement_type="time_reminder",
            target_scope="selected_participants" if target_type == "selected_student" else "all_participants",
            target_participant_ids=[str(student_id)] if target_type == "selected_student" and student_id else None,
            requires_acknowledgement=False,
        )

        db.commit()
        db.refresh(intervention)

        return MonitoringInterventionResponse(
            id=intervention.id,
            quiz_id=intervention.quiz_id,
            action_type=intervention.action_type,
            performed_by_id=admin.id,
            performed_by_name=admin.full_name or admin.email,
            target_type=intervention.target_type,
            target_id=intervention.target_id,
            reason=intervention.reason,
            previous_state=intervention.previous_state,
            new_state=intervention.new_state,
            created_at=_ensure_utc(intervention.created_at),
        )

    @staticmethod
    def terminate_attempt(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        attempt_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        reason: str = "Administrative termination",
    ) -> MonitoringInterventionResponse:
        LiveMonitoringService.check_intervention_permission(db, admin, quiz_id)

        attempt = None
        if attempt_id:
            attempt = db.query(ExaminationAttempt).filter(
                ExaminationAttempt.id == attempt_id,
                ExaminationAttempt.quiz_id == quiz_id,
            ).first()

        if not attempt and student_id:
            # Query active attempt first, or most recent attempt for student
            attempt = db.query(ExaminationAttempt).filter(
                ExaminationAttempt.quiz_id == quiz_id,
                ExaminationAttempt.student_id == student_id,
                ExaminationAttempt.status.in_(["in_progress", "submitted", "ready"])
            ).order_by(desc(ExaminationAttempt.created_at)).first()
            if not attempt:
                attempt = db.query(ExaminationAttempt).filter(
                    ExaminationAttempt.quiz_id == quiz_id,
                    ExaminationAttempt.student_id == student_id,
                ).order_by(desc(ExaminationAttempt.created_at)).first()

        if not attempt:
            raise HTTPException(status_code=404, detail="No active attempt found to terminate")

        prev_status = attempt.status
        now = datetime.now(timezone.utc)

        attempt.status = "submitted"  # mark submitted with reason ADMIN_TERMINATED
        attempt.submitted_at = now
        attempt.submission_reason = "ADMIN_TERMINATED"
        attempt.submission_source = "admin_portal"

        # Log security / attempt event
        event = AttemptEvent(
            id=uuid.uuid4(),
            attempt_id=attempt.id,
            event_type="ADMIN_TERMINATION",
            actor_type="admin",
            actor_id=str(admin.id),
            event_metadata={"admin_id": str(admin.id), "reason": reason.strip(), "severity": "CRITICAL"},
            occurred_at=now,
        )
        db.add(event)

        # Record intervention
        intervention = MonitoringIntervention(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            action_type="TERMINATE_ATTEMPT",
            performed_by=admin.id,
            target_type="attempt",
            target_id=str(attempt.id),
            reason=reason.strip(),
            previous_state={"status": prev_status},
            new_state={"status": "terminated", "submission_reason": "ADMIN_TERMINATED"},
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)

        return MonitoringInterventionResponse(
            id=intervention.id,
            quiz_id=intervention.quiz_id,
            action_type=intervention.action_type,
            performed_by_id=admin.id,
            performed_by_name=admin.full_name or admin.email,
            target_type=intervention.target_type,
            target_id=intervention.target_id,
            reason=intervention.reason,
            previous_state=intervention.previous_state,
            new_state=intervention.new_state,
            created_at=_ensure_utc(intervention.created_at),
        )

    @staticmethod
    def cancel_examination(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        reason: str,
    ) -> MonitoringInterventionResponse:
        LiveMonitoringService.check_intervention_permission(db, admin, quiz_id)

        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        now = datetime.now(timezone.utc)
        prev_status = quiz.status
        quiz.status = "cancelled"

        # Terminate all in-progress attempts
        in_progress_attempts = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id == quiz_id,
            ExaminationAttempt.status == "in_progress",
        ).all()

        for att in in_progress_attempts:
            att.status = "cancelled"
            att.submitted_at = now
            att.submission_reason = "EXAM_CANCELLED"

        intervention = MonitoringIntervention(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            action_type="CANCEL_EXAM",
            performed_by=admin.id,
            target_type="quiz",
            target_id=str(quiz_id),
            reason=reason.strip(),
            previous_state={"quiz_status": prev_status, "cancelled_attempts": len(in_progress_attempts)},
            new_state={"quiz_status": "cancelled"},
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)

        return MonitoringInterventionResponse(
            id=intervention.id,
            quiz_id=intervention.quiz_id,
            action_type=intervention.action_type,
            performed_by_id=admin.id,
            performed_by_name=admin.full_name or admin.email,
            target_type=intervention.target_type,
            target_id=intervention.target_id,
            reason=intervention.reason,
            previous_state=intervention.previous_state,
            new_state=intervention.new_state,
            created_at=_ensure_utc(intervention.created_at),
        )

    # -------------------------------------------------------------------------
    # 10. Unified Alert Center
    # -------------------------------------------------------------------------
    @staticmethod
    def list_alerts(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
        priority: Optional[str] = None,
        is_resolved: Optional[bool] = None,
    ) -> List[MonitoringAlertItem]:
        is_super = is_super_admin(admin)

        query = db.query(MonitoringAlert).options(
            joinedload(MonitoringAlert.quiz),
            joinedload(MonitoringAlert.student),
        )

        if quiz_id:
            LiveMonitoringService.check_monitoring_access(db, admin, quiz_id)
            query = query.filter(MonitoringAlert.quiz_id == quiz_id)
        elif not is_super:
            assigned_quiz_ids = [
                r[0] for r in db.query(AdminQuizAssignment.quiz_id).filter(AdminQuizAssignment.admin_id == admin.id).all()
            ]
            invig_quiz_ids = [
                r[0] for r in db.query(InvigilatorAssignment.quiz_id).filter(
                    InvigilatorAssignment.invigilator_id == admin.id,
                    InvigilatorAssignment.status == "active"
                ).all()
            ]
            owned_quiz_ids = [
                r[0] for r in db.query(Quiz.id).filter(Quiz.created_by == admin.id).all()
            ]
            allowed_ids = list(set(assigned_quiz_ids + invig_quiz_ids + owned_quiz_ids))
            query = query.filter(MonitoringAlert.quiz_id.in_(allowed_ids))

        if priority and priority.upper() != "ALL":
            query = query.filter(MonitoringAlert.priority == priority.upper())

        if is_resolved is not None:
            query = query.filter(MonitoringAlert.is_resolved == is_resolved)

        alerts = query.order_by(desc(MonitoringAlert.created_at)).limit(100).all()

        items = []
        for a in alerts:
            st_name = a.student.full_name if a.student else None
            items.append(MonitoringAlertItem(
                id=a.id,
                quiz_id=a.quiz_id,
                quiz_title=a.quiz.title if a.quiz else "Examination",
                student_id=a.student_id,
                student_name=st_name,
                attempt_id=a.attempt_id,
                alert_type=a.alert_type,
                priority=a.priority,
                title=a.title,
                details=a.details,
                is_acknowledged=a.is_acknowledged,
                is_resolved=a.is_resolved,
                created_at=_ensure_utc(a.created_at),
            ))

        return items

    @staticmethod
    def acknowledge_alert(db: Session, admin: Admin, alert_id: uuid.UUID) -> Dict[str, Any]:
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        LiveMonitoringService.check_monitoring_access(db, admin, alert.quiz_id)

        now = datetime.now(timezone.utc)
        alert.is_acknowledged = True
        alert.acknowledged_by = admin.id
        alert.acknowledged_at = now
        db.commit()

        return {"message": "Alert acknowledged", "id": str(alert_id), "acknowledged_at": now.isoformat()}

    @staticmethod
    def resolve_alert(db: Session, admin: Admin, alert_id: uuid.UUID) -> Dict[str, Any]:
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        LiveMonitoringService.check_monitoring_access(db, admin, alert.quiz_id)

        now = datetime.now(timezone.utc)
        alert.is_resolved = True
        alert.resolved_by = admin.id
        alert.resolved_at = now
        db.commit()

        return {"message": "Alert resolved", "id": str(alert_id), "resolved_at": now.isoformat()}
