import re
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import uuid

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from fastapi import HTTPException, status

from backend.app.models.invitation import InvitationLink, InvitationUsage
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.registration import QuizRegistrationForm, QuizParticipant
from backend.app.models.student import Student, StudentProfile
from backend.app.models.auth_rbac import Admin
from backend.app.schemas.invitation import (
    RegistrationFormFieldConfig,
    RegistrationFormCreateUpdateRequest,
    RegistrationFormResponse,
    PublicInvitationValidationResponse,
    PublicRegistrationSubmitRequest,
    PublicRegistrationReceiptResponse,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _filter_invitation_by_token(query, token: str):
    token_str = str(token).strip() if token else ""
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    parsed_uuid = None
    try:
        parsed_uuid = uuid.UUID(token_str)
    except (ValueError, AttributeError):
        parsed_uuid = None

    if parsed_uuid:
        return query.filter(or_(InvitationLink.token_hash == token_hash, InvitationLink.id == parsed_uuid))
    return query.filter(InvitationLink.token_hash == token_hash)


def resolve_invitation_or_quiz(
    db: Session, token: str, for_update: bool = False
) -> Tuple[Optional[InvitationLink], Optional[str], Optional[str]]:
    """
    Robustly resolves an invitation link or quiz from:
    1. Cryptographic token hash (raw token)
    2. Invitation UUID (invitation.id)
    3. Quiz UUID (quiz.id)
    4. Quiz Slug (quiz.slug)

    Returns (invitation, error_code, error_message).
    """
    token_str = str(token).strip() if token else ""
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    parsed_uuid = None
    try:
        parsed_uuid = uuid.UUID(token_str)
    except (ValueError, AttributeError):
        parsed_uuid = None

    inv_query = db.query(InvitationLink)
    if parsed_uuid:
        inv_query = inv_query.filter(or_(InvitationLink.token_hash == token_hash, InvitationLink.id == parsed_uuid))
    else:
        inv_query = inv_query.filter(InvitationLink.token_hash == token_hash)

    if for_update:
        # In PostgreSQL, FOR UPDATE cannot be used with joinedload outer joins.
        # Query and lock InvitationLink directly; relationships are loaded cleanly after lock.
        inv = inv_query.with_for_update().first()
    else:
        inv = inv_query.options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
            joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
        ).first()

    if inv:
        return inv, None, None

    # Fallback: check if token represents a Quiz UUID or Quiz Slug
    quiz = None
    if parsed_uuid:
        quiz = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.configuration),
        ).filter(Quiz.id == parsed_uuid).first()
    if not quiz and token_str:
        quiz = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.configuration),
        ).filter(Quiz.slug == token_str).first()

    if quiz:
        if quiz.status == "draft":
            return (
                None,
                "QUIZ_DRAFT",
                f"The examination '{quiz.title}' is currently saved as a Draft. Please publish the quiz in the Quiz Management dashboard before inviting candidates.",
            )
        if quiz.status not in ["published", "scheduled"]:
            return (
                None,
                "QUIZ_INELIGIBLE",
                "The associated examination is currently not open for candidate registration.",
            )

        # Look for existing active invitation for this published quiz
        active_query = db.query(InvitationLink).filter(
            InvitationLink.quiz_id == quiz.id,
            InvitationLink.is_revoked == False,
        ).order_by(desc(InvitationLink.created_at))

        if for_update:
            active_inv = active_query.with_for_update().first()
        else:
            active_inv = active_query.options(
                joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
                joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
            ).first()

        if not active_inv:
            # Auto-provision a default official invitation so candidates can enter seamlessly
            import secrets
            raw_tok = secrets.token_urlsafe(32)
            tok_hash = hashlib.sha256(raw_tok.encode("utf-8")).hexdigest()
            active_inv = InvitationLink(
                id=uuid.uuid4(),
                quiz_id=quiz.id,
                token_hash=tok_hash,
                name=f"{quiz.title} - Official Invitation",
                invitation_type="general",
                category="Regular",
                status="active",
                max_uses=1000,
                used_count=0,
                is_reusable=True,
            )
            db.add(active_inv)
            db.commit()
            db.refresh(active_inv)

        return active_inv, None, None

    return None, "INVALID", "The invitation link is invalid or does not exist."


DEFAULT_REGISTRATION_FIELDS: List[Dict[str, Any]] = [
    {
        "field_name": "full_name",
        "field_label": "Full Name",
        "field_type": "text",
        "placeholder": "Enter your full name",
        "help_text": "Name as registered in official academic records",
        "is_required": True,
        "is_built_in": True,
        "min_length": 2,
        "max_length": 255,
        "is_unique": False,
        "display_order": 1,
    },
    {
        "field_name": "register_number",
        "field_label": "Register / Roll Number",
        "field_type": "text",
        "placeholder": "e.g. 2026CS101",
        "help_text": "Your student matriculation ID or roll number",
        "is_required": True,
        "is_built_in": True,
        "min_length": 2,
        "max_length": 100,
        "is_unique": True,
        "display_order": 2,
    },
    {
        "field_name": "email",
        "field_label": "Email Address",
        "field_type": "email",
        "placeholder": "student@institution.edu",
        "help_text": "Used for examination confirmation and notifications",
        "is_required": True,
        "is_built_in": True,
        "min_length": 5,
        "max_length": 255,
        "is_unique": True,
        "display_order": 3,
    },
    {
        "field_name": "phone_number",
        "field_label": "Phone Number",
        "field_type": "phone",
        "placeholder": "+1 234 567 8900",
        "help_text": "Active contact mobile number",
        "is_required": False,
        "is_built_in": True,
        "min_length": 7,
        "max_length": 25,
        "is_unique": False,
        "display_order": 4,
    },
    {
        "field_name": "college_name",
        "field_label": "College / Institution",
        "field_type": "text",
        "placeholder": "e.g. School of Computer Engineering",
        "help_text": "College, institution, or school name",
        "is_required": False,
        "is_built_in": True,
        "min_length": 2,
        "max_length": 255,
        "is_unique": False,
        "display_order": 5,
    },
    {
        "field_name": "academic_year",
        "field_label": "Academic Year / Session",
        "field_type": "text",
        "placeholder": "2025-2026",
        "help_text": "Current academic year or cohort session",
        "is_required": False,
        "is_built_in": True,
        "min_length": 2,
        "max_length": 50,
        "is_unique": False,
        "display_order": 6,
    },
]


class StudentRegistrationService:

    @staticmethod
    def get_default_fields() -> List[RegistrationFormFieldConfig]:
        return [RegistrationFormFieldConfig(**f) for f in DEFAULT_REGISTRATION_FIELDS]

    @staticmethod
    def get_quiz_registration_form(db: Session, quiz_id: uuid.UUID) -> RegistrationFormResponse:
        """
        Get active registration form for a quiz.
        If no custom form exists, provisions a default version 1 form.
        """
        form = db.query(QuizRegistrationForm).filter(
            QuizRegistrationForm.quiz_id == quiz_id,
            QuizRegistrationForm.is_active == True,
        ).order_by(desc(QuizRegistrationForm.version_number)).first()

        if not form:
            # Check if quiz exists
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if not quiz:
                raise HTTPException(status_code=404, detail="Quiz not found")

            # Create default form
            form = QuizRegistrationForm(
                quiz_id=quiz_id,
                version_number=1,
                title="Student Registration Form",
                description="Default student registration configuration",
                fields_config=DEFAULT_REGISTRATION_FIELDS,
                unique_fields=["email", "register_number"],
                require_manual_approval=False,
                is_active=True,
            )
            db.add(form)
            db.commit()
            db.refresh(form)

        return RegistrationFormResponse(
            id=form.id,
            quiz_id=form.quiz_id,
            version_number=form.version_number,
            title=form.title,
            description=form.description,
            fields_config=[RegistrationFormFieldConfig(**f) for f in form.fields_config],
            unique_fields=form.unique_fields or ["email"],
            require_manual_approval=form.require_manual_approval,
            is_active=form.is_active,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )

    @staticmethod
    def save_quiz_registration_form(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        req: RegistrationFormCreateUpdateRequest
    ) -> RegistrationFormResponse:
        """
        Save registration form. Modifying creates a new incremented version.
        Existing participant registrations stay tied to historical version.
        """
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Deactivate existing active forms
        existing_active = db.query(QuizRegistrationForm).filter(
            QuizRegistrationForm.quiz_id == quiz_id,
            QuizRegistrationForm.is_active == True,
        ).all()

        max_version = db.query(func.max(QuizRegistrationForm.version_number)).filter(
            QuizRegistrationForm.quiz_id == quiz_id
        ).scalar() or 0

        for f in existing_active:
            f.is_active = False

        new_form = QuizRegistrationForm(
            quiz_id=quiz_id,
            version_number=max_version + 1,
            title=req.title,
            description=req.description,
            fields_config=[f.model_dump() for f in req.fields_config],
            unique_fields=req.unique_fields,
            require_manual_approval=req.require_manual_approval,
            is_active=True,
            created_by=admin.id,
        )

        db.add(new_form)
        db.commit()
        db.refresh(new_form)

        return RegistrationFormResponse(
            id=new_form.id,
            quiz_id=new_form.quiz_id,
            version_number=new_form.version_number,
            title=new_form.title,
            description=new_form.description,
            fields_config=[RegistrationFormFieldConfig(**f) for f in new_form.fields_config],
            unique_fields=new_form.unique_fields,
            require_manual_approval=new_form.require_manual_approval,
            is_active=new_form.is_active,
            created_at=new_form.created_at,
            updated_at=new_form.updated_at,
        )

    @staticmethod
    def validate_public_token(db: Session, token: str) -> PublicInvitationValidationResponse:
        """
        Public token validation for candidates scanning QR or following invitation link.
        Validates token hash or invitation ID, status, expiration, quotas, and quiz eligibility.
        Never reveals whether candidate records exist.
        """
        inv, err_code, err_msg = resolve_invitation_or_quiz(db, token, for_update=False)

        if not inv:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code=err_code or "INVALID",
                error_message=err_msg or "The invitation link is invalid or does not exist."
            )

        if inv.is_revoked:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code="REVOKED",
                error_message="This invitation link has been revoked by the examination administrator."
            )

        now = datetime.now(timezone.utc)
        if inv.starts_at and _ensure_utc(inv.starts_at) > now:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code="NOT_ACTIVE",
                error_message=f"This examination invitation will become active on {inv.starts_at.strftime('%Y-%m-%d %H:%M:%S UTC')}."
            )

        if inv.expires_at and _ensure_utc(inv.expires_at) < now:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code="EXPIRED",
                error_message="This invitation link has expired."
            )

        if inv.used_count >= inv.max_uses:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code="EXHAUSTED",
                error_message="This invitation link has reached its maximum registration limit."
            )

        quiz = inv.quiz
        if not quiz or quiz.status not in ["published", "scheduled"]:
            return PublicInvitationValidationResponse(
                is_valid=False,
                error_code="QUIZ_INELIGIBLE",
                error_message="The associated examination is currently not open for candidate registration."
            )

        # Retrieve active form
        form = db.query(QuizRegistrationForm).filter(
            QuizRegistrationForm.quiz_id == quiz.id,
            QuizRegistrationForm.is_active == True,
        ).first()

        fields = [RegistrationFormFieldConfig(**f) for f in (form.fields_config if form else DEFAULT_REGISTRATION_FIELDS)]

        cfg = quiz.configuration
        return PublicInvitationValidationResponse(
            is_valid=True,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            duration_minutes=quiz.duration_minutes or 60,
            total_marks=float(quiz.total_marks or 0.0),
            instructions=quiz.instructions,
            schedule_start=cfg.start_time if cfg else None,
            schedule_end=cfg.end_time if cfg else None,
            timezone=inv.timezone,
            invitation_name=inv.name,
            invitation_type=inv.invitation_type,
            require_approval=inv.require_approval or (form.require_manual_approval if form else False),
            registration_form=fields,
        )

    @staticmethod
    def register_candidate(
        db: Session,
        token: str,
        form_data: Dict[str, Any],
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicRegistrationReceiptResponse:
        """
        Atomic student registration:
        - Locks invitation link row
        - Validates form input against field schema
        - Deduplicates candidate
        - Enforces invitation quota
        - Upserts Student and StudentProfile
        - Creates QuizParticipant
        - Logs InvitationUsage
        """
        inv, err_code, err_msg = resolve_invitation_or_quiz(db, token, for_update=True)

        if not inv:
            raise HTTPException(
                status_code=400 if err_code == "QUIZ_DRAFT" else 404,
                detail=err_msg or "Invalid invitation token",
            )

        if inv.is_revoked:
            raise HTTPException(status_code=400, detail="This invitation link has been revoked")

        now = datetime.now(timezone.utc)
        if inv.starts_at and _ensure_utc(inv.starts_at) > now:
            raise HTTPException(status_code=400, detail="This invitation link is not yet active")

        if inv.expires_at and _ensure_utc(inv.expires_at) < now:
            raise HTTPException(status_code=400, detail="This invitation link has expired")

        if inv.used_count >= inv.max_uses:
            raise HTTPException(status_code=400, detail="Maximum registration capacity reached for this invitation")

        quiz = inv.quiz
        if not quiz or quiz.status not in ["published", "scheduled"]:
            raise HTTPException(status_code=400, detail="This examination is not open for registration")

        # Load active form configuration
        form = db.query(QuizRegistrationForm).filter(
            QuizRegistrationForm.quiz_id == quiz.id,
            QuizRegistrationForm.is_active == True,
        ).first()

        raw_fields = form.fields_config if form else DEFAULT_REGISTRATION_FIELDS

        # Field validation
        for field in raw_fields:
            fname = field["field_name"]
            flabel = field["field_label"]
            is_req = field.get("is_required", False)
            val = form_data.get(fname)

            if is_req and (val is None or str(val).strip() == ""):
                raise HTTPException(status_code=422, detail=f"Required field '{flabel}' is missing")

            if val is not None and str(val).strip() != "":
                s_val = str(val).strip()
                min_len = field.get("min_length")
                max_len = field.get("max_length")
                if min_len and len(s_val) < min_len:
                    raise HTTPException(status_code=422, detail=f"'{flabel}' must be at least {min_len} characters")
                if max_len and len(s_val) > max_len:
                    raise HTTPException(status_code=422, detail=f"'{flabel}' cannot exceed {max_len} characters")

                # Email validation
                if field.get("field_type") == "email":
                    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", s_val):
                        raise HTTPException(status_code=422, detail=f"Invalid email address provided for '{flabel}'")

                # Choice options validation
                if field.get("field_type") in ["select", "radio"]:
                    opts = field.get("options") or []
                    if opts and s_val not in opts:
                        raise HTTPException(status_code=422, detail=f"Invalid selection for '{flabel}'. Allowed: {', '.join(opts)}")

                # Custom Regex validation
                custom_regex = field.get("validation_regex")
                if custom_regex:
                    try:
                        if not re.search(custom_regex, s_val):
                            raise HTTPException(status_code=422, detail=f"'{flabel}' format is invalid")
                    except re.error:
                        pass

        # Extract primary identity
        raw_email = form_data.get("email")
        if not raw_email:
            raise HTTPException(status_code=422, detail="Email address is required for registration")
        email = str(raw_email).strip().lower()

        full_name = str(form_data.get("full_name") or "Student Candidate").strip()
        register_number = str(form_data.get("register_number") or "").strip()
        phone = str(form_data.get("phone_number") or "").strip() or None
        college = str(form_data.get("college_name") or "").strip() or None

        # Check group restriction if invitation is restricted or group-scoped
        if inv.allowed_student_groups and len(inv.allowed_student_groups) > 0:
            allowed = False
            for group in inv.allowed_student_groups:
                if group.startswith("@") and email.endswith(group):
                    allowed = True
                    break
                elif group.lower() in [email, register_number.lower(), (college or "").lower()]:
                    allowed = True
                    break
            if not allowed:
                raise HTTPException(status_code=403, detail="You are not eligible for this restricted invitation.")

        # Check individual invitation target_email match
        if inv.invitation_type == "individual" and inv.target_email:
            if inv.target_email.lower().strip() != email:
                raise HTTPException(status_code=403, detail="This invitation is restricted to a specific recipient email.")

        # Candidate Deduplication:
        # Check if student already exists
        existing_student = db.query(Student).filter(func.lower(Student.email) == email).first()

        # If student exists, check if already enrolled in this quiz
        if existing_student:
            existing_enrollment = db.query(QuizParticipant).filter(
                QuizParticipant.quiz_id == quiz.id,
                QuizParticipant.student_id == existing_student.id,
            ).first()

            if existing_enrollment:
                raise HTTPException(
                    status_code=409,
                    detail="You are already registered for this examination. Duplicate registration is not permitted."
                )

        # Create or update Student
        if not existing_student:
            student = Student(
                full_name=full_name,
                email=email,
                phone=phone,
                is_guest=True,
                status="active",
            )
            db.add(student)
            db.flush()

            # Create StudentProfile
            profile = StudentProfile(
                student_id=student.id,
                student_identifier=register_number if register_number else None,
                institution=college,
                timezone=inv.timezone,
            )
            db.add(profile)
        else:
            student = existing_student
            if not student.profile:
                profile = StudentProfile(
                    student_id=student.id,
                    student_identifier=register_number if register_number else None,
                    institution=college,
                    timezone=inv.timezone,
                )
                db.add(profile)
            else:
                if register_number and not student.profile.student_identifier:
                    student.profile.student_identifier = register_number
                if college and not student.profile.institution:
                    student.profile.institution = college

        # Determine participant approval status
        require_approval = inv.require_approval or (form.require_manual_approval if form else False)
        status_val = "pending_approval" if require_approval else "approved"
        approved_at_val = now if not require_approval else None

        # Create QuizParticipant
        participant = QuizParticipant(
            quiz_id=quiz.id,
            invitation_id=inv.id,
            student_id=student.id,
            form_version_id=form.id if form else None,
            registration_data=form_data,
            status=status_val,
            attempt_count=0,
            registered_at=now,
            approved_at=approved_at_val,
        )
        db.add(participant)

        # Record InvitationUsage
        usage = InvitationUsage(
            invitation_id=inv.id,
            student_id=student.id,
            status="success",
            device_type="mobile" if user_agent and ("Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent) else "desktop",
            ip_address=client_ip,
            user_agent=user_agent,
            used_at=now,
        )
        db.add(usage)

        # Atomic increment of used_count
        inv.used_count += 1
        if inv.used_count >= inv.max_uses:
            inv.status = "exhausted"
        if inv.invitation_type == "single_use":
            inv.status = "exhausted"

        db.commit()
        db.refresh(participant)

        reg_code = f"REG-{str(participant.id)[:8].upper()}"
        msg = (
            "Registration submitted and awaiting administrator approval."
            if require_approval
            else "Registration completed successfully! You are enrolled for this examination."
        )

        cfg = quiz.configuration
        return PublicRegistrationReceiptResponse(
            success=True,
            participant_id=participant.id,
            registration_code=reg_code,
            status=participant.status,
            message=msg,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            student_name=student.full_name,
            student_identifier=register_number or None,
            scheduled_start=cfg.start_time if cfg else None,
            examination_duration_minutes=quiz.duration_minutes or 60,
        )
