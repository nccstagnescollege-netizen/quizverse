import uuid
import re
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, cast, String

from backend.app.core.config import settings
from backend.app.models.base import utc_now
from backend.app.models.invitation import InvitationLink
from backend.app.models.quiz import (
    Quiz,
    QuizConfiguration,
    QuizSection,
    QuizQuestion,
    QuizPublishedVersion,
)
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
    AttemptEvent,
    AttemptSession,
)
from backend.app.models.results import ExaminationResult, QuestionEvaluation
from backend.app.services.evaluation_service import EvaluationService
from backend.app.schemas.student_exam import (
    StudentExamLandingResponse,
    StudentExamInstructionsResponse,
    StudentExamStartRequest,
    StudentExamStartResponse,
    StudentAttemptDetailResponse,
    StudentQuestionItemResponse,
    StudentQuestionOptionResponse,
    StudentSectionItemResponse,
    StudentSaveAnswerRequest,
    StudentSaveAnswerResponse,
    AnswerItemResponse,
    SingleAnswerUpdateRequest,
    BatchAnswerSaveRequest,
    BatchAnswerSaveResponse,
    StudentProgressResponse,
    ReviewFlagUpdateRequest,
    ReviewFlagUpdateResponse,
    StudentHeartbeatRequest,
    StudentHeartbeatResponse,
    StudentSubmitRequest,
    StudentReviewSummaryResponse,
    StudentSubmitResponse,
    StudentResultResponse,
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


def _resolve_invitation_or_quiz(db: Session, token: str, load_sections: bool = False):
    """
    Robustly resolves an InvitationLink from:
    1. Cryptographic token hash
    2. Invitation UUID
    3. Quiz UUID (auto-links to active invitation or provisions one)
    4. Quiz Slug (auto-links to active invitation or provisions one)
    """
    token_str = str(token).strip() if token else ""
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    parsed_uuid = None
    try:
        parsed_uuid = uuid.UUID(token_str)
    except (ValueError, AttributeError):
        parsed_uuid = None

    opts = [
        joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
        joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
    ]
    if load_sections:
        opts.append(joinedload(InvitationLink.quiz).joinedload(Quiz.sections).joinedload(QuizSection.questions))

    base_query = db.query(InvitationLink).options(*opts)
    if parsed_uuid:
        inv = base_query.filter(or_(InvitationLink.token_hash == token_hash, InvitationLink.id == parsed_uuid)).first()
    else:
        inv = base_query.filter(InvitationLink.token_hash == token_hash).first()

    if inv:
        return inv

    # Fallback to Quiz UUID or Slug
    quiz_opts = [
        joinedload(Quiz.subject),
        joinedload(Quiz.configuration),
    ]
    if load_sections:
        quiz_opts.append(joinedload(Quiz.sections).joinedload(QuizSection.questions))

    quiz = None
    if parsed_uuid:
        quiz = db.query(Quiz).options(*quiz_opts).filter(Quiz.id == parsed_uuid).first()
    if not quiz and token_str:
        quiz = db.query(Quiz).options(*quiz_opts).filter(Quiz.slug == token_str).first()

    # Fallback: Candidate Registration Code (e.g. REG-390DF52D or REG-D280DB0A)
    if not quiz and token_str:
        clean_code = token_str.upper().replace("REG-", "").strip().lower()
        if len(clean_code) >= 4:
            # 1. Direct query on prefix of participant UUID
            matched_p = (
                db.query(QuizParticipant)
                .options(
                    joinedload(QuizParticipant.quiz).joinedload(Quiz.subject),
                    joinedload(QuizParticipant.quiz).joinedload(Quiz.configuration),
                )
                .filter(cast(QuizParticipant.id, String).ilike(f"{clean_code}%"))
                .first()
            )
            if matched_p and matched_p.quiz:
                quiz = matched_p.quiz
            else:
                # 2. In-memory check on loaded participants
                parts = db.query(QuizParticipant).options(
                    joinedload(QuizParticipant.quiz).joinedload(Quiz.subject),
                    joinedload(QuizParticipant.quiz).joinedload(Quiz.configuration),
                ).all()
                for p in parts:
                    p_hex = str(p.id).replace("-", "").lower()
                    p_str = str(p.id).lower()
                    if p_hex.startswith(clean_code) or p_str.startswith(clean_code):
                        quiz = p.quiz
                        break

    if quiz:
        if quiz.status == "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The examination '{quiz.title}' is currently saved as a Draft. Please publish the quiz in the Quiz Management dashboard before starting attempts."
            )
        active_inv = db.query(InvitationLink).options(*opts).filter(
            InvitationLink.quiz_id == quiz.id,
            InvitationLink.is_revoked == False,
        ).order_by(desc(InvitationLink.created_at)).first()

        if not active_inv:
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

        return active_inv

    return None


class StudentExamService:

    @staticmethod
    def _create_session_token(
        student_id: uuid.UUID,
        attempt_id: uuid.UUID,
        quiz_id: uuid.UUID,
        expires_at: datetime,
        session_id: Optional[uuid.UUID] = None,
    ) -> str:
        """Create a cryptographically signed JWT for the active candidate examination attempt."""
        payload = {
            "sub": str(student_id),
            "attempt_id": str(attempt_id),
            "quiz_id": str(quiz_id),
            "session_id": str(session_id) if session_id else str(uuid.uuid4()),
            "iat": datetime.now(timezone.utc),
            "exp": expires_at + timedelta(hours=2),  # Valid through examination window + buffer
            "type": "student_exam_session",
        }
        return jwt.encode(payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def _evaluate_objective_scoring(db: Session, attempt: ExaminationAttempt, calculated_at: datetime):
        """Internal helper: Computes objective question scores and records ExaminationResult via EvaluationService."""
        EvaluationService.run_evaluation(db, attempt.id)

    @staticmethod
    def _auto_expire_and_submit_attempt(
        db: Session,
        attempt: ExaminationAttempt,
        commit: bool = True,
    ) -> ExaminationAttempt:
        """
        Server-side authoritative expiry finalization:
        - Freezes the attempt (is_immutable = True)
        - Finalizes status to 'submitted'
        - Sets submission_reason to 'TIME_EXPIRED'
        - Sets submission_source to 'server_deadline'
        - Computes preliminary objective evaluation
        - Increments participant attempt count
        - Logs audit event DEADLINE_EXPIRED
        """
        if attempt.status == "submitted":
            return attempt

        now = datetime.now(timezone.utc)
        effective_sub_time = _ensure_utc(attempt.deadline_at or attempt.expires_at) or now
        attempt.status = "submitted"
        attempt.submitted_at = effective_sub_time
        attempt.submission_reason = "TIME_EXPIRED"
        attempt.submission_source = "server_deadline"
        attempt.is_immutable = True

        # Increment participant count
        participant = db.query(QuizParticipant).filter(
            QuizParticipant.quiz_id == attempt.quiz_id,
            QuizParticipant.student_id == attempt.student_id,
        ).first()
        if participant:
            participant.attempt_count += 1

        # Evaluate objective scoring
        StudentExamService._evaluate_objective_scoring(db, attempt, now)

        # Audit event
        event = AttemptEvent(
            attempt_id=attempt.id,
            event_type="DEADLINE_EXPIRED",
            event_metadata={"reason": "TIME_EXPIRED", "expired_at": effective_sub_time.isoformat()},
            actor_type="system",
            occurred_at=now,
        )
        db.add(event)

        if commit:
            db.commit()
            db.refresh(attempt)
        return attempt

    @staticmethod
    def verify_session_token(token: str) -> Dict[str, Any]:
        """Verify the candidate's exam session JWT."""
        try:
            payload = jwt.decode(token, settings.effective_jwt_secret, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "student_exam_session":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token type")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Examination session has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid examination session credentials")

    @staticmethod
    def get_exam_landing_details(
        db: Session,
        token: str,
        registration_code: Optional[str] = None,
        email: Optional[str] = None,
    ) -> StudentExamLandingResponse:
        """
        Public / candidate entrypoint:
        Fetches examination metadata, verifies invitation and schedule eligibility,
        and determines allowed actions based on registration and attempt status.
        """
        if not registration_code and token and token.upper().startswith("REG-"):
            registration_code = token.upper()

        inv = _resolve_invitation_or_quiz(db, token, load_sections=True)

        if not inv:
            if token and token.upper().startswith("REG-"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate registration code '{token}' was not found. Please verify your registration code or complete exam registration."
                )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid examination invitation token")

        if inv.is_revoked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This examination invitation has been revoked")

        quiz = inv.quiz
        if not quiz or quiz.status not in ["published", "scheduled"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This examination is currently not open")

        cfg = quiz.configuration
        now = datetime.now(timezone.utc)

        # Calculate availability status
        availability_status = "available"
        if inv.expires_at and _ensure_utc(inv.expires_at) < now:
            availability_status = "expired"
        elif cfg and cfg.start_time and _ensure_utc(cfg.start_time) > now:
            availability_status = "scheduled"
        elif cfg and cfg.end_time:
            end_limit = _ensure_utc(cfg.end_time) + timedelta(minutes=cfg.grace_period_minutes)
            if now > end_limit:
                availability_status = "expired"

        # Calculate counts
        sections = quiz.sections or []
        total_questions = sum(len(s.questions) for s in sections) if sections else len(quiz.quiz_questions)

        # Registration requirements
        requires_registration = bool(cfg.registration_required if cfg else False) or (inv.invitation_type != "general")

        # Resolve candidate if registration_code or email provided
        participant: Optional[QuizParticipant] = None
        student: Optional[Student] = None

        if registration_code:
            code_clean = registration_code.strip().upper()
            pure_code = code_clean.replace("REG-", "").strip().lower()
            # Match by participant id prefix or full id
            all_parts = db.query(QuizParticipant).options(
                joinedload(QuizParticipant.student).joinedload(Student.profile)
            ).filter(QuizParticipant.quiz_id == quiz.id).all()
            for p in all_parts:
                p_hex = str(p.id).replace("-", "").lower()
                p_str = str(p.id).lower()
                expected_code = f"REG-{str(p.id)[:8].upper()}"
                if (
                    expected_code == code_clean
                    or str(p.id).upper() == code_clean
                    or p_str.startswith(pure_code)
                    or p_hex.startswith(pure_code)
                ):
                    participant = p
                    student = p.student
                    break
        elif email:
            student = db.query(Student).options(joinedload(Student.profile)).filter(
                func.lower(Student.email) == email.strip().lower()
            ).first()
            if student:
                participant = db.query(QuizParticipant).filter(
                    QuizParticipant.quiz_id == quiz.id,
                    QuizParticipant.student_id == student.id,
                ).first()

        is_registered = participant is not None
        participant_status = participant.status if participant else None

        # Check existing attempts
        can_start = False
        can_resume = False
        active_attempt_id = None
        attempts_used = 0
        max_attempts = cfg.max_attempts if cfg else 1

        if student:
            existing_attempts = db.query(ExaminationAttempt).filter(
                ExaminationAttempt.quiz_id == quiz.id,
                ExaminationAttempt.student_id == student.id,
            ).order_by(ExaminationAttempt.attempt_number.desc()).all()

            attempts_used = len(existing_attempts)

            # Check if active attempt can be resumed
            for att in existing_attempts:
                if att.status == "in_progress":
                    if _ensure_utc(att.expires_at) > now:
                        can_resume = True
                        active_attempt_id = att.id
                        availability_status = "active"
                        break
                    else:
                        # Auto-expire
                        att.status = "timed_out"
                        att.submitted_at = att.expires_at
                        db.commit()

            if not can_resume:
                if attempts_used >= max_attempts:
                    availability_status = "completed"
                else:
                    if availability_status == "available":
                        # Candidate can start if approved
                        if participant and participant.status == "approved":
                            can_start = True

        allowed_actions = []
        if not is_registered and requires_registration:
            allowed_actions.append("register")
        if can_resume:
            allowed_actions.extend(["resume", "view_instructions"])
        elif can_start:
            allowed_actions.extend(["start", "view_instructions"])
        elif availability_status == "completed":
            allowed_actions.append("view_result")
        else:
            allowed_actions.append("view_instructions")

        candidate_info = None
        if student:
            reg_num = student.profile.student_identifier if student.profile else None
            candidate_info = {
                "id": str(student.id),
                "name": student.full_name,
                "email": student.email,
                "register_number": reg_num,
                "registration_code": f"REG-{str(participant.id)[:8].upper()}" if participant else None,
            }

        return StudentExamLandingResponse(
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            description=quiz.description,
            instructions=quiz.instructions,
            total_marks=float(quiz.total_marks or 0.0),
            total_questions=total_questions,
            total_sections=len(sections),
            duration_minutes=quiz.duration_minutes or 60,
            start_time=_ensure_utc(cfg.start_time) if cfg else None,
            end_time=_ensure_utc(cfg.end_time) if cfg else None,
            timezone=inv.timezone,
            max_attempts=max_attempts,
            attempts_used=attempts_used,
            availability_status=availability_status,
            requires_registration=requires_registration,
            is_registered=is_registered,
            participant_status=participant_status,
            can_start=can_start,
            can_resume=can_resume,
            active_attempt_id=active_attempt_id,
            candidate=candidate_info,
            allowed_actions=allowed_actions,
        )

    @staticmethod
    def get_exam_instructions(db: Session, token: str) -> StudentExamInstructionsResponse:
        """
        Retrieves detailed instructions, rules, section breakdown, and selection guidelines
        configured for the examination.
        """
        inv = _resolve_invitation_or_quiz(db, token, load_sections=True)

        if not inv or not inv.quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")

        quiz = inv.quiz
        cfg = quiz.configuration
        sections = quiz.sections or []

        sections_summary = []
        selection_rules_notices = []

        for s in sections:
            q_count = len(s.questions)
            summary = {
                "id": str(s.id),
                "title": s.title,
                "question_count": q_count,
                "marks": float(s.section_total_marks or 0.0),
                "selection_rule": s.selection_rule,
                "required_question_count": s.required_question_count,
            }
            sections_summary.append(summary)

            if s.selection_rule == "answer_n_of_m" and s.required_question_count:
                selection_rules_notices.append(
                    f"{s.title}: Answer any {s.required_question_count} out of {q_count} questions."
                )

        rules = [
            "Ensure a stable internet connection before beginning the examination.",
            "Once you begin, the countdown timer cannot be paused.",
            "Do not switch tabs, minimize the browser window, or exit fullscreen mode. Activity is logged.",
            "Answers can be marked for review and revisited prior to final submission where allowed.",
            "If disconnected, you may rejoin the session within the remaining examination time.",
            "When the timer reaches zero, the examination will automatically submit all saved answers.",
        ]

        if cfg:
            if not cfg.allow_previous_nav:
                rules.append("Sequential navigation is enforced: you cannot return to previously visited questions.")
            if not cfg.allow_answer_change:
                rules.append("Answers cannot be modified once selected.")

        from backend.app.services.security_service import SecurityService
        sec_policy = SecurityService.get_effective_policy(db, quiz.id)
        sec_notice = {
            "track_tab_switch": sec_policy.track_tab_switch,
            "track_focus_loss": sec_policy.track_focus_loss,
            "require_fullscreen": sec_policy.require_fullscreen,
            "track_fullscreen_exit": sec_policy.track_fullscreen_exit,
            "block_copy_paste": sec_policy.block_copy_paste,
            "track_copy_paste": sec_policy.track_copy_paste,
            "block_context_menu": sec_policy.block_context_menu,
            "enable_watermark": sec_policy.enable_watermark,
            "student_acknowledgement_required": sec_policy.student_acknowledgement_required,
            "notice_text": sec_policy.student_notice_text or (
                "Academic integrity monitoring is enabled for this examination. "
                "The system logs tab switches, window focus changes, and full-screen exits. "
                "Clipboard actions may be restricted. No personal files or cameras are monitored."
            ),
        }

        return StudentExamInstructionsResponse(
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            duration_minutes=quiz.duration_minutes or 60,
            total_marks=float(quiz.total_marks or 0.0),
            total_questions=sum(len(s.questions) for s in sections) if sections else len(quiz.quiz_questions),
            total_sections=len(sections),
            max_attempts=cfg.max_attempts if cfg else 1,
            instructions=quiz.instructions,
            sections_summary=sections_summary,
            rules=rules,
            selection_rules_notice=" | ".join(selection_rules_notices) if selection_rules_notices else None,
            allow_previous_nav=cfg.allow_previous_nav if cfg else True,
            allow_answer_change=cfg.allow_answer_change if cfg else True,
            allow_mark_for_review=cfg.allow_mark_for_review if cfg else True,
            navigation_mode=cfg.navigation_mode if cfg else "free",
            security_notice=sec_notice,
            monitoring_required=sec_policy.student_acknowledgement_required,
        )

    @staticmethod
    def start_or_resume_exam(
        db: Session,
        token: str,
        req: StudentExamStartRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> StudentExamStartResponse:
        """
        Authoritative start & resume handler:
        - Validates invitation & schedule
        - Verifies candidate registration and approval
        - Resumes active attempt if one is running
        - Creates a new attempt if within max_attempts
        - Generates signed JWT session token
        """
        if not req.registration_code and token and token.upper().startswith("REG-"):
            req.registration_code = token.upper()

        inv = _resolve_invitation_or_quiz(db, token, load_sections=False)

        if not inv or not inv.quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")

        if inv.is_revoked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation link has been revoked")

        quiz = inv.quiz
        cfg = quiz.configuration
        now = datetime.now(timezone.utc)

        # Schedule check
        if cfg and cfg.start_time and _ensure_utc(cfg.start_time) > now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Examination has not started yet")
        if cfg and cfg.end_time:
            end_limit = _ensure_utc(cfg.end_time) + timedelta(minutes=cfg.grace_period_minutes)
            if now > end_limit:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Examination window has closed")

        # Resolve candidate
        participant: Optional[QuizParticipant] = None
        student: Optional[Student] = None

        if req.registration_code:
            code_clean = req.registration_code.strip().upper()
            all_parts = db.query(QuizParticipant).options(
                joinedload(QuizParticipant.student).joinedload(Student.profile)
            ).filter(QuizParticipant.quiz_id == quiz.id).all()
            for p in all_parts:
                expected_code = f"REG-{str(p.id)[:8].upper()}"
                if expected_code == code_clean or str(p.id).upper() == code_clean:
                    participant = p
                    student = p.student
                    break
        elif req.email:
            student = db.query(Student).options(joinedload(Student.profile)).filter(
                func.lower(Student.email) == req.email.strip().lower()
            ).first()
            if student:
                participant = db.query(QuizParticipant).filter(
                    QuizParticipant.quiz_id == quiz.id,
                    QuizParticipant.student_id == student.id,
                ).first()
        elif req.student_identifier:
            prof = db.query(StudentProfile).options(joinedload(StudentProfile.student)).filter(
                StudentProfile.student_identifier == req.student_identifier.strip()
            ).first()
            if prof:
                student = prof.student
                participant = db.query(QuizParticipant).filter(
                    QuizParticipant.quiz_id == quiz.id,
                    QuizParticipant.student_id == student.id,
                ).first()

        if not student or not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate registration not found. Please register for this examination before entering."
            )

        if participant.status == "pending_approval":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration is awaiting administrator approval. You cannot start the exam yet."
            )
        if participant.status in ["rejected", "revoked"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your examination registration has been rejected or revoked."
            )

        # Check for active in-progress attempt to resume
        active_attempt = db.query(ExaminationAttempt).filter(
            ExaminationAttempt.quiz_id == quiz.id,
            ExaminationAttempt.student_id == student.id,
            ExaminationAttempt.status == "in_progress",
        ).first()

        if active_attempt:
            act_deadline = _ensure_utc(active_attempt.deadline_at or active_attempt.expires_at)
            if act_deadline > now:
                remaining = max(0, int((act_deadline - now).total_seconds()))
                session_id = uuid.uuid4()
                session_token = StudentExamService._create_session_token(
                    student_id=student.id,
                    attempt_id=active_attempt.id,
                    quiz_id=quiz.id,
                    expires_at=act_deadline,
                    session_id=session_id,
                )
                active_attempt.active_session_token = str(session_id)
                active_attempt.last_heartbeat_at = now

                # Register active session
                sess_record = AttemptSession(
                    attempt_id=active_attempt.id,
                    session_token_hash=hashlib.sha256(str(session_id).encode("utf-8")).hexdigest(),
                    device_info=user_agent,
                    ip_address=client_ip,
                    is_active=True,
                )
                db.add(sess_record)

                # Record resumption event
                res_event = AttemptEvent(
                    attempt_id=active_attempt.id,
                    event_type="ATTEMPT_RESUMED",
                    event_metadata={"client_ip": client_ip, "user_agent": user_agent},
                    actor_type="student",
                    occurred_at=now,
                )
                db.add(res_event)
                db.commit()

                return StudentExamStartResponse(
                    attempt_id=active_attempt.id,
                    session_token=session_token,
                    quiz_id=quiz.id,
                    student_name=student.full_name,
                    student_identifier=student.profile.student_identifier if student.profile else None,
                    attempt_number=active_attempt.attempt_number,
                    started_at=_ensure_utc(active_attempt.started_at),
                    expires_at=act_deadline,
                    remaining_seconds=remaining,
                    is_resumed=True,
                    status=active_attempt.status,
                )
            else:
                StudentExamService._auto_expire_and_submit_attempt(db, active_attempt, commit=True)

        # Check maximum attempts
        max_attempts = cfg.max_attempts if cfg else 1
        past_attempts_count = db.query(func.count(ExaminationAttempt.id)).filter(
            ExaminationAttempt.quiz_id == quiz.id,
            ExaminationAttempt.student_id == student.id,
        ).scalar() or 0

        if past_attempts_count >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reached the maximum allowed attempts for this examination."
            )

        # Calculate expiration deadline
        duration_mins = quiz.duration_minutes or 60
        duration_seconds = duration_mins * 60
        expires_at = now + timedelta(seconds=duration_seconds)
        if cfg and cfg.end_time:
            end_limit = _ensure_utc(cfg.end_time) + timedelta(minutes=cfg.grace_period_minutes)
            if expires_at > end_limit:
                expires_at = end_limit

        # Resolve published quiz version for immutable question binding
        pub_version = db.query(QuizPublishedVersion).filter(
            QuizPublishedVersion.quiz_id == quiz.id
        ).order_by(QuizPublishedVersion.version_number.desc()).first()

        session_id = uuid.uuid4()

        # Phase 14 Question and Option Randomization Engine
        from backend.app.services.security_service import SecurityService
        policy = SecurityService.get_effective_policy(db, quiz.id)
        seed_hex = secrets.token_hex(16)
        pres_order = None

        if policy.randomize_question_order or policy.randomize_option_order:
            import random
            qq_objs = sorted(quiz.quiz_questions, key=lambda q: (q.section_id or uuid.UUID(int=0), q.question_order))

            question_order_list = []
            if policy.randomize_question_order:
                by_sec: Dict[Any, List[str]] = {}
                for qq in qq_objs:
                    sec_key = str(qq.section_id) if qq.section_id else "default"
                    by_sec.setdefault(sec_key, []).append(str(qq.id))
                for sec_key, q_ids in by_sec.items():
                    rng = random.Random(f"{seed_hex}_{sec_key}")
                    shuffled = list(q_ids)
                    rng.shuffle(shuffled)
                    question_order_list.extend(shuffled)
            else:
                question_order_list = [str(qq.id) for qq in qq_objs]

            option_order_dict = {}
            for qq in qq_objs:
                snap = qq.question_snapshot or {}
                q_type = snap.get("question_type") or ""
                raw_options = snap.get("options") or []
                opt_ids = [str(o.get("id") or o.get("option_id")) for o in raw_options if (o.get("id") or o.get("option_id"))]

                if policy.randomize_option_order and q_type not in ["true_false", "short_answer"] and len(opt_ids) > 1:
                    rng_opt = random.Random(f"{seed_hex}_{qq.id}")
                    shuffled_opts = list(opt_ids)
                    rng_opt.shuffle(shuffled_opts)
                    option_order_dict[str(qq.id)] = shuffled_opts
                else:
                    option_order_dict[str(qq.id)] = opt_ids

            pres_order = {
                "question_order": question_order_list,
                "option_order": option_order_dict,
            }

        new_attempt = ExaminationAttempt(
            quiz_id=quiz.id,
            student_id=student.id,
            attempt_number=past_attempts_count + 1,
            status="in_progress",
            started_at=now,
            expires_at=expires_at,
            deadline_at=expires_at,
            duration_seconds=duration_seconds,
            extra_time_seconds=0,
            published_quiz_version_id=pub_version.id if pub_version else None,
            presentation_seed=seed_hex,
            question_presentation_order=pres_order,
            active_session_token=str(session_id),
            last_heartbeat_at=now,
            is_immutable=False,
            time_spent_seconds=0,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(new_attempt)
        db.flush()

        # Record initial session
        sess_record = AttemptSession(
            attempt_id=new_attempt.id,
            session_token_hash=hashlib.sha256(str(session_id).encode("utf-8")).hexdigest(),
            device_info=user_agent,
            ip_address=client_ip,
            is_active=True,
        )
        db.add(sess_record)

        # Record attempt lifecycle audit events
        ev_created = AttemptEvent(
            attempt_id=new_attempt.id,
            event_type="ATTEMPT_CREATED",
            event_metadata={"attempt_number": new_attempt.attempt_number, "published_version_id": str(pub_version.id) if pub_version else None},
            actor_type="student",
            occurred_at=now,
        )
        ev_started = AttemptEvent(
            attempt_id=new_attempt.id,
            event_type="ATTEMPT_STARTED",
            event_metadata={"deadline": expires_at.isoformat(), "duration_seconds": duration_seconds},
            actor_type="student",
            occurred_at=now,
        )
        db.add_all([ev_created, ev_started])
        db.commit()
        db.refresh(new_attempt)

        session_token = StudentExamService._create_session_token(
            student_id=student.id,
            attempt_id=new_attempt.id,
            quiz_id=quiz.id,
            expires_at=_ensure_utc(new_attempt.expires_at),
            session_id=session_id,
        )

        remaining = max(0, int((_ensure_utc(new_attempt.expires_at) - now).total_seconds()))
        return StudentExamStartResponse(
            attempt_id=new_attempt.id,
            session_token=session_token,
            quiz_id=quiz.id,
            student_name=student.full_name,
            student_identifier=student.profile.student_identifier if student.profile else None,
            attempt_number=new_attempt.attempt_number,
            started_at=_ensure_utc(new_attempt.started_at),
            expires_at=_ensure_utc(new_attempt.expires_at),
            remaining_seconds=remaining,
            is_resumed=False,
            status=new_attempt.status,
        )

    @staticmethod
    def get_attempt_questions(db: Session, attempt_id: uuid.UUID, session_student_id: uuid.UUID) -> StudentAttemptDetailResponse:
        """
        Retrieves full question set and existing answers for an active attempt.
        CRITICAL SECURITY REQUIREMENT: Filters out correct answers, keys, and private explanations!
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.sections),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.student).joinedload(Student.profile),
            joinedload(ExaminationAttempt.answers),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found")

        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this attempt")

        # Once an attempt is submitted, concluded, or immutable, returning to the exam hall is strictly prohibited
        if attempt.is_immutable or attempt.status in ["submitted", "completed", "evaluated", "timed_out"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This examination attempt has already been submitted and concluded. Returning to the exam hall is not permitted."
            )

        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(attempt.expires_at)

        # Auto-timeout check
        if attempt.status == "in_progress" and now > expires_at:
            attempt.status = "timed_out"
            attempt.submitted_at = expires_at
            db.commit()

        quiz = attempt.quiz
        cfg = quiz.configuration

        # Sections
        sections = sorted(quiz.sections, key=lambda s: s.section_order) if quiz.sections else []
        section_responses = []
        for s in sections:
            section_responses.append(StudentSectionItemResponse(
                id=s.id,
                title=s.title,
                description=s.description,
                instructions=s.instructions,
                section_order=s.section_order,
                selection_rule=s.selection_rule,
                required_question_count=s.required_question_count,
                total_questions_count=len(s.questions) if s.questions else s.total_questions_count,
                section_total_marks=float(s.section_total_marks or 0.0),
            ))

        # Questions: Sanitized from question_snapshot without answer keys!
        question_responses = []

        # Check for frozen question presentation order (Phase 14 Randomization)
        pres = attempt.question_presentation_order or {}
        frozen_q_order = pres.get("question_order") or []
        frozen_opt_order = pres.get("option_order") or {}

        if frozen_q_order:
            q_order_map = {qid_str: idx for idx, qid_str in enumerate(frozen_q_order)}
            quiz_questions = sorted(quiz.quiz_questions, key=lambda q: q_order_map.get(str(q.id), 999999))
        else:
            quiz_questions = sorted(quiz.quiz_questions, key=lambda q: (q.section_id or uuid.UUID(int=0), q.question_order))

        for qq in quiz_questions:
            snap = qq.question_snapshot or {}

            # Sanitize options: exclude is_correct, explanation
            raw_options = snap.get("options") or []
            qq_id_str = str(qq.id)
            if frozen_opt_order and qq_id_str in frozen_opt_order:
                opt_order_map = {opt_id_str: idx for idx, opt_id_str in enumerate(frozen_opt_order[qq_id_str])}
                raw_options = sorted(raw_options, key=lambda o: opt_order_map.get(str(o.get("id") or o.get("option_id") or ""), 999999))

            sanitized_options = []
            for idx, opt in enumerate(raw_options, start=1):
                opt_id = str(opt.get("id") or opt.get("option_id") or "")
                opt_text = opt.get("text") or opt.get("option_text") or ""
                opt_img = opt.get("image_url") or opt.get("option_image_path")
                sanitized_options.append(StudentQuestionOptionResponse(
                    id=opt_id,
                    text=opt_text,
                    order=idx,
                    image_url=opt_img,
                ))

            q_resp = StudentQuestionItemResponse(
                id=qq.id,
                section_id=qq.section_id,
                question_order=qq.question_order,
                question_type=snap.get("question_type") or "single_choice",
                question_text=snap.get("question_text") or "",
                marks=float(qq.marks or snap.get("marks") or 1.0),
                negative_marks=float(qq.negative_marks or snap.get("negative_marks") or 0.0),
                is_compulsory=qq.is_compulsory,
                code_language=snap.get("code_language"),
                is_mathematical=bool(snap.get("is_mathematical", False)),
                attachments=snap.get("attachments"),
                options=sanitized_options if sanitized_options else None,
            )
            question_responses.append(q_resp)

        # Existing saved answers mapping
        answers_dict = {}
        for ans in attempt.answers:
            answers_dict[str(ans.quiz_question_id)] = {
                "selected_option_ids": ans.selected_option_ids or [],
                "text_response": ans.text_response or "",
                "is_flagged_for_review": ans.is_flagged_for_review,
                "time_spent_seconds": ans.time_spent_seconds,
                "answered_at": ans.answered_at.isoformat() if ans.answered_at else None,
            }

        remaining = max(0, int((expires_at - now).total_seconds())) if attempt.status == "in_progress" else 0

        # Phase 14 & Phase 23 Security Policy & Dynamic Watermark
        from backend.app.services.security_service import SecurityService, _mask_identifier
        sec_policy = SecurityService.get_effective_policy(db, quiz.id)
        wm_session = None
        watermark_str = None
        watermark_enabled = bool(sec_policy.enable_watermark or (cfg.watermark_enabled if cfg else False))
        if watermark_enabled and attempt.student:
            wm_session = SecurityService.generate_or_get_watermark_session(db, attempt)
            stud = attempt.student
            masked_code = _mask_identifier(stud.profile.student_identifier if stud.profile else None)
            att_slug = str(attempt.id)[:8].upper()
            if getattr(sec_policy, "watermark_pattern", None) and "{student_name}" in sec_policy.watermark_pattern:
                watermark_str = sec_policy.watermark_pattern.format(
                    student_name=stud.full_name,
                    masked_reg=masked_code,
                    attempt_id=att_slug,
                )
            else:
                watermark_str = wm_session.watermark_text

        policy_dict = {
            "track_tab_switch": sec_policy.track_tab_switch,
            "track_focus_loss": sec_policy.track_focus_loss,
            "require_fullscreen": sec_policy.require_fullscreen or (cfg.enforce_fullscreen if cfg else False),
            "track_fullscreen_exit": sec_policy.track_fullscreen_exit,
            "block_copy_paste": sec_policy.block_copy_paste or (cfg.disable_copy if cfg else False),
            "track_copy_paste": sec_policy.track_copy_paste,
            "block_context_menu": sec_policy.block_context_menu or (cfg.disable_context_menu if cfg else True),
            "track_page_reload": sec_policy.track_page_reload,
            "enable_watermark": watermark_enabled,
            "max_tab_switches_warning": sec_policy.max_tab_switches_warning,
            "max_tab_switches_critical": sec_policy.max_tab_switches_critical,
            "max_focus_losses_warning": sec_policy.max_focus_losses_warning,
            "max_fullscreen_exits_warning": sec_policy.max_fullscreen_exits_warning,
            # Phase 22 Advanced Browser Lockdown Settings
            "fullscreen_exit_policy": getattr(cfg, "fullscreen_exit_policy", getattr(sec_policy, "fullscreen_exit_policy", "warning_only")),
            "max_focus_loss_count": getattr(cfg, "max_focus_loss_count", getattr(sec_policy, "max_focus_loss_count", 5)),
            "disable_copy": getattr(cfg, "disable_copy", getattr(sec_policy, "disable_copy", True)),
            "disable_paste": getattr(cfg, "disable_paste", getattr(sec_policy, "disable_paste", True)),
            "disable_context_menu": getattr(cfg, "disable_context_menu", getattr(sec_policy, "disable_context_menu", True)),
            "print_restrictions": getattr(cfg, "print_restrictions", getattr(sec_policy, "print_restrictions", True)),
            "navigation_warning": getattr(cfg, "navigation_warning", getattr(sec_policy, "navigation_warning", True)),
            "network_interruption_policy": getattr(cfg, "network_interruption_policy", getattr(sec_policy, "network_interruption_policy", "buffer_and_resume")),
            "require_invigilator_review": getattr(cfg, "require_invigilator_review", getattr(sec_policy, "require_invigilator_review", True)),
            # Phase 23 Screenshot, Screen Recording & Dynamic Watermark Settings
            "watermark_code": wm_session.watermark_code if wm_session else None,
            "watermark_opacity": float(getattr(cfg, "watermark_opacity", getattr(sec_policy, "watermark_opacity", 0.06))),
            "watermark_font_size": int(getattr(cfg, "watermark_font_size", getattr(sec_policy, "watermark_font_size", 12))),
            "watermark_rotation_deg": int(getattr(cfg, "watermark_rotation_deg", getattr(sec_policy, "watermark_rotation_deg", -25))),
            "watermark_spacing_px": int(getattr(cfg, "watermark_spacing_px", getattr(sec_policy, "watermark_spacing_px", 140))),
            "watermark_update_interval_sec": int(getattr(cfg, "watermark_update_interval_sec", getattr(sec_policy, "watermark_update_interval_sec", 30))),
            "block_screen_capture_api": bool(getattr(cfg, "block_screen_capture_api", getattr(sec_policy, "block_screen_capture_api", True))),
            "track_screenshot_signals": bool(getattr(cfg, "track_screenshot_signals", getattr(sec_policy, "track_screenshot_signals", True))),
            "track_screen_recording_signals": bool(getattr(cfg, "track_screen_recording_signals", getattr(sec_policy, "track_screen_recording_signals", True))),
            # Phase 24 Mobile Security Settings
            "require_native_app": bool(getattr(cfg, "require_native_app", False)),
            "android_secure_mode": bool(getattr(cfg, "android_secure_mode", True)),
            "ios_secure_mode": bool(getattr(cfg, "ios_secure_mode", True)),
            "require_kiosk_mode": bool(getattr(cfg, "require_kiosk_mode", False)),
            "min_android_version": int(getattr(cfg, "min_android_version", 26)),
            "min_ios_version": str(getattr(cfg, "min_ios_version", "15.0")),
            "mobile_interruption_policy": str(getattr(cfg, "mobile_interruption_policy", "allow_with_event")),
            "allow_device_recovery": bool(getattr(cfg, "allow_device_recovery", True)),
            "block_rooted_devices": bool(getattr(cfg, "block_rooted_devices", False)),
        }

        return StudentAttemptDetailResponse(
            attempt_id=attempt.id,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            student_name=attempt.student.full_name,
            student_identifier=attempt.student.profile.student_identifier if attempt.student.profile else None,
            status=attempt.status,
            started_at=_ensure_utc(attempt.started_at),
            expires_at=expires_at,
            remaining_seconds=remaining,
            server_time=now,
            navigation_mode=cfg.navigation_mode if cfg else "free",
            allow_previous_nav=cfg.allow_previous_nav if cfg else True,
            allow_answer_change=cfg.allow_answer_change if cfg else True,
            allow_mark_for_review=cfg.allow_mark_for_review if cfg else True,
            show_question_palette=cfg.show_question_palette if cfg else True,
            sections=section_responses,
            questions=question_responses,
            answers=answers_dict,
            watermark_text=watermark_str,
            security_policy=policy_dict,
            monitoring_acknowledged=attempt.monitoring_acknowledged_at is not None,
        )

    @staticmethod
    def save_attempt_answer(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: StudentSaveAnswerRequest,
    ) -> StudentSaveAnswerResponse:
        """
        Saves or updates a candidate's response for a specific question.
        Enforces active status, server deadline, option validation, and optimistic concurrency.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if attempt.is_immutable or attempt.status == "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Examination attempt is finalized and immutable. Answers cannot be modified."
            )

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if attempt.status != "in_progress" or now > deadline:
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Examination attempt is no longer active or time has expired"
            )

        quiz = attempt.quiz
        cfg = quiz.configuration

        # Validate that the question belongs to this quiz
        qq = next((q for q in quiz.quiz_questions if q.id == req.quiz_question_id), None)
        if not qq:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to this examination."
            )

        snap = qq.question_snapshot or {}
        valid_opts = {str(opt.get("id") or opt.get("option_id")) for opt in (snap.get("options") or [])}
        if req.selected_option_ids:
            for opt_id in req.selected_option_ids:
                if valid_opts and str(opt_id) not in valid_opts:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid option selection '{opt_id}' for question."
                    )

        if req.text_response and len(req.text_response) > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text response exceeds maximum character limit."
            )

        existing = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.quiz_question_id == req.quiz_question_id,
        ).first()

        # Idempotent retry detection
        if existing and req.idempotency_key and existing.idempotency_key == req.idempotency_key:
            has_ans = bool(existing.selected_option_ids or (existing.text_response and existing.text_response.strip()))
            return StudentSaveAnswerResponse(
                success=True,
                quiz_question_id=req.quiz_question_id,
                saved_at=existing.answered_at,
                is_answered=has_ans,
                is_flagged_for_review=existing.is_flagged_for_review,
                answer_id=existing.id,
                version=existing.version,
                answer_status=existing.answer_status,
            )

        # Optimistic concurrency control check
        if existing and req.version is not None and req.version < existing.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Client answer version ({req.version}) is older than server version ({existing.version})."
            )

        if existing and cfg and not cfg.allow_answer_change:
            has_prev = bool(existing.selected_option_ids or (existing.text_response and existing.text_response.strip()))
            if has_prev:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Answer modification is restricted for this examination."
                )

        target_record = existing
        if existing:
            if req.selected_option_ids is not None or req.text_response is not None:
                existing.selected_option_ids = req.selected_option_ids
                existing.text_response = req.text_response
            if req.is_flagged_for_review is not None:
                existing.is_flagged_for_review = req.is_flagged_for_review
            existing.version += 1
            existing.idempotency_key = req.idempotency_key
            existing.client_timestamp = req.client_timestamp
            existing.time_spent_seconds = existing.time_spent_seconds + req.time_spent_seconds
            existing.answered_at = now

            has_content = bool(existing.selected_option_ids or (existing.text_response and existing.text_response.strip()))
            if has_content and existing.is_flagged_for_review:
                existing.answer_status = "ANSWERED_AND_MARKED"
            elif has_content:
                existing.answer_status = "ANSWERED"
            elif existing.is_flagged_for_review:
                existing.answer_status = "MARKED_FOR_REVIEW"
            else:
                existing.answer_status = "NOT_ANSWERED"

            # Event logging
            db.add(AttemptEvent(
                attempt_id=attempt.id,
                event_type="ANSWER_UPDATED",
                event_metadata={"quiz_question_id": str(req.quiz_question_id), "version": existing.version},
                actor_type="student",
                occurred_at=now,
            ))
        else:
            has_content = bool(req.selected_option_ids or (req.text_response and req.text_response.strip()))
            flag = req.is_flagged_for_review if req.is_flagged_for_review is not None else False
            if has_content and flag:
                status_str = "ANSWERED_AND_MARKED"
            elif has_content:
                status_str = "ANSWERED"
            elif flag:
                status_str = "MARKED_FOR_REVIEW"
            else:
                status_str = "NOT_ANSWERED"

            new_ans = AttemptAnswer(
                attempt_id=attempt.id,
                quiz_question_id=req.quiz_question_id,
                selected_option_ids=req.selected_option_ids,
                text_response=req.text_response,
                is_flagged_for_review=flag,
                version=1,
                idempotency_key=req.idempotency_key,
                answer_status=status_str,
                client_timestamp=req.client_timestamp,
                source_question_id=qq.question_id,
                time_spent_seconds=req.time_spent_seconds,
                answered_at=now,
            )
            db.add(new_ans)
            target_record = new_ans

            db.add(AttemptEvent(
                attempt_id=attempt.id,
                event_type="ANSWER_SAVED",
                event_metadata={"quiz_question_id": str(req.quiz_question_id), "version": 1},
                actor_type="student",
                occurred_at=now,
            ))

        attempt.time_spent_seconds = attempt.time_spent_seconds + req.time_spent_seconds
        attempt.last_heartbeat_at = now
        db.commit()
        db.refresh(target_record)

        is_ans = bool(target_record.selected_option_ids or (target_record.text_response and target_record.text_response.strip()))
        return StudentSaveAnswerResponse(
            success=True,
            quiz_question_id=req.quiz_question_id,
            saved_at=target_record.answered_at,
            is_answered=is_ans,
            is_flagged_for_review=target_record.is_flagged_for_review,
            answer_id=target_record.id,
            version=target_record.version,
            answer_status=target_record.answer_status,
        )

    @staticmethod
    def update_answer_by_id(
        db: Session,
        attempt_id: uuid.UUID,
        answer_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: SingleAnswerUpdateRequest,
    ) -> AnswerItemResponse:
        """PATCH handler for a specific answer record by answer_id."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if attempt.is_immutable or attempt.status == "submitted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is finalized.")

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if attempt.status != "in_progress" or now > deadline:
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deadline expired.")

        ans = db.query(AttemptAnswer).filter(
            AttemptAnswer.id == answer_id,
            AttemptAnswer.attempt_id == attempt.id,
        ).first()
        if not ans:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found.")

        if req.version is not None and req.version < ans.version:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conflict: Version {req.version} is stale.")

        if req.selected_option_ids is not None:
            ans.selected_option_ids = req.selected_option_ids
        if req.text_response is not None:
            ans.text_response = req.text_response
        if req.is_flagged_for_review is not None:
            ans.is_flagged_for_review = req.is_flagged_for_review
        ans.version += 1
        ans.time_spent_seconds += req.time_spent_seconds
        ans.answered_at = now

        has_content = bool(ans.selected_option_ids or (ans.text_response and ans.text_response.strip()))
        if has_content and ans.is_flagged_for_review:
            ans.answer_status = "ANSWERED_AND_MARKED"
        elif has_content:
            ans.answer_status = "ANSWERED"
        elif ans.is_flagged_for_review:
            ans.answer_status = "MARKED_FOR_REVIEW"
        else:
            ans.answer_status = "NOT_ANSWERED"

        db.add(AttemptEvent(
            attempt_id=attempt.id,
            event_type="ANSWER_UPDATED",
            event_metadata={"answer_id": str(ans.id), "version": ans.version},
            actor_type="student",
            occurred_at=now,
        ))
        attempt.last_heartbeat_at = now
        db.commit()
        db.refresh(ans)

        return AnswerItemResponse(
            id=ans.id,
            attempt_id=ans.attempt_id,
            quiz_question_id=ans.quiz_question_id,
            selected_option_ids=ans.selected_option_ids,
            text_response=ans.text_response,
            is_flagged_for_review=ans.is_flagged_for_review,
            version=ans.version,
            answer_status=ans.answer_status,
            time_spent_seconds=ans.time_spent_seconds,
            answered_at=ans.answered_at,
        )

    @staticmethod
    def delete_answer_by_id(
        db: Session,
        attempt_id: uuid.UUID,
        answer_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Clears an answer's selected options or text response without clearing the review marker."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if attempt.is_immutable or attempt.status == "submitted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is finalized.")

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if attempt.status != "in_progress" or now > deadline:
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deadline expired.")

        ans = db.query(AttemptAnswer).filter(
            AttemptAnswer.id == answer_id,
            AttemptAnswer.attempt_id == attempt.id,
        ).first()
        if not ans:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found.")

        ans.selected_option_ids = None
        ans.text_response = None
        ans.version += 1
        ans.answer_status = "MARKED_FOR_REVIEW" if ans.is_flagged_for_review else "NOT_ANSWERED"
        ans.answered_at = now

        db.add(AttemptEvent(
            attempt_id=attempt.id,
            event_type="ANSWER_CLEARED",
            event_metadata={"answer_id": str(ans.id), "quiz_question_id": str(ans.quiz_question_id)},
            actor_type="student",
            occurred_at=now,
        ))
        attempt.last_heartbeat_at = now
        db.commit()

        return {
            "success": True,
            "answer_id": str(ans.id),
            "quiz_question_id": str(ans.quiz_question_id),
            "version": ans.version,
            "answer_status": ans.answer_status,
        }

    @staticmethod
    def batch_save_attempt_answers(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: BatchAnswerSaveRequest,
    ) -> BatchAnswerSaveResponse:
        """Processes a batch of answer synchronization operations atomically in one transaction."""
        saved_list = []
        for op in req.operations:
            res = StudentExamService.save_attempt_answer(
                db=db,
                attempt_id=attempt_id,
                session_student_id=session_student_id,
                req=op,
            )
            saved_list.append(res)

        return BatchAnswerSaveResponse(
            success=True,
            total_processed=len(saved_list),
            saved_answers=saved_list,
            server_time=datetime.now(timezone.utc),
        )

    @staticmethod
    def get_attempt_answers(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> List[AnswerItemResponse]:
        """Retrieves all persisted answers for the active attempt."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
        return [
            AnswerItemResponse(
                id=a.id,
                attempt_id=a.attempt_id,
                quiz_question_id=a.quiz_question_id,
                selected_option_ids=a.selected_option_ids,
                text_response=a.text_response,
                is_flagged_for_review=a.is_flagged_for_review,
                version=a.version,
                answer_status=a.answer_status,
                time_spent_seconds=a.time_spent_seconds,
                answered_at=a.answered_at,
            )
            for a in answers
        ]

    @staticmethod
    def toggle_review_flag(
        db: Session,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: ReviewFlagUpdateRequest,
    ) -> ReviewFlagUpdateResponse:
        """Persistently marks or unmarks a question for review without altering the answer."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if attempt.is_immutable or attempt.status == "submitted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is finalized.")

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if attempt.status != "in_progress" or now > deadline:
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deadline expired.")

        existing = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.quiz_question_id == question_id,
        ).first()

        if existing:
            existing.is_flagged_for_review = req.is_flagged_for_review
            existing.version += 1
            has_content = bool(existing.selected_option_ids or (existing.text_response and existing.text_response.strip()))
            if has_content and existing.is_flagged_for_review:
                existing.answer_status = "ANSWERED_AND_MARKED"
            elif has_content:
                existing.answer_status = "ANSWERED"
            elif existing.is_flagged_for_review:
                existing.answer_status = "MARKED_FOR_REVIEW"
            else:
                existing.answer_status = "NOT_ANSWERED"
        else:
            status_str = "MARKED_FOR_REVIEW" if req.is_flagged_for_review else "NOT_ANSWERED"
            new_ans = AttemptAnswer(
                attempt_id=attempt.id,
                quiz_question_id=question_id,
                is_flagged_for_review=req.is_flagged_for_review,
                answer_status=status_str,
                version=1,
                time_spent_seconds=0,
                answered_at=now,
            )
            db.add(new_ans)

        db.add(AttemptEvent(
            attempt_id=attempt.id,
            event_type="QUESTION_MARKED_REVIEW",
            event_metadata={"quiz_question_id": str(question_id), "is_flagged": req.is_flagged_for_review},
            actor_type="student",
            occurred_at=now,
        ))
        attempt.last_heartbeat_at = now
        db.commit()

        return ReviewFlagUpdateResponse(
            success=True,
            quiz_question_id=question_id,
            is_flagged_for_review=req.is_flagged_for_review,
            updated_at=now,
        )

    @staticmethod
    def get_attempt_progress(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> StudentProgressResponse:
        """Calculates server-authoritative progress, answered statistics, and section requirements."""
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.sections).joinedload(QuizSection.questions),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.answers),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt or attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if attempt.is_immutable or attempt.status in ["submitted", "completed", "evaluated", "timed_out"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This examination attempt has already been submitted and concluded. Review is unavailable."
            )

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        is_expired = now > deadline

        if is_expired and attempt.status == "in_progress":
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)

        quiz = attempt.quiz
        sections = sorted(quiz.sections, key=lambda s: s.section_order) if quiz.sections else []

        answered_map = {}
        flagged_map = {}
        for a in attempt.answers:
            has_ans = bool(a.selected_option_ids or (a.text_response and a.text_response.strip()))
            answered_map[a.quiz_question_id] = has_ans
            flagged_map[a.quiz_question_id] = a.is_flagged_for_review

        total_questions = len(quiz.quiz_questions)
        total_answered = sum(1 for is_ans in answered_map.values() if is_ans)
        total_marked = sum(1 for is_flag in flagged_map.values() if is_flag)
        total_unanswered = max(0, total_questions - total_answered)
        remaining = max(0, int((deadline - now).total_seconds())) if not is_expired else 0

        sections_prog = []
        if sections:
            for s in sections:
                sqs = s.questions or []
                stot = len(sqs)
                sans = sum(1 for q in sqs if answered_map.get(q.id))
                smark = sum(1 for q in sqs if flagged_map.get(q.id))
                sunans = max(0, stot - sans)
                is_sat = True
                if s.selection_rule == "all_compulsory":
                    is_sat = (sunans == 0)
                elif s.selection_rule == "answer_n_of_m" and s.required_question_count:
                    is_sat = (sans >= s.required_question_count)
                sections_prog.append({
                    "section_id": str(s.id),
                    "title": s.title,
                    "total": stot,
                    "answered": sans,
                    "unanswered": sunans,
                    "marked": smark,
                    "selection_rule": s.selection_rule,
                    "required_count": s.required_question_count,
                    "is_satisfied": is_sat,
                })

        return StudentProgressResponse(
            attempt_id=attempt.id,
            total_questions=total_questions,
            answered_count=total_answered,
            unanswered_count=total_unanswered,
            marked_for_review_count=total_marked,
            remaining_seconds=remaining,
            deadline_at=deadline,
            status=attempt.status,
            is_expired=is_expired,
            sections_progress=sections_prog,
        )

    @staticmethod
    def heartbeat(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: StudentHeartbeatRequest,
    ) -> StudentHeartbeatResponse:
        """Heartbeat to track session liveness, sync timer, and detect expiry."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if attempt.status == "in_progress" and now > deadline:
            StudentExamService._auto_expire_and_submit_attempt(db, attempt, commit=True)

        attempt.last_heartbeat_at = now
        db.commit()

        remaining = max(0, int((deadline - now).total_seconds())) if now <= deadline else 0
        return StudentHeartbeatResponse(
            server_time=now,
            remaining_seconds=remaining,
            deadline_at=deadline,
            status=attempt.status,
            is_active_session=True,
        )

    @staticmethod
    def record_attempt_event(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records telemetry / proctoring events during the examination session."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt or attempt.student_id != session_student_id:
            return

        event = AttemptEvent(
            attempt_id=attempt.id,
            event_type=event_type,
            event_metadata=metadata or {},
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()

    @staticmethod
    def get_attempt_review_summary(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> StudentReviewSummaryResponse:
        """
        Computes section-wise completion, optional vs mandatory requirements,
        answered counts, and flagged review items prior to final submission.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.sections).joinedload(QuizSection.questions),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.answers),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt or attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if attempt.is_immutable or attempt.status in ["submitted", "completed", "evaluated", "timed_out"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This examination attempt has already been submitted and concluded. Review is unavailable."
            )

        quiz = attempt.quiz
        sections = sorted(quiz.sections, key=lambda s: s.section_order) if quiz.sections else []
        all_qq = {qq.id: qq for qq in quiz.quiz_questions}

        answered_map = {}
        flagged_map = {}
        for a in attempt.answers:
            is_ans = bool(a.selected_option_ids or (a.text_response and a.text_response.strip()))
            answered_map[a.quiz_question_id] = is_ans
            flagged_map[a.quiz_question_id] = a.is_flagged_for_review

        total_questions = len(quiz.quiz_questions)
        total_answered = sum(1 for is_ans in answered_map.values() if is_ans)
        total_marked = sum(1 for is_flag in flagged_map.values() if is_flag)
        total_unanswered = max(0, total_questions - total_answered)

        sections_breakdown = []
        mandatory_unanswered = []

        if sections:
            for s in sections:
                s_questions = s.questions or []
                s_total = len(s_questions)
                s_answered = sum(1 for q in s_questions if answered_map.get(q.id))
                s_marked = sum(1 for q in s_questions if flagged_map.get(q.id))
                s_unanswered = max(0, s_total - s_answered)

                is_satisfied = True
                if s.selection_rule == "all_compulsory":
                    is_satisfied = (s_unanswered == 0)
                    for q in s_questions:
                        if not answered_map.get(q.id):
                            mandatory_unanswered.append({
                                "question_id": str(q.id),
                                "order": q.question_order,
                                "section_title": s.title,
                            })
                elif s.selection_rule == "answer_n_of_m" and s.required_question_count:
                    is_satisfied = (s_answered >= s.required_question_count)

                sections_breakdown.append({
                    "section_id": str(s.id),
                    "title": s.title,
                    "total": s_total,
                    "answered": s_answered,
                    "unanswered": s_unanswered,
                    "marked": s_marked,
                    "selection_rule": s.selection_rule,
                    "required_question_count": s.required_question_count,
                    "is_satisfied": is_satisfied,
                })
        else:
            for qq in quiz.quiz_questions:
                if qq.is_compulsory and not answered_map.get(qq.id):
                    mandatory_unanswered.append({
                        "question_id": str(qq.id),
                        "order": qq.question_order,
                        "section_title": "General",
                    })

        return StudentReviewSummaryResponse(
            total_questions=total_questions,
            answered_count=total_answered,
            unanswered_count=total_unanswered,
            marked_for_review_count=total_marked,
            sections=sections_breakdown,
            mandatory_unanswered=mandatory_unanswered,
            can_submit=True,
        )

    @staticmethod
    def submit_attempt(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
        req: Optional[StudentSubmitRequest] = None,
    ) -> StudentSubmitResponse:
        """
        Finalizes candidate submission:
        - Sets attempt status = 'submitted'
        - Increments participant attempt_count
        - Computes preliminary evaluation if automatic scoring is configured
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.answers),
            joinedload(ExaminationAttempt.student),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Idempotent response if already submitted
        if attempt.status == "submitted" or attempt.is_immutable:
            return StudentSubmitResponse(
                success=True,
                submitted_at=_ensure_utc(attempt.submitted_at) or datetime.now(timezone.utc),
                message="Examination has already been submitted.",
                status="submitted",
            )

        now = datetime.now(timezone.utc)
        deadline = _ensure_utc(attempt.deadline_at or attempt.expires_at)
        if now > deadline:
            submission_reason = "TIME_EXPIRED"
            submission_source = "server_deadline"
        else:
            submission_reason = (req.submission_reason if req and req.submission_reason else "STUDENT_SUBMITTED")
            submission_source = "web_client"

        attempt.status = "submitted"
        attempt.submitted_at = now
        attempt.submission_reason = submission_reason
        attempt.submission_source = submission_source
        attempt.is_immutable = True

        # Update participant attempt count
        participant = db.query(QuizParticipant).filter(
            QuizParticipant.quiz_id == attempt.quiz_id,
            QuizParticipant.student_id == attempt.student_id,
        ).first()
        if participant:
            participant.attempt_count += 1

        # Authoritative scoring evaluation via Phase 15 Evaluation Engine
        EvaluationService.run_evaluation(db, attempt.id)

        db.add(AttemptEvent(
            attempt_id=attempt.id,
            event_type="SUBMISSION_COMPLETED",
            event_metadata={"reason": submission_reason, "source": submission_source},
            actor_type="student",
            occurred_at=now,
        ))

        db.commit()

        return StudentSubmitResponse(
            success=True,
            submitted_at=now,
            message="Your examination has been submitted successfully.",
            status="submitted",
        )

    @staticmethod
    def process_expired_attempts(db: Session) -> int:
        """
        Proactive worker / scheduler helper:
        Finds all active in_progress attempts whose deadline has passed and finalizes them safely.
        """
        now = datetime.now(timezone.utc)
        expired_attempts = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.answers),
        ).filter(
            ExaminationAttempt.status == "in_progress",
            or_(
                ExaminationAttempt.deadline_at <= now,
                ExaminationAttempt.expires_at <= now,
            )
        ).all()

        count = 0
        for att in expired_attempts:
            StudentExamService._auto_expire_and_submit_attempt(db, att, commit=False)
            count += 1

        if count > 0:
            db.commit()
        return count

    @staticmethod
    def _build_result_response(quiz: Quiz, cfg: Optional[QuizConfiguration], attempt: ExaminationAttempt) -> StudentResultResponse:
        now = datetime.now(timezone.utc)
        policy = cfg.result_release_policy if cfg else "immediate"

        is_released = False
        message = "Results are not yet available for this examination."

        if policy == "immediate":
            is_released = True
            message = "Examination evaluation completed."
        elif policy == "after_close":
            if cfg and cfg.end_time and now > _ensure_utc(cfg.end_time):
                is_released = True
                message = "Examination window has closed. Results are now available."
            else:
                message = "Results will be published after the examination window closes."
        elif policy in ["after_admin_approval", "after_manual_eval"]:
            message = "Results will be released after administrator verification and manual scoring."
        elif policy == "never":
            message = "Examination submitted. Result viewing is not enabled for this session."

        if not is_released or not attempt.result:
            return StudentResultResponse(
                is_released=False,
                message=message,
                quiz_title=quiz.title,
                student_name=attempt.student.full_name,
                student_identifier=attempt.student.profile.student_identifier if attempt.student.profile else None,
                submission_status=attempt.status,
            )

        res = attempt.result
        return StudentResultResponse(
            is_released=True,
            message=message,
            quiz_title=quiz.title,
            student_name=attempt.student.full_name,
            student_identifier=attempt.student.profile.student_identifier if attempt.student.profile else None,
            score=float(res.score or 0.0),
            total_marks=float(quiz.total_marks or 100.0),
            percentage=float(res.percentage or 0.0),
            is_passed=bool(res.is_passed),
            submission_status=attempt.status,
            total_correct=res.total_correct,
            total_incorrect=res.total_incorrect,
            total_unanswered=res.total_unanswered,
            sections_breakdown=res.section_scores,
        )

    @staticmethod
    def get_attempt_result(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: uuid.UUID,
    ) -> StudentResultResponse:
        """
        Retrieves result if permitted according to Phase 10 visibility settings.
        PROTECTION: Never exposes answer keys or explanations when restricted!
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.student).joinedload(Student.profile),
            joinedload(ExaminationAttempt.result),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return StudentExamService._build_result_response(attempt.quiz, attempt.quiz.configuration, attempt)

    @staticmethod
    def get_exam_result_by_candidate(
        db: Session,
        token: str,
        registration_code: Optional[str] = None,
        email: Optional[str] = None,
        student_identifier: Optional[str] = None,
    ) -> StudentResultResponse:
        """
        Retrieves the finalized examination result scorecard for a candidate identified
        by their registration code, roll number, or email without requiring an ephemeral in-exam JWT.
        """
        if not registration_code and token and token.upper().startswith("REG-"):
            registration_code = token.upper()

        inv = _resolve_invitation_or_quiz(db, token, load_sections=False)
        if not inv or not inv.quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")

        quiz = inv.quiz

        # Resolve student candidate
        student: Optional[Student] = None
        if registration_code:
            code_clean = registration_code.strip().upper()
            pure_code = code_clean.replace("REG-", "").strip().lower()
            all_parts = (
                db.query(QuizParticipant)
                .options(joinedload(QuizParticipant.student).joinedload(Student.profile))
                .filter(QuizParticipant.quiz_id == quiz.id)
                .all()
            )
            for p in all_parts:
                p_hex = str(p.id).replace("-", "").lower()
                p_str = str(p.id).lower()
                expected_code = f"REG-{str(p.id)[:8].upper()}"
                if (
                    expected_code == code_clean
                    or str(p.id).upper() == code_clean
                    or p_str.startswith(pure_code)
                    or p_hex.startswith(pure_code)
                ):
                    student = p.student
                    break
        elif email:
            student = db.query(Student).filter(func.lower(Student.email) == email.strip().lower()).first()
        elif student_identifier:
            prof = db.query(StudentProfile).filter(StudentProfile.student_identifier == student_identifier.strip()).first()
            if prof:
                student = prof.student

        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate record not found. Please provide a valid registration code."
            )

        # Locate completed or submitted attempt for this student
        attempt = (
            db.query(ExaminationAttempt)
            .options(
                joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
                joinedload(ExaminationAttempt.student).joinedload(Student.profile),
                joinedload(ExaminationAttempt.result),
            )
            .filter(
                ExaminationAttempt.quiz_id == quiz.id,
                ExaminationAttempt.student_id == student.id,
            )
            .order_by(ExaminationAttempt.attempt_number.desc())
            .first()
        )

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No examination attempt found for this candidate."
            )

        # Proactively evaluate scoring if attempt is concluded/submitted but has no result record yet!
        if not attempt.result:
            try:
                EvaluationService.run_evaluation(db, attempt.id)
                db.commit()
                db.refresh(attempt)
            except Exception as eval_err:
                logger.warning(f"On-demand evaluation warning for attempt {attempt.id}: {eval_err}")

        return StudentExamService._build_result_response(quiz, quiz.configuration, attempt)
