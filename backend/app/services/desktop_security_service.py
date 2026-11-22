import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.auth_rbac import Admin
from backend.app.models.student import Student
from backend.app.models.quiz import Quiz
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.security_audit import SecurityEvent, AuditLog
from backend.app.models.desktop_security import (
    SEBConfiguration,
    ComputerLab,
    LabDevice,
    DesktopExamSession,
)
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
from backend.app.services.seb_config_service import SEBConfigService


class DesktopSecurityService:
    """
    Core business logic for Phase 25: Secure Desktop Examination Mode &
    Safe Exam Browser (SEB) integration, lab device management, and audit logging.
    """

    # -----------------------------------------------------------------
    # SEB Configuration Management
    # -----------------------------------------------------------------

    @classmethod
    def create_or_update_seb_config(
        cls,
        db: Session,
        quiz_id: uuid.UUID,
        req: SEBConfigCreateRequest,
        admin_id: Optional[uuid.UUID] = None,
        base_url: str = "https://quizverse-ymsg.onrender.com",
    ) -> SEBConfigResponse:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

        # Determine start URL and quit URL
        start_url = req.start_url or f"{base_url}/exam/{quiz.id}"
        quit_url = req.quit_url or f"{base_url}/exam/concluded"

        # Generate official SEB XML plist & cryptographic keys
        config_data, xml_string, config_key, bek = SEBConfigService.generate_seb_configuration(
            quiz_id=quiz.id,
            start_url=start_url,
            quit_url=quit_url,
            allow_quit=req.allow_quit,
            config_password=req.config_password,
            quit_password=req.quit_password,
            min_seb_version=req.min_seb_version,
            allow_reload=req.allow_reload,
            enable_url_filter=req.enable_url_filter,
            browser_view_mode=req.browser_view_mode,
            custom_settings=req.custom_settings,
        )

        # Check existing latest version
        latest_config = (
            db.query(SEBConfiguration)
            .filter(SEBConfiguration.quiz_id == quiz.id)
            .order_by(SEBConfiguration.version_number.desc())
            .first()
        )
        new_version = (latest_config.version_number + 1) if latest_config else 1

        hashed_admin_pwd = SEBConfigService.hash_seb_password(req.config_password) if req.config_password else None
        hashed_quit_pwd = SEBConfigService.hash_seb_password(req.quit_password) if req.quit_password else None

        new_config = SEBConfiguration(
            quiz_id=quiz.id,
            version_number=new_version,
            config_name=req.config_name,
            config_key=config_key,
            browser_exam_key=bek,
            config_data=config_data,
            encrypted_xml=xml_string,
            config_password_hash=hashed_admin_pwd,
            quit_password_hash=hashed_quit_pwd,
            status="published",
            is_mandatory=req.is_mandatory,
            allow_quit=req.allow_quit,
            min_seb_version=req.min_seb_version,
            allow_reload=req.allow_reload,
            enable_url_filter=req.enable_url_filter,
            browser_view_mode=req.browser_view_mode,
            created_by=admin_id,
        )

        db.add(new_config)
        db.commit()
        db.refresh(new_config)

        # Log audit entry
        cls._log_system_event(
            db,
            action="seb_config.created",
            entity_type="seb_configuration",
            entity_id=str(new_config.id),
            admin_id=admin_id,
            details={
                "quiz_id": str(quiz.id),
                "version_number": new_version,
                "is_mandatory": req.is_mandatory,
                "config_key": config_key,
            },
        )

        return cls._map_seb_config_response(new_config)

    @classmethod
    def get_seb_config_by_quiz_id(cls, db: Session, quiz_id: uuid.UUID) -> Optional[SEBConfigResponse]:
        cfg = (
            db.query(SEBConfiguration)
            .filter(SEBConfiguration.quiz_id == quiz_id, SEBConfiguration.status == "published")
            .order_by(SEBConfiguration.version_number.desc())
            .first()
        )
        if not cfg:
            # Fall back to latest version even if draft/revoked for preview
            cfg = (
                db.query(SEBConfiguration)
                .filter(SEBConfiguration.quiz_id == quiz_id)
                .order_by(SEBConfiguration.version_number.desc())
                .first()
            )
        if not cfg:
            return None
        return cls._map_seb_config_response(cfg)

    @classmethod
    def get_seb_xml(cls, db: Session, quiz_id: uuid.UUID, version: Optional[int] = None) -> Tuple[str, str]:
        """
        Retrieves the XML plist string (.seb file) for download.
        Returns: (xml_string, filename)
        """
        query = db.query(SEBConfiguration).filter(SEBConfiguration.quiz_id == quiz_id)
        if version:
            query = query.filter(SEBConfiguration.version_number == version)
        else:
            query = query.order_by(SEBConfiguration.version_number.desc())
        
        cfg = query.first()
        if not cfg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No SEB configuration found for this quiz.")
        
        filename = f"quiz_{str(quiz_id)[:8]}_v{cfg.version_number}.seb"
        return cfg.encrypted_xml, filename

    @classmethod
    def revoke_seb_config(
        cls,
        db: Session,
        quiz_id: uuid.UUID,
        req: SEBRevokeRequest,
        admin_id: Optional[uuid.UUID] = None,
    ) -> SEBConfigResponse:
        cfg = (
            db.query(SEBConfiguration)
            .filter(SEBConfiguration.quiz_id == quiz_id, SEBConfiguration.status == "published")
            .order_by(SEBConfiguration.version_number.desc())
            .first()
        )
        if not cfg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active published SEB configuration found to revoke.")

        now = datetime.now(timezone.utc)
        cfg.status = "revoked"
        cfg.revoked_at = now
        cfg.revocation_reason = req.revocation_reason
        db.commit()
        db.refresh(cfg)

        cls._log_system_event(
            db,
            action="seb_config.revoked",
            entity_type="seb_configuration",
            entity_id=str(cfg.id),
            admin_id=admin_id,
            details={
                "quiz_id": str(quiz_id),
                "version_number": cfg.version_number,
                "reason": req.revocation_reason,
            },
        )

        return cls._map_seb_config_response(cfg)

    # -----------------------------------------------------------------
    # Session Verification & Heartbeat
    # -----------------------------------------------------------------

    @classmethod
    def verify_desktop_session(
        cls,
        db: Session,
        req: DesktopSessionVerifyRequest,
        ip_address: Optional[str] = None,
    ) -> DesktopSessionVerifyResponse:
        """
        Authenticates incoming desktop client environment.
        Detects standard browser vs SEB, validates cryptographic ConfigKey / RequestHash,
        checks lab workstation readiness, logs security events, and establishes DesktopExamSession.
        """
        now = datetime.now(timezone.utc)
        quiz = db.query(Quiz).filter(Quiz.id == req.quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

        # Fetch latest published SEB config for this quiz
        cfg = (
            db.query(SEBConfiguration)
            .filter(SEBConfiguration.quiz_id == quiz.id)
            .order_by(SEBConfiguration.version_number.desc())
            .first()
        )

        is_mandatory = cfg.is_mandatory if cfg else False
        is_revoked = cfg.status == "revoked" if cfg else False

        # Detect SEB client
        check_headers = {}
        if req.config_key_hash:
            check_headers["x-safeexambrowser-configkeyhash"] = req.config_key_hash
        if req.request_hash:
            check_headers["x-safeexambrowser-requesthash"] = req.request_hash

        is_seb, detected_seb_ver, os_platform = SEBConfigService.detect_seb_client(
            user_agent=req.user_agent,
            headers=check_headers,
        )

        effective_seb_ver = req.seb_version or detected_seb_ver
        effective_os = req.os_platform or os_platform

        # Identify student if reg_code or student_id provided
        student_id = req.student_id
        if not student_id and req.reg_code:
            try:
                from backend.app.models.registration import RegistrationSubmission
                sub = db.query(RegistrationSubmission).filter(RegistrationSubmission.quiz_id == quiz.id).first()
                if sub:
                    student_id = sub.student_id
            except Exception:
                pass

        # Identify lab workstation if device reference or IP provided
        lab_device = None
        if req.lab_device_reference:
            lab_device = db.query(LabDevice).filter(LabDevice.device_reference == req.lab_device_reference).first()
        elif ip_address:
            lab_device = db.query(LabDevice).filter(LabDevice.ip_address == ip_address).first()

        lab_device_dict = None
        if lab_device:
            lab_device_dict = {
                "id": str(lab_device.id),
                "device_reference": lab_device.device_reference,
                "compatibility_status": lab_device.compatibility_status,
                "os_platform": lab_device.os_platform,
            }

        # Case 1: Active SEB configuration is REVOKED
        if cfg and is_revoked:
            cls._log_security_event(
                db,
                quiz_id=quiz.id,
                student_id=student_id,
                attempt_id=req.attempt_id,
                event_category="DESKTOP_SEB",
                severity="HIGH",
                event_name="SEB_CONFIGURATION_REVOKED",
                description=f"SEB configuration v{cfg.version_number} has been revoked: {cfg.revocation_reason or 'Administratively revoked.'}",
                ip_address=ip_address,
                user_agent=req.user_agent,
            )
            return DesktopSessionVerifyResponse(
                verified=False,
                session_mode="standard_browser" if not is_mandatory else "seb_enforced",
                is_seb=is_seb,
                seb_version=effective_seb_ver,
                os_platform=effective_os,
                is_mandatory=is_mandatory,
                can_proceed=not is_mandatory,
                config_status="revoked",
                message="This Safe Exam Browser configuration profile has been revoked by administrators. Please contact your invigilator.",
                lab_device=lab_device_dict,
            )

        # Case 2: SEB is MANDATORY but user is on a standard desktop browser
        if is_mandatory and not is_seb:
            cls._log_security_event(
                db,
                quiz_id=quiz.id,
                student_id=student_id,
                attempt_id=req.attempt_id,
                event_category="DESKTOP_SEB",
                severity="HIGH",
                event_name="STANDARD_BROWSER_ACCESS_ATTEMPT",
                description="Candidate attempted to access mandatory SEB examination using a standard desktop browser.",
                ip_address=ip_address,
                user_agent=req.user_agent,
            )
            return DesktopSessionVerifyResponse(
                verified=False,
                session_mode="standard_browser",
                is_seb=False,
                seb_version=None,
                os_platform=effective_os,
                is_mandatory=True,
                can_proceed=False,
                config_status="not_required" if not cfg else "valid",
                message="Safe Exam Browser is mandatory for this examination. Standard web browsers are prohibited. Please download and open the examination .seb file.",
                lab_device=lab_device_dict,
                config_details={"min_seb_version": cfg.min_seb_version if cfg else "3.0.0"},
            )

        # Case 3: SEB is detected
        if is_seb and cfg:
            # Check version
            min_ver = cfg.min_seb_version or "3.0.0"
            if effective_seb_ver and not SEBConfigService.is_version_supported(effective_seb_ver, min_ver):
                cls._log_security_event(
                    db,
                    quiz_id=quiz.id,
                    student_id=student_id,
                    attempt_id=req.attempt_id,
                    event_category="DESKTOP_SEB",
                    severity="HIGH",
                    event_name="SEB_VERSION_UNSUPPORTED",
                    description=f"Installed SEB version ({effective_seb_ver}) is lower than minimum requirement ({min_ver}).",
                    ip_address=ip_address,
                    user_agent=req.user_agent,
                )
                return DesktopSessionVerifyResponse(
                    verified=False,
                    session_mode="seb_enforced",
                    is_seb=True,
                    seb_version=effective_seb_ver,
                    os_platform=effective_os,
                    is_mandatory=is_mandatory,
                    can_proceed=False,
                    config_status="version_unsupported",
                    message=f"Safe Exam Browser version {effective_seb_ver} is unsupported. Minimum required version is {min_ver}. Please update SEB.",
                    lab_device=lab_device_dict,
                )

            # Check Cryptographic Hash if provided
            hash_valid, hash_msg = True, "SEB Verified"
            if req.config_key_hash or req.request_hash:
                hash_valid, hash_msg = SEBConfigService.verify_seb_headers(
                    request_url=req.request_url,
                    config_key=cfg.config_key,
                    browser_exam_key=cfg.browser_exam_key,
                    config_key_hash=req.config_key_hash,
                    request_hash=req.request_hash,
                )

            if not hash_valid:
                cls._log_security_event(
                    db,
                    quiz_id=quiz.id,
                    student_id=student_id,
                    attempt_id=req.attempt_id,
                    event_category="DESKTOP_SEB",
                    severity="HIGH",
                    event_name="CONFIGURATION_VERIFICATION_FAILED",
                    description=f"SEB cryptographic hash verification failed: {hash_msg}",
                    ip_address=ip_address,
                    user_agent=req.user_agent,
                )
                return DesktopSessionVerifyResponse(
                    verified=False,
                    session_mode="seb_enforced",
                    is_seb=True,
                    seb_version=effective_seb_ver,
                    os_platform=effective_os,
                    is_mandatory=is_mandatory,
                    can_proceed=False,
                    config_status="hash_mismatch",
                    message=f"Configuration verification failed: {hash_msg}",
                    lab_device=lab_device_dict,
                )

            # Check lab device compatibility status if device matched
            if lab_device and lab_device.compatibility_status in ["incompatible", "update_required"]:
                cls._log_security_event(
                    db,
                    quiz_id=quiz.id,
                    student_id=student_id,
                    attempt_id=req.attempt_id,
                    event_category="DESKTOP_SEB",
                    severity="MEDIUM",
                    event_name="LAB_DEVICE_COMPATIBILITY_FAILED",
                    description=f"Workstation {lab_device.device_reference} status is '{lab_device.compatibility_status}'.",
                    ip_address=ip_address,
                    user_agent=req.user_agent,
                )

            # Successful SEB Verification
            cls._log_security_event(
                db,
                quiz_id=quiz.id,
                student_id=student_id,
                attempt_id=req.attempt_id,
                event_category="DESKTOP_SEB",
                severity="INFO",
                event_name="SEB_SESSION_VERIFIED",
                description=f"Safe Exam Browser {effective_seb_ver or ''} verified for desktop examination.",
                ip_address=ip_address,
                user_agent=req.user_agent,
            )

            session = cls._upsert_desktop_session(
                db=db,
                attempt_id=req.attempt_id,
                student_id=student_id,
                quiz_id=quiz.id,
                seb_config_id=cfg.id,
                lab_device_id=lab_device.id if lab_device else None,
                session_mode="seb_enforced" if is_mandatory else "seb_voluntary",
                is_seb_verified=True,
                seb_version=effective_seb_ver,
                os_platform=effective_os,
                config_key_hash=req.config_key_hash,
                request_hash=req.request_hash,
            )

            return DesktopSessionVerifyResponse(
                verified=True,
                session_mode="seb_enforced" if is_mandatory else "seb_voluntary",
                is_seb=True,
                seb_version=effective_seb_ver,
                os_platform=effective_os,
                is_mandatory=is_mandatory,
                can_proceed=True,
                config_status="valid",
                message="Safe Exam Browser environment verified and secured.",
                lab_device=lab_device_dict,
                session_id=session.id if session else None,
                config_details={
                    "config_name": cfg.config_name,
                    "version_number": cfg.version_number,
                    "allow_quit": cfg.allow_quit,
                },
            )

        # Case 4: Standard browser allowed (voluntary / optional mode)
        session = cls._upsert_desktop_session(
            db=db,
            attempt_id=req.attempt_id,
            student_id=student_id,
            quiz_id=quiz.id,
            seb_config_id=cfg.id if cfg else None,
            lab_device_id=lab_device.id if lab_device else None,
            session_mode="standard_browser",
            is_seb_verified=False,
            seb_version=None,
            os_platform=effective_os,
            config_key_hash=None,
            request_hash=None,
        )

        return DesktopSessionVerifyResponse(
            verified=True,
            session_mode="standard_browser",
            is_seb=False,
            seb_version=None,
            os_platform=effective_os,
            is_mandatory=False,
            can_proceed=True,
            config_status="not_required",
            message="Standard desktop browser session established with active examination lockdown.",
            lab_device=lab_device_dict,
            session_id=session.id if session else None,
        )

    @classmethod
    def record_desktop_heartbeat(
        cls,
        db: Session,
        req: DesktopHeartbeatRequest,
    ) -> DesktopHeartbeatResponse:
        now = datetime.now(timezone.utc)
        session = db.query(DesktopExamSession).filter(DesktopExamSession.id == req.session_id).first()
        if not session:
            # Fall back to attempt_id
            session = db.query(DesktopExamSession).filter(DesktopExamSession.attempt_id == req.attempt_id).first()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Desktop examination session not found.")

        session.last_heartbeat_at = now
        db.commit()

        return DesktopHeartbeatResponse(
            status=session.status,
            recorded_at=now,
            interruption_count=session.interruption_count,
        )

    @classmethod
    def record_desktop_interruption(
        cls,
        db: Session,
        req: DesktopInterruptionRequest,
    ) -> DesktopInterruptionResponse:
        now = datetime.now(timezone.utc)
        session = db.query(DesktopExamSession).filter(DesktopExamSession.id == req.session_id).first()
        if not session:
            session = db.query(DesktopExamSession).filter(DesktopExamSession.attempt_id == req.attempt_id).first()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Desktop examination session not found.")

        session.interruption_count += 1
        session.status = "interrupted"
        session.updated_at = now
        db.commit()

        # Log security event
        cls._log_security_event(
            db,
            quiz_id=session.quiz_id,
            student_id=session.student_id,
            attempt_id=session.attempt_id,
            event_category="DESKTOP_SEB",
            severity=req.severity,
            event_name=req.interruption_type,
            description=f"Desktop security interruption recorded: {req.interruption_type}",
            details=req.details,
        )

        return DesktopInterruptionResponse(
            logged=True,
            action="logged",
            message="Desktop examination interruption logged for invigilator review.",
            new_interruption_count=session.interruption_count,
        )

    # -----------------------------------------------------------------
    # Computer Lab Management
    # -----------------------------------------------------------------

    @classmethod
    def create_computer_lab(cls, db: Session, req: ComputerLabCreateRequest) -> ComputerLabResponse:
        lab = ComputerLab(
            institution_id=req.institution_id,
            campus_name=req.campus_name,
            lab_name=req.lab_name,
            room_number=req.room_number,
            total_workstations=req.total_workstations,
            network_subnet=req.network_subnet,
            contact_person=req.contact_person,
            notes=req.notes,
            status="active",
        )
        db.add(lab)
        db.commit()
        db.refresh(lab)
        return cls._map_lab_response(lab, device_count=0, ready_count=0)

    @classmethod
    def list_computer_labs(
        cls,
        db: Session,
        institution_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[ComputerLabResponse]:
        query = db.query(ComputerLab)
        if institution_id:
            query = query.filter(ComputerLab.institution_id == institution_id)
        if status_filter:
            query = query.filter(ComputerLab.status == status_filter)
        labs = query.order_by(ComputerLab.lab_name.asc()).all()

        results = []
        for lab in labs:
            devices = db.query(LabDevice).filter(LabDevice.lab_id == lab.id).all()
            d_count = len(devices)
            ready_count = sum(1 for d in devices if d.compatibility_status == "ready" and d.is_active)
            results.append(cls._map_lab_response(lab, device_count=d_count, ready_count=ready_count))
        return results

    @classmethod
    def get_computer_lab(cls, db: Session, lab_id: uuid.UUID) -> ComputerLabResponse:
        lab = db.query(ComputerLab).filter(ComputerLab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer lab not found.")
        devices = db.query(LabDevice).filter(LabDevice.lab_id == lab.id).all()
        ready_count = sum(1 for d in devices if d.compatibility_status == "ready" and d.is_active)
        return cls._map_lab_response(lab, device_count=len(devices), ready_count=ready_count)

    @classmethod
    def update_computer_lab(cls, db: Session, lab_id: uuid.UUID, req: ComputerLabUpdateRequest) -> ComputerLabResponse:
        lab = db.query(ComputerLab).filter(ComputerLab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer lab not found.")

        for field, value in req.dict(exclude_unset=True).items():
            setattr(lab, field, value)

        lab.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lab)
        devices = db.query(LabDevice).filter(LabDevice.lab_id == lab.id).all()
        ready_count = sum(1 for d in devices if d.compatibility_status == "ready" and d.is_active)
        return cls._map_lab_response(lab, device_count=len(devices), ready_count=ready_count)

    @classmethod
    def delete_computer_lab(cls, db: Session, lab_id: uuid.UUID) -> Dict[str, Any]:
        lab = db.query(ComputerLab).filter(ComputerLab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer lab not found.")
        db.delete(lab)
        db.commit()
        return {"success": True, "message": f"Computer lab '{lab.lab_name}' deleted."}

    # -----------------------------------------------------------------
    # Lab Device Management & Readiness Audit
    # -----------------------------------------------------------------

    @classmethod
    def register_lab_device(cls, db: Session, lab_id: uuid.UUID, req: LabDeviceCreateRequest) -> LabDeviceResponse:
        lab = db.query(ComputerLab).filter(ComputerLab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer lab not found.")

        # Check reference uniqueness in lab
        existing = (
            db.query(LabDevice)
            .filter(LabDevice.lab_id == lab_id, LabDevice.device_reference == req.device_reference)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device reference '{req.device_reference}' already exists in this computer lab.",
            )

        now = datetime.now(timezone.utc)
        device = LabDevice(
            lab_id=lab_id,
            device_reference=req.device_reference,
            os_platform=req.os_platform,
            os_version=req.os_version,
            seb_version=req.seb_version,
            ip_address=req.ip_address,
            mac_address_masked=req.mac_address_masked,
            compatibility_status=req.compatibility_status,
            is_active=True,
            last_verified_at=now,
            metadata_info=req.metadata_info,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return LabDeviceResponse.model_validate(device)

    @classmethod
    def list_lab_devices(cls, db: Session, lab_id: uuid.UUID) -> List[LabDeviceResponse]:
        devices = db.query(LabDevice).filter(LabDevice.lab_id == lab_id).order_by(LabDevice.device_reference.asc()).all()
        return [LabDeviceResponse.model_validate(d) for d in devices]

    @classmethod
    def update_lab_device(cls, db: Session, device_id: uuid.UUID, req: LabDeviceUpdateRequest) -> LabDeviceResponse:
        device = db.query(LabDevice).filter(LabDevice.id == device_id).first()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab device not found.")

        for field, value in req.model_dump(exclude_unset=True).items():
            setattr(device, field, value)

        device.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
        return LabDeviceResponse.model_validate(device)

    @classmethod
    def delete_lab_device(cls, db: Session, device_id: uuid.UUID) -> Dict[str, Any]:
        device = db.query(LabDevice).filter(LabDevice.id == device_id).first()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab device not found.")
        db.delete(device)
        db.commit()
        return {"success": True, "message": f"Device '{device.device_reference}' removed from lab."}

    @classmethod
    def audit_lab_readiness(cls, db: Session, lab_id: uuid.UUID) -> LabReadinessAuditResponse:
        lab = db.query(ComputerLab).filter(ComputerLab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer lab not found.")

        devices = db.query(LabDevice).filter(LabDevice.lab_id == lab.id).all()
        total = len(devices)

        ready_count = 0
        update_count = 0
        incompatible_count = 0
        unverified_count = 0

        for d in devices:
            if not d.is_active:
                continue
            status_val = (d.compatibility_status or "unverified").lower()
            if status_val == "ready":
                ready_count += 1
            elif status_val == "update_required":
                update_count += 1
            elif status_val == "incompatible":
                incompatible_count += 1
            else:
                unverified_count += 1

        percentage = round((ready_count / total * 100.0), 1) if total > 0 else 0.0
        is_ready = total > 0 and percentage >= 90.0 and incompatible_count == 0

        recommendations = []
        if total == 0:
            recommendations.append("No devices registered in this laboratory. Register workstations before conducting exams.")
        if incompatible_count > 0:
            recommendations.append(f"{incompatible_count} workstation(s) marked incompatible. Repair or replace before exam session.")
        if update_count > 0:
            recommendations.append(f"{update_count} workstation(s) need Safe Exam Browser updates to meet the minimum version requirement.")
        if unverified_count > 0:
            recommendations.append(f"{unverified_count} workstation(s) require verification and health checks.")
        if is_ready:
            recommendations.append("Laboratory environment passes all pre-examination checks and is approved for high-stakes testing.")

        return LabReadinessAuditResponse(
            lab_id=lab.id,
            lab_name=lab.lab_name,
            total_devices=total,
            ready_devices=ready_count,
            update_required_devices=update_count,
            incompatible_devices=incompatible_count,
            unverified_devices=unverified_count,
            readiness_percentage=percentage,
            is_ready_for_examination=is_ready,
            audit_timestamp=datetime.now(timezone.utc),
            recommendations=recommendations,
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @classmethod
    def _upsert_desktop_session(
        cls,
        db: Session,
        attempt_id: Optional[uuid.UUID],
        student_id: Optional[uuid.UUID],
        quiz_id: uuid.UUID,
        seb_config_id: Optional[uuid.UUID],
        lab_device_id: Optional[uuid.UUID],
        session_mode: str,
        is_seb_verified: bool,
        seb_version: Optional[str],
        os_platform: Optional[str],
        config_key_hash: Optional[str],
        request_hash: Optional[str],
    ) -> Optional[DesktopExamSession]:
        if not attempt_id or not student_id:
            return None

        now = datetime.now(timezone.utc)
        session = db.query(DesktopExamSession).filter(DesktopExamSession.attempt_id == attempt_id).first()
        if session:
            session.session_mode = session_mode
            session.is_seb_verified = is_seb_verified
            session.seb_version = seb_version
            session.os_platform = os_platform
            session.config_key_hash = config_key_hash
            session.request_hash = request_hash
            session.seb_config_id = seb_config_id
            session.lab_device_id = lab_device_id or session.lab_device_id
            session.last_heartbeat_at = now
            session.updated_at = now
        else:
            session = DesktopExamSession(
                attempt_id=attempt_id,
                student_id=student_id,
                quiz_id=quiz_id,
                seb_config_id=seb_config_id,
                lab_device_id=lab_device_id,
                session_mode=session_mode,
                is_seb_verified=is_seb_verified,
                seb_version=seb_version,
                os_platform=os_platform,
                config_key_hash=config_key_hash,
                request_hash=request_hash,
                status="active",
                interruption_count=0,
                last_heartbeat_at=now,
            )
            db.add(session)

        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def _map_seb_config_response(cls, cfg: SEBConfiguration) -> SEBConfigResponse:
        return SEBConfigResponse(
            id=cfg.id,
            quiz_id=cfg.quiz_id,
            version_number=cfg.version_number,
            config_name=cfg.config_name,
            config_key=cfg.config_key,
            browser_exam_key=cfg.browser_exam_key,
            is_mandatory=cfg.is_mandatory,
            allow_quit=cfg.allow_quit,
            min_seb_version=cfg.min_seb_version,
            allow_reload=cfg.allow_reload,
            enable_url_filter=cfg.enable_url_filter,
            browser_view_mode=cfg.browser_view_mode,
            status=cfg.status,
            has_config_password=bool(cfg.config_password_hash),
            has_quit_password=bool(cfg.quit_password_hash),
            created_at=cfg.created_at,
            updated_at=cfg.updated_at,
            revoked_at=cfg.revoked_at,
            revocation_reason=cfg.revocation_reason,
        )

    @classmethod
    def _map_lab_response(cls, lab: ComputerLab, device_count: int, ready_count: int) -> ComputerLabResponse:
        return ComputerLabResponse(
            id=lab.id,
            institution_id=lab.institution_id,
            campus_name=lab.campus_name,
            lab_name=lab.lab_name,
            room_number=lab.room_number,
            total_workstations=lab.total_workstations,
            network_subnet=lab.network_subnet,
            status=lab.status,
            contact_person=lab.contact_person,
            notes=lab.notes,
            device_count=device_count,
            ready_devices_count=ready_count,
            created_at=lab.created_at,
            updated_at=lab.updated_at,
        )

    @staticmethod
    def _log_security_event(
        db: Session,
        quiz_id: Optional[uuid.UUID],
        student_id: Optional[uuid.UUID],
        attempt_id: Optional[uuid.UUID],
        event_category: str,
        severity: str,
        event_name: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        try:
            event = SecurityEvent(
                quiz_id=quiz_id,
                student_id=student_id,
                attempt_id=attempt_id,
                event_category=event_category,
                severity=severity,
                event_name=event_name,
                description=description,
                event_metadata=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(event)
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def _log_system_event(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: str,
        admin_id: Optional[uuid.UUID],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            log = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                admin_id=admin_id,
                details=details or {},
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
