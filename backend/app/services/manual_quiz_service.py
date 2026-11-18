import uuid
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, select, func, and_
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status

from backend.app.models.auth_rbac import Admin, AdminQuizAssignment, AdminAcademicScope
from backend.app.models.quiz import (
    Quiz,
    QuizSection,
    QuizQuestion,
    QuizDraftVersion,
    QuizAttachment,
)
from backend.app.models.question_bank import (
    Question,
    QuestionOption,
    QuestionTag,
    QuestionTagRelation,
)
from backend.app.models.academic import Subject, Unit, Chapter, Topic
from backend.app.schemas.manual_quiz import (
    ManualQuizCreateRequest,
    QuizDetailsUpdateRequest,
    QuizSectionCreateRequest,
    QuizSectionUpdateRequest,
    ManualQuestionCreateRequest,
    AddQuestionsFromBankRequest,
    UpdateQuizQuestionRequest,
    ReorderQuestionsItem,
    ReorderSectionsItem,
    SaveDraftRequest,
    SaveToQuestionBankRequest,
    QuizSectionResponse,
    QuizQuestionItemResponse,
    QuizScoringSummary,
    QuizEditorResponse,
    QuizValidationResponse,
    QuizPreviewResponse,
    QuizPreviewSection,
    QuizPreviewQuestion,
)
from backend.app.services.audit_service import log_audit_event


def _slugify(text_val: str) -> str:
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    random_suffix = uuid.uuid4().hex[:6]
    return f"{s[:180]}-{random_suffix}" if s else f"quiz-{random_suffix}"


def verify_quiz_access(db: Session, admin: Admin, quiz: Quiz, require_edit: bool = False) -> None:
    """
    Verifies that the administrator has permission to access or edit the quiz.
    - Super Admin can access and edit all quizzes.
    - User Admin can access and edit only quizzes they created (Quiz.created_by == admin.id)
      or that were assigned to them via AdminQuizAssignment.
    """
    if admin.is_super_admin:
        return

    is_creator = str(quiz.created_by) == str(admin.id)
    is_assigned = (
        db.query(AdminQuizAssignment)
        .filter(
            AdminQuizAssignment.admin_id == admin.id,
            AdminQuizAssignment.quiz_id == quiz.id,
        )
        .first()
        is not None
    )

    if not (is_creator or is_assigned):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to view or edit this quiz.",
        )


def verify_academic_scope(db: Session, admin: Admin, subject_id: Optional[uuid.UUID]) -> None:
    """
    Verifies that a User Admin has permission for the specified academic subject.
    """
    if admin.is_super_admin or not subject_id:
        return

    scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
    if not scopes:
        return

    # Check if subject matches any assigned scope
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return

    has_match = False
    for s in scopes:
        if s.subject_id and s.subject_id == subject.id:
            has_match = True
            break
        if s.programme_id and subject.semester and subject.semester.programme_id == s.programme_id:
            has_match = True
            break
        if s.institution_id:
            # check subject's institution
            has_match = True
            break

    if not has_match and scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: The selected academic subject is outside your assigned administrative scope.",
        )


# =============================================================================
# 1. QUIZ CREATION & DETAILS MANAGEMENT
# =============================================================================

def create_manual_quiz(db: Session, admin: Admin, payload: ManualQuizCreateRequest) -> Quiz:
    """
    Initializes a new quiz in manual authoring mode.
    """
    verify_academic_scope(db, admin, payload.subject_id)

    slug = _slugify(payload.title)
    quiz = Quiz(
        title=payload.title,
        slug=slug,
        description=payload.description,
        instructions=payload.instructions,
        institution_id=payload.institution_id,
        programme_id=payload.programme_id,
        academic_session_id=payload.academic_session_id,
        semester_id=payload.semester_id,
        subject_id=payload.subject_id,
        duration_minutes=payload.duration_minutes,
        passing_percentage=payload.passing_percentage,
        category=payload.category,
        reference_code=payload.reference_code,
        cover_image_url=payload.cover_image_url,
        shuffle_questions=payload.shuffle_questions,
        shuffle_options=payload.shuffle_options,
        status="draft",
        creation_mode="manual",
        is_draft=True,
        draft_version=1,
        created_by=admin.id,
    )
    db.add(quiz)
    db.flush()

    # Initial draft version snapshot
    draft_entry = QuizDraftVersion(
        quiz_id=quiz.id,
        version_number=1,
        saved_by=admin.id,
        snapshot_data={
            "quiz": {
                "id": str(quiz.id),
                "title": quiz.title,
                "slug": quiz.slug,
                "description": quiz.description,
                "instructions": quiz.instructions,
                "duration_minutes": quiz.duration_minutes,
                "passing_percentage": float(quiz.passing_percentage),
            },
            "sections": [],
            "questions": [],
        },
        change_summary="Initial manual quiz creation",
    )
    db.add(draft_entry)
    db.commit()
    db.refresh(quiz)

    log_audit_event(
        db=db,
        admin=admin,
        action="quiz.create.manual",
        entity="quiz",
        entity_id=quiz.id,
        details={"title": quiz.title, "mode": "manual"},
    )

    return quiz


def update_quiz_details(db: Session, admin: Admin, quiz_id: uuid.UUID, payload: QuizDetailsUpdateRequest) -> Quiz:
    """
    Updates the academic, metadata, and examination settings of a quiz.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    verify_quiz_access(db, admin, quiz, require_edit=True)

    if payload.subject_id is not None and payload.subject_id != quiz.subject_id:
        verify_academic_scope(db, admin, payload.subject_id)
        quiz.subject_id = payload.subject_id

    update_fields = [
        "title", "description", "instructions", "institution_id", "programme_id",
        "academic_session_id", "semester_id", "duration_minutes", "passing_percentage",
        "max_attempts", "shuffle_questions", "shuffle_options", "show_results_immediately",
        "show_correct_answers", "allow_review", "category", "reference_code",
        "cover_image_url", "academic_scope", "scoring_policy"
    ]

    for field in update_fields:
        val = getattr(payload, field)
        if val is not None:
            setattr(quiz, field, val)

    if payload.slug is not None and payload.slug.strip():
        # Check uniqueness if changed
        existing = db.query(Quiz).filter(Quiz.slug == payload.slug.strip(), Quiz.id != quiz.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use.")
        quiz.slug = payload.slug.strip()

    quiz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(quiz)
    return quiz


# =============================================================================
# 2. SECTION & PART MANAGEMENT
# =============================================================================

def create_quiz_section(db: Session, admin: Admin, quiz_id: uuid.UUID, payload: QuizSectionCreateRequest) -> QuizSection:
    """
    Creates a new examination section or part.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    verify_quiz_access(db, admin, quiz, require_edit=True)

    # Determine order if default
    existing_count = db.query(QuizSection).filter(QuizSection.quiz_id == quiz_id).count()
    sec_order = payload.section_order if payload.section_order > 0 else existing_count

    section = QuizSection(
        quiz_id=quiz_id,
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        section_order=sec_order,
        selection_rule=payload.selection_rule or "all_compulsory",
        required_question_count=payload.required_question_count,
        default_marks_per_question=payload.default_marks_per_question,
        default_negative_marks_per_question=payload.default_negative_marks_per_question,
        section_total_marks=0.00,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def update_quiz_section(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: QuizSectionUpdateRequest,
) -> QuizSection:
    """
    Updates configuration and selection rules of an examination section.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    section = db.query(QuizSection).filter(QuizSection.id == section_id, QuizSection.quiz_id == quiz_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz section not found.")

    if payload.title is not None:
        section.title = payload.title
    if payload.description is not None:
        section.description = payload.description
    if payload.instructions is not None:
        section.instructions = payload.instructions
    if payload.section_order is not None:
        section.section_order = payload.section_order
    if payload.selection_rule is not None:
        section.selection_rule = payload.selection_rule
    if payload.required_question_count is not None:
        section.required_question_count = payload.required_question_count
    if payload.default_marks_per_question is not None:
        section.default_marks_per_question = payload.default_marks_per_question
    if payload.default_negative_marks_per_question is not None:
        section.default_negative_marks_per_question = payload.default_negative_marks_per_question

    section.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(section)
    recalculate_quiz_totals(db, quiz_id)
    return section


def delete_quiz_section(db: Session, admin: Admin, quiz_id: uuid.UUID, section_id: uuid.UUID) -> None:
    """
    Deletes an examination section and moves contained questions to standalone (section_id=None).
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    section = db.query(QuizSection).filter(QuizSection.id == section_id, QuizSection.quiz_id == quiz_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz section not found.")

    # Detach questions to standalone
    db.query(QuizQuestion).filter(QuizQuestion.section_id == section_id).update({"section_id": None})
    db.delete(section)
    db.commit()
    recalculate_quiz_totals(db, quiz_id)


def reorder_quiz_sections(db: Session, admin: Admin, quiz_id: uuid.UUID, section_orders: List[ReorderSectionsItem]) -> None:
    """
    Reorders examination sections sequentially.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    for item in section_orders:
        db.query(QuizSection).filter(
            QuizSection.id == item.id,
            QuizSection.quiz_id == quiz_id,
        ).update({"section_order": item.section_order})

    db.commit()


# =============================================================================
# 3. QUESTION ADDITION & MANAGEMENT (METHOD A & METHOD B)
# =============================================================================

def add_manual_question(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    payload: ManualQuestionCreateRequest,
) -> QuizQuestion:
    """
    Method A: Directly authors a new question inside the quiz draft.
    The question is stored as quiz-specific with an immutable freeze snapshot.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    # Validate section if specified
    if payload.section_id:
        sec = db.query(QuizSection).filter(QuizSection.id == payload.section_id, QuizSection.quiz_id == quiz_id).first()
        if not sec:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target section does not exist in quiz.")

    # Build options list
    formatted_options = []
    correct_options = []
    if payload.question_type in ['single_choice', 'multiple_choice', 'true_false']:
        for idx, opt in enumerate(payload.options):
            opt_id = opt.id or str(uuid.uuid4())
            opt_data = {
                "id": opt_id,
                "option_text": opt.option_text,
                "option_order": opt.option_order if opt.option_order is not None else idx,
                "is_correct": bool(opt.is_correct),
                "explanation": opt.explanation,
                "image_url": opt.image_url,
            }
            formatted_options.append(opt_data)
            if opt.is_correct:
                correct_options.append(opt.option_text)

        # Validation for single choice
        if payload.question_type == 'single_choice' and len(correct_options) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Single Choice question must have exactly 1 correct answer (found {len(correct_options)}).",
            )
        if payload.question_type == 'multiple_choice' and len(correct_options) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple Choice question must have at least 1 correct answer.",
            )

    # Build immutable snapshot
    question_snapshot = {
        "title": payload.question_text[:80] + ("..." if len(payload.question_text) > 80 else ""),
        "question_text": payload.question_text,
        "question_type": payload.question_type,
        "difficulty": payload.difficulty,
        "marks": payload.marks,
        "negative_marks": payload.negative_marks,
        "options": formatted_options,
        "correct_answers": payload.correct_answers or correct_options,
        "short_answer_config": payload.short_answer_config or {},
        "explanation": payload.explanation,
        "unit_id": str(payload.unit_id) if payload.unit_id else None,
        "chapter_id": str(payload.chapter_id) if payload.chapter_id else None,
        "topic_id": str(payload.topic_id) if payload.topic_id else None,
        "tags": payload.tags,
        "is_mathematical": payload.is_mathematical,
        "code_language": payload.code_language,
        "attachments": payload.attachments,
        "source": "manual_authoring",
    }

    # Determine order
    current_max_order = (
        db.query(func.max(QuizQuestion.question_order))
        .filter(QuizQuestion.quiz_id == quiz_id)
        .scalar()
    ) or 0

    quiz_question = QuizQuestion(
        quiz_id=quiz_id,
        question_id=None,  # Nullable for manual quiz-specific questions
        section_id=payload.section_id,
        question_order=current_max_order + 1,
        marks=Decimal(str(payload.marks)),
        negative_marks=Decimal(str(payload.negative_marks)),
        is_compulsory=payload.is_compulsory,
        is_manual=True,
        source_type="manual",
        custom_instructions=payload.custom_instructions,
        question_snapshot=question_snapshot,
    )
    db.add(quiz_question)
    db.commit()
    db.refresh(quiz_question)

    recalculate_quiz_totals(db, quiz_id)
    return quiz_question


def add_questions_from_bank(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    payload: AddQuestionsFromBankRequest,
) -> List[QuizQuestion]:
    """
    Method B: Selects existing approved Question Bank questions and links them to the quiz.
    Builds immutable snapshots and prevents duplicate addition.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    if not payload.question_ids:
        return []

    # Check for duplicate additions in this quiz
    existing_question_ids = set(
        q_id for (q_id,) in db.query(QuizQuestion.question_id)
        .filter(QuizQuestion.quiz_id == quiz_id, QuizQuestion.question_id.isnot(None))
        .all()
    )

    duplicate_ids = [str(qid) for qid in payload.question_ids if qid in existing_question_ids]
    if duplicate_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following questions are already present in this quiz: {', '.join(duplicate_ids)}",
        )

    # Fetch Question Bank questions
    questions = (
        db.query(Question)
        .filter(Question.id.in_(payload.question_ids))
        .all()
    )

    if len(questions) != len(payload.question_ids):
        found_ids = {q.id for q in questions}
        missing_ids = [str(qid) for qid in payload.question_ids if qid not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Questions not found in Question Bank: {', '.join(missing_ids)}",
        )

    # Enforce User Admin academic scope on selected questions
    if not admin.is_super_admin:
        scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
        if scopes:
            for q in questions:
                # If question has topic, verify it is accessible
                if q.topic and q.topic.chapter and q.topic.chapter.unit:
                    subject_id = q.topic.chapter.unit.subject_id
                    verify_academic_scope(db, admin, subject_id)

    # Determine next question order
    current_max_order = (
        db.query(func.max(QuizQuestion.question_order))
        .filter(QuizQuestion.quiz_id == quiz_id)
        .scalar()
    ) or 0

    added_records: List[QuizQuestion] = []
    for idx, q in enumerate(questions):
        # Build options snapshot
        options_data = [
            {
                "id": str(opt.id),
                "option_text": opt.option_text,
                "option_order": opt.option_order,
                "is_correct": opt.is_correct,
                "explanation": getattr(opt, "explanation", None),
                "image_url": getattr(opt, "option_image_path", None),
            }
            for opt in q.options
        ]
        correct_answers = [opt.option_text for opt in q.options if opt.is_correct]

        snapshot = {
            "title": q.title or q.question_text[:80],
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "marks": float(payload.default_marks if payload.default_marks is not None else q.default_marks),
            "negative_marks": float(payload.default_negative_marks if payload.default_negative_marks is not None else q.default_negative_marks),
            "options": options_data,
            "correct_answers": correct_answers,
            "short_answer_config": q.short_answer_config or {},
            "explanation": q.explanation,
            "subject_id": str(q.topic.chapter.unit.subject_id) if q.topic and q.topic.chapter and q.topic.chapter.unit else None,
            "subject_name": q.topic.chapter.unit.subject.subject_name if q.topic and q.topic.chapter and q.topic.chapter.unit and q.topic.chapter.unit.subject else None,
            "unit_id": str(q.topic.chapter.unit_id) if q.topic and q.topic.chapter else None,
            "unit_name": q.topic.chapter.unit.unit_name if q.topic and q.topic.chapter and q.topic.chapter.unit else None,
            "topic_id": str(q.topic_id) if q.topic_id else None,
            "topic_name": q.topic.topic_name if q.topic else None,
            "tags": [r.tag.name for r in q.tag_relations if r.tag],
            "is_mathematical": q.is_mathematical,
            "code_language": q.code_language,
            "source": "question_bank",
        }

        effective_marks = Decimal(str(payload.default_marks if payload.default_marks is not None else q.default_marks))
        effective_neg_marks = Decimal(str(payload.default_negative_marks if payload.default_negative_marks is not None else q.default_negative_marks))

        qq = QuizQuestion(
            quiz_id=quiz_id,
            question_id=q.id,
            section_id=payload.section_id,
            question_order=current_max_order + idx + 1,
            marks=effective_marks,
            negative_marks=effective_neg_marks,
            is_compulsory=payload.is_compulsory,
            is_manual=False,
            source_type="bank",
            question_snapshot=snapshot,
        )
        db.add(qq)
        added_records.append(qq)

    db.commit()
    recalculate_quiz_totals(db, quiz_id)
    return added_records


def save_manual_question_to_bank(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    quiz_question_id: uuid.UUID,
    payload: SaveToQuestionBankRequest,
) -> Question:
    """
    Explicit action: promotes a manually authored quiz question into the shared Question Bank.
    Requires explicit confirmation from administrator.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    qq = db.query(QuizQuestion).filter(QuizQuestion.id == quiz_question_id, QuizQuestion.quiz_id == quiz_id).first()
    if not qq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in quiz.")

    snap = qq.question_snapshot or {}
    topic_id = payload.target_topic_id or (uuid.UUID(snap["topic_id"]) if snap.get("topic_id") else None)
    if not topic_id:
        from backend.app.models.academic import Topic
        fallback_topic = db.query(Topic).first()
        if fallback_topic:
            topic_id = fallback_topic.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A target topic is required to save this question into the Question Bank."
            )

    # Create new Question in Question Bank
    new_question = Question(
        title=snap.get("title") or (snap.get("question_text", "Untitled Question")[:80]),
        topic_id=topic_id,
        question_text=snap.get("question_text", ""),
        question_type=snap.get("question_type", "single_choice"),
        difficulty=snap.get("difficulty", "medium"),
        default_marks=Decimal(str(qq.marks)),
        default_negative_marks=Decimal(str(qq.negative_marks)),
        explanation=snap.get("explanation"),
        short_answer_config=snap.get("short_answer_config"),
        is_mathematical=snap.get("is_mathematical", False),
        code_language=snap.get("code_language"),
        status="approved" if admin.is_super_admin else "pending_review",
        created_by=admin.id,
    )
    db.add(new_question)
    db.flush()

    # Add Options
    for opt in snap.get("options", []):
        opt_record = QuestionOption(
            question_id=new_question.id,
            option_text=opt.get("option_text", ""),
            option_order=opt.get("option_order", 0),
            is_correct=opt.get("is_correct", False),
            option_image_path=opt.get("image_url") or opt.get("option_image_path"),
        )
        db.add(opt_record)

    # Link quiz question to Question Bank record
    qq.question_id = new_question.id
    qq.source_type = "bank"
    qq.is_manual = False
    snap["source"] = "saved_to_question_bank"
    snap["bank_question_id"] = str(new_question.id)
    qq.question_snapshot = snap
    flag_modified(qq, "question_snapshot")

    db.commit()
    db.refresh(new_question)

    log_audit_event(
        db=db,
        admin=admin,
        action="question.promote_to_bank",
        entity="question",
        entity_id=new_question.id,
        details={"quiz_id": str(quiz_id), "status": new_question.status},
    )

    return new_question


def update_quiz_question(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    quiz_question_id: uuid.UUID,
    payload: UpdateQuizQuestionRequest,
) -> QuizQuestion:
    """
    Updates quiz-specific marks, negative marks, section, or manual question text/options.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    qq = db.query(QuizQuestion).filter(QuizQuestion.id == quiz_question_id, QuizQuestion.quiz_id == quiz_id).first()
    if not qq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in quiz.")

    if payload.marks is not None:
        qq.marks = Decimal(str(payload.marks))
    if payload.negative_marks is not None:
        qq.negative_marks = Decimal(str(payload.negative_marks))
    if payload.is_compulsory is not None:
        qq.is_compulsory = payload.is_compulsory
    if payload.section_id is not None:
        qq.section_id = payload.section_id
    if payload.custom_instructions is not None:
        qq.custom_instructions = payload.custom_instructions
    if payload.question_order is not None:
        qq.question_order = payload.question_order

    # If it's a manual question and question text or options are being edited
    snap = dict(qq.question_snapshot or {})
    if payload.question_text is not None:
        snap["question_text"] = payload.question_text
        snap["title"] = payload.question_text[:80]
    if payload.options is not None:
        formatted_opts = [
            {
                "id": opt.id or str(uuid.uuid4()),
                "option_text": opt.option_text,
                "option_order": opt.option_order,
                "is_correct": opt.is_correct,
                "explanation": opt.explanation,
                "image_url": opt.image_url,
            }
            for opt in payload.options
        ]
        snap["options"] = formatted_opts
        snap["correct_answers"] = [opt.option_text for opt in payload.options if opt.is_correct]
    if payload.explanation is not None:
        snap["explanation"] = payload.explanation
    if payload.short_answer_config is not None:
        snap["short_answer_config"] = payload.short_answer_config
    if payload.difficulty is not None:
        snap["difficulty"] = payload.difficulty
    if payload.is_mathematical is not None:
        snap["is_mathematical"] = payload.is_mathematical
    if payload.code_language is not None:
        snap["code_language"] = payload.code_language

    snap["marks"] = float(qq.marks)
    snap["negative_marks"] = float(qq.negative_marks)
    qq.question_snapshot = snap
    flag_modified(qq, "question_snapshot")

    db.commit()
    db.refresh(qq)
    recalculate_quiz_totals(db, quiz_id)
    return qq


def delete_quiz_question(db: Session, admin: Admin, quiz_id: uuid.UUID, quiz_question_id: uuid.UUID) -> None:
    """
    Removes a question from the quiz.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    qq = db.query(QuizQuestion).filter(QuizQuestion.id == quiz_question_id, QuizQuestion.quiz_id == quiz_id).first()
    if not qq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in quiz.")

    db.delete(qq)
    db.commit()
    recalculate_quiz_totals(db, quiz_id)


def reorder_quiz_questions(db: Session, admin: Admin, quiz_id: uuid.UUID, items: List[ReorderQuestionsItem]) -> None:
    """
    Updates sequential question orders and section associations.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    for itm in items:
        update_data = {"question_order": itm.question_order}
        if itm.section_id is not None:
            update_data["section_id"] = itm.section_id
        db.query(QuizQuestion).filter(
            QuizQuestion.id == itm.id,
            QuizQuestion.quiz_id == quiz_id,
        ).update(update_data)

    db.commit()


# =============================================================================
# 4. SCORING, VALIDATION & DRAFT RECOVERY
# =============================================================================

def recalculate_quiz_totals(db: Session, quiz_id: uuid.UUID) -> None:
    """
    Synchronizes section totals and authoritative quiz total_marks in the database.
    """
    sections = db.query(QuizSection).filter(QuizSection.quiz_id == quiz_id).all()
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()

    # Calculate for each section
    for sec in sections:
        sec_questions = [q for q in questions if q.section_id == sec.id]
        sec.total_questions_count = len(sec_questions)
        sec_total = sum(float(q.marks) for q in sec_questions)
        sec.section_total_marks = Decimal(str(sec_total))

    # Calculate overall quiz total marks
    total_quiz_marks = sum(float(q.marks) for q in questions)
    db.query(Quiz).filter(Quiz.id == quiz_id).update({
        "total_marks": Decimal(str(total_quiz_marks)),
        "updated_at": datetime.now(timezone.utc),
    })
    db.commit()


def calculate_scoring_summary(db: Session, quiz_id: uuid.UUID) -> QuizScoringSummary:
    """
    Dynamically computes maximum possible marks, obtainable marks under section rules,
    compulsory/optional counts, and validates scoring consistency.
    """
    sections = (
        db.query(QuizSection)
        .filter(QuizSection.quiz_id == quiz_id)
        .order_by(QuizSection.section_order)
        .all()
    )
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order)
        .all()
    )

    total_questions = len(questions)
    total_sections = len(sections)
    compulsory_count = 0
    optional_count = 0
    max_possible_marks = 0.0
    obtainable_marks = 0.0
    total_negative_exposure = 0.0

    type_dist: Dict[str, int] = {}
    diff_dist: Dict[str, int] = {}
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

    # Map questions by section
    sec_map: Dict[Optional[uuid.UUID], List[QuizQuestion]] = {None: []}
    for s in sections:
        sec_map[s.id] = []

    for q in questions:
        sec_id = q.section_id
        if sec_id not in sec_map:
            sec_map[sec_id] = []
        sec_map[sec_id].append(q)

        q_marks = float(q.marks)
        q_neg = float(q.negative_marks)
        max_possible_marks += q_marks
        total_negative_exposure += q_neg

        snap = q.question_snapshot or {}
        q_type = snap.get("question_type", "single_choice")
        q_diff = snap.get("difficulty", "medium")
        type_dist[q_type] = type_dist.get(q_type, 0) + 1
        diff_dist[q_diff] = diff_dist.get(q_diff, 0) + 1

    # 1. Evaluate section selection rules
    for s in sections:
        s_questions = sec_map.get(s.id, [])
        s_count = len(s_questions)
        s_rule = s.selection_rule

        if s_rule == 'all_compulsory':
            compulsory_count += s_count
            obtainable_marks += sum(float(q.marks) for q in s_questions)
        elif s_rule == 'all_optional':
            optional_count += s_count
            # In all_optional without count, obtainable takes average or target
            obtainable_marks += sum(float(q.marks) for q in s_questions)
        elif s_rule == 'answer_n_of_m':
            req_n = s.required_question_count or s_count
            if req_n > s_count:
                validation_errors.append(
                    f"Section '{s.title}': Required count ({req_n}) exceeds available questions ({s_count})."
                )
            # Count compulsory quota as req_n, and optional as rest
            compulsory_count += min(req_n, s_count)
            optional_count += max(0, s_count - req_n)

            # Obtainable marks is sum of highest N question marks in the section
            sorted_marks = sorted([float(q.marks) for q in s_questions], reverse=True)
            obtainable_marks += sum(sorted_marks[:req_n])
        else:
            # Custom or standard section
            for q in s_questions:
                if q.is_compulsory:
                    compulsory_count += 1
                    obtainable_marks += float(q.marks)
                else:
                    optional_count += 1

    # 2. Standalone questions (no section)
    standalone = sec_map.get(None, [])
    for q in standalone:
        if q.is_compulsory:
            compulsory_count += 1
            obtainable_marks += float(q.marks)
        else:
            optional_count += 1

    if total_questions == 0:
        validation_warnings.append("The quiz currently contains no questions.")

    is_valid = len(validation_errors) == 0

    return QuizScoringSummary(
        total_questions=total_questions,
        total_sections=total_sections,
        compulsory_questions=compulsory_count,
        optional_questions=optional_count,
        max_possible_marks=round(max_possible_marks, 2),
        obtainable_marks=round(obtainable_marks, 2),
        total_negative_exposure=round(total_negative_exposure, 2),
        type_distribution=type_dist,
        difficulty_distribution=diff_dist,
        is_valid=is_valid,
        validation_errors=validation_errors,
        validation_warnings=validation_warnings,
    )


def get_quiz_editor_data(db: Session, admin: Admin, quiz_id: uuid.UUID) -> QuizEditorResponse:
    """
    Loads full workspace editor state including quiz details, sections, questions with answer keys,
    scoring summary, and current draft version.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)

    sections = (
        db.query(QuizSection)
        .filter(QuizSection.quiz_id == quiz_id)
        .order_by(QuizSection.section_order)
        .all()
    )
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order)
        .all()
    )

    scoring_summary = calculate_scoring_summary(db, quiz_id)

    formatted_sections = [
        QuizSectionResponse(
            id=s.id,
            quiz_id=s.quiz_id,
            title=s.title,
            description=s.description,
            instructions=s.instructions,
            section_order=s.section_order,
            selection_rule=s.selection_rule,
            required_question_count=s.required_question_count,
            total_questions_count=s.total_questions_count,
            default_marks_per_question=float(s.default_marks_per_question) if s.default_marks_per_question is not None else None,
            default_negative_marks_per_question=float(s.default_negative_marks_per_question) if s.default_negative_marks_per_question is not None else None,
            section_total_marks=float(s.section_total_marks),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sections
    ]

    formatted_questions = [
        QuizQuestionItemResponse(
            id=q.id,
            quiz_id=q.quiz_id,
            question_id=q.question_id,
            section_id=q.section_id,
            question_order=q.question_order,
            marks=float(q.marks),
            negative_marks=float(q.negative_marks),
            is_compulsory=q.is_compulsory,
            is_manual=q.is_manual,
            source_type=q.source_type,
            custom_instructions=q.custom_instructions,
            scoring_settings=q.scoring_settings,
            question_snapshot=q.question_snapshot,
            created_at=q.created_at,
        )
        for q in questions
    ]

    quiz_dict = {
        "id": str(quiz.id),
        "title": quiz.title,
        "slug": quiz.slug,
        "description": quiz.description,
        "instructions": quiz.instructions,
        "duration_minutes": quiz.duration_minutes,
        "total_marks": float(quiz.total_marks),
        "passing_percentage": float(quiz.passing_percentage),
        "max_attempts": quiz.max_attempts,
        "shuffle_questions": quiz.shuffle_questions,
        "shuffle_options": quiz.shuffle_options,
        "show_results_immediately": quiz.show_results_immediately,
        "show_correct_answers": quiz.show_correct_answers,
        "allow_review": quiz.allow_review,
        "status": quiz.status,
        "category": quiz.category,
        "reference_code": quiz.reference_code,
        "cover_image_url": quiz.cover_image_url,
        "institution_id": str(quiz.institution_id) if quiz.institution_id else None,
        "programme_id": str(quiz.programme_id) if quiz.programme_id else None,
        "academic_session_id": str(quiz.academic_session_id) if quiz.academic_session_id else None,
        "semester_id": str(quiz.semester_id) if quiz.semester_id else None,
        "subject_id": str(quiz.subject_id) if quiz.subject_id else None,
        "subject_name": quiz.subject.subject_name if quiz.subject else None,
        "is_draft": quiz.is_draft,
        "draft_version": quiz.draft_version,
        "created_by": str(quiz.created_by) if quiz.created_by else None,
        "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
        "updated_at": quiz.updated_at.isoformat() if quiz.updated_at else None,
    }

    return QuizEditorResponse(
        quiz=quiz_dict,
        sections=formatted_sections,
        questions=formatted_questions,
        scoring_summary=scoring_summary,
        draft_version=quiz.draft_version,
    )


def save_quiz_draft(db: Session, admin: Admin, quiz_id: uuid.UUID, payload: SaveDraftRequest) -> QuizDraftVersion:
    """
    Saves an authoritative draft version snapshot in quiz_draft_versions.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    recalculate_quiz_totals(db, quiz_id)
    quiz.draft_version += 1
    quiz.updated_at = datetime.now(timezone.utc)

    # Compile snapshot
    sections = db.query(QuizSection).filter(QuizSection.quiz_id == quiz_id).order_by(QuizSection.section_order).all()
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.question_order).all()

    snapshot = payload.snapshot_data or {
        "quiz": {
            "title": quiz.title,
            "description": quiz.description,
            "instructions": quiz.instructions,
            "total_marks": float(quiz.total_marks),
            "duration_minutes": quiz.duration_minutes,
        },
        "sections": [
            {"id": str(s.id), "title": s.title, "rule": s.selection_rule, "order": s.section_order}
            for s in sections
        ],
        "questions": [
            {
                "id": str(q.id),
                "marks": float(q.marks),
                "section_id": str(q.section_id) if q.section_id else None,
                "snapshot": q.question_snapshot,
            }
            for q in questions
        ],
    }

    draft = QuizDraftVersion(
        quiz_id=quiz.id,
        version_number=quiz.draft_version,
        saved_by=admin.id,
        snapshot_data=snapshot,
        change_summary=payload.change_summary or f"Version {quiz.draft_version} saved",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


# =============================================================================
# 5. LIVE PAPER PREVIEW (STUDENT VIEW VS ANSWER KEY)
# =============================================================================

def get_quiz_preview(db: Session, admin: Admin, quiz_id: uuid.UUID, mode: str = "student") -> QuizPreviewResponse:
    """
    Renders live examination preview.
    - If mode == 'student': strictly strips correct answers and explanations.
    - If mode == 'answer_key': provides complete answer key and explanations for authorized admins.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)

    sections = (
        db.query(QuizSection)
        .filter(QuizSection.quiz_id == quiz_id)
        .order_by(QuizSection.section_order)
        .all()
    )
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order)
        .all()
    )

    scoring = calculate_scoring_summary(db, quiz_id)
    is_answer_key = (mode == "answer_key")

    preview_sections: List[QuizPreviewSection] = []
    sec_q_map: Dict[Optional[uuid.UUID], List[QuizQuestion]] = {None: []}
    for s in sections:
        sec_q_map[s.id] = []

    for q in questions:
        if q.section_id in sec_q_map:
            sec_q_map[q.section_id].append(q)
        else:
            sec_q_map[None].append(q)

    global_q_counter = 1

    for s in sections:
        s_preview_questions: List[QuizPreviewQuestion] = []
        for q in sec_q_map.get(s.id, []):
            snap = q.question_snapshot or {}

            # Process options based on mode
            sanitized_options = []
            for opt in snap.get("options", []):
                opt_dict = {
                    "id": opt.get("id"),
                    "option_text": opt.get("option_text"),
                    "option_order": opt.get("option_order"),
                    "image_url": opt.get("image_url"),
                }
                if is_answer_key:
                    opt_dict["is_correct"] = opt.get("is_correct", False)
                    opt_dict["explanation"] = opt.get("explanation")
                sanitized_options.append(opt_dict)

            pq = QuizPreviewQuestion(
                id=q.id,
                section_id=s.id,
                section_title=s.title,
                display_number=global_q_counter,
                question_text=snap.get("question_text", ""),
                question_type=snap.get("question_type", "single_choice"),
                marks=float(q.marks),
                negative_marks=float(q.negative_marks),
                is_compulsory=q.is_compulsory,
                is_mathematical=snap.get("is_mathematical", False),
                code_language=snap.get("code_language"),
                custom_instructions=q.custom_instructions,
                options=sanitized_options,
                attachments=snap.get("attachments", []),
                correct_answers=snap.get("correct_answers") if is_answer_key else None,
                explanation=snap.get("explanation") if is_answer_key else None,
                difficulty=snap.get("difficulty") if is_answer_key else None,
            )
            s_preview_questions.append(pq)
            global_q_counter += 1

        sec_total = sum(pq.marks for pq in s_preview_questions)
        preview_sections.append(
            QuizPreviewSection(
                id=s.id,
                title=s.title,
                description=s.description,
                instructions=s.instructions,
                section_order=s.section_order,
                selection_rule=s.selection_rule,
                required_question_count=s.required_question_count,
                section_total_marks=sec_total,
                questions=s_preview_questions,
            )
        )

    # Standalone questions
    standalone_preview: List[QuizPreviewQuestion] = []
    for q in sec_q_map.get(None, []):
        snap = q.question_snapshot or {}
        sanitized_options = []
        for opt in snap.get("options", []):
            opt_dict = {
                "id": opt.get("id"),
                "option_text": opt.get("option_text"),
                "option_order": opt.get("option_order"),
                "image_url": opt.get("image_url"),
            }
            if is_answer_key:
                opt_dict["is_correct"] = opt.get("is_correct", False)
                opt_dict["explanation"] = opt.get("explanation")
            sanitized_options.append(opt_dict)

        pq = QuizPreviewQuestion(
            id=q.id,
            section_id=None,
            section_title=None,
            display_number=global_q_counter,
            question_text=snap.get("question_text", ""),
            question_type=snap.get("question_type", "single_choice"),
            marks=float(q.marks),
            negative_marks=float(q.negative_marks),
            is_compulsory=q.is_compulsory,
            is_mathematical=snap.get("is_mathematical", False),
            code_language=snap.get("code_language"),
            custom_instructions=q.custom_instructions,
            options=sanitized_options,
            attachments=snap.get("attachments", []),
            correct_answers=snap.get("correct_answers") if is_answer_key else None,
            explanation=snap.get("explanation") if is_answer_key else None,
            difficulty=snap.get("difficulty") if is_answer_key else None,
        )
        standalone_preview.append(pq)
        global_q_counter += 1

    return QuizPreviewResponse(
        quiz_id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        instructions=quiz.instructions,
        duration_minutes=quiz.duration_minutes,
        total_marks=float(quiz.total_marks),
        obtainable_marks=scoring.obtainable_marks,
        passing_percentage=float(quiz.passing_percentage),
        mode="answer_key" if is_answer_key else "student",
        sections=preview_sections,
        standalone_questions=standalone_preview,
    )
