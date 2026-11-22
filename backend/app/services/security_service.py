"""
QUIZVERSE Phase 14 Advanced Examination Security & Anti-Cheating Service
Implements centralized policy management, transparent student notices,
rate-limited event collection, deterministic question randomization,
server-side risk evaluation, alert aggregation, and administrator investigations.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import uuid
import secrets
import hashlib
import json
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, desc, select
from fastapi import HTTPException, status

from backend.app.models.security_audit import (
    ExaminationSecurityPolicy,
    SecurityEvent,
    SecurityAlert,
    SecurityInvestigationNote,
    AuditLog,
    BrowserCompatibilityRecord,
    WatermarkSession,
    CaptureCapabilityReport,
)
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptEvent,
    AttemptSession,
)
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student, StudentProfile
from backend.app.models.auth_rbac import Admin
from backend.app.schemas.security import (
    SecurityPolicyCreateRequest,
    SecurityPolicyUpdateRequest,
    SecurityPolicyResponse,
    SecurityNoticeResponse,
    SecurityEventItem,
    SecurityEventSubmitRequest,
    SecurityEventSubmitResponse,
    SecurityAlertResponse,
    SecurityAlertListResponse,
    SecurityAlertUpdateRequest,
    InvestigationNoteCreateRequest,
    InvestigationNoteResponse,
    InvestigationTimelineItemResponse,
    InvestigationDetailResponse,
    SecurityDashboardSummaryResponse,
    SecurityRetentionPurgeResponse,
    BrowserCompatibilityCheckItem,
    BrowserCompatibilitySubmitRequest,
    BrowserCompatibilityResponse,
    WatermarkSessionResponse,
    WatermarkVerificationRequest,
    WatermarkVerificationResponse,
    CaptureCapabilitySubmitRequest,
    CaptureCapabilityResponse,
    CaptureSignalSubmitRequest,
    CaptureSignalResponse,
)
from backend.app.services.audit_service import log_audit_event


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _mask_identifier(ident: Optional[str]) -> str:
    if not ident:
        return "N/A"
    if len(ident) <= 4:
        return "****"
    return "*" * (len(ident) - 4) + ident[-4:]


def is_super_admin(admin: Admin) -> bool:
    if getattr(admin, "is_super_admin", False):
        return True
    for r in getattr(admin, "roles", []):
        r_name = getattr(r, "role_name", getattr(r, "name", ""))
        if "super" in r_name.lower():
            return True
    return False


def check_quiz_access(db: Session, admin: Admin, quiz_id: uuid.UUID) -> bool:
    """Verifies whether admin is super admin or creator / assigned to this quiz."""
    if is_super_admin(admin):
        return True
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return False
    if quiz.created_by == admin.id:
        return True
    from backend.app.models.auth_rbac import AdminQuizAssignment
    assignment = db.query(AdminQuizAssignment).filter(
        AdminQuizAssignment.admin_id == admin.id,
        AdminQuizAssignment.quiz_id == quiz_id,
    ).first()
    return assignment is not None


class SecurityService:

    # -----------------------------------------------------------------------
    # 1. Security Policy Management
    # -----------------------------------------------------------------------

    @staticmethod
    def get_platform_default_policy(db: Session) -> ExaminationSecurityPolicy:
        """Retrieves or creates the platform-level default security policy."""
        policy = db.query(ExaminationSecurityPolicy).filter(
            ExaminationSecurityPolicy.quiz_id.is_(None)
        ).first()

        if not policy:
            policy = ExaminationSecurityPolicy(
                quiz_id=None,
                policy_scope="platform",
                track_tab_switch=True,
                track_focus_loss=True,
                require_fullscreen=False,
                track_fullscreen_exit=True,
                block_copy_paste=False,
                track_copy_paste=True,
                block_context_menu=True,
                track_page_reload=True,
                enable_watermark=True,
                watermark_pattern="QUIZVERSE | {student_name} | {masked_reg} | {attempt_id}",
                max_tab_switches_warning=2,
                max_tab_switches_critical=5,
                max_focus_losses_warning=3,
                max_fullscreen_exits_warning=2,
                single_session_enforced=True,
                allow_session_recovery=True,
                randomize_question_order=True,
                randomize_option_order=True,
                student_notice_text=None,
                student_acknowledgement_required=True,
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    @staticmethod
    def get_effective_policy(db: Session, quiz_id: Optional[uuid.UUID] = None) -> ExaminationSecurityPolicy:
        """
        Retrieves the effective policy for a quiz.
        If quiz has a specific override, return it; otherwise return platform default.
        """
        if quiz_id:
            policy = db.query(ExaminationSecurityPolicy).filter(
                ExaminationSecurityPolicy.quiz_id == quiz_id
            ).first()
            if policy:
                return policy
        return SecurityService.get_platform_default_policy(db)

    @staticmethod
    def save_quiz_policy(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID],
        req: SecurityPolicyCreateRequest,
    ) -> ExaminationSecurityPolicy:
        """
        Creates or updates a security policy override.
        User Admin can only configure policies for quizzes they own/manage.
        Platform default (`quiz_id is None`) requires Super Admin.
        """
        if quiz_id is None:
            if not is_super_admin(admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Super Administrators can modify platform default security policies."
                )
        else:
            if not check_quiz_access(db, admin, quiz_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have administrative permission to modify security policies for this quiz."
                )

        existing = db.query(ExaminationSecurityPolicy).filter(
            ExaminationSecurityPolicy.quiz_id == quiz_id if quiz_id else ExaminationSecurityPolicy.quiz_id.is_(None)
        ).first()

        now = datetime.now(timezone.utc)
        if existing:
            for field, val in req.model_dump(exclude_unset=True).items():
                if field not in ["id", "quiz_id", "created_at", "updated_at", "created_by"]:
                    setattr(existing, field, val)
            existing.updated_at = now
            policy = existing
        else:
            policy = ExaminationSecurityPolicy(
                quiz_id=quiz_id,
                policy_scope="platform" if quiz_id is None else "quiz",
                created_by=admin.id,
                created_at=now,
                updated_at=now,
                **req.model_dump(exclude={"quiz_id"}),
            )
            db.add(policy)

        db.commit()
        db.refresh(policy)

        # Audit policy change
        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="SECURITY_POLICY_SAVED",
            entity_type="ExaminationSecurityPolicy",
            entity_id=str(policy.id),
            details={"quiz_id": str(quiz_id) if quiz_id else None, "policy_scope": policy.policy_scope},
        )
        return policy

    # -----------------------------------------------------------------------
    # 2. Transparent Student Notice & Acknowledgement
    # -----------------------------------------------------------------------

    @staticmethod
    def get_student_security_notice(
        db: Session,
        quiz_id: uuid.UUID,
        student_id: Optional[uuid.UUID] = None,
        attempt_id: Optional[uuid.UUID] = None,
    ) -> SecurityNoticeResponse:
        """Provides full transparency to candidate regarding what events are monitored."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        policy = SecurityService.get_effective_policy(db, quiz_id)

        candidate_name = None
        masked_ident = None
        if student_id:
            stud = db.query(Student).options(joinedload(Student.profile)).filter(Student.id == student_id).first()
            if stud:
                candidate_name = stud.full_name
                if stud.profile and stud.profile.student_identifier:
                    masked_ident = _mask_identifier(stud.profile.student_identifier)

        watermark_text = None
        if policy.enable_watermark and candidate_name:
            att_slug = str(attempt_id)[:8].upper() if attempt_id else "PREVIEW"
            watermark_text = policy.watermark_pattern.format(
                student_name=candidate_name,
                masked_reg=masked_ident or "STUDENT",
                attempt_id=att_slug,
            )

        notice_text = policy.student_notice_text or (
            "This examination interface employs integrity safeguards. "
            "For academic verification, the system monitors tab switching, window focus changes, "
            "and full-screen continuity. Clipboard copying and context menu actions may be restricted. "
            "No personal files, camera, microphone, or unrelated browser tabs are ever accessed."
        )

        return SecurityNoticeResponse(
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            track_tab_switch=policy.track_tab_switch,
            track_focus_loss=policy.track_focus_loss,
            require_fullscreen=policy.require_fullscreen,
            track_fullscreen_exit=policy.track_fullscreen_exit,
            block_copy_paste=policy.block_copy_paste,
            track_copy_paste=policy.track_copy_paste,
            block_context_menu=policy.block_context_menu,
            enable_watermark=policy.enable_watermark,
            student_acknowledgement_required=policy.student_acknowledgement_required,
            notice_text=notice_text,
            watermark_text=watermark_text,
            candidate_name=candidate_name,
            masked_identifier=masked_ident,
        )

    @staticmethod
    def acknowledge_monitoring(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Records candidate consent/acknowledgement of examination monitoring."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        now = datetime.now(timezone.utc)
        attempt.monitoring_acknowledged_at = now
        db.commit()

        return {
            "success": True,
            "attempt_id": attempt.id,
            "acknowledged_at": now,
            "message": "Security and monitoring notice acknowledged successfully.",
        }

    @staticmethod
    def record_browser_compatibility(
        db: Session,
        quiz_id: uuid.UUID,
        req: BrowserCompatibilitySubmitRequest,
        student_id: Optional[uuid.UUID] = None,
        attempt_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BrowserCompatibilityResponse:
        """Saves pre-flight browser compatibility test results and determines if candidate may proceed."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        has_action_required = any(c.status in ["action_required", "unsupported"] for c in req.checks)
        has_warning = any(c.status == "warning" for c in req.checks)

        if has_action_required:
            overall = "ACTION_REQUIRED"
            can_proceed = False
            msg = "One or more critical browser security checks failed. Please address required items before entering."
        elif has_warning:
            overall = "WARNING"
            can_proceed = True
            msg = "Some browser security warnings were detected, but you may proceed to the examination."
        else:
            overall = "PASSED"
            can_proceed = True
            msg = "All browser security compatibility checks passed successfully."

        checks_json = [c.model_dump() for c in req.checks]

        record = BrowserCompatibilityRecord(
            attempt_id=attempt_id or req.attempt_id,
            quiz_id=quiz_id,
            student_id=student_id,
            session_id=session_id,
            browser_name=req.browser_name,
            browser_version=req.browser_version,
            os_name=req.os_name,
            os_version=req.os_version,
            device_type=req.device_type,
            is_secure_context=req.is_secure_context,
            javascript_enabled=req.javascript_enabled,
            fullscreen_supported=req.fullscreen_supported,
            visibility_api_supported=req.visibility_api_supported,
            storage_available=req.storage_available,
            screen_width=req.screen_width,
            screen_height=req.screen_height,
            viewport_width=req.viewport_width,
            viewport_height=req.viewport_height,
            network_online=req.network_online,
            network_downlink=Decimal(str(req.network_downlink)) if req.network_downlink is not None else None,
            network_rtt=req.network_rtt,
            is_seb_detected=req.is_seb_detected,
            checks_summary=checks_json,
            overall_status=overall,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(record)

        if (attempt_id or req.attempt_id) and not can_proceed:
            eff_attempt_id = attempt_id or req.attempt_id
            ev = SecurityEvent(
                student_id=student_id,
                quiz_id=quiz_id,
                attempt_id=eff_attempt_id,
                event_category="COMPATIBILITY",
                severity="MEDIUM",
                event_name="COMPATIBILITY_FAILURE",
                description=f"Candidate environment compatibility failure: {overall}",
                event_metadata={"checks": checks_json, "device_type": req.device_type},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(ev)

        db.commit()
        db.refresh(record)

        return BrowserCompatibilityResponse(
            success=True,
            record_id=record.id,
            overall_status=overall,
            can_proceed=can_proceed,
            message=msg,
            checks=req.checks,
        )

    # -----------------------------------------------------------------------
    # 3. Secure Event Collection & Server Validation
    # -----------------------------------------------------------------------

    @staticmethod
    def record_security_events(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: SecurityEventSubmitRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SecurityEventSubmitResponse:
        """
        Receives browser security events, validates ownership, enforces rate limiting,
        deduplicates events, stores authoritative records, updates risk scores,
        and generates alerts when warning/critical thresholds are crossed.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this attempt")

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)

        # Immutability check
        if attempt.is_immutable or attempt.status in ["submitted", "evaluated"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Examination attempt is finalized. Security events cannot be posted for submitted exams."
            )

        if deadline and now > deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Examination attempt has expired."
            )

        policy = SecurityService.get_effective_policy(db, attempt.quiz_id)

        # Rate limiting: max 200 security events per attempt per hour
        recent_count = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.attempt_id == attempt.id,
            SecurityEvent.created_at >= (now - timedelta(minutes=5))
        ).scalar() or 0

        if recent_count > 150:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Security event rate limit exceeded. Excess events throttled."
            )

        allowed_categories = {
            "TAB_SWITCH", "FOCUS_LOSS", "FULLSCREEN", "CLIPBOARD", "CONTEXT_MENU", "NAVIGATION", "SESSION"
        }

        recorded_records = []
        warnings = []

        # Find existing sequence number
        last_seq = db.query(func.max(SecurityEvent.sequence_number)).filter(
            SecurityEvent.attempt_id == attempt.id
        ).scalar() or 0

        # Deduplication tracking for current batch
        seen_in_batch = set()

        for item in req.events:
            cat = (item.event_category or "GENERAL").upper()
            if cat not in allowed_categories:
                cat = "GENERAL"

            # Deduplication: check network retries and duplicate transmissions
            if item.sequence_number:
                dup_seq = db.query(SecurityEvent).filter(
                    SecurityEvent.attempt_id == attempt.id,
                    SecurityEvent.sequence_number == item.sequence_number
                ).first()
                if dup_seq:
                    continue

            if item.client_timestamp:
                dup_ts = db.query(SecurityEvent).filter(
                    SecurityEvent.attempt_id == attempt.id,
                    SecurityEvent.event_name == item.event_name,
                    SecurityEvent.client_timestamp == _ensure_utc(item.client_timestamp)
                ).first()
                if dup_ts:
                    continue

            batch_key = (item.event_name.upper(), str(item.client_timestamp), item.sequence_number)
            if batch_key in seen_in_batch:
                continue
            seen_in_batch.add(batch_key)

            last_seq += 1
            severity = SecurityService._classify_event_severity(item.event_name, cat)

            sec_event = SecurityEvent(
                student_id=attempt.student_id,
                quiz_id=attempt.quiz_id,
                attempt_id=attempt.id,
                event_category=cat,
                event_name=item.event_name.upper(),
                severity=severity,
                description=f"Client event: {item.event_name} in category {cat}",
                client_timestamp=_ensure_utc(item.client_timestamp),
                event_metadata=item.event_metadata or ({"duration_ms": item.duration_ms} if item.duration_ms else {}),
                sequence_number=last_seq,
                session_id=attempt.active_session_token,
                ip_address=client_ip,
                user_agent=user_agent,
                created_at=now,
            )
            db.add(sec_event)
            recorded_records.append(sec_event)

        db.flush()

        # Re-evaluate risk score and alerts
        new_risk_score, new_risk_level = SecurityService.evaluate_attempt_risk(db, attempt)
        attempt.risk_score = Decimal(str(new_risk_score))
        attempt.risk_level = new_risk_level

        # Evaluate and aggregate alerts based on policy
        active_alerts_count, alert_warnings = SecurityService._evaluate_alerts(db, attempt, policy, now)
        warnings.extend(alert_warnings)

        db.commit()

        return SecurityEventSubmitResponse(
            success=True,
            recorded_count=len(recorded_records),
            current_risk_score=float(new_risk_score),
            current_risk_level=new_risk_level,
            active_alerts_count=active_alerts_count,
            warnings=warnings,
        )

    @staticmethod
    def _classify_event_severity(event_name: str, category: str) -> str:
        """Classifies individual raw events into LOW, MEDIUM, or HIGH."""
        high_events = {
            "SESSION_CONFLICT",
            "UNAUTHORIZED_SUBMISSION_ATTEMPT",
            "SCREEN_RECORDING_SIGNAL_DETECTED",
            "CONTENT_EXPORT_ATTEMPT",
        }
        med_events = {
            "FULLSCREEN_EXIT",
            "COPY_ATTEMPT",
            "PASTE_ATTEMPT",
            "CUT_ATTEMPT",
            "RESTRICTED_COPY_ATTEMPT",
            "RESTRICTED_PASTE_ATTEMPT",
            "PRINT_ATTEMPT",
            "PRINT_RESTRICTION_TRIGGERED",
            "NAVIGATION_ATTEMPT",
            "COMPATIBILITY_FAILURE",
            "SCREENSHOT_SIGNAL_DETECTED",
            "CAPTURE_API_ACTIVITY",
            "WATERMARK_VALIDATION_FAILED",
        }
        info_events = {
            "TAB_VISIBLE",
            "WINDOW_FOCUS_GAINED",
            "WINDOW_FOCUS",
            "PAGE_VISIBLE",
            "FULLSCREEN_ENTER",
            "NETWORK_RECONNECTED",
            "WATERMARK_RENDERED",
            "WATERMARK_CONFIGURATION_CHANGED",
        }
        name_up = event_name.upper()

        if name_up in high_events:
            return "HIGH"
        if name_up in med_events:
            return "MEDIUM"
        if name_up in info_events:
            return "INFO"
        return "LOW"

    # -----------------------------------------------------------------------
    # 4. Risk Assessment Engine & Alert Aggregator
    # -----------------------------------------------------------------------

    @staticmethod
    def evaluate_attempt_risk(db: Session, attempt: ExaminationAttempt) -> Tuple[float, str]:
        """
        Rule-based, reproducible risk scoring calculated strictly on the backend:
        - Tab Hidden: 5 pts
        - Focus Lost: 3 pts
        - Fullscreen Exit: 10 pts
        - Copy Attempt: 8 pts
        - Paste Attempt: 8 pts
        - Cut Attempt: 8 pts
        - Context Menu: 3 pts
        - Print / Navigation Attempt: 6 pts
        - Session Conflict: 15 pts

        Cumulative Score Mapping:
        0 - 25: LOW
        26 - 55: MEDIUM
        56+: HIGH

        CRITICAL REQUIREMENT: Score is strictly informational; never auto-disqualifies.
        """
        events = db.query(SecurityEvent).filter(SecurityEvent.attempt_id == attempt.id).all()

        score = 0.0
        for ev in events:
            name = (ev.event_name or "").upper()
            if name in ["TAB_HIDDEN", "TAB_SWITCH", "PAGE_HIDDEN"]:
                score += 5.0
            elif name in ["WINDOW_FOCUS_LOST", "WINDOW_BLUR"]:
                score += 3.0
            elif name == "FULLSCREEN_EXIT":
                score += 10.0
            elif name in ["COPY_ATTEMPT", "PASTE_ATTEMPT", "CUT_ATTEMPT", "RESTRICTED_COPY_ATTEMPT", "RESTRICTED_PASTE_ATTEMPT"]:
                score += 8.0
            elif name in ["CONTEXT_MENU", "CONTEXT_MENU_ATTEMPT"]:
                score += 3.0
            elif name in ["PRINT_ATTEMPT", "NAVIGATION_ATTEMPT", "PRINT_RESTRICTION_TRIGGERED"]:
                score += 6.0
            elif name in ["SCREENSHOT_SIGNAL_DETECTED", "SCREENSHOT_SIGNAL", "SCREENSHOT_ATTEMPT"]:
                score += 8.0
            elif name in ["SCREEN_RECORDING_SIGNAL_DETECTED", "SCREEN_RECORDING_SIGNAL"]:
                score += 15.0
            elif name in ["APP_INTERRUPTION", "NATIVE_APP_BACKGROUND"]:
                score += 5.0
            elif name in ["ROOT_RISK_SIGNAL", "ROOT_DETECTED"]:
                score += 25.0
            elif name in ["KIOSK_MODE_STATUS_CHANGED", "KIOSK_VIOLATION"]:
                score += 15.0
            elif name == "CAPTURE_API_ACTIVITY":
                score += 10.0
            elif name == "WATERMARK_VALIDATION_FAILED":
                score += 8.0
            elif name == "CONTENT_EXPORT_ATTEMPT":
                score += 12.0
            elif name == "SESSION_CONFLICT":
                score += 15.0
            elif name == "COMPATIBILITY_FAILURE":
                score += 10.0

        score = round(min(score, 100.0), 2)
        if score >= 56.0:
            level = "HIGH"
        elif score >= 26.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level

    @staticmethod
    def _evaluate_alerts(
        db: Session,
        attempt: ExaminationAttempt,
        policy: ExaminationSecurityPolicy,
        now: datetime,
    ) -> Tuple[int, List[str]]:
        """
        Aggregates recurring events into SecurityAlert records when policy thresholds are breached.
        Returns total active alerts count and student warning messages.
        """
        # Count event types
        tab_switches = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.attempt_id == attempt.id,
            SecurityEvent.event_name == "TAB_HIDDEN"
        ).scalar() or 0

        fullscreen_exits = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.attempt_id == attempt.id,
            SecurityEvent.event_name == "FULLSCREEN_EXIT"
        ).scalar() or 0

        clipboard_attempts = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.attempt_id == attempt.id,
            SecurityEvent.event_name.in_(["COPY_ATTEMPT", "PASTE_ATTEMPT", "CUT_ATTEMPT"])
        ).scalar() or 0

        warnings = []

        # 1. Tab switches alert
        if tab_switches >= policy.max_tab_switches_warning:
            sev = "HIGH" if tab_switches >= policy.max_tab_switches_critical else "MEDIUM"
            SecurityService._upsert_alert(
                db=db,
                attempt=attempt,
                alert_type="REPEATED_TAB_SWITCH",
                severity=sev,
                occurrences=tab_switches,
                now=now,
            )
            warnings.append(f"Warning: Tab switching detected ({tab_switches} times). Please stay on the examination page.")

        # 2. Fullscreen exit alert
        if policy.require_fullscreen and fullscreen_exits >= policy.max_fullscreen_exits_warning:
            SecurityService._upsert_alert(
                db=db,
                attempt=attempt,
                alert_type="FULLSCREEN_EXIT_EXCEEDED",
                severity="MEDIUM",
                occurrences=fullscreen_exits,
                now=now,
            )
            warnings.append(f"Warning: Full-screen mode has been exited ({fullscreen_exits} times). Return to full-screen mode.")

        # 3. Clipboard alert
        if clipboard_attempts >= 3:
            SecurityService._upsert_alert(
                db=db,
                attempt=attempt,
                alert_type="FREQUENT_CLIPBOARD_ATTEMPT",
                severity="MEDIUM",
                occurrences=clipboard_attempts,
                now=now,
            )
            warnings.append("Notice: Clipboard copy/paste is monitored during this examination.")

        # 4. Phase 22 Focus Loss Limit check
        max_focus = getattr(policy, "max_focus_loss_count", 5) or 5
        focus_losses = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.attempt_id == attempt.id,
            SecurityEvent.event_name.in_(["WINDOW_FOCUS_LOST", "WINDOW_BLUR", "PAGE_HIDDEN"])
        ).scalar() or 0

        if focus_losses >= max_focus:
            SecurityService._upsert_alert(
                db=db,
                attempt=attempt,
                alert_type="FOCUS_LOSS_EXCEEDED",
                severity="HIGH" if focus_losses >= (max_focus + 3) else "MEDIUM",
                occurrences=focus_losses,
                now=now,
            )
            warnings.append(f"Notice: Focus loss threshold reached ({focus_losses}/{max_focus}). This activity is recorded for invigilator review.")

        # 5. Fullscreen policy flag check
        fs_policy = getattr(policy, "fullscreen_exit_policy", "warning_only")
        if fs_policy in ["flag_review", "pause_exam"] and fullscreen_exits > 0:
            SecurityService._upsert_alert(
                db=db,
                attempt=attempt,
                alert_type="FULLSCREEN_POLICY_FLAGGED",
                severity="HIGH" if fs_policy == "pause_exam" else "MEDIUM",
                occurrences=fullscreen_exits,
                now=now,
            )

        active_count = db.query(func.count(SecurityAlert.id)).filter(
            SecurityAlert.attempt_id == attempt.id,
            SecurityAlert.status.in_(["UNREVIEWED", "UNDER_REVIEW"])
        ).scalar() or 0

        return active_count, warnings

    @staticmethod
    def _upsert_alert(
        db: Session,
        attempt: ExaminationAttempt,
        alert_type: str,
        severity: str,
        occurrences: int,
        now: datetime,
    ) -> SecurityAlert:
        """Finds or creates an alert for this attempt and alert_type."""
        alert = db.query(SecurityAlert).filter(
            SecurityAlert.attempt_id == attempt.id,
            SecurityAlert.alert_type == alert_type,
        ).first()

        if alert:
            alert.occurrences_count = occurrences
            alert.last_observed_at = now
            if severity == "HIGH":
                alert.severity = "HIGH"
        else:
            alert = SecurityAlert(
                attempt_id=attempt.id,
                quiz_id=attempt.quiz_id,
                student_id=attempt.student_id,
                alert_type=alert_type,
                severity=severity,
                occurrences_count=occurrences,
                first_observed_at=now,
                last_observed_at=now,
                status="UNREVIEWED",
                created_at=now,
                updated_at=now,
            )
            db.add(alert)
        db.flush()
        return alert

    # -----------------------------------------------------------------------
    # 5. Security Alerts Management (Admin Interface)
    # -----------------------------------------------------------------------

    @staticmethod
    def list_security_alerts(
        db: Session,
        admin: Admin,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        quiz_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SecurityAlertListResponse:
        """Lists security alerts respecting administrator RBAC permissions."""
        query = db.query(SecurityAlert).options(
            joinedload(SecurityAlert.quiz),
            joinedload(SecurityAlert.student).joinedload(Student.profile),
            joinedload(SecurityAlert.reviewer),
        )

        # RBAC scope isolation: User Admin only sees their quizzes
        if not is_super_admin(admin):
            from backend.app.models.auth_rbac import AdminQuizAssignment
            assigned_subquery = select(AdminQuizAssignment.quiz_id).filter(
                AdminQuizAssignment.admin_id == admin.id
            )
            query = query.join(Quiz, SecurityAlert.quiz_id == Quiz.id).filter(
                or_(Quiz.created_by == admin.id, SecurityAlert.quiz_id.in_(assigned_subquery))
            )

        if quiz_id:
            query = query.filter(SecurityAlert.quiz_id == quiz_id)

        if status_filter and status_filter.upper() != "ALL":
            query = query.filter(SecurityAlert.status == status_filter.upper())

        if severity_filter and severity_filter.upper() != "ALL":
            query = query.filter(SecurityAlert.severity == severity_filter.upper())

        if search:
            query = query.join(Student, SecurityAlert.student_id == Student.id).filter(
                or_(
                    Student.full_name.ilike(f"%{search}%"),
                    SecurityAlert.alert_type.ilike(f"%{search}%")
                )
            )

        total = query.count()
        alerts = query.order_by(SecurityAlert.last_observed_at.desc()).offset(offset).limit(limit).all()

        unreviewed = db.query(func.count(SecurityAlert.id)).filter(SecurityAlert.status == "UNREVIEWED").scalar() or 0
        med_high = db.query(func.count(SecurityAlert.id)).filter(SecurityAlert.severity.in_(["MEDIUM", "HIGH"])).scalar() or 0

        res_list = []
        for a in alerts:
            stud_name = a.student.full_name if a.student else "Unknown Student"
            masked_id = _mask_identifier(a.student.profile.student_identifier if a.student and a.student.profile else None)
            res_list.append(SecurityAlertResponse(
                id=a.id,
                attempt_id=a.attempt_id,
                quiz_id=a.quiz_id,
                quiz_title=a.quiz.title if a.quiz else None,
                student_id=a.student_id,
                student_name=stud_name,
                masked_identifier=masked_id,
                alert_type=a.alert_type,
                severity=a.severity,
                occurrences_count=a.occurrences_count,
                first_observed_at=_ensure_utc(a.first_observed_at),
                last_observed_at=_ensure_utc(a.last_observed_at),
                status=a.status,
                resolution_reason=a.resolution_reason,
                reviewed_by=a.reviewed_by,
                reviewed_by_name=a.reviewer.full_name if a.reviewer else None,
                reviewed_at=_ensure_utc(a.reviewed_at),
                created_at=_ensure_utc(a.created_at),
                updated_at=_ensure_utc(a.updated_at),
            ))

        return SecurityAlertListResponse(
            alerts=res_list,
            total=total,
            unreviewed_count=unreviewed,
            medium_or_high_count=med_high,
        )

    @staticmethod
    def update_alert_status(
        db: Session,
        admin: Admin,
        alert_id: uuid.UUID,
        req: SecurityAlertUpdateRequest,
    ) -> SecurityAlertResponse:
        """
        Updates an alert's review status (UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED).
        Appends a corresponding investigation note.
        """
        alert = db.query(SecurityAlert).options(
            joinedload(SecurityAlert.quiz),
            joinedload(SecurityAlert.student).joinedload(Student.profile),
            joinedload(SecurityAlert.reviewer),
        ).filter(SecurityAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security alert not found")

        if not check_quiz_access(db, admin, alert.quiz_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage alerts for this quiz."
            )

        now = datetime.now(timezone.utc)
        new_status = req.status.upper().replace(" ", "_")
        valid_statuses = [
            "NEW",
            "UNREVIEWED",
            "UNDER_REVIEW",
            "VERIFIED",
            "NOT_A_VIOLATION",
            "DISMISSED",
            "ESCALATED",
            "RESOLVED",
        ]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid alert status: {req.status}")

        alert.status = new_status
        alert.resolution_reason = req.resolution_reason
        alert.reviewed_by = admin.id
        alert.reviewed_at = now
        alert.updated_at = now

        # Add an audit note
        note = SecurityInvestigationNote(
            attempt_id=alert.attempt_id,
            alert_id=alert.id,
            admin_id=admin.id,
            note_text=req.resolution_reason or f"Status changed to {new_status} by {admin.full_name}",
            action_taken=new_status,
            created_at=now,
        )
        db.add(note)
        db.commit()
        db.refresh(alert)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="SECURITY_ALERT_UPDATED",
            entity_type="SecurityAlert",
            entity_id=str(alert.id),
            details={"new_status": new_status, "reason": req.resolution_reason},
        )

        return SecurityAlertResponse(
            id=alert.id,
            attempt_id=alert.attempt_id,
            quiz_id=alert.quiz_id,
            quiz_title=alert.quiz.title if alert.quiz else None,
            student_id=alert.student_id,
            student_name=alert.student.full_name if alert.student else None,
            masked_identifier=_mask_identifier(alert.student.profile.student_identifier if alert.student and alert.student.profile else None),
            alert_type=alert.alert_type,
            severity=alert.severity,
            occurrences_count=alert.occurrences_count,
            first_observed_at=_ensure_utc(alert.first_observed_at),
            last_observed_at=_ensure_utc(alert.last_observed_at),
            status=alert.status,
            resolution_reason=alert.resolution_reason,
            reviewed_by=alert.reviewed_by,
            reviewed_by_name=admin.full_name,
            reviewed_at=_ensure_utc(alert.reviewed_at),
            created_at=_ensure_utc(alert.created_at),
            updated_at=_ensure_utc(alert.updated_at),
        )

    # -----------------------------------------------------------------------
    # 6. Investigation Timeline & Notes
    # -----------------------------------------------------------------------

    @staticmethod
    def get_investigation_detail(
        db: Session,
        admin: Admin,
        attempt_id: uuid.UUID,
    ) -> InvestigationDetailResponse:
        """
        Retrieves chronological timeline, alerts, notes, and attempt state for investigation.
        Read-only event log; notes stored separately.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz),
            joinedload(ExaminationAttempt.student).joinedload(Student.profile),
            joinedload(ExaminationAttempt.security_events),
            joinedload(ExaminationAttempt.security_alerts).joinedload(SecurityAlert.reviewer),
            joinedload(ExaminationAttempt.investigation_notes).joinedload(SecurityInvestigationNote.admin),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        if not check_quiz_access(db, admin, attempt.quiz_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to investigate this attempt."
            )

        stud = attempt.student
        masked_id = _mask_identifier(stud.profile.student_identifier if stud and stud.profile else None)

        # Timeline combines security_events and lifecycle attempt_events
        timeline_items = []
        for ev in attempt.security_events:
            dur = None
            if ev.event_metadata and isinstance(ev.event_metadata, dict):
                dur = ev.event_metadata.get("duration_ms")
            timeline_items.append(InvestigationTimelineItemResponse(
                id=ev.id,
                event_category=ev.event_category,
                event_name=ev.event_name,
                severity=ev.severity,
                description=ev.description,
                client_timestamp=_ensure_utc(ev.client_timestamp),
                server_timestamp=_ensure_utc(ev.created_at),
                duration_ms=dur,
                sequence_number=ev.sequence_number,
                metadata=ev.event_metadata,
            ))

        # Sort chronologically by server timestamp
        timeline_items.sort(key=lambda t: t.server_timestamp)

        # Map alerts
        alert_items = []
        for a in attempt.security_alerts:
            alert_items.append(SecurityAlertResponse(
                id=a.id,
                attempt_id=a.attempt_id,
                quiz_id=a.quiz_id,
                quiz_title=attempt.quiz.title if attempt.quiz else None,
                student_id=a.student_id,
                student_name=stud.full_name if stud else None,
                masked_identifier=masked_id,
                alert_type=a.alert_type,
                severity=a.severity,
                occurrences_count=a.occurrences_count,
                first_observed_at=_ensure_utc(a.first_observed_at),
                last_observed_at=_ensure_utc(a.last_observed_at),
                status=a.status,
                resolution_reason=a.resolution_reason,
                reviewed_by=a.reviewed_by,
                reviewed_by_name=a.reviewer.full_name if a.reviewer else None,
                reviewed_at=_ensure_utc(a.reviewed_at),
                created_at=_ensure_utc(a.created_at),
                updated_at=_ensure_utc(a.updated_at),
            ))

        # Map notes
        note_items = []
        for n in attempt.investigation_notes:
            note_items.append(InvestigationNoteResponse(
                id=n.id,
                attempt_id=n.attempt_id,
                alert_id=n.alert_id,
                admin_id=n.admin_id,
                admin_name=n.admin.full_name if n.admin else None,
                note_text=n.note_text,
                action_taken=n.action_taken,
                created_at=_ensure_utc(n.created_at),
            ))

        return InvestigationDetailResponse(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            quiz_title=attempt.quiz.title if attempt.quiz else "Examination",
            student_id=attempt.student_id,
            student_name=stud.full_name if stud else "Unknown",
            masked_identifier=masked_id,
            attempt_status=attempt.status,
            started_at=_ensure_utc(attempt.started_at),
            deadline_at=_ensure_utc(attempt.deadline_at or attempt.expires_at),
            submitted_at=_ensure_utc(attempt.submitted_at),
            submission_reason=attempt.submission_reason,
            risk_score=float(attempt.risk_score or 0.0),
            risk_level=attempt.risk_level or "LOW",
            total_events_count=len(timeline_items),
            timeline=timeline_items,
            alerts=alert_items,
            notes=note_items,
        )

    @staticmethod
    def add_investigation_note(
        db: Session,
        admin: Admin,
        attempt_id: uuid.UUID,
        req: InvestigationNoteCreateRequest,
    ) -> InvestigationNoteResponse:
        """Appends a new investigation note without altering original security events."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        if not check_quiz_access(db, admin, attempt.quiz_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to add investigation notes to this attempt."
            )

        now = datetime.now(timezone.utc)
        note = SecurityInvestigationNote(
            attempt_id=attempt.id,
            alert_id=req.alert_id,
            admin_id=admin.id,
            note_text=req.note_text.strip(),
            action_taken=req.action_taken.upper(),
            created_at=now,
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        return InvestigationNoteResponse(
            id=note.id,
            attempt_id=note.attempt_id,
            alert_id=note.alert_id,
            admin_id=note.admin_id,
            admin_name=admin.full_name,
            note_text=note.note_text,
            action_taken=note.action_taken,
            created_at=_ensure_utc(note.created_at),
        )

    # -----------------------------------------------------------------------
    # 7. Administrator Security Dashboard Analytics
    # -----------------------------------------------------------------------

    @staticmethod
    def get_dashboard_summary(db: Session, admin: Admin) -> SecurityDashboardSummaryResponse:
        """Computes security metrics strictly from real database records within authorized scope."""
        base_query = db.query(SecurityEvent)
        alert_query = db.query(SecurityAlert)
        attempt_query = db.query(ExaminationAttempt)

        if not is_super_admin(admin):
            from backend.app.models.auth_rbac import AdminQuizAssignment
            assigned_subquery = select(AdminQuizAssignment.quiz_id).filter(
                AdminQuizAssignment.admin_id == admin.id
            )
            base_query = base_query.join(Quiz, SecurityEvent.quiz_id == Quiz.id).filter(
                or_(Quiz.created_by == admin.id, SecurityEvent.quiz_id.in_(assigned_subquery))
            )
            alert_query = alert_query.join(Quiz, SecurityAlert.quiz_id == Quiz.id).filter(
                or_(Quiz.created_by == admin.id, SecurityAlert.quiz_id.in_(assigned_subquery))
            )
            attempt_query = attempt_query.join(Quiz, ExaminationAttempt.quiz_id == Quiz.id).filter(
                or_(Quiz.created_by == admin.id, ExaminationAttempt.quiz_id.in_(assigned_subquery))
            )

        total_active = attempt_query.filter(ExaminationAttempt.status.in_(["started", "in_progress"])).count()
        total_events = base_query.count()
        low_sev = base_query.filter(SecurityEvent.severity == "LOW").count()
        med_sev = base_query.filter(SecurityEvent.severity == "MEDIUM").count()
        high_sev = base_query.filter(SecurityEvent.severity == "HIGH").count()

        unreviewed = alert_query.filter(SecurityAlert.status == "UNREVIEWED").count()
        resolved = alert_query.filter(SecurityAlert.status == "RESOLVED").count()
        under_investigation = alert_query.filter(SecurityAlert.status == "UNDER_REVIEW").count()
        session_conflicts = base_query.filter(SecurityEvent.event_category == "SESSION").count()

        # Category distribution
        cat_counts = db.query(SecurityEvent.event_category, func.count(SecurityEvent.id)).group_by(
            SecurityEvent.event_category
        ).all()
        cat_dist = {c: cnt for c, cnt in cat_counts}

        sev_dist = {"LOW": low_sev, "MEDIUM": med_sev, "HIGH": high_sev}

        # Recent alerts (top 5)
        recent_alerts_objs = alert_query.order_by(SecurityAlert.last_observed_at.desc()).limit(5).all()
        recent_alerts_res = []
        for a in recent_alerts_objs:
            recent_alerts_res.append(SecurityAlertResponse(
                id=a.id,
                attempt_id=a.attempt_id,
                quiz_id=a.quiz_id,
                quiz_title=a.quiz.title if a.quiz else None,
                student_id=a.student_id,
                student_name=a.student.full_name if a.student else None,
                masked_identifier=_mask_identifier(a.student.profile.student_identifier if a.student and a.student.profile else None),
                alert_type=a.alert_type,
                severity=a.severity,
                occurrences_count=a.occurrences_count,
                first_observed_at=_ensure_utc(a.first_observed_at),
                last_observed_at=_ensure_utc(a.last_observed_at),
                status=a.status,
                resolution_reason=a.resolution_reason,
                reviewed_by=a.reviewed_by,
                reviewed_by_name=a.reviewer.full_name if a.reviewer else None,
                reviewed_at=_ensure_utc(a.reviewed_at),
                created_at=_ensure_utc(a.created_at),
                updated_at=_ensure_utc(a.updated_at),
            ))

        return SecurityDashboardSummaryResponse(
            total_active_attempts=total_active,
            total_security_events=total_events,
            low_severity_events=low_sev,
            medium_severity_events=med_sev,
            high_severity_events=high_sev,
            unreviewed_alerts=unreviewed,
            resolved_alerts=resolved,
            attempts_under_investigation=under_investigation,
            session_conflicts_count=session_conflicts,
            event_categories_distribution=cat_dist,
            severity_distribution=sev_dist,
            recent_alerts=recent_alerts_res,
        )

    # -----------------------------------------------------------------------
    # 8. Privacy & Data Retention Purge
    # -----------------------------------------------------------------------

    @staticmethod
    def purge_retention_records(
        db: Session,
        admin: Admin,
        retention_days: int = 90,
        preserve_under_investigation: bool = True,
    ) -> SecurityRetentionPurgeResponse:
        """
        Super Admin only: Purges old security events older than retention_days.
        Preserves events associated with attempts currently under investigation or unresolved alerts.
        """
        if not is_super_admin(admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Administrators are authorized to run security retention purges."
            )

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        investigated_attempt_ids = set()
        if preserve_under_investigation:
            # Active unresolved alerts
            alert_att_ids = db.query(SecurityAlert.attempt_id).filter(
                SecurityAlert.status.in_(["UNREVIEWED", "UNDER_REVIEW"])
            ).all()
            for r in alert_att_ids:
                investigated_attempt_ids.add(r[0])

            # Notes
            note_att_ids = db.query(SecurityInvestigationNote.attempt_id).all()
            for r in note_att_ids:
                investigated_attempt_ids.add(r[0])

        query = db.query(SecurityEvent).filter(SecurityEvent.created_at < cutoff)
        if investigated_attempt_ids:
            query = query.filter(SecurityEvent.attempt_id.notin_(list(investigated_attempt_ids)))

        purged_count = query.delete(synchronize_session=False)
        db.commit()

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="SECURITY_RETENTION_PURGED",
            entity_type="SecurityEvent",
            entity_id=None,
            details={"purged_count": purged_count, "retention_days": retention_days, "cutoff": cutoff.isoformat()},
        )

        return SecurityRetentionPurgeResponse(
            success=True,
            purged_events_count=purged_count,
            retention_cutoff_date=cutoff,
            preserved_investigations_count=len(investigated_attempt_ids),
            message=f"Purged {purged_count} security events older than {retention_days} days. {len(investigated_attempt_ids)} active investigations preserved.",
        )

    # -----------------------------------------------------------------------
    # 10. Dynamic Student Watermark & Capture Signals (Phase 23)
    # -----------------------------------------------------------------------

    @staticmethod
    def generate_or_get_watermark_session(
        db: Session,
        attempt: ExaminationAttempt,
    ) -> WatermarkSession:
        """
        Retrieves or generates a tamper-resistant, server-authoritative WatermarkSession
        for the active examination attempt using authentic DB records.
        """
        session = db.query(WatermarkSession).filter(WatermarkSession.attempt_id == attempt.id).first()
        if session:
            return session

        quiz = attempt.quiz
        config = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == attempt.quiz_id).first()
        policy = db.query(ExaminationSecurityPolicy).filter(ExaminationSecurityPolicy.quiz_id == attempt.quiz_id).first()

        opacity = float(getattr(config, "watermark_opacity", getattr(policy, "watermark_opacity", 0.06)))
        font_size = int(getattr(config, "watermark_font_size", getattr(policy, "watermark_font_size", 12)))
        rotation_deg = int(getattr(config, "watermark_rotation_deg", getattr(policy, "watermark_rotation_deg", -25)))
        spacing_px = int(getattr(config, "watermark_spacing_px", getattr(policy, "watermark_spacing_px", 140)))
        update_interval_sec = int(getattr(config, "watermark_update_interval_sec", getattr(policy, "watermark_update_interval_sec", 30)))
        mask_student_id = bool(getattr(config, "watermark_mask_student_id", getattr(policy, "watermark_mask_student_id", True)))
        show_exam_id = bool(getattr(config, "watermark_show_exam_id", getattr(policy, "watermark_show_exam_id", True)))
        custom_prefix = getattr(config, "watermark_custom_text", getattr(policy, "watermark_custom_text", None))

        student = attempt.student
        student_name = student.full_name if student else "Candidate"
        raw_reg = None
        if student and getattr(student, "profile", None) and student.profile.student_identifier:
            raw_reg = student.profile.student_identifier
        elif student and getattr(student, "register_number", None):
            raw_reg = student.register_number
        if not raw_reg:
            raw_reg = f"STU-{str(attempt.student_id)[:4].upper()}" if attempt.student_id else "STU-0000"
        masked_reg = _mask_identifier(raw_reg) if mask_student_id else raw_reg

        institution_name = "QUIZVERSE"
        if student and getattr(student, "profile", None) and student.profile.institution:
            institution_name = student.profile.institution
        elif quiz and quiz.subject and getattr(quiz.subject, "curriculum", None):
            curriculum = quiz.subject.curriculum
            if curriculum and getattr(curriculum, "programme", None):
                prog = curriculum.programme
                if getattr(prog, "institution", None) and prog.institution.name:
                    institution_name = prog.institution.name
                elif prog.name:
                    institution_name = prog.name

        watermark_code = f"WM-{secrets.token_hex(4).upper()}"
        while db.query(WatermarkSession).filter(WatermarkSession.watermark_code == watermark_code).first():
            watermark_code = f"WM-{secrets.token_hex(4).upper()}"

        parts = []
        if custom_prefix and custom_prefix.strip():
            parts.append(custom_prefix.strip())
        else:
            parts.append(institution_name.upper())

        parts.append(student_name.upper())
        parts.append(masked_reg)
        if show_exam_id:
            short_quiz = str(attempt.quiz_id)[:8].upper()
            parts.append(f"EXAM-{short_quiz}")
        parts.append(watermark_code)

        watermark_text = " | ".join(parts)

        session = WatermarkSession(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            student_id=attempt.student_id,
            watermark_code=watermark_code,
            watermark_text=watermark_text,
            student_display_name=student_name,
            student_masked_identifier=masked_reg,
            institution_name=institution_name,
            opacity=opacity,
            font_size=font_size,
            rotation_deg=rotation_deg,
            spacing_px=spacing_px,
            update_interval_sec=update_interval_sec,
            is_valid=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def verify_watermark_session(
        db: Session,
        attempt_id: uuid.UUID,
        watermark_code: str,
        client_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        session = db.query(WatermarkSession).filter(WatermarkSession.attempt_id == attempt_id).first()
        if not session:
            return False, "No active watermark session found for this attempt."
        if session.watermark_code != watermark_code:
            session.tamper_flag = True
            db.commit()
            ev = SecurityEvent(
                attempt_id=attempt_id,
                student_id=session.student_id,
                quiz_id=session.quiz_id,
                event_category="WATERMARK",
                severity="HIGH",
                event_name="WATERMARK_VALIDATION_FAILED",
                description=f"Watermark mismatch detected. Expected {session.watermark_code}, received {watermark_code}.",
                client_timestamp=client_timestamp,
            )
            db.add(ev)
            db.commit()
            return False, "Watermark validation code mismatch."

        session.last_verified_at = datetime.now(timezone.utc)
        session.verification_count += 1
        session.is_valid = True
        db.commit()
        return True, "Watermark verified successfully."

    @staticmethod
    def record_capture_capability(
        db: Session,
        attempt: ExaminationAttempt,
        payload: CaptureCapabilitySubmitRequest,
    ) -> CaptureCapabilityReport:
        report = CaptureCapabilityReport(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            student_id=attempt.student_id,
            screen_capture_api_supported=payload.screen_capture_api_supported,
            screenshot_shortcut_supported=payload.screenshot_shortcut_supported,
            display_media_active=payload.display_media_active,
            detection_tier=payload.detection_tier,
            browser_vendor=payload.browser_vendor,
            os_platform=payload.os_platform,
            notes=payload.notes,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def record_capture_signal(
        db: Session,
        attempt: ExaminationAttempt,
        payload: CaptureSignalSubmitRequest,
    ) -> SecurityEvent:
        event_name = "SCREENSHOT_SIGNAL_DETECTED"
        sig_up = payload.signal_type.upper()
        if "MEDIA" in sig_up or "RECORD" in sig_up:
            event_name = "SCREEN_RECORDING_SIGNAL_DETECTED"
        elif "API" in sig_up:
            event_name = "CAPTURE_API_ACTIVITY"
        elif "PRINT_SCREEN" in sig_up or "PRTSCN" in sig_up or "SNIP" in sig_up or "SCREENSHOT" in sig_up:
            event_name = "SCREENSHOT_SIGNAL_DETECTED"
        elif "PRINT" in sig_up:
            event_name = "PRINT_RESTRICTION_TRIGGERED"

        severity = "MEDIUM"
        if payload.confidence_level == "high" or event_name == "SCREEN_RECORDING_SIGNAL_DETECTED":
            severity = "HIGH"
        elif payload.confidence_level == "low":
            severity = "LOW"

        ev = SecurityEvent(
            attempt_id=attempt.id,
            student_id=attempt.student_id,
            quiz_id=attempt.quiz_id,
            event_category="CAPTURE_DETECTION",
            severity=severity,
            event_name=event_name,
            description=f"Capture signal detected via {payload.detection_source} (confidence: {payload.confidence_level}). Signal: {payload.signal_type}",
            client_timestamp=payload.client_timestamp,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # Re-evaluate alerts
        policy = db.query(ExaminationSecurityPolicy).filter(ExaminationSecurityPolicy.quiz_id == attempt.quiz_id).first()
        if policy:
            SecurityService._evaluate_alerts(db, attempt, policy, datetime.now(timezone.utc))

        return ev
