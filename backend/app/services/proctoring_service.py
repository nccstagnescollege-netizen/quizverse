import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, text
from fastapi import HTTPException, status

from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.examination import ExaminationAttempt, AttemptEvent
from backend.app.models.student import Student, StudentProfile
from backend.app.models.monitoring import MonitoringAlert, ExaminationIncident
from backend.app.models.proctoring import (
    ProctoringSession,
    ProctoringEvent,
    ProctoringIncidentReview,
)
from backend.app.schemas.proctoring import (
    ProctoringPolicyUpdateRequest,
    ProctoringPolicyResponse,
    ProctoringSessionInitRequest,
    ProctoringSessionResponse,
    ProctoringSignalBatchRequest,
    ProctoringEventItem,
    ProctoringRiskAssessmentResponse,
    ProctoringIncidentReviewRequest,
    ProctoringIncidentReviewResponse,
    ProctoringDashboardCandidateItem,
    ProctoringDashboardOverviewResponse,
    ProctoringAlertItem,
)

logger = logging.getLogger("quizverse.proctoring")


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AIProctoringService:
    """
    Advanced AI-Assisted Live Proctoring Service.
    Processes on-device camera/microphone signals, calculates explainable
    risk scores without biased facial recognition, and facilitates human-reviewed invigilation.
    """

    @staticmethod
    def check_quiz_access(db: Session, admin: Admin, quiz_id: uuid.UUID) -> Quiz:
        quiz = db.query(Quiz).options(joinedload(Quiz.configuration)).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        if admin.is_super_admin:
            return quiz

        # Check ownership or assignment
        if quiz.created_by == admin.id:
            return quiz

        assignment = db.query(AdminQuizAssignment).filter(
            AdminQuizAssignment.admin_id == admin.id,
            AdminQuizAssignment.quiz_id == quiz_id,
        ).first()
        if assignment:
            return quiz

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have administrative authorization for this examination",
        )

    # -------------------------------------------------------------------------
    # 1. Proctoring Policy Management
    # -------------------------------------------------------------------------
    @staticmethod
    def get_quiz_proctoring_policy(db: Session, quiz_id: uuid.UUID, admin: Optional[Admin] = None) -> ProctoringPolicyResponse:
        quiz = db.query(Quiz).options(joinedload(Quiz.configuration)).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Examination not found")

        cfg = quiz.configuration
        if not cfg:
            cfg = QuizConfiguration(quiz_id=quiz.id)
            db.add(cfg)
            db.commit()
            db.refresh(cfg)

        return ProctoringPolicyResponse(
            quiz_id=quiz.id,
            webcam_monitoring_enabled=bool(getattr(cfg, "webcam_monitoring_enabled", False)),
            microphone_monitoring_enabled=bool(getattr(cfg, "microphone_monitoring_enabled", False)),
            face_presence_detection=bool(getattr(cfg, "face_presence_detection", False)),
            multiple_person_detection=bool(getattr(cfg, "multiple_person_detection", False)),
            head_position_detection=bool(getattr(cfg, "head_position_detection", False)),
            audio_anomaly_detection=bool(getattr(cfg, "audio_anomaly_detection", False)),
            browser_activity_integration=bool(getattr(cfg, "browser_activity_integration", True)),
            mobile_interruption_integration=bool(getattr(cfg, "mobile_interruption_integration", True)),
            seb_security_integration=bool(getattr(cfg, "seb_security_integration", True)),
            proctoring_mandatory=bool(getattr(cfg, "proctoring_mandatory", False)),
            webcam_permission_required=bool(getattr(cfg, "webcam_permission_required", False)),
            microphone_permission_required=bool(getattr(cfg, "microphone_permission_required", False)),
            monitoring_interval_seconds=int(getattr(cfg, "monitoring_interval_seconds", 10)),
            risk_warning_threshold=int(getattr(cfg, "risk_warning_threshold", 50)),
            risk_critical_threshold=int(getattr(cfg, "risk_critical_threshold", 80)),
            human_review_required=bool(getattr(cfg, "human_review_required", True)),
            recording_enabled=bool(getattr(cfg, "recording_enabled", False)),
            recording_retention_days=int(getattr(cfg, "recording_retention_days", 30)),
        )

    @staticmethod
    def update_quiz_proctoring_policy(
        db: Session,
        quiz_id: uuid.UUID,
        req: ProctoringPolicyUpdateRequest,
        admin: Admin,
    ) -> ProctoringPolicyResponse:
        quiz = AIProctoringService.check_quiz_access(db, admin, quiz_id)
        cfg = quiz.configuration
        if not cfg:
            cfg = QuizConfiguration(quiz_id=quiz.id)
            db.add(cfg)

        update_data = req.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(cfg, key) and value is not None:
                setattr(cfg, key, value)

        db.commit()
        db.refresh(cfg)
        return AIProctoringService.get_quiz_proctoring_policy(db, quiz_id, admin)

    # -------------------------------------------------------------------------
    # 2. Proctoring Session Lifecycle
    # -------------------------------------------------------------------------
    @staticmethod
    def initialize_session(
        db: Session,
        attempt_id: uuid.UUID,
        req: ProctoringSessionInitRequest,
    ) -> ProctoringSessionResponse:
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Examination attempt not found")

        now = datetime.now(timezone.utc)
        session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == attempt_id).first()

        if session:
            # Update hardware & consent status
            session.camera_status = req.camera_status
            session.microphone_status = req.microphone_status
            if req.camera_label:
                session.camera_label = req.camera_label
            if req.microphone_label:
                session.microphone_label = req.microphone_label
            if req.lighting_condition:
                session.lighting_condition = req.lighting_condition
            if req.is_accommodated_exempt is not None:
                session.is_accommodated_exempt = req.is_accommodated_exempt
            if req.recording_consent_given is not None:
                session.recording_consent_given = req.recording_consent_given
            session.last_heartbeat_at = now
            session.status = "active"
            db.commit()
            db.refresh(session)
        else:
            session = ProctoringSession(
                id=uuid.uuid4(),
                attempt_id=attempt.id,
                quiz_id=attempt.quiz_id,
                student_id=attempt.student_id,
                status="active",
                started_at=now,
                last_heartbeat_at=now,
                camera_status=req.camera_status,
                microphone_status=req.microphone_status,
                camera_label=req.camera_label,
                microphone_label=req.microphone_label,
                lighting_condition=req.lighting_condition or "good",
                is_accommodated_exempt=bool(req.is_accommodated_exempt),
                recording_consent_given=bool(req.recording_consent_given),
                session_metadata=req.client_metadata or {},
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # Student info
        student = db.query(Student).options(joinedload(Student.profile)).filter(Student.id == session.student_id).first()
        reg_num = getattr(student, "register_number", None)
        if not reg_num and student and student.profile:
            reg_num = getattr(student.profile, "student_identifier", getattr(student.profile, "register_number", None))

        return ProctoringSessionResponse(
            id=session.id,
            attempt_id=session.attempt_id,
            quiz_id=session.quiz_id,
            student_id=session.student_id,
            student_name=student.full_name if student else "Candidate",
            register_number=reg_num,
            status=session.status,
            camera_status=session.camera_status,
            microphone_status=session.microphone_status,
            lighting_condition=session.lighting_condition,
            is_accommodated_exempt=session.is_accommodated_exempt,
            face_presence_state=session.face_presence_state,
            head_position_state=session.head_position_state,
            multiple_faces_detected=session.multiple_faces_detected,
            audio_level_state=session.audio_level_state,
            total_face_absent_count=session.total_face_absent_count,
            total_multiple_face_count=session.total_multiple_face_count,
            total_head_movement_count=session.total_head_movement_count,
            total_audio_anomaly_count=session.total_audio_anomaly_count,
            total_proctoring_events=session.total_proctoring_events,
            ai_risk_score=float(session.ai_risk_score or 0.0),
            ai_risk_level=session.ai_risk_level,
            ai_classification=session.ai_classification,
            ai_confidence=float(session.ai_confidence or 0.90),
            risk_factors=session.risk_factors or [],
            review_status=session.review_status,
            reviewer_decision=session.reviewer_decision,
            reviewer_notes=session.reviewer_notes,
            reviewed_at=_ensure_utc(session.reviewed_at),
            recording_consent_given=session.recording_consent_given,
            started_at=_ensure_utc(session.started_at),
            last_heartbeat_at=_ensure_utc(session.last_heartbeat_at),
        )

    # -------------------------------------------------------------------------
    # 3. Telemetry Signal Ingestion & Explainable Risk Scoring Engine
    # -------------------------------------------------------------------------
    @staticmethod
    def record_signal_batch(
        db: Session,
        session_id: uuid.UUID,
        req: ProctoringSignalBatchRequest,
    ) -> ProctoringSessionResponse:
        session = db.query(ProctoringSession).filter(ProctoringSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Proctoring session not found")

        now = datetime.now(timezone.utc)
        session.last_heartbeat_at = now

        # Update current live states if provided
        if req.face_presence_state:
            session.face_presence_state = req.face_presence_state
        if req.head_position_state:
            session.head_position_state = req.head_position_state
        if req.multiple_faces_detected is not None:
            session.multiple_faces_detected = req.multiple_faces_detected
        if req.audio_level_state:
            session.audio_level_state = req.audio_level_state
        if req.lighting_condition:
            session.lighting_condition = req.lighting_condition

        # Ingest event signals
        new_event_count = 0
        for sig in req.signals:
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                attempt_id=session.attempt_id,
                quiz_id=session.quiz_id,
                student_id=session.student_id,
                event_type=sig.event_type.upper(),
                severity=(sig.severity or "LOW").upper(),
                confidence_score=Decimal(str(round(sig.confidence_score or 0.85, 3))),
                duration_seconds=sig.duration_seconds or 0,
                details=sig.details or {},
                occurred_at=_ensure_utc(sig.occurred_at) or now,
                created_at=now,
            )
            db.add(ev)
            new_event_count += 1

            # Update discrete metric counters
            if ev.event_type in ["FACE_ABSENT", "FACE_TEMPORARILY_ABSENT", "FACE_OUT_OF_BOUNDS"]:
                session.total_face_absent_count += 1
            elif ev.event_type in ["MULTIPLE_FACES", "MULTIPLE_PERSONS_DETECTED"]:
                session.total_multiple_face_count += 1
            elif ev.event_type in ["HEAD_POSE_ANOMALY", "HEAD_TURNED_AWAY", "SIGNIFICANT_HEAD_MOVEMENT"]:
                session.total_head_movement_count += 1
            elif ev.event_type in ["AUDIO_ELEVATED", "SPEECH_DETECTED", "AUDIO_ANOMALY"]:
                session.total_audio_anomaly_count += 1

        session.total_proctoring_events += new_event_count

        # Compute explainable AI risk score
        AIProctoringService._compute_and_apply_risk_score(db, session)

        db.commit()
        db.refresh(session)

        # Trigger invigilator alert if risk reaches critical threshold
        if session.ai_risk_level in ["HIGH", "CRITICAL"] and session.review_status == "NOT_REQUIRED":
            session.review_status = "PENDING"
            # Deduplicate existing unresolved alert
            existing_alert = db.query(MonitoringAlert).filter(
                MonitoringAlert.quiz_id == session.quiz_id,
                MonitoringAlert.student_id == session.student_id,
                MonitoringAlert.alert_type == "PROCTORING_RISK_SPIKE",
                MonitoringAlert.is_resolved == False,
            ).first()
            if not existing_alert:
                alert = MonitoringAlert(
                    id=uuid.uuid4(),
                    quiz_id=session.quiz_id,
                    student_id=session.student_id,
                    attempt_id=session.attempt_id,
                    alert_type="PROCTORING_RISK_SPIKE",
                    priority="HIGH" if session.ai_risk_level == "HIGH" else "CRITICAL",
                    title=f"AI Proctoring Review: {session.ai_classification}",
                    details={
                        "risk_score": float(session.ai_risk_score),
                        "risk_level": session.ai_risk_level,
                        "classification": session.ai_classification,
                        "risk_factors": session.risk_factors or [],
                    },
                )
                db.add(alert)
                db.commit()

        # Build response
        student = db.query(Student).options(joinedload(Student.profile)).filter(Student.id == session.student_id).first()
        reg_num = getattr(student, "register_number", None)
        if not reg_num and student and student.profile:
            reg_num = getattr(student.profile, "student_identifier", getattr(student.profile, "register_number", None))

        return ProctoringSessionResponse(
            id=session.id,
            attempt_id=session.attempt_id,
            quiz_id=session.quiz_id,
            student_id=session.student_id,
            student_name=student.full_name if student else "Candidate",
            register_number=reg_num,
            status=session.status,
            camera_status=session.camera_status,
            microphone_status=session.microphone_status,
            lighting_condition=session.lighting_condition,
            is_accommodated_exempt=session.is_accommodated_exempt,
            face_presence_state=session.face_presence_state,
            head_position_state=session.head_position_state,
            multiple_faces_detected=session.multiple_faces_detected,
            audio_level_state=session.audio_level_state,
            total_face_absent_count=session.total_face_absent_count,
            total_multiple_face_count=session.total_multiple_face_count,
            total_head_movement_count=session.total_head_movement_count,
            total_audio_anomaly_count=session.total_audio_anomaly_count,
            total_proctoring_events=session.total_proctoring_events,
            ai_risk_score=float(session.ai_risk_score or 0.0),
            ai_risk_level=session.ai_risk_level,
            ai_classification=session.ai_classification,
            ai_confidence=float(session.ai_confidence or 0.90),
            risk_factors=session.risk_factors or [],
            review_status=session.review_status,
            reviewer_decision=session.reviewer_decision,
            reviewer_notes=session.reviewer_notes,
            reviewed_at=_ensure_utc(session.reviewed_at),
            recording_consent_given=session.recording_consent_given,
            started_at=_ensure_utc(session.started_at),
            last_heartbeat_at=_ensure_utc(session.last_heartbeat_at),
        )

    @staticmethod
    def _compute_and_apply_risk_score(db: Session, session: ProctoringSession) -> None:
        """
        Explainable, rule-based algorithmic scoring engine.
        Weights discrete events while accounting for false positives (lighting, normal movement).
        AI prediction strictly aids human proctors; NEVER fails students automatically.
        """
        # If student has approved accommodation exemption, cap risk
        if session.is_accommodated_exempt:
            session.ai_risk_score = Decimal("0.00")
            session.ai_risk_level = "LOW"
            session.ai_classification = "NORMAL"
            session.risk_factors = [{"factor": "Accommodated Process", "impact": 0, "note": "Student granted accessibility accommodation"}]
            return

        score = 0.0
        factors = []

        # 1. Multiple Faces Detected (Stronger signal, but could be posters/mirrors)
        mult_count = session.total_multiple_face_count
        if mult_count > 0:
            impact = min(35.0, mult_count * 15.0)
            score += impact
            factors.append({
                "factor": "Multiple Persons Detected",
                "count": mult_count,
                "impact": impact,
                "note": "Multiple faces detected in camera frame; requires verification of environment.",
            })

        # 2. Prolonged / Frequent Face Absence
        abs_count = session.total_face_absent_count
        if abs_count >= 3:
            impact = min(25.0, (abs_count - 2) * 5.0)
            score += impact
            factors.append({
                "factor": "Extended Face Absence",
                "count": abs_count,
                "impact": impact,
                "note": "Candidate face temporarily out of frame multiple times.",
            })

        # 3. Repeated Extreme Head Position Anomaly
        head_count = session.total_head_movement_count
        if head_count >= 4:
            impact = min(15.0, (head_count - 3) * 3.0)
            score += impact
            factors.append({
                "factor": "Repeated Head Movement",
                "count": head_count,
                "impact": impact,
                "note": "Frequent head position shifts outside expected screen focus area.",
            })

        # 4. Audio Anomaly / Speech Activity
        audio_count = session.total_audio_anomaly_count
        if audio_count >= 2:
            impact = min(20.0, audio_count * 5.0)
            score += impact
            factors.append({
                "factor": "Audio Activity",
                "count": audio_count,
                "impact": impact,
                "note": "Elevated microphone activity or speech patterns detected in examination environment.",
            })

        # 5. Integrate Browser & Security Events (Phase 22 Lockdown Events)
        attempt_events = db.query(AttemptEvent).filter(AttemptEvent.attempt_id == session.attempt_id).all()
        focus_losses = sum(1 for e in attempt_events if e.event_type in ["WINDOW_FOCUS_LOST", "WINDOW_BLUR", "TAB_HIDDEN", "PAGE_HIDDEN"])
        fullscreen_exits = sum(1 for e in attempt_events if e.event_type == "FULLSCREEN_EXIT")

        if focus_losses >= 3:
            impact = min(20.0, focus_losses * 4.0)
            score += impact
            factors.append({
                "factor": "Browser Focus Loss",
                "count": focus_losses,
                "impact": impact,
                "note": "Candidate navigated away from examination window.",
            })

        if fullscreen_exits >= 1:
            impact = min(15.0, fullscreen_exits * 8.0)
            score += impact
            factors.append({
                "factor": "Fullscreen Window Exit",
                "count": fullscreen_exits,
                "impact": impact,
                "note": "Candidate exited mandated browser fullscreen mode.",
            })

        # 6. Poor Lighting Penalty Discount (Avoid false accusations when room is dim)
        if session.lighting_condition == "poor" and score > 20:
            score = max(15.0, score * 0.75)  # 25% discount due to lighting uncertainty
            factors.append({
                "factor": "Lighting Uncertainty Discount",
                "impact": -10,
                "note": "Suboptimal ambient lighting observed; algorithm reduced confidence.",
            })

        # Cap score between 0 and 100
        final_score = min(100.0, max(0.0, score))
        session.ai_risk_score = Decimal(str(round(final_score, 2)))

        # Classification mapping
        if final_score < 25.0:
            session.ai_risk_level = "LOW"
            session.ai_classification = "NORMAL"
        elif final_score < 50.0:
            session.ai_risk_level = "MEDIUM"
            session.ai_classification = "REQUIRES_ATTENTION" if (mult_count > 0 or focus_losses > 0) else "TECHNICAL_INTERRUPTION"
        elif final_score < 75.0:
            session.ai_risk_level = "HIGH"
            session.ai_classification = "POTENTIALLY_SUSPICIOUS"
        else:
            session.ai_risk_level = "CRITICAL"
            session.ai_classification = "CRITICAL_REVIEW"

        session.risk_factors = factors

    # -------------------------------------------------------------------------
    # 4. Human Decision Workflow & Incident Review
    # -------------------------------------------------------------------------
    @staticmethod
    def review_incident(
        db: Session,
        session_id: uuid.UUID,
        req: ProctoringIncidentReviewRequest,
        admin: Admin,
    ) -> ProctoringIncidentReviewResponse:
        session = db.query(ProctoringSession).filter(ProctoringSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Proctoring session not found")

        # Verify admin has quiz access
        AIProctoringService.check_quiz_access(db, admin, session.quiz_id)

        now = datetime.now(timezone.utc)
        valid_decisions = ["confirmed_concern", "not_a_violation", "technical_issue", "inconclusive", "escalated"]
        if req.decision not in valid_decisions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision '{req.decision}'. Must be one of {valid_decisions}",
            )

        review = ProctoringIncidentReview(
            id=uuid.uuid4(),
            session_id=session.id,
            reviewer_id=admin.id,
            decision=req.decision,
            justification=req.justification.strip(),
            risk_score_at_review=session.ai_risk_score,
            classification_at_review=session.ai_classification,
            action_taken=req.action_taken or "noted",
            created_at=now,
        )
        db.add(review)

        # Update session review state
        if req.decision in ["not_a_violation", "technical_issue"]:
            session.review_status = "REVIEWED_PASSED"
        elif req.decision == "confirmed_concern":
            session.review_status = "REVIEWED_FLAGGED"
        else:
            session.review_status = "INCONCLUSIVE"

        session.reviewer_decision = req.decision
        session.reviewer_id = admin.id
        session.reviewed_at = now
        session.reviewer_notes = req.justification.strip()

        # If confirmed concern, record formal ExaminationIncident for records
        if req.decision == "confirmed_concern":
            date_str = now.strftime("%Y%m%d")
            rand_code = uuid.uuid4().hex[:4].upper()
            incident = ExaminationIncident(
                id=uuid.uuid4(),
                incident_code=f"INC-{date_str}-{rand_code}",
                quiz_id=session.quiz_id,
                student_id=session.student_id,
                attempt_id=session.attempt_id,
                category="security_concern",
                severity="high" if session.ai_risk_level == "HIGH" else "critical",
                status="ASSIGNED",
                title=f"Proctor Review: {session.ai_classification}",
                description=f"Confirmed after human review: {req.justification.strip()} (Score: {session.ai_risk_score})",
                reported_by=admin.id,
                assigned_to=admin.id,
            )
            db.add(incident)

        db.commit()
        db.refresh(review)

        return ProctoringIncidentReviewResponse(
            id=review.id,
            session_id=review.session_id,
            reviewer_id=admin.id,
            reviewer_name=admin.full_name or admin.email,
            decision=review.decision,
            justification=review.justification,
            risk_score_at_review=float(review.risk_score_at_review or 0.0),
            classification_at_review=review.classification_at_review,
            action_taken=review.action_taken,
            created_at=_ensure_utc(review.created_at),
        )

    # -------------------------------------------------------------------------
    # 5. Live Invigilator Proctoring Dashboard & Telemetry Feed
    # -------------------------------------------------------------------------
    @staticmethod
    def get_dashboard_overview(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
    ) -> ProctoringDashboardOverviewResponse:
        AIProctoringService.check_quiz_access(db, admin, quiz_id)

        now = datetime.now(timezone.utc)
        sessions = db.query(ProctoringSession).options(
            joinedload(ProctoringSession.student).joinedload(Student.profile),
            joinedload(ProctoringSession.attempt),
        ).filter(ProctoringSession.quiz_id == quiz_id).all()

        candidates_list = []
        active_now = 0
        nominal_cnt = 0
        attention_cnt = 0
        critical_cnt = 0

        for s in sessions:
            st = s.student
            att = s.attempt
            att_status = att.status if att else "unknown"

            # Check heartbeat recency (active if within 45s)
            hb = _ensure_utc(s.last_heartbeat_at)
            is_active = (now - hb).total_seconds() <= 45 if hb else False
            if is_active and att_status == "in_progress":
                active_now += 1

            if s.ai_risk_level == "LOW":
                nominal_cnt += 1
            elif s.ai_risk_level in ["MEDIUM", "HIGH"]:
                attention_cnt += 1
            elif s.ai_risk_level == "CRITICAL":
                critical_cnt += 1

            reg_num = getattr(st, "register_number", None)
            if not reg_num and st and st.profile:
                reg_num = getattr(st.profile, "student_identifier", getattr(st.profile, "register_number", None))

            candidates_list.append(ProctoringDashboardCandidateItem(
                session_id=s.id,
                attempt_id=s.attempt_id,
                student_id=s.student_id,
                student_name=st.full_name if st else "Candidate",
                register_number=reg_num,
                email=st.email if st else "",
                attempt_status=att_status,
                camera_status=s.camera_status,
                microphone_status=s.microphone_status,
                lighting_condition=s.lighting_condition,
                face_presence_state=s.face_presence_state,
                head_position_state=s.head_position_state,
                multiple_faces_detected=s.multiple_faces_detected,
                audio_level_state=s.audio_level_state,
                ai_risk_score=float(s.ai_risk_score or 0.0),
                ai_risk_level=s.ai_risk_level,
                ai_classification=s.ai_classification,
                review_status=s.review_status,
                reviewer_decision=s.reviewer_decision,
                total_events=s.total_proctoring_events,
                last_heartbeat_at=_ensure_utc(s.last_heartbeat_at),
                is_accommodated=s.is_accommodated_exempt,
            ))

        # Count unresolved alerts
        unresolved_alerts = db.query(func.count(MonitoringAlert.id)).filter(
            MonitoringAlert.quiz_id == quiz_id,
            MonitoringAlert.alert_type == "PROCTORING_RISK_SPIKE",
            MonitoringAlert.is_resolved == False,
        ).scalar() or 0

        return ProctoringDashboardOverviewResponse(
            quiz_id=quiz_id,
            total_proctored_candidates=len(sessions),
            active_now=active_now,
            nominal_count=nominal_cnt,
            requires_attention_count=attention_cnt,
            critical_review_count=critical_cnt,
            unresolved_alerts_count=unresolved_alerts,
            candidates=candidates_list,
        )

    @staticmethod
    def get_candidate_session_details(
        db: Session,
        session_id: uuid.UUID,
        admin: Admin,
    ) -> Dict[str, Any]:
        session = db.query(ProctoringSession).options(
            joinedload(ProctoringSession.student).joinedload(Student.profile),
            joinedload(ProctoringSession.attempt),
            joinedload(ProctoringSession.events),
            joinedload(ProctoringSession.reviews).joinedload(ProctoringIncidentReview.reviewer),
        ).filter(ProctoringSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Proctoring session not found")

        AIProctoringService.check_quiz_access(db, admin, session.quiz_id)

        st = session.student
        reg_num = getattr(st, "register_number", None)
        if not reg_num and st and st.profile:
            reg_num = getattr(st.profile, "student_identifier", getattr(st.profile, "register_number", None))

        events_list = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "confidence_score": float(e.confidence_score or 0.85),
                "duration_seconds": e.duration_seconds,
                "details": e.details or {},
                "occurred_at": _ensure_utc(e.occurred_at).isoformat() if e.occurred_at else None,
            }
            for e in sorted(session.events, key=lambda x: x.occurred_at or datetime.min, reverse=True)[:100]
        ]

        reviews_list = [
            {
                "id": str(r.id),
                "reviewer_name": r.reviewer.full_name or r.reviewer.email if r.reviewer else "Administrator",
                "decision": r.decision,
                "justification": r.justification,
                "risk_score_at_review": float(r.risk_score_at_review or 0.0),
                "classification_at_review": r.classification_at_review,
                "action_taken": r.action_taken,
                "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None,
            }
            for r in session.reviews
        ]

        return {
            "session_id": str(session.id),
            "attempt_id": str(session.attempt_id),
            "quiz_id": str(session.quiz_id),
            "student_id": str(session.student_id),
            "student_name": st.full_name if st else "Candidate",
            "register_number": reg_num,
            "email": st.email if st else "",
            "status": session.status,
            "camera_status": session.camera_status,
            "microphone_status": session.microphone_status,
            "lighting_condition": session.lighting_condition,
            "face_presence_state": session.face_presence_state,
            "head_position_state": session.head_position_state,
            "multiple_faces_detected": session.multiple_faces_detected,
            "audio_level_state": session.audio_level_state,
            "total_face_absent_count": session.total_face_absent_count,
            "total_multiple_face_count": session.total_multiple_face_count,
            "total_head_movement_count": session.total_head_movement_count,
            "total_audio_anomaly_count": session.total_audio_anomaly_count,
            "ai_risk_score": float(session.ai_risk_score or 0.0),
            "ai_risk_level": session.ai_risk_level,
            "ai_classification": session.ai_classification,
            "ai_confidence": float(session.ai_confidence or 0.90),
            "risk_factors": session.risk_factors or [],
            "review_status": session.review_status,
            "reviewer_decision": session.reviewer_decision,
            "reviewer_notes": session.reviewer_notes,
            "reviewed_at": _ensure_utc(session.reviewed_at).isoformat() if session.reviewed_at else None,
            "recording_consent_given": session.recording_consent_given,
            "started_at": _ensure_utc(session.started_at).isoformat() if session.started_at else None,
            "last_heartbeat_at": _ensure_utc(session.last_heartbeat_at).isoformat() if session.last_heartbeat_at else None,
            "events": events_list,
            "reviews": reviews_list,
        }

    # -------------------------------------------------------------------------
    # 6. Real-time Proctoring Alerts
    # -------------------------------------------------------------------------
    @staticmethod
    def list_proctoring_alerts(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
    ) -> List[ProctoringAlertItem]:
        AIProctoringService.check_quiz_access(db, admin, quiz_id)

        alerts = db.query(MonitoringAlert).options(
            joinedload(MonitoringAlert.student)
        ).filter(
            MonitoringAlert.quiz_id == quiz_id,
            MonitoringAlert.alert_type == "PROCTORING_RISK_SPIKE",
        ).order_by(desc(MonitoringAlert.created_at)).limit(50).all()

        results = []
        for a in alerts:
            st_name = a.student.full_name if a.student else "Candidate"
            sess = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == a.attempt_id).first()
            sess_id = sess.id if sess else uuid.uuid4()
            results.append(ProctoringAlertItem(
                id=a.id,
                session_id=sess_id,
                quiz_id=a.quiz_id,
                student_id=a.student_id or uuid.uuid4(),
                student_name=st_name,
                alert_type=a.alert_type,
                severity=a.priority,
                message=a.title,
                details=a.details,
                occurred_at=_ensure_utc(a.created_at),
                acknowledged=bool(a.is_acknowledged or a.is_resolved),
            ))
        return results

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: uuid.UUID, admin: Admin) -> Dict[str, Any]:
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        AIProctoringService.check_quiz_access(db, admin, alert.quiz_id)

        alert.is_acknowledged = True
        alert.acknowledged_by = admin.id
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "success", "alert_id": str(alert.id), "acknowledged": True}
