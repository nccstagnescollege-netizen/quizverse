import io
import base64
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import uuid

try:
    import qrcode
    import qrcode.image.svg
    QRCODE_AVAILABLE = True
except ImportError:
    qrcode = None
    QRCODE_AVAILABLE = False
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, select
from fastapi import HTTPException, status, Request

from backend.app.models.invitation import InvitationLink, InvitationUsage
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.registration import QuizRegistrationForm, QuizParticipant
from backend.app.models.student import Student, StudentProfile
from backend.app.models.auth_rbac import Admin, Role
from backend.app.schemas.invitation import (
    InvitationCreateRequest,
    InvitationUpdateRequest,
    InvitationResponse,
    InvitationListResponse,
    InvitationUsageResponse,
    InvitationUsageItemResponse,
    ParticipantItemResponse,
    ParticipantListResponse,
    EligibleQuizResponse,
)
from backend.app.core.config import settings


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def generate_secure_token() -> Tuple[str, str]:
    """
    Generates a cryptographically secure token and its SHA-256 hash.
    Raw token is never persisted in plaintext.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def generate_qr_svg(url: str) -> str:
    """Generate local SVG vector QR code without external APIs."""
    if not QRCODE_AVAILABLE or qrcode is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QR code generator is not available on server (missing 'qrcode' dependency).",
        )
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10, border=2)
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def generate_qr_png_base64(url: str) -> str:
    """Generate local PNG raster QR code formatted as data URI without external APIs."""
    if not QRCODE_AVAILABLE or qrcode is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QR code generator is not available on server (missing 'qrcode' dependency).",
        )
    img = qrcode.make(url, box_size=10, border=2)
    stream = io.BytesIO()
    img.save(stream, format="PNG")
    b64 = base64.b64encode(stream.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def is_super_admin(admin: Admin) -> bool:
    if getattr(admin, "is_super_admin", False):
        return True
    for r in getattr(admin, "roles", []):
        r_name = getattr(r, "role_name", getattr(r, "name", ""))
        if "super" in r_name.lower():
            return True
    return False


class InvitationService:

    @staticmethod
    def _get_base_url(req_base_url: Optional[str] = None, request: Optional[Request] = None) -> str:
        # 1. Explicitly passed in payload or function argument
        if req_base_url and req_base_url.strip():
            return req_base_url.strip().rstrip("/")

        # 2. Extract from request Origin or Referer header (sent by browsers on web requests)
        if request:
            origin = request.headers.get("origin")
            if origin and origin.strip():
                return origin.strip().rstrip("/")
            referer = request.headers.get("referer")
            if referer and referer.strip():
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"

        # 3. Environment configuration settings.FRONTEND_URL
        if getattr(settings, "FRONTEND_URL", None):
            return settings.FRONTEND_URL.rstrip("/")

        # 4. Fallback to production CORS origin if present
        cors = getattr(settings, "BACKEND_CORS_ORIGINS", None)
        if cors and isinstance(cors, list):
            for o in cors:
                if isinstance(o, str) and ("vercel.app" in o or "https://" in o):
                    return o.rstrip("/")

        return "http://localhost:3000"

    @staticmethod
    def check_quiz_permission(db: Session, admin: Admin, quiz: Quiz) -> bool:
        """
        Enforce RBAC: Super Admin has global access; User Admin must own quiz or have assignment.
        """
        if is_super_admin(admin):
            return True
        
        # User Admin check
        if quiz.created_by == admin.id:
            return True

        return False

    @staticmethod
    def get_eligible_quizzes(db: Session, admin: Admin) -> List[EligibleQuizResponse]:
        """
        Return published and scheduled quizzes eligible for invitation generation.
        Strictly RBAC isolated.
        """
        is_super = is_super_admin(admin)

        query = db.query(Quiz).options(
            joinedload(Quiz.subject),
            joinedload(Quiz.configuration),
            joinedload(Quiz.invitation_links),
        ).filter(Quiz.status.in_(["published", "scheduled"]))

        if not is_super:
            query = query.filter(Quiz.created_by == admin.id)

        quizzes = query.order_by(desc(Quiz.updated_at)).all()

        results = []
        for q in quizzes:
            # Count active invitations
            active_count = sum(1 for inv in q.invitation_links if not inv.is_revoked and inv.status == "active")
            requires_inv = q.configuration.require_invitation if q.configuration else False
            total_questions = sum(len(s.questions) for s in q.sections) if hasattr(q, "sections") and q.sections else 0
            
            # schedule timing
            sch_start = q.configuration.start_time if q.configuration else None
            sch_end = q.configuration.end_time if q.configuration else None

            results.append(EligibleQuizResponse(
                id=q.id,
                title=q.title,
                subject_name=q.subject.subject_name if q.subject else None,
                status=q.status,
                total_questions=total_questions,
                total_marks=float(q.total_marks or 0.0),
                duration_minutes=q.duration_minutes or 60,
                schedule_start=sch_start,
                schedule_end=sch_end,
                requires_invitation=requires_inv,
                active_invitations_count=active_count,
            ))
        return results

    @staticmethod
    def create_invitation(
        db: Session,
        admin: Admin,
        req: InvitationCreateRequest,
        request: Optional[Request] = None,
    ) -> InvitationResponse:
        """
        Create a secure invitation link for an eligible quiz.
        Generates cryptographic token, stores SHA-256 hash, and generates QR representations.
        """
        quiz = db.query(Quiz).options(joinedload(Quiz.subject)).filter(Quiz.id == req.quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if not InvitationService.check_quiz_permission(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Not authorized to create invitations for this quiz")

        if quiz.status not in ["published", "scheduled", "draft"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invitations can only be generated for published or scheduled quizzes (current status: {quiz.status})"
            )

        # Enforce type rules
        max_uses = req.max_uses
        is_reusable = req.is_reusable
        if req.invitation_type == "single_use":
            max_uses = 1
            is_reusable = False
        elif req.invitation_type == "individual":
            if not req.target_email:
                raise HTTPException(status_code=400, detail="Target email is required for individual invitations")
            max_uses = 1
            is_reusable = False

        # Status determination
        now = datetime.now(timezone.utc)
        initial_status = "active"
        if req.starts_at and _ensure_utc(req.starts_at) > now:
            initial_status = "scheduled"
        if req.expires_at and _ensure_utc(req.expires_at) < now:
            raise HTTPException(status_code=400, detail="Expiry date cannot be in the past")

        # Generate cryptographic token & hash
        raw_token, token_hash = generate_secure_token()

        invitation = InvitationLink(
            quiz_id=quiz.id,
            token_hash=token_hash,
            name=req.name,
            description=req.description,
            invitation_type=req.invitation_type,
            category=req.category,
            status=initial_status,
            target_email=req.target_email,
            max_uses=max_uses,
            used_count=0,
            max_attempts_per_student=req.max_attempts_per_student,
            starts_at=req.starts_at,
            expires_at=req.expires_at,
            timezone=req.timezone,
            allowed_student_groups=req.allowed_student_groups,
            is_reusable=is_reusable,
            require_account=req.require_account,
            require_approval=req.require_approval,
            internal_notes=req.internal_notes,
            is_revoked=False,
            created_by=admin.id,
        )

        db.add(invitation)
        db.commit()
        db.refresh(invitation)

        # Construct URLs & QR code
        base_url = InvitationService._get_base_url(req_base_url=getattr(req, "base_url", None), request=request)
        access_url = f"{base_url}/join/{raw_token}"
        qr_svg = generate_qr_svg(access_url)
        qr_png = generate_qr_png_base64(access_url)

        return InvitationResponse(
            id=invitation.id,
            quiz_id=invitation.quiz_id,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            name=invitation.name,
            description=invitation.description,
            invitation_type=invitation.invitation_type,
            category=invitation.category,
            status=invitation.status,
            target_email=invitation.target_email,
            max_uses=invitation.max_uses,
            used_count=invitation.used_count,
            remaining_uses=max(0, invitation.max_uses - invitation.used_count),
            max_attempts_per_student=invitation.max_attempts_per_student,
            starts_at=invitation.starts_at,
            expires_at=invitation.expires_at,
            timezone=invitation.timezone,
            allowed_student_groups=invitation.allowed_student_groups,
            is_reusable=invitation.is_reusable,
            require_account=invitation.require_account,
            require_approval=invitation.require_approval,
            internal_notes=invitation.internal_notes,
            is_revoked=invitation.is_revoked,
            created_by_name=admin.full_name,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
            access_url=access_url,
            qr_svg=qr_svg,
            qr_png_base64=qr_png,
            raw_token=raw_token,  # returned ONLY on creation
        )

    @staticmethod
    def list_invitations(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        invitation_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> InvitationListResponse:
        """
        List invitations with status evaluation, filters, and RBAC scoping.
        """
        is_super = is_super_admin(admin)

        query = db.query(InvitationLink).join(Quiz).options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
            joinedload(InvitationLink.creator),
        )

        if not is_super:
            query = query.filter(Quiz.created_by == admin.id)

        if quiz_id:
            query = query.filter(InvitationLink.quiz_id == quiz_id)

        if invitation_type and invitation_type != "all":
            query = query.filter(InvitationLink.invitation_type == invitation_type)

        if search:
            s = f"%{search}%"
            query = query.filter(or_(
                InvitationLink.name.ilike(s),
                Quiz.title.ilike(s),
                InvitationLink.target_email.ilike(s)
            ))

        now = datetime.now(timezone.utc)
        all_invitations = query.order_by(desc(InvitationLink.created_at)).all()

        # Update & compute dynamic status
        filtered_items = []
        for inv in all_invitations:
            computed_status = inv.status
            if inv.is_revoked:
                computed_status = "revoked"
            elif inv.used_count >= inv.max_uses:
                computed_status = "exhausted"
            elif inv.expires_at and _ensure_utc(inv.expires_at) < now:
                computed_status = "expired"
            elif inv.starts_at and _ensure_utc(inv.starts_at) > now:
                computed_status = "scheduled"
            else:
                computed_status = "active"

            if inv.status != computed_status:
                inv.status = computed_status
                db.add(inv)

            if status_filter and status_filter != "all":
                if computed_status != status_filter:
                    continue

            filtered_items.append(inv)

        db.commit()

        total = len(filtered_items)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = filtered_items[start_idx:end_idx]

        items = []
        for inv in paginated_items:
            items.append(InvitationResponse(
                id=inv.id,
                quiz_id=inv.quiz_id,
                quiz_title=inv.quiz.title if inv.quiz else None,
                subject_name=inv.quiz.subject.subject_name if inv.quiz and inv.quiz.subject else None,
                name=inv.name,
                description=inv.description,
                invitation_type=inv.invitation_type,
                category=inv.category,
                status=inv.status,
                target_email=inv.target_email,
                max_uses=inv.max_uses,
                used_count=inv.used_count,
                remaining_uses=max(0, inv.max_uses - inv.used_count),
                max_attempts_per_student=inv.max_attempts_per_student,
                starts_at=inv.starts_at,
                expires_at=inv.expires_at,
                timezone=inv.timezone,
                allowed_student_groups=inv.allowed_student_groups,
                is_reusable=inv.is_reusable,
                require_account=inv.require_account,
                require_approval=inv.require_approval,
                internal_notes=inv.internal_notes,
                is_revoked=inv.is_revoked,
                created_by_name=inv.creator.full_name if inv.creator else None,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
                access_url=None,
                qr_svg=None,
                qr_png_base64=None,
                raw_token=None,
            ))

        pages = (total + limit - 1) // limit if total > 0 else 1
        return InvitationListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    @staticmethod
    def get_invitation(db: Session, admin: Admin, invitation_id: uuid.UUID) -> InvitationResponse:
        """
        Get invitation detail, checking RBAC scoping.
        """
        inv = db.query(InvitationLink).options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
            joinedload(InvitationLink.creator),
        ).filter(InvitationLink.id == invitation_id).first()

        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if not InvitationService.check_quiz_permission(db, admin, inv.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to access this invitation")

        return InvitationResponse(
            id=inv.id,
            quiz_id=inv.quiz_id,
            quiz_title=inv.quiz.title if inv.quiz else None,
            subject_name=inv.quiz.subject.subject_name if inv.quiz and inv.quiz.subject else None,
            name=inv.name,
            description=inv.description,
            invitation_type=inv.invitation_type,
            category=inv.category,
            status=inv.status,
            target_email=inv.target_email,
            max_uses=inv.max_uses,
            used_count=inv.used_count,
            remaining_uses=max(0, inv.max_uses - inv.used_count),
            max_attempts_per_student=inv.max_attempts_per_student,
            starts_at=inv.starts_at,
            expires_at=inv.expires_at,
            timezone=inv.timezone,
            allowed_student_groups=inv.allowed_student_groups,
            is_reusable=inv.is_reusable,
            require_account=inv.require_account,
            require_approval=inv.require_approval,
            internal_notes=inv.internal_notes,
            is_revoked=inv.is_revoked,
            created_by_name=inv.creator.full_name if inv.creator else None,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    @staticmethod
    def update_invitation(
        db: Session,
        admin: Admin,
        invitation_id: uuid.UUID,
        req: InvitationUpdateRequest
    ) -> InvitationResponse:
        """
        Update allowed parameters of an invitation.
        """
        inv = db.query(InvitationLink).options(joinedload(InvitationLink.quiz)).filter(InvitationLink.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if not InvitationService.check_quiz_permission(db, admin, inv.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to modify this invitation")

        if inv.is_revoked:
            raise HTTPException(status_code=400, detail="Cannot modify a revoked invitation")

        if req.name is not None:
            inv.name = req.name
        if req.description is not None:
            inv.description = req.description
        if req.category is not None:
            inv.category = req.category
        if req.max_uses is not None:
            if req.max_uses < inv.used_count:
                raise HTTPException(status_code=400, detail=f"Cannot reduce max uses below current usage count ({inv.used_count})")
            inv.max_uses = req.max_uses
        if req.max_attempts_per_student is not None:
            inv.max_attempts_per_student = req.max_attempts_per_student
        if req.target_email is not None:
            inv.target_email = req.target_email
        if req.starts_at is not None:
            inv.starts_at = req.starts_at
        if req.expires_at is not None:
            inv.expires_at = req.expires_at
        if req.timezone is not None:
            inv.timezone = req.timezone
        if req.allowed_student_groups is not None:
            inv.allowed_student_groups = req.allowed_student_groups
        if req.is_reusable is not None:
            inv.is_reusable = req.is_reusable
        if req.require_account is not None:
            inv.require_account = req.require_account
        if req.require_approval is not None:
            inv.require_approval = req.require_approval
        if req.internal_notes is not None:
            inv.internal_notes = req.internal_notes

        inv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(inv)

        return InvitationService.get_invitation(db, admin, invitation_id)

    @staticmethod
    def revoke_invitation(db: Session, admin: Admin, invitation_id: uuid.UUID) -> Dict[str, Any]:
        """
        Revoke an invitation immediately. Invalidates all future access attempts and QR scans.
        """
        inv = db.query(InvitationLink).options(joinedload(InvitationLink.quiz)).filter(InvitationLink.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if not InvitationService.check_quiz_permission(db, admin, inv.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to revoke this invitation")

        inv.is_revoked = True
        inv.status = "revoked"
        inv.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "success": True,
            "message": f"Invitation '{inv.name}' has been permanently revoked.",
            "invitation_id": str(inv.id),
            "status": "revoked"
        }

    @staticmethod
    def get_invitation_usage(db: Session, admin: Admin, invitation_id: uuid.UUID) -> InvitationUsageResponse:
        """
        Retrieve usage and redemption analytics for an invitation link.
        """
        inv = db.query(InvitationLink).options(joinedload(InvitationLink.quiz)).filter(InvitationLink.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if not InvitationService.check_quiz_permission(db, admin, inv.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to access usage data")

        usages = db.query(InvitationUsage).options(
            joinedload(InvitationUsage.student).joinedload(Student.profile)
        ).filter(InvitationUsage.invitation_id == invitation_id).order_by(desc(InvitationUsage.used_at)).all()

        items = []
        success_count = 0
        failed_count = 0

        for u in usages:
            if u.status == "success":
                success_count += 1
            else:
                failed_count += 1

            student_name = u.student.full_name if u.student else None
            student_email = u.student.email if u.student else None
            student_ident = u.student.profile.student_identifier if u.student and u.student.profile else None

            items.append(InvitationUsageItemResponse(
                id=u.id,
                invitation_id=u.invitation_id,
                student_id=u.student_id,
                student_name=student_name,
                student_email=student_email,
                student_identifier=student_ident,
                status=u.status,
                failure_reason=u.failure_reason,
                device_type=u.device_type,
                ip_address=u.ip_address,
                user_agent=u.user_agent,
                used_at=u.used_at,
            ))

        return InvitationUsageResponse(
            total_redemptions=len(items),
            successful_count=success_count,
            failed_count=failed_count,
            remaining_capacity=max(0, inv.max_uses - inv.used_count),
            usages=items,
        )

    @staticmethod
    def get_participants(
        db: Session,
        admin: Admin,
        invitation_id: Optional[uuid.UUID] = None,
        quiz_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> ParticipantListResponse:
        """
        Retrieve registered participants with search, status filtering, and RBAC isolation.
        """
        is_super = is_super_admin(admin)

        query = db.query(QuizParticipant).join(Quiz).options(
            joinedload(QuizParticipant.student).joinedload(Student.profile),
            joinedload(QuizParticipant.approver),
        )

        if not is_super:
            query = query.filter(Quiz.created_by == admin.id)

        if invitation_id:
            inv = db.query(InvitationLink).options(joinedload(InvitationLink.quiz)).filter(InvitationLink.id == invitation_id).first()
            if not inv:
                raise HTTPException(status_code=404, detail="Invitation not found")
            if not InvitationService.check_quiz_permission(db, admin, inv.quiz):
                raise HTTPException(status_code=403, detail="Not authorized to access participants for this invitation")
            query = query.filter(QuizParticipant.invitation_id == invitation_id)

        if quiz_id:
            q_target = db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if not q_target:
                raise HTTPException(status_code=404, detail="Quiz not found")
            if not InvitationService.check_quiz_permission(db, admin, q_target):
                raise HTTPException(status_code=403, detail="Not authorized to access participants for this quiz")
            query = query.filter(QuizParticipant.quiz_id == quiz_id)

        if status_filter and status_filter != "all":
            query = query.filter(QuizParticipant.status == status_filter)

        if search:
            s = f"%{search}%"
            query = query.join(Student).filter(or_(
                Student.full_name.ilike(s),
                Student.email.ilike(s),
            ))

        total = query.count()
        participants = query.order_by(desc(QuizParticipant.registered_at)).offset((page - 1) * limit).limit(limit).all()

        # Stats breakdown
        stats_query = db.query(QuizParticipant.status, func.count(QuizParticipant.id)).join(Quiz)
        if not is_super:
            stats_query = stats_query.filter(Quiz.created_by == admin.id)
        if invitation_id:
            stats_query = stats_query.filter(QuizParticipant.invitation_id == invitation_id)
        if quiz_id:
            stats_query = stats_query.filter(QuizParticipant.quiz_id == quiz_id)
        raw_stats = stats_query.group_by(QuizParticipant.status).all()

        stats = {"total": total, "approved": 0, "pending_approval": 0, "rejected": 0, "revoked": 0}
        for st, count in raw_stats:
            stats[st] = count

        items = []
        for p in participants:
            st = p.student
            prof = st.profile if st else None
            items.append(ParticipantItemResponse(
                id=p.id,
                quiz_id=p.quiz_id,
                invitation_id=p.invitation_id,
                student_id=p.student_id,
                full_name=st.full_name if st else "Unknown",
                email=st.email if st else "Unknown",
                phone=st.phone if st else None,
                student_identifier=prof.student_identifier if prof else None,
                institution=prof.institution if prof else None,
                registration_data=p.registration_data or {},
                status=p.status,
                attempt_count=p.attempt_count or 0,
                registered_at=p.registered_at,
                approved_at=p.approved_at,
                approved_by_name=p.approver.full_name if p.approver else None,
                rejection_reason=p.rejection_reason,
                internal_notes=p.internal_notes,
            ))

        pages = (total + limit - 1) // limit if total > 0 else 1
        return ParticipantListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            stats=stats,
        )

    @staticmethod
    def update_participant_status(
        db: Session,
        admin: Admin,
        participant_id: uuid.UUID,
        new_status: str,
        rejection_reason: Optional[str] = None,
        internal_notes: Optional[str] = None,
    ) -> ParticipantItemResponse:
        """
        Approve, reject, or revoke a participant's registration.
        """
        p = db.query(QuizParticipant).options(
            joinedload(QuizParticipant.quiz),
            joinedload(QuizParticipant.student).joinedload(Student.profile),
            joinedload(QuizParticipant.approver)
        ).filter(QuizParticipant.id == participant_id).first()

        if not p:
            raise HTTPException(status_code=404, detail="Participant not found")

        if not InvitationService.check_quiz_permission(db, admin, p.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to manage participants for this quiz")

        p.status = new_status
        if new_status == "approved":
            p.approved_at = datetime.now(timezone.utc)
            p.approved_by = admin.id
            p.rejection_reason = None
        elif new_status == "rejected":
            p.rejection_reason = rejection_reason or "Registration rejected by administrator"
        elif new_status == "revoked":
            p.rejection_reason = rejection_reason or "Registration revoked by administrator"

        if internal_notes is not None:
            p.internal_notes = internal_notes

        db.commit()
        db.refresh(p)

        st = p.student
        prof = st.profile if st else None
        return ParticipantItemResponse(
            id=p.id,
            quiz_id=p.quiz_id,
            invitation_id=p.invitation_id,
            student_id=p.student_id,
            full_name=st.full_name if st else "Unknown",
            email=st.email if st else "Unknown",
            phone=st.phone if st else None,
            student_identifier=prof.student_identifier if prof else None,
            institution=prof.institution if prof else None,
            registration_data=p.registration_data or {},
            status=p.status,
            attempt_count=p.attempt_count or 0,
            registered_at=p.registered_at,
            approved_at=p.approved_at,
            approved_by_name=admin.full_name if p.approved_by else None,
            rejection_reason=p.rejection_reason,
            internal_notes=p.internal_notes,
        )

    @staticmethod
    def export_participants_csv(db: Session, admin: Admin, invitation_id: Optional[uuid.UUID] = None, quiz_id: Optional[uuid.UUID] = None) -> str:
        """
        Export participants roster in clean CSV format.
        """
        participants_data = InvitationService.get_participants(
            db=db,
            admin=admin,
            invitation_id=invitation_id,
            quiz_id=quiz_id,
            status_filter="all",
            page=1,
            limit=5000,
        )

        headers = ["ID", "Full Name", "Register / Roll Number", "Email", "Phone", "Institution", "Status", "Attempt Count", "Registration Date", "Approved At"]
        rows = [",".join([f'"{h}"' for h in headers])]

        for p in participants_data.items:
            row = [
                str(p.id),
                p.full_name.replace('"', '""'),
                (p.student_identifier or "").replace('"', '""'),
                p.email.replace('"', '""'),
                (p.phone or "").replace('"', '""'),
                (p.institution or "").replace('"', '""'),
                p.status,
                str(p.attempt_count),
                p.registered_at.strftime("%Y-%m-%d %H:%M:%S") if p.registered_at else "",
                p.approved_at.strftime("%Y-%m-%d %H:%M:%S") if p.approved_at else "",
            ]
            rows.append(",".join([f'"{c}"' for c in row]))

        return "\n".join(rows)
