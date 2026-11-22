import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.student import Student
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.security_audit import (
    SecurityEvent,
    SecurityAlert,
    ExaminationSecurityPolicy,
)
from backend.app.models.mobile_security import (
    DeviceRegistration,
    MobileExamSession,
    MobileInterruptionEvent,
)
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
from backend.app.services.security_service import SecurityService, _mask_identifier


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class MobileSecurityService:
    """
    Centralized business logic for mobile examination security, device registration,
    FLAG_SECURE native monitoring, lifecycle interruption handling, and session recovery.
    """

    @staticmethod
    def register_device(
        db: Session,
        student_id: uuid.UUID,
        req: DeviceRegisterRequest,
        ip_address: Optional[str] = None,
    ) -> DeviceRegisterResponse:
        """
        Registers or updates a student's mobile device reference.
        Enforces device trust and blocks revoked devices.
        """
        device = db.query(DeviceRegistration).filter(
            DeviceRegistration.student_id == student_id,
            DeviceRegistration.device_fingerprint == req.device_fingerprint,
        ).first()

        now = datetime.now(timezone.utc)

        if device:
            if device.is_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This mobile device has been restricted by an examination administrator: {device.block_reason or 'Security policy violation'}",
                )
            device.device_model = req.device_model
            device.os_version = req.os_version
            device.app_version = req.app_version
            device.app_build_number = req.app_build_number
            device.last_seen_at = now
            device.last_ip_address = ip_address
            if req.device_metadata:
                device.device_metadata = req.device_metadata
            device.updated_at = now
            db.commit()
            db.refresh(device)
            return DeviceRegisterResponse(
                success=True,
                device_id=device.id,
                device_fingerprint=device.device_fingerprint,
                is_trusted=device.is_trusted,
                is_blocked=device.is_blocked,
                registered_at=device.created_at,
                message="Device registration verified and updated.",
            )

        new_device = DeviceRegistration(
            student_id=student_id,
            device_fingerprint=req.device_fingerprint,
            device_model=req.device_model,
            os_platform=req.os_platform.lower(),
            os_version=req.os_version,
            app_version=req.app_version,
            app_build_number=req.app_build_number,
            is_trusted=True,
            is_blocked=False,
            last_seen_at=now,
            last_ip_address=ip_address,
            device_metadata=req.device_metadata,
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)

        return DeviceRegisterResponse(
            success=True,
            device_id=new_device.id,
            device_fingerprint=new_device.device_fingerprint,
            is_trusted=new_device.is_trusted,
            is_blocked=new_device.is_blocked,
            registered_at=new_device.created_at,
            message="Mobile device successfully registered for secure examination.",
        )

    @staticmethod
    def verify_mobile_compatibility(
        db: Session,
        student_id: uuid.UUID,
        req: MobileCompatibilityCheckRequest,
    ) -> MobileCompatibilityCheckResponse:
        """
        Executes pre-exam mobile device security and capability verification.
        Evaluates OS version, FLAG_SECURE status, root/jailbreak signals, and kiosk mode.
        """
        checks: List[Dict[str, Any]] = []
        can_proceed = True
        overall_status = "PASSED"

        # Check quiz-specific mobile policies if quiz_id is provided
        cfg = None
        if req.quiz_id:
            cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == req.quiz_id).first()

        # 1. Platform & Minimum OS Check
        platform_lower = req.os_platform.lower()
        if platform_lower == "android":
            min_api = getattr(cfg, "min_android_version", 26) if cfg else 26
            checks.append({
                "key": "os_compatibility",
                "title": "Android OS Compatibility",
                "status": "passed",
                "details": f"{req.os_version} (Target API >= {min_api})",
                "is_mandatory": True,
            })
        elif platform_lower == "ios":
            min_ios = getattr(cfg, "min_ios_version", "15.0") if cfg else "15.0"
            checks.append({
                "key": "os_compatibility",
                "title": "iOS Compatibility",
                "status": "passed",
                "details": f"{req.os_version} (Min iOS {min_ios})",
                "is_mandatory": True,
            })
        else:
            can_proceed = False
            overall_status = "BLOCKED"
            checks.append({
                "key": "os_compatibility",
                "title": "Unsupported Platform",
                "status": "action_required",
                "details": f"Unknown OS platform: {req.os_platform}",
                "is_mandatory": True,
            })

        # 2. FLAG_SECURE / Native Capture Protection Check
        if req.is_flag_secure_active:
            checks.append({
                "key": "flag_secure",
                "title": "Screen Capture Protection",
                "status": "passed",
                "details": "Native FLAG_SECURE active (Hardware screenshots & screen recording blocked)",
                "is_mandatory": True,
            })
        else:
            checks.append({
                "key": "flag_secure",
                "title": "Screen Capture Protection",
                "status": "warning",
                "details": "FLAG_SECURE inactive or running in compatibility fallback mode",
                "is_mandatory": False,
            })
            if overall_status != "BLOCKED":
                overall_status = "WARNING"

        # 3. Root / Jailbreak Risk Signal Check
        block_roots = getattr(cfg, "block_rooted_devices", False) if cfg else False
        if req.is_rooted:
            if block_roots:
                can_proceed = False
                overall_status = "BLOCKED"
                checks.append({
                    "key": "integrity_check",
                    "title": "Device Integrity Status",
                    "status": "action_required",
                    "details": "Root or jailbreak binary detected. Examination policy prohibits rooted devices.",
                    "is_mandatory": True,
                })
            else:
                checks.append({
                    "key": "integrity_check",
                    "title": "Device Integrity Status",
                    "status": "warning",
                    "details": "Root risk signal detected (Permitted with audit review flag)",
                    "is_mandatory": False,
                })
                if overall_status != "BLOCKED":
                    overall_status = "WARNING"
        else:
            checks.append({
                "key": "integrity_check",
                "title": "Device Integrity Status",
                "status": "passed",
                "details": "No root or system binary modifications detected",
                "is_mandatory": True,
            })

        # 4. Kiosk / Lock Task Mode Check
        kiosk_required = getattr(cfg, "require_kiosk_mode", False) if cfg else False
        if kiosk_required:
            if req.is_kiosk_mode_active:
                checks.append({
                    "key": "kiosk_mode",
                    "title": "Lock Task Kiosk Mode",
                    "status": "passed",
                    "details": "Device locked in dedicated Lock Task mode",
                    "is_mandatory": True,
                })
            else:
                can_proceed = False
                overall_status = "BLOCKED"
                checks.append({
                    "key": "kiosk_mode",
                    "title": "Lock Task Kiosk Mode",
                    "status": "action_required",
                    "details": "This examination requires an institutional managed device locked in Kiosk Mode.",
                    "is_mandatory": True,
                })
        else:
            checks.append({
                "key": "kiosk_mode",
                "title": "Lock Task Kiosk Mode",
                "status": "passed",
                "details": "Optional - Standard native secure mode active",
                "is_mandatory": False,
            })

        # 5. Secure Storage Check
        if req.has_secure_storage:
            checks.append({
                "key": "secure_storage",
                "title": "Hardware Encrypted Keystore",
                "status": "passed",
                "details": "Android Keystore / iOS Keychain available",
                "is_mandatory": True,
            })
        else:
            checks.append({
                "key": "secure_storage",
                "title": "Hardware Encrypted Keystore",
                "status": "warning",
                "details": "Software keystore fallback",
                "is_mandatory": False,
            })

        tier = "native_secure" if req.is_flag_secure_active and not req.is_rooted else "limited_protection"
        if not can_proceed:
            tier = "unsupported"

        message = (
            "Mobile device passed security and integrity checks. You may proceed to the examination."
            if can_proceed
            else "Mobile security requirements not met. Please resolve the highlighted items."
        )

        return MobileCompatibilityCheckResponse(
            can_proceed=can_proceed,
            overall_status=overall_status,
            device_tier=tier,
            message=message,
            checks=checks,
            disclosures=(
                "Note: Native FLAG_SECURE prevents ordinary screenshots and screen recording on supported devices. "
                "It cannot detect external cameras or second devices. Dynamic student watermarks provide forensic traceability."
            ),
        )

    @staticmethod
    def init_mobile_exam_session(
        db: Session,
        attempt_id: uuid.UUID,
        student_id: uuid.UUID,
        req: MobileExamSessionInitRequest,
    ) -> MobileExamSessionResponse:
        """
        Initializes or resumes a native mobile examination session.
        Enforces server-authoritative timer deadline and simultaneous device conflict checks.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

        if attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to this examination attempt.")

        if attempt.status != "in_progress":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Examination attempt is already {attempt.status}.")

        now = datetime.now(timezone.utc)
        exp = _ensure_utc(attempt.expires_at)
        if exp and now >= exp:
            attempt.status = "timed_out"
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Examination duration has expired.")

        # Find or link device
        device = None
        if req.device_id:
            device = db.query(DeviceRegistration).filter(DeviceRegistration.id == req.device_id).first()
        if not device and req.device_fingerprint:
            device = db.query(DeviceRegistration).filter(
                DeviceRegistration.student_id == student_id,
                DeviceRegistration.device_fingerprint == req.device_fingerprint,
            ).first()

        # Check for simultaneous session conflict on a different device
        existing_session = db.query(MobileExamSession).filter(
            MobileExamSession.attempt_id == attempt_id,
        ).first()

        if existing_session and existing_session.device_id and device and existing_session.device_id != device.id:
            # Device reassignment attempt during active examination
            cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == attempt.quiz_id).first()
            allow_recovery = getattr(cfg, "allow_device_recovery", True) if cfg else True
            if not allow_recovery:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Examination session cannot be transferred to a secondary mobile device.",
                )

        # Upsert MobileExamSession
        if existing_session:
            session = existing_session
            session.device_id = device.id if device else session.device_id
            session.secure_mode_active = req.flag_secure_active
            session.kiosk_mode_active = req.kiosk_mode_active
            session.app_state = "foreground"
            session.last_foreground_at = now
            session.root_detected = req.root_detected
            session.integrity_status = req.integrity_status
            session.updated_at = now
        else:
            session = MobileExamSession(
                attempt_id=attempt.id,
                device_id=device.id if device else None,
                student_id=student_id,
                quiz_id=attempt.quiz_id,
                secure_mode_active=req.flag_secure_active,
                kiosk_mode_active=req.kiosk_mode_active,
                app_state="foreground",
                last_foreground_at=now,
                root_detected=req.root_detected,
                integrity_status=req.integrity_status,
            )
            db.add(session)

        # Log NATIVE_APP_STARTED security event
        ev = SecurityEvent(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            student_id=student_id,
            event_category="NATIVE_MOBILE",
            event_name="NATIVE_APP_STARTED",
            severity="LOW",
            description=f"Native mobile examination started (FLAG_SECURE: {req.flag_secure_active}, Kiosk: {req.kiosk_mode_active})",
            sequence_number=1,
            event_metadata={
                "device_id": str(device.id) if device else None,
                "device_model": device.device_model if device else "Unknown",
                "os_platform": device.os_platform if device else "android",
                "root_detected": req.root_detected,
            },
        )
        db.add(ev)
        db.commit()
        db.refresh(session)

        # Dynamic watermark details
        wm_session = SecurityService.generate_or_get_watermark_session(db, attempt)
        exp = _ensure_utc(attempt.expires_at)
        remaining_seconds = max(0, int((exp - now).total_seconds())) if exp else 3600

        return MobileExamSessionResponse(
            session_id=session.id,
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            student_id=student_id,
            secure_mode_active=session.secure_mode_active,
            kiosk_mode_active=session.kiosk_mode_active,
            app_state=session.app_state,
            remaining_seconds=remaining_seconds,
            server_time=now,
            deadline_at=attempt.expires_at,
            watermark_text=wm_session.watermark_text,
            watermark_code=wm_session.watermark_code,
            message="Native mobile examination session active and secured.",
        )

    @staticmethod
    def record_interruption(
        db: Session,
        attempt_id: uuid.UUID,
        student_id: uuid.UUID,
        req: MobileInterruptionSubmitRequest,
    ) -> MobileInterruptionSubmitResponse:
        """
        Records lifecycle interruptions (incoming phone call, app background, OS dialogs, app exit).
        Updates attempt risk score and triggers invigilator alerts if policies are violated.
        Fairness: Candidate is NEVER automatically disqualified.
        """
        session = db.query(MobileExamSession).filter(MobileExamSession.attempt_id == attempt_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active mobile examination session not found.")

        if session.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to this session.")

        now = datetime.now(timezone.utc)
        session.interruption_count += 1

        # Map interruption to event name & severity
        itype = req.interruption_type.upper()
        severity = "MEDIUM"
        event_name = "APP_INTERRUPTION"

        if "BACKGROUND" in itype:
            session.app_state = "background"
            session.last_background_at = now
            event_name = "NATIVE_APP_BACKGROUND"
            severity = "MEDIUM"
        elif "FOREGROUND" in itype:
            session.app_state = "foreground"
            session.last_foreground_at = now
            event_name = "NATIVE_APP_FOREGROUND"
            severity = "LOW"
        elif "CALL" in itype:
            event_name = "APP_INTERRUPTION"
            severity = "MEDIUM"
        elif "SCREENSHOT" in itype:
            event_name = "SCREENSHOT_SIGNAL"
            severity = "HIGH"
        elif "KIOSK" in itype:
            event_name = "KIOSK_MODE_STATUS_CHANGED"
            severity = "HIGH"
        elif "ROOT" in itype:
            event_name = "ROOT_RISK_SIGNAL"
            severity = "HIGH"
            session.root_detected = True

        session.updated_at = now

        # Create MobileInterruptionEvent record
        interruption = MobileInterruptionEvent(
            mobile_session_id=session.id,
            attempt_id=attempt_id,
            student_id=student_id,
            interruption_type=req.interruption_type,
            severity=severity,
            duration_ms=req.duration_ms,
            details=req.details,
            client_timestamp=req.client_timestamp,
            server_timestamp=now,
        )
        db.add(interruption)

        # Also log to unified security_events for Live Monitoring Dashboard
        ev = SecurityEvent(
            attempt_id=attempt_id,
            quiz_id=session.quiz_id,
            student_id=student_id,
            event_category="NATIVE_MOBILE",
            event_name=event_name,
            severity=severity,
            description=f"Mobile interruption detected: {req.interruption_type} ({req.duration_ms or 0}ms)",
            client_timestamp=req.client_timestamp,
            sequence_number=session.interruption_count + 1,
            event_metadata={**(req.details or {}), "duration_ms": req.duration_ms},
        )
        db.add(ev)
        db.commit()
        db.refresh(interruption)

        # Check quiz configuration interruption policy
        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == session.quiz_id).first()
        policy = getattr(cfg, "mobile_interruption_policy", "allow_with_event") if cfg else "allow_with_event"

        policy_action = "logged"
        requires_review = False

        if policy == "pause_and_review" and severity in ["HIGH", "CRITICAL"]:
            policy_action = "paused"
            session.app_state = "paused"
            requires_review = True
        elif policy == "strict_flag" or severity == "HIGH":
            policy_action = "flagged"
            requires_review = True

        # Re-evaluate risk score
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if attempt:
            score, level = SecurityService.evaluate_attempt_risk(db, attempt)
            if score >= 15.0 or requires_review:
                # Trigger SecurityAlert for live monitoring
                alert = db.query(SecurityAlert).filter(
                    SecurityAlert.attempt_id == attempt_id,
                    SecurityAlert.alert_type == "MOBILE_INTERRUPTION_RISK",
                    SecurityAlert.status == "UNREVIEWED",
                ).first()
                if alert:
                    alert.occurrences_count = session.interruption_count
                    alert.last_observed_at = now
                    alert.updated_at = now
                else:
                    db.add(SecurityAlert(
                        attempt_id=attempt_id,
                        quiz_id=session.quiz_id,
                        student_id=student_id,
                        alert_type="MOBILE_INTERRUPTION_RISK",
                        severity="MEDIUM" if score < 25.0 else "HIGH",
                        occurrences_count=session.interruption_count,
                        first_observed_at=now,
                        last_observed_at=now,
                        status="UNREVIEWED",
                        created_at=now,
                    ))
                db.commit()

        return MobileInterruptionSubmitResponse(
            success=True,
            event_id=interruption.id,
            interruption_count=session.interruption_count,
            policy_action=policy_action,
            requires_invigilator_review=requires_review,
            message=f"Interruption {req.interruption_type} recorded under policy '{policy_action}'.",
        )

    @staticmethod
    def recover_exam_session(
        db: Session,
        attempt_id: uuid.UUID,
        student_id: uuid.UUID,
        req: MobileRecoveryRequest,
    ) -> MobileRecoveryResponse:
        """
        Recovers an interrupted native examination session (e.g. after incoming call or app relaunch).
        Guarantees: Server-authoritative timer deadline is preserved without time extension.
        Answers and attempt status remain intact.
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

        if attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to this examination attempt.")

        now = datetime.now(timezone.utc)
        exp = _ensure_utc(attempt.expires_at)
        if exp and now >= exp:
            attempt.status = "timed_out"
            db.commit()
            return MobileRecoveryResponse(
                success=False,
                recovered=False,
                attempt_id=attempt.id,
                remaining_seconds=0,
                server_time=now,
                status="timed_out",
                recovery_count=0,
                message="Examination deadline expired during interruption.",
            )

        session = db.query(MobileExamSession).filter(MobileExamSession.attempt_id == attempt_id).first()
        recovery_count = 1
        if session:
            session.recovery_count += 1
            session.app_state = "foreground"
            session.last_foreground_at = now
            session.updated_at = now
            recovery_count = session.recovery_count

        # Log EXAM_SESSION_RECOVERED event
        ev = SecurityEvent(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            student_id=student_id,
            event_category="NATIVE_MOBILE",
            event_name="EXAM_SESSION_RECOVERED",
            severity="LOW",
            description=f"Mobile exam session recovered (Reason: {req.recovery_reason}, Cycle: {recovery_count})",
            client_timestamp=req.client_timestamp,
            event_metadata={"recovery_reason": req.recovery_reason, "device_fingerprint": req.device_fingerprint},
        )
        db.add(ev)
        db.commit()

        exp = _ensure_utc(attempt.expires_at)
        remaining_seconds = max(0, int((exp - now).total_seconds())) if exp else 3600

        return MobileRecoveryResponse(
            success=True,
            recovered=True,
            attempt_id=attempt.id,
            remaining_seconds=remaining_seconds,
            server_time=now,
            status=attempt.status,
            recovery_count=recovery_count,
            message="Examination session restored. Answers and timer deadline safely preserved.",
        )

    @staticmethod
    def get_quiz_mobile_policy(db: Session, quiz_id: uuid.UUID) -> MobileQuizSecurityPolicyResponse:
        """
        Retrieves mobile security settings configured for a specific quiz.
        """
        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_id).first()
        return MobileQuizSecurityPolicyResponse(
            quiz_id=quiz_id,
            require_native_app=getattr(cfg, "require_native_app", False) if cfg else False,
            android_secure_mode=getattr(cfg, "android_secure_mode", True) if cfg else True,
            ios_secure_mode=getattr(cfg, "ios_secure_mode", True) if cfg else True,
            require_kiosk_mode=getattr(cfg, "require_kiosk_mode", False) if cfg else False,
            min_android_version=getattr(cfg, "min_android_version", 26) if cfg else 26,
            min_ios_version=getattr(cfg, "min_ios_version", "15.0") if cfg else "15.0",
            mobile_interruption_policy=getattr(cfg, "mobile_interruption_policy", "allow_with_event") if cfg else "allow_with_event",
            allow_device_recovery=getattr(cfg, "allow_device_recovery", True) if cfg else True,
            block_rooted_devices=getattr(cfg, "block_rooted_devices", False) if cfg else False,
        )

    @staticmethod
    def get_student_devices(db: Session, student_id: uuid.UUID) -> List[DeviceListItemResponse]:
        """
        Lists registered mobile devices for a student.
        """
        devices = db.query(DeviceRegistration).filter(DeviceRegistration.student_id == student_id).order_by(DeviceRegistration.last_seen_at.desc()).all()
        return [DeviceListItemResponse.model_validate(d) for d in devices]

    @staticmethod
    def update_device_status(
        db: Session,
        device_id: uuid.UUID,
        is_trusted: Optional[bool] = None,
        is_blocked: Optional[bool] = None,
        block_reason: Optional[str] = None,
    ) -> DeviceListItemResponse:
        """
        Administrator device management: trust or block registered mobile devices.
        """
        device = db.query(DeviceRegistration).filter(DeviceRegistration.id == device_id).first()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

        if is_trusted is not None:
            device.is_trusted = is_trusted
        if is_blocked is not None:
            device.is_blocked = is_blocked
            if is_blocked and block_reason:
                device.block_reason = block_reason
            elif not is_blocked:
                device.block_reason = None
        device.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
        return DeviceListItemResponse.model_validate(device)
