import uuid
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from backend.app.core.config import settings
from backend.app.models.base import utc_now
from backend.app.models.invitation import InvitationLink
from backend.app.models.quiz import (
    Quiz,
    QuizConfiguration,
    QuizSection,
    QuizQuestion,
)
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer, AttemptEvent
from backend.app.models.results import ExaminationResult, QuestionEvaluation
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


class StudentExamService:

    @staticmethod
    def _create_session_token(student_id: uuid.UUID, attempt_id: uuid.UUID, quiz_id: uuid.UUID, expires_at: datetime) -> str:
        """Create a cryptographically signed JWT for the active candidate examination attempt."""
        payload = {
            "sub": str(student_id),
            "attempt_id": str(attempt_id),
            "quiz_id": str(quiz_id),
            "iat": datetime.now(timezone.utc),
            "exp": expires_at + timedelta(hours=2),  # Valid through examination window + buffer
            "type": "student_exam_session",
        }
        return jwt.encode(payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)

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
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        inv = db.query(InvitationLink).options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
            joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
            joinedload(InvitationLink.quiz).joinedload(Quiz.sections).joinedload(QuizSection.questions),
        ).filter(InvitationLink.token_hash == token_hash).first()

        if not inv:
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
            # Match by participant id prefix or full id
            all_parts = db.query(QuizParticipant).options(
                joinedload(QuizParticipant.student).joinedload(Student.profile)
            ).filter(QuizParticipant.quiz_id == quiz.id).all()
            for p in all_parts:
                expected_code = f"REG-{str(p.id)[:8].upper()}"
                if expected_code == code_clean or str(p.id).upper() == code_clean:
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
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        inv = db.query(InvitationLink).options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.subject),
            joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
            joinedload(InvitationLink.quiz).joinedload(Quiz.sections).joinedload(QuizSection.questions),
        ).filter(InvitationLink.token_hash == token_hash).first()

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
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        inv = db.query(InvitationLink).options(
            joinedload(InvitationLink.quiz).joinedload(Quiz.configuration),
        ).filter(InvitationLink.token_hash == token_hash).first()

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
            if _ensure_utc(active_attempt.expires_at) > now:
                remaining = max(0, int((_ensure_utc(active_attempt.expires_at) - now).total_seconds()))
                session_token = StudentExamService._create_session_token(
                    student_id=student.id,
                    attempt_id=active_attempt.id,
                    quiz_id=quiz.id,
                    expires_at=_ensure_utc(active_attempt.expires_at),
                )
                return StudentExamStartResponse(
                    attempt_id=active_attempt.id,
                    session_token=session_token,
                    quiz_id=quiz.id,
                    student_name=student.full_name,
                    student_identifier=student.profile.student_identifier if student.profile else None,
                    attempt_number=active_attempt.attempt_number,
                    started_at=_ensure_utc(active_attempt.started_at),
                    expires_at=_ensure_utc(active_attempt.expires_at),
                    remaining_seconds=remaining,
                    is_resumed=True,
                    status=active_attempt.status,
                )
            else:
                active_attempt.status = "timed_out"
                active_attempt.submitted_at = active_attempt.expires_at
                db.commit()

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
        expires_at = now + timedelta(minutes=duration_mins)
        if cfg and cfg.end_time:
            end_limit = _ensure_utc(cfg.end_time) + timedelta(minutes=cfg.grace_period_minutes)
            if expires_at > end_limit:
                expires_at = end_limit

        new_attempt = ExaminationAttempt(
            quiz_id=quiz.id,
            student_id=student.id,
            attempt_number=past_attempts_count + 1,
            status="in_progress",
            started_at=now,
            expires_at=expires_at,
            time_spent_seconds=0,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(new_attempt)
        db.commit()
        db.refresh(new_attempt)

        session_token = StudentExamService._create_session_token(
            student_id=student.id,
            attempt_id=new_attempt.id,
            quiz_id=quiz.id,
            expires_at=_ensure_utc(new_attempt.expires_at),
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
        quiz_questions = sorted(quiz.quiz_questions, key=lambda q: (q.section_id or uuid.UUID(int=0), q.question_order))

        for qq in quiz_questions:
            snap = qq.question_snapshot or {}

            # Sanitize options: exclude is_correct, explanation
            raw_options = snap.get("options") or []
            sanitized_options = []
            for opt in raw_options:
                opt_id = str(opt.get("id") or opt.get("option_id") or "")
                opt_text = opt.get("text") or opt.get("option_text") or ""
                opt_order = opt.get("order") or opt.get("option_order") or 0
                opt_img = opt.get("image_url") or opt.get("option_image_path")
                sanitized_options.append(StudentQuestionOptionResponse(
                    id=opt_id,
                    text=opt_text,
                    order=opt_order,
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
        Enforces active status, deadline, and navigation change rules.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration)
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.student_id != session_student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        now = datetime.now(timezone.utc)
        if attempt.status != "in_progress" or now > _ensure_utc(attempt.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Examination attempt is no longer active or time has expired"
            )

        cfg = attempt.quiz.configuration

        # Find existing answer
        existing = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.quiz_question_id == req.quiz_question_id,
        ).first()

        if existing and cfg and not cfg.allow_answer_change:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Answer modification is restricted for this examination."
            )

        is_answered = bool(req.selected_option_ids or (req.text_response and req.text_response.strip()))

        if existing:
            existing.selected_option_ids = req.selected_option_ids
            existing.text_response = req.text_response
            existing.is_flagged_for_review = req.is_flagged_for_review
            existing.time_spent_seconds = existing.time_spent_seconds + req.time_spent_seconds
            existing.answered_at = now
        else:
            new_ans = AttemptAnswer(
                attempt_id=attempt.id,
                quiz_question_id=req.quiz_question_id,
                selected_option_ids=req.selected_option_ids,
                text_response=req.text_response,
                is_flagged_for_review=req.is_flagged_for_review,
                time_spent_seconds=req.time_spent_seconds,
                answered_at=now,
            )
            db.add(new_ans)

        # Accumulate total time spent on attempt
        attempt.time_spent_seconds = attempt.time_spent_seconds + req.time_spent_seconds
        db.commit()

        return StudentSaveAnswerResponse(
            success=True,
            quiz_question_id=req.quiz_question_id,
            saved_at=now,
            is_answered=is_answered,
            is_flagged_for_review=req.is_flagged_for_review,
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

        if attempt.status == "submitted":
            return StudentSubmitResponse(
                success=True,
                submitted_at=_ensure_utc(attempt.submitted_at) or datetime.now(timezone.utc),
                message="Examination has already been submitted.",
                status="submitted",
            )

        now = datetime.now(timezone.utc)
        attempt.status = "submitted"
        attempt.submitted_at = now

        # Update participant attempt count
        participant = db.query(QuizParticipant).filter(
            QuizParticipant.quiz_id == attempt.quiz_id,
            QuizParticipant.student_id == attempt.student_id,
        ).first()
        if participant:
            participant.attempt_count += 1

        # Preliminary scoring evaluation
        quiz = attempt.quiz
        cfg = quiz.configuration
        total_quiz_marks = float(quiz.total_marks or 100.0)
        passing_pct = float(cfg.passing_percentage if cfg else 40.0)

        # Compute objective question evaluation
        answers_by_qq = {a.quiz_question_id: a for a in attempt.answers}
        total_correct = 0
        total_incorrect = 0
        total_unanswered = 0
        earned_marks = 0.0

        for qq in quiz.quiz_questions:
            snap = qq.question_snapshot or {}
            ans = answers_by_qq.get(qq.id)

            if not ans or (not ans.selected_option_ids and not (ans.text_response and ans.text_response.strip())):
                total_unanswered += 1
                continue

            qtype = snap.get("question_type")
            q_marks = float(qq.marks or snap.get("marks") or 1.0)
            q_neg_marks = float(qq.negative_marks or snap.get("negative_marks") or 0.0)

            # Evaluate objective questions (single_choice, multiple_choice, true_false)
            if qtype in ["single_choice", "true_false", "multiple_choice"]:
                # Correct options from snapshot
                correct_opts = []
                for opt in snap.get("options") or []:
                    if opt.get("is_correct"):
                        correct_opts.append(str(opt.get("id") or opt.get("option_id")))
                if not correct_opts and snap.get("correct_answers"):
                    correct_opts = [str(x) for x in snap.get("correct_answers")]

                user_selected = [str(x) for x in (ans.selected_option_ids or [])]

                if sorted(user_selected) == sorted(correct_opts) and len(correct_opts) > 0:
                    total_correct += 1
                    earned_marks += q_marks
                else:
                    total_incorrect += 1
                    earned_marks -= q_neg_marks

        if total_quiz_marks > 0:
            pct = round((earned_marks / total_quiz_marks) * 100.0, 2)
        else:
            pct = 0.0

        is_passed = (pct >= passing_pct)

        # Upsert ExaminationResult
        existing_res = db.query(ExaminationResult).filter(ExaminationResult.attempt_id == attempt.id).first()
        if existing_res:
            existing_res.score = earned_marks
            existing_res.percentage = pct
            existing_res.is_passed = is_passed
            existing_res.total_correct = total_correct
            existing_res.total_incorrect = total_incorrect
            existing_res.total_unanswered = total_unanswered
            existing_res.calculated_at = now
        else:
            exam_res = ExaminationResult(
                attempt_id=attempt.id,
                quiz_id=quiz.id,
                student_id=attempt.student_id,
                score=earned_marks,
                percentage=pct,
                is_passed=is_passed,
                total_correct=total_correct,
                total_incorrect=total_incorrect,
                total_unanswered=total_unanswered,
                calculated_at=now,
            )
            db.add(exam_res)

        db.commit()

        return StudentSubmitResponse(
            success=True,
            submitted_at=now,
            message="Your examination has been submitted successfully.",
            status="submitted",
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

        quiz = attempt.quiz
        cfg = quiz.configuration
        now = datetime.now(timezone.utc)

        # Check visibility policy
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
        )
