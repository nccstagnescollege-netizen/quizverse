import uuid
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, Permission
from backend.app.models.academic import Subject, Unit, Chapter, Topic, Institution, Programme, Semester, AcademicSession
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.quiz import Quiz, QuizQuestion, GenerationHistory
from backend.app.schemas.quiz_generator import (
    AcademicScopeRequest,
    DifficultyConfig,
    MarksConfig,
    NegativeMarkingConfig,
    UnitDistributionConfig,
    ExamSettingsRequest,
    PreflightCheckRequest,
    PreflightCheckResponse,
    GeneratePaperRequest,
    SelectedQuestionItem,
    SelectedQuestionOption,
    GenerationSessionResponse,
    ReplaceQuestionRequest,
    ReplacementCandidateItem,
    SaveAsDraftResponse,
)
from backend.app.services.rbac_service import has_permission, check_academic_scope, get_admin_effective_permissions


def slugify(text: str) -> str:
    """Generate URL-safe slug from title."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", text)
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def calculate_quotas_largest_remainder(total: int, percentages: Dict[str, Decimal]) -> Dict[str, int]:
    """
    Applies the Largest Remainder Method (Hamilton-Hare method) to convert percentage quotas
    into exact integer quotas that strictly sum to the requested total question count.
    """
    if total <= 0:
        return {k: 0 for k in percentages}

    exact_quotas: Dict[str, Decimal] = {}
    integer_quotas: Dict[str, int] = {}
    remainders: Dict[str, Decimal] = {}

    for cat, pct in percentages.items():
        exact = Decimal(total) * (pct / Decimal("100.00"))
        exact_quotas[cat] = exact
        int_part = int(exact)
        integer_quotas[cat] = int_part
        remainders[cat] = exact - Decimal(int_part)

    allocated = sum(integer_quotas.values())
    shortfall = total - allocated

    if shortfall > 0:
        # Sort categories by remainder descending; break ties by category name for determinism
        sorted_by_remainder = sorted(remainders.items(), key=lambda x: (x[1], x[0]), reverse=True)
        for i in range(shortfall):
            cat_to_increment = sorted_by_remainder[i % len(sorted_by_remainder)][0]
            integer_quotas[cat_to_increment] += 1

    return integer_quotas


def get_academic_cascading_options(db: Session, admin: Admin) -> Dict[str, Any]:
    """
    Fetch cascading academic options (Institutions, Programmes, Sessions, Semesters, Subjects, Units)
    honoring the administrator's assigned academic scopes.
    """
    # 1. Institutions
    inst_query = db.query(Institution).filter(Institution.status == "active")
    institutions = inst_query.order_by(Institution.name).all()

    # 2. Programmes
    prog_query = db.query(Programme).filter(Programme.status == "active")
    programmes = prog_query.order_by(Programme.name).all()

    # 3. Academic Sessions
    sess_query = db.query(AcademicSession).filter(AcademicSession.status == "active")
    sessions = sess_query.order_by(AcademicSession.session_name.desc()).all()

    # 4. Semesters
    sem_query = db.query(Semester).filter(Semester.status == "active")
    semesters = sem_query.order_by(Semester.semester_number).all()

    # 5. Subjects
    subj_query = db.query(Subject).filter(Subject.status == "active")
    all_subjects = subj_query.order_by(Subject.subject_name).all()

    # Filter subjects by admin academic scope if not super admin
    allowed_subjects = []
    for s in all_subjects:
        if admin.is_super_admin or check_academic_scope(db, admin, subject_id=s.id, institution_id=s.institution_id):
            allowed_subjects.append(s)

    # 6. Units for allowed subjects
    allowed_subj_ids = {s.id for s in allowed_subjects}
    units = (
        db.query(Unit)
        .filter(Unit.subject_id.in_(allowed_subj_ids), Unit.status == "active")
        .order_by(Unit.unit_number)
        .all()
    ) if allowed_subj_ids else []

    return {
        "institutions": [{"id": str(i.id), "name": i.name, "code": i.code} for i in institutions],
        "programmes": [{"id": str(p.id), "name": p.name, "code": p.code, "institution_id": str(p.institution_id)} for p in programmes],
        "academic_sessions": [{"id": str(s.id), "session_name": s.session_name, "institution_id": str(s.institution_id) if s.institution_id else None} for s in sessions],
        "semesters": [{"id": str(sem.id), "semester_name": sem.semester_name, "semester_number": sem.semester_number, "programme_id": str(sem.programme_id)} for sem in semesters],
        "subjects": [{"id": str(sub.id), "subject_name": sub.subject_name, "subject_code": sub.subject_code, "institution_id": str(sub.institution_id) if sub.institution_id else None} for sub in allowed_subjects],
        "units": [{"id": str(u.id), "unit_name": u.unit_name, "unit_number": u.unit_number, "subject_id": str(u.subject_id)} for u in units],
    }


def get_subject_syllabus_hierarchy(db: Session, admin: Admin, subject_id: uuid.UUID) -> Dict[str, Any]:
    """
    Load the hierarchical tree (Units -> Chapters -> Topics) for a given subject.
    Validates that the administrator is authorized to access the subject.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subject '{subject_id}' not found.")

    if not admin.is_super_admin and not check_academic_scope(db, admin, subject_id=subject.id, institution_id=subject.institution_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Subject is outside your academic scope.")

    units = db.query(Unit).filter(Unit.subject_id == subject.id, Unit.status == "active").order_by(Unit.unit_number).all()

    tree = []
    for u in units:
        chapters = db.query(Chapter).filter(Chapter.unit_id == u.id, Chapter.status == "active").order_by(Chapter.chapter_number).all()
        chapter_nodes = []
        for ch in chapters:
            topics = db.query(Topic).filter(Topic.chapter_id == ch.id, Topic.status == "active").order_by(Topic.display_order).all()
            topic_nodes = [
                {
                    "id": str(t.id),
                    "name": t.topic_name,
                    "code": t.topic_code,
                    "questions_count": db.query(func.count(Question.id)).filter(Question.topic_id == t.id, Question.status == "approved").scalar() or 0,
                }
                for t in topics
            ]
            chapter_nodes.append({
                "id": str(ch.id),
                "name": ch.chapter_name,
                "code": ch.chapter_code,
                "topics": topic_nodes,
            })
        tree.append({
            "id": str(u.id),
            "name": u.unit_name,
            "unit_number": u.unit_number,
            "chapters": chapter_nodes,
        })

    return {
        "subject_id": str(subject.id),
        "subject_name": subject.subject_name,
        "subject_code": subject.subject_code,
        "units": tree,
    }


def _build_eligible_questions_query(
    db: Session,
    admin: Admin,
    academic_scope: AcademicScopeRequest,
    question_types: List[str],
    reuse_policy: str = "allow_all",
):
    """
    Builds the base SQLAlchemy query selecting eligible approved questions from the actual Question Bank.
    Enforces RBAC academic scope, syllabus selections, and reuse policies.
    """
    # Verify Subject Access
    subject = db.query(Subject).filter(Subject.id == academic_scope.subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subject '{academic_scope.subject_id}' not found.")

    if not admin.is_super_admin and not check_academic_scope(db, admin, subject_id=subject.id, institution_id=subject.institution_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Subject is outside your academic scope.")

    query = db.query(Question).filter(
        Question.subject_id == subject.id,
        Question.status == "approved",
    )

    # Syllabus Selection: Units -> Chapters -> Topics
    if academic_scope.selected_topic_ids:
        query = query.filter(Question.topic_id.in_(academic_scope.selected_topic_ids))
    elif academic_scope.selected_chapter_ids:
        query = query.filter(Question.chapter_id.in_(academic_scope.selected_chapter_ids))
    elif academic_scope.selected_unit_ids:
        query = query.filter(Question.unit_id.in_(academic_scope.selected_unit_ids))

    # Question types
    if question_types:
        query = query.filter(Question.question_type.in_(question_types))

    # Question reuse policy
    if reuse_policy == "unused_only":
        used_ids_subquery = db.query(QuizQuestion.question_id).distinct()
        query = query.filter(~Question.id.in_(used_ids_subquery))

    return query


def preflight_availability_check(
    db: Session,
    admin: Admin,
    req: PreflightCheckRequest,
) -> PreflightCheckResponse:
    """
    Performs a pre-generation availability check.
    Calculates difficulty and unit quotas, queries the real Question Bank, and detects shortfalls.
    """
    # 1. Calculate difficulty quotas using Largest Remainder Method
    diff_percentages = {
        "easy": req.difficulty.easy_pct,
        "medium": req.difficulty.medium_pct,
        "hard": req.difficulty.hard_pct,
    }
    diff_quotas = calculate_quotas_largest_remainder(req.total_questions, diff_percentages)

    # 2. Base query
    base_query = _build_eligible_questions_query(
        db, admin, req.academic_scope, req.question_types, req.reuse_policy
    )
    eligible_questions: List[Question] = base_query.all()
    available_total = len(eligible_questions)

    # 3. Availability by difficulty
    diff_available = {"easy": 0, "medium": 0, "hard": 0}
    type_available: Dict[str, int] = {t: 0 for t in req.question_types}
    unit_available: Dict[str, int] = {}

    for q in eligible_questions:
        d = q.difficulty.lower()
        if d in diff_available:
            diff_available[d] += 1
        t = q.question_type
        if t in type_available:
            type_available[t] += 1
        u_key = str(q.unit_id) if q.unit_id else "unknown_unit"
        unit_available[u_key] = unit_available.get(u_key, 0) + 1

    # 4. Shortfall detection
    shortfalls = []
    suggestions = []

    # Total questions check
    if available_total < req.total_questions:
        missing = req.total_questions - available_total
        shortfalls.append({
            "category": "Total Questions",
            "requested": req.total_questions,
            "available": available_total,
            "missing": missing,
            "reason": f"Question bank has only {available_total} eligible questions matching syllabus criteria.",
        })
        suggestions.append(f"Reduce requested question count from {req.total_questions} to {available_total} or lower.")
        suggestions.append("Expand the syllabus selection to include more units, chapters, or topics.")

    # Difficulty quotas check
    for d, requested_count in diff_quotas.items():
        avail = diff_available.get(d, 0)
        if avail < requested_count:
            shortfalls.append({
                "category": f"Difficulty: {d.capitalize()}",
                "requested": requested_count,
                "available": avail,
                "missing": requested_count - avail,
                "reason": f"Only {avail} {d} questions are available in the selected syllabus scope.",
            })

    if shortfalls:
        suggestions.append("Adjust difficulty percentage distribution to align with available question bank inventory.")
        suggestions.append("Add more approved questions into the Question Bank for this subject.")

    is_valid = len(shortfalls) == 0

    return PreflightCheckResponse(
        is_valid=is_valid,
        requested_total=req.total_questions,
        available_total=available_total,
        difficulty_quotas=diff_quotas,
        difficulty_available=diff_available,
        type_quotas={},
        type_available=type_available,
        unit_quotas={},
        unit_available=unit_available,
        shortfalls=shortfalls,
        suggestions=suggestions,
        message="All question requirements can be fulfilled." if is_valid else f"Shortage detected: {len(shortfalls)} requirement(s) cannot be satisfied.",
    )


def generate_question_paper(
    db: Session,
    admin: Admin,
    req: GeneratePaperRequest,
) -> GenerationSessionResponse:
    """
    Constraint-aware, deterministic, server-side automatic examination paper generator.
    Selects actual Question Bank questions meeting all difficulty, syllabus, marks, and negative marking constraints.
    Creates immutable question snapshots.
    """
    # 1. Enforce Generator Permissions
    if not admin.is_super_admin:
        effective_perms = get_admin_effective_permissions(db, admin)
        if not ("quiz.generate" in effective_perms or "quiz.create" in effective_perms or "*" in effective_perms):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Missing 'quiz.generate' or 'quiz.create' permission.")

    # 2. Availability & Quota Preflight
    preflight = preflight_availability_check(
        db, admin,
        PreflightCheckRequest(
            academic_scope=req.academic_scope,
            total_questions=req.total_questions,
            difficulty=req.difficulty,
            question_types=req.question_types,
            unit_distribution=req.unit_distribution,
            reuse_policy=req.reuse_policy,
        ),
    )

    if not preflight.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INSUFFICIENT_QUESTIONS",
                "message": "Question bank has insufficient questions to fulfill the requested generation quotas.",
                "shortfalls": preflight.shortfalls,
                "suggestions": preflight.suggestions,
            },
        )

    # 3. Seeded RNG for reproducible generation
    seed_str = req.seed or str(uuid.uuid4())
    rng = random.Random(seed_str)

    # 4. Fetch all eligible questions
    base_query = _build_eligible_questions_query(
        db, admin, req.academic_scope, req.question_types, req.reuse_policy
    )
    eligible_questions: List[Question] = base_query.all()

    # 5. Bucket questions by difficulty
    bucket_easy = [q for q in eligible_questions if q.difficulty.lower() == "easy"]
    bucket_medium = [q for q in eligible_questions if q.difficulty.lower() == "medium"]
    bucket_hard = [q for q in eligible_questions if q.difficulty.lower() == "hard"]

    # 6. Sample according to Largest Remainder quotas
    quotas = preflight.difficulty_quotas
    selected_easy = rng.sample(bucket_easy, quotas["easy"])
    selected_medium = rng.sample(bucket_medium, quotas["medium"])
    selected_hard = rng.sample(bucket_hard, quotas["hard"])

    selected_pool = selected_easy + selected_medium + selected_hard

    # Shuffle selected questions deterministically if requested
    if req.exam_settings.shuffle_questions:
        rng.shuffle(selected_pool)

    # 7. Build Selected Items & Calculate Marks
    selected_items: List[SelectedQuestionItem] = []
    running_total_marks = Decimal("0.00")

    for order_idx, q in enumerate(selected_pool, start=1):
        # Effective Marks calculation
        if req.marks_config.mode == "uniform" and req.marks_config.uniform_marks is not None:
            effective_marks = req.marks_config.uniform_marks
        elif req.marks_config.mode == "by_type" and req.marks_config.type_marks:
            effective_marks = req.marks_config.type_marks.get(q.question_type, q.default_marks)
        else:
            effective_marks = q.default_marks

        # Effective Negative Marks calculation
        if not req.negative_marking.enabled:
            effective_neg = Decimal("0.00")
        elif req.negative_marking.mode == "custom" and req.negative_marking.custom_value is not None:
            effective_neg = req.negative_marking.custom_value
        elif req.negative_marking.mode == "by_type" and req.negative_marking.type_negative_marks:
            effective_neg = req.negative_marking.type_negative_marks.get(q.question_type, Decimal("0.00"))
        else:
            effective_neg = q.default_negative_marks

        running_total_marks += effective_marks

        # Snapshot Options
        options_data = []
        for opt in q.options:
            options_data.append(SelectedQuestionOption(
                id=opt.id,
                option_text=opt.option_text,
                option_order=opt.option_order,
                is_correct=opt.is_correct,  # Admin view only
            ))

        selected_items.append(SelectedQuestionItem(
            question_id=q.id,
            display_order=order_idx,
            marks=effective_marks,
            negative_marks=effective_neg,
            is_locked=False,
            question_type=q.question_type,
            difficulty=q.difficulty,
            title=q.title,
            question_text=q.question_text,
            options=options_data,
            explanation=q.explanation,
            short_answer_config=q.short_answer_config,
            subject_id=q.subject_id,
            subject_name=q.subject.subject_name if q.subject else None,
            unit_id=q.unit_id,
            unit_name=q.unit.unit_name if q.unit else None,
            chapter_id=q.chapter_id,
            chapter_name=q.chapter.chapter_name if q.chapter else None,
            topic_id=q.topic_id,
            topic_name=q.topic.topic_name if q.topic else None,
            is_mathematical=q.is_mathematical,
            code_language=q.code_language,
        ))

    # 8. Target Total Marks Validation
    if req.marks_config.target_total_marks is not None:
        if abs(running_total_marks - req.marks_config.target_total_marks) > Decimal("0.01"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Effective question marks total ({running_total_marks}) does not match requested target total marks ({req.marks_config.target_total_marks}). Adjust question count or marks per question.",
            )

    # 9. Persist Generation Session to GenerationHistory
    subject = db.query(Subject).filter(Subject.id == req.academic_scope.subject_id).first()
    configuration_payload = {
        "total_questions": req.total_questions,
        "difficulty": req.difficulty.model_dump(mode="json"),
        "question_types": req.question_types,
        "marks_config": req.marks_config.model_dump(mode="json"),
        "negative_marking": req.negative_marking.model_dump(mode="json"),
        "unit_distribution": req.unit_distribution.model_dump(mode="json"),
        "reuse_policy": req.reuse_policy,
    }
    gen_session = GenerationHistory(
        id=uuid.uuid4(),
        session_title=req.exam_settings.title,
        subject_id=subject.id if subject else None,
        generated_by=admin.id,
        questions_selected_count=len(selected_items),
        generation_rule_snapshot=configuration_payload,
        academic_scope=req.academic_scope.model_dump(mode="json"),
        configuration=configuration_payload,
        exam_settings=req.exam_settings.model_dump(mode="json"),
        selected_questions=[item.model_dump(mode="json") for item in selected_items],
        validation_report={
            "is_valid": True,
            "requested_total": req.total_questions,
            "available_total": preflight.available_total,
            "difficulty_quotas": quotas,
            "seed": seed_str,
        },
        seed=seed_str,
        status="generated",
    )
    db.add(gen_session)
    db.commit()
    db.refresh(gen_session)

    logger.info(f"Generated question paper session [{gen_session.id}] with {len(selected_items)} questions by admin [{admin.email}]")

    return _to_generation_session_response(gen_session, subject.subject_name if subject else "")


def get_generation_session(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
) -> GenerationSessionResponse:
    """Fetch an existing generation session with RBAC authorization check."""
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Generation session '{generation_id}' not found.")

    # RBAC Scoping check
    if not admin.is_super_admin:
        if session.generated_by != admin.id:
            if session.subject_id and not check_academic_scope(db, admin, subject_id=session.subject_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Generation session is outside your academic scope.")

    subject_name = session.subject.subject_name if session.subject else ""
    return _to_generation_session_response(session, subject_name)


def list_generation_history(
    db: Session,
    admin: Admin,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List generation history sessions, respecting administrator scope."""
    query = db.query(GenerationHistory)
    if not admin.is_super_admin:
        query = query.filter(GenerationHistory.generated_by == admin.id)

    sessions = query.order_by(GenerationHistory.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(s.id),
            "session_title": s.session_title or "Untitled Examination Paper",
            "subject_id": str(s.subject_id) if s.subject_id else None,
            "subject_name": s.subject.subject_name if s.subject else "N/A",
            "questions_selected_count": s.questions_selected_count,
            "status": s.status,
            "saved_quiz_id": str(s.quiz_id) if s.quiz_id else None,
            "generated_by": str(s.generated_by) if s.generated_by else None,
            "generator_name": s.generator.full_name if s.generator else "System Admin",
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


def get_replacement_candidates(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    question_id: uuid.UUID,
    match_difficulty: bool = True,
    match_type: bool = True,
    match_topic: bool = False,
) -> List[ReplacementCandidateItem]:
    """
    Finds replacement candidates from the Question Bank matching the target question's constraints.
    Excludes questions already included in the active generation paper.
    """
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    target_q = db.query(Question).filter(Question.id == question_id).first()
    if not target_q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target question not found.")

    # Exclude currently selected question IDs
    current_items = session.selected_questions or []
    current_ids = {uuid.UUID(item["question_id"]) for item in current_items if "question_id" in item}

    # Build candidates query
    query = db.query(Question).filter(
        Question.subject_id == target_q.subject_id,
        Question.status == "approved",
        ~Question.id.in_(current_ids),
    )

    if match_difficulty:
        query = query.filter(Question.difficulty == target_q.difficulty)
    if match_type:
        query = query.filter(Question.question_type == target_q.question_type)
    if match_topic and target_q.topic_id:
        query = query.filter(Question.topic_id == target_q.topic_id)

    candidates = query.limit(30).all()

    return [
        ReplacementCandidateItem(
            id=c.id,
            title=c.title,
            question_text=c.question_text,
            question_type=c.question_type,
            difficulty=c.difficulty,
            default_marks=c.default_marks,
            topic_name=c.topic.topic_name if c.topic else None,
            unit_name=c.unit.unit_name if c.unit else None,
        )
        for c in candidates
    ]


def replace_question_in_session(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    req: ReplaceQuestionRequest,
) -> GenerationSessionResponse:
    """
    Replaces a specific question in the generated paper with an eligible alternative.
    Maintains question position/display_order and configuration.
    """
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    current_items = session.selected_questions or []
    target_idx = None
    target_item = None
    for idx, item in enumerate(current_items):
        if str(item["question_id"]) == str(req.question_id):
            target_idx = idx
            target_item = item
            break

    if target_idx is None or target_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question to replace not found in this session.")

    if target_item.get("is_locked"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot replace a locked question. Unlock it first.")

    # Find replacement candidate
    replacement_q = None
    if req.replacement_question_id:
        replacement_q = db.query(Question).filter(Question.id == req.replacement_question_id).first()
        if not replacement_q or replacement_q.status != "approved":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified replacement question is invalid or not approved.")
    else:
        candidates = get_replacement_candidates(
            db, admin, generation_id, req.question_id,
            match_difficulty=req.match_difficulty,
            match_type=req.match_type,
            match_topic=req.match_topic,
        )
        if not candidates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No eligible replacement questions available matching the constraints.")
        replacement_q = db.query(Question).filter(Question.id == candidates[0].id).first()

    # Build replacement snapshot
    options_data = [
        {"id": str(opt.id), "option_text": opt.option_text, "option_order": opt.option_order, "is_correct": opt.is_correct}
        for opt in replacement_q.options
    ]

    new_item = {
        "question_id": str(replacement_q.id),
        "display_order": target_item.get("display_order", target_idx + 1),
        "marks": str(target_item.get("marks", replacement_q.default_marks)),
        "negative_marks": str(target_item.get("negative_marks", Decimal("0.00"))),
        "is_locked": False,
        "question_type": replacement_q.question_type,
        "difficulty": replacement_q.difficulty,
        "title": replacement_q.title,
        "question_text": replacement_q.question_text,
        "options": options_data,
        "explanation": replacement_q.explanation,
        "short_answer_config": replacement_q.short_answer_config,
        "subject_id": str(replacement_q.subject_id) if replacement_q.subject_id else None,
        "subject_name": replacement_q.subject.subject_name if replacement_q.subject else None,
        "unit_id": str(replacement_q.unit_id) if replacement_q.unit_id else None,
        "unit_name": replacement_q.unit.unit_name if replacement_q.unit else None,
        "chapter_id": str(replacement_q.chapter_id) if replacement_q.chapter_id else None,
        "chapter_name": replacement_q.chapter.chapter_name if replacement_q.chapter else None,
        "topic_id": str(replacement_q.topic_id) if replacement_q.topic_id else None,
        "topic_name": replacement_q.topic.topic_name if replacement_q.topic else None,
        "is_mathematical": replacement_q.is_mathematical,
        "code_language": replacement_q.code_language,
    }

    current_items[target_idx] = new_item
    session.selected_questions = list(current_items)
    flag_modified(session, "selected_questions")
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return _to_generation_session_response(session, session.subject.subject_name if session.subject else "")


def reorder_questions_in_session(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    question_ids_order: List[uuid.UUID],
) -> GenerationSessionResponse:
    """Reorders the generated questions list according to the provided sequence."""
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    current_items = session.selected_questions or []
    item_by_id = {str(item["question_id"]): item for item in current_items if "question_id" in item}

    reordered = []
    for order_idx, q_id in enumerate(question_ids_order, start=1):
        s_id = str(q_id)
        if s_id in item_by_id:
            item = item_by_id[s_id]
            item["display_order"] = order_idx
            reordered.append(item)

    # Any remaining items not specified in order list
    seen_ids = {str(q_id) for q_id in question_ids_order}
    for item in current_items:
        s_id = str(item.get("question_id"))
        if s_id not in seen_ids:
            item["display_order"] = len(reordered) + 1
            reordered.append(item)

    session.selected_questions = list(reordered)
    flag_modified(session, "selected_questions")
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return _to_generation_session_response(session, session.subject.subject_name if session.subject else "")


def update_question_settings_in_session(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    question_id: uuid.UUID,
    marks: Optional[Decimal] = None,
    negative_marks: Optional[Decimal] = None,
    is_locked: Optional[bool] = None,
) -> GenerationSessionResponse:
    """Updates individual question marks, negative marks, or locked status."""
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    current_items = session.selected_questions or []
    updated = False
    for item in current_items:
        if str(item.get("question_id")) == str(question_id):
            if marks is not None:
                item["marks"] = str(marks)
            if negative_marks is not None:
                item["negative_marks"] = str(negative_marks)
            if is_locked is not None:
                item["is_locked"] = is_locked
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in this generation session.")

    session.selected_questions = list(current_items)
    flag_modified(session, "selected_questions")
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return _to_generation_session_response(session, session.subject.subject_name if session.subject else "")


def regenerate_unlocked_questions(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    preserve_locked: bool = True,
    new_seed: Optional[str] = None,
) -> GenerationSessionResponse:
    """
    Regenerates unlocked questions using a new randomization seed while preserving all locked items.
    """
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    current_items = session.selected_questions or []
    config = session.configuration or {}
    scope_data = session.academic_scope or {}

    locked_items = [it for it in current_items if it.get("is_locked")] if preserve_locked else []
    locked_ids = {it["question_id"] for it in locked_items}

    total_target = config.get("total_questions", len(current_items))
    needed_count = total_target - len(locked_items)

    if needed_count > 0:
        seed_str = new_seed or str(uuid.uuid4())
        rng = random.Random(seed_str)

        # Build query for eligible questions excluding locked ones
        academic_scope = AcademicScopeRequest(
            subject_id=uuid.UUID(scope_data.get("subject_id")),
            selected_unit_ids=[uuid.UUID(u) for u in scope_data.get("selected_unit_ids", [])],
            selected_chapter_ids=[uuid.UUID(c) for c in scope_data.get("selected_chapter_ids", [])],
            selected_topic_ids=[uuid.UUID(t) for t in scope_data.get("selected_topic_ids", [])],
        )

        base_query = _build_eligible_questions_query(
            db, admin, academic_scope,
            config.get("question_types", ["single_choice", "multiple_choice", "true_false", "short_answer"]),
            config.get("reuse_policy", "allow_all"),
        )
        candidates = base_query.filter(~Question.id.in_([uuid.UUID(qid) for qid in locked_ids])).all()

        if len(candidates) < needed_count:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient remaining questions in Question Bank to regenerate ({len(candidates)} available, {needed_count} required).")

        selected_new = rng.sample(candidates, needed_count)
        new_items = []
        for q in selected_new:
            options_data = [
                {"id": str(opt.id), "option_text": opt.option_text, "option_order": opt.option_order, "is_correct": opt.is_correct}
                for opt in q.options
            ]
            new_items.append({
                "question_id": str(q.id),
                "display_order": 0,
                "marks": str(q.default_marks),
                "negative_marks": str(q.default_negative_marks),
                "is_locked": False,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "title": q.title,
                "question_text": q.question_text,
                "options": options_data,
                "explanation": q.explanation,
                "short_answer_config": q.short_answer_config,
                "subject_id": str(q.subject_id) if q.subject_id else None,
                "subject_name": q.subject.subject_name if q.subject else None,
                "unit_id": str(q.unit_id) if q.unit_id else None,
                "unit_name": q.unit.unit_name if q.unit else None,
                "chapter_id": str(q.chapter_id) if q.chapter_id else None,
                "chapter_name": q.chapter.chapter_name if q.chapter else None,
                "topic_id": str(q.topic_id) if q.topic_id else None,
                "topic_name": q.topic.topic_name if q.topic else None,
                "is_mathematical": q.is_mathematical,
                "code_language": q.code_language,
            })

        combined = locked_items + new_items
        for idx, it in enumerate(combined, start=1):
            it["display_order"] = idx

        session.selected_questions = list(combined)
        flag_modified(session, "selected_questions")
        session.seed = seed_str
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    return _to_generation_session_response(session, session.subject.subject_name if session.subject else "")


def save_generation_as_draft(
    db: Session,
    admin: Admin,
    generation_id: uuid.UUID,
    override_settings: Optional[Dict[str, Any]] = None,
) -> SaveAsDraftResponse:
    """
    Saves the generated question paper into the authoritative quizzes & quiz_questions database tables
    with status 'draft'.
    Creates immutable question snapshots.
    """
    session = db.query(GenerationHistory).filter(GenerationHistory.id == generation_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation session not found.")

    exam_settings = session.exam_settings or {}
    if override_settings:
        exam_settings.update(override_settings)

    items = session.selected_questions or []
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot save empty paper draft.")

    title = exam_settings.get("title", session.session_title or "Generated Examination Paper")
    total_marks = sum(Decimal(str(it.get("marks", 1.0))) for it in items)

    # 1. Create Quiz Entity
    new_quiz = Quiz(
        id=uuid.uuid4(),
        title=title,
        slug=slugify(title),
        description=exam_settings.get("description"),
        instructions=exam_settings.get("instructions"),
        subject_id=session.subject_id,
        duration_minutes=int(exam_settings.get("duration_minutes", 60)),
        total_marks=total_marks,
        passing_percentage=Decimal(str(exam_settings.get("passing_percentage", 40.0))),
        max_attempts=1,
        shuffle_questions=bool(exam_settings.get("shuffle_questions", True)),
        shuffle_options=bool(exam_settings.get("shuffle_options", True)),
        show_results_immediately=True,
        show_correct_answers=False,
        allow_review=True,
        status="draft",  # STRICTLY DRAFT in Phase 8
        creation_mode="generator",
        created_by=admin.id,
    )
    db.add(new_quiz)
    db.flush()

    # 2. Create QuizQuestions with immutable snapshots
    for it in items:
        q_id = uuid.UUID(it["question_id"])
        db_q = db.query(Question).filter(Question.id == q_id).first()
        if not db_q:
            continue

        # Immutable question snapshot
        snapshot = {
            "question_id": str(db_q.id),
            "title": db_q.title,
            "question_text": db_q.question_text,
            "question_type": db_q.question_type,
            "difficulty": db_q.difficulty,
            "default_marks": str(db_q.default_marks),
            "explanation": db_q.explanation,  # Protected, available only for admin view
            "short_answer_config": db_q.short_answer_config,
            "is_mathematical": db_q.is_mathematical,
            "code_language": db_q.code_language,
            "options": [
                {
                    "id": str(opt.id),
                    "option_text": opt.option_text,
                    "option_order": opt.option_order,
                    "is_correct": opt.is_correct,
                }
                for opt in db_q.options
            ],
            "frozen_at": datetime.now(timezone.utc).isoformat(),
        }

        qq = QuizQuestion(
            id=uuid.uuid4(),
            quiz_id=new_quiz.id,
            question_id=db_q.id,
            question_order=it.get("display_order", 1),
            marks=Decimal(str(it.get("marks", 1.0))),
            negative_marks=Decimal(str(it.get("negative_marks", 0.0))),
            question_snapshot=snapshot,
        )
        db.add(qq)

    # 3. Update GenerationHistory session
    session.quiz_id = new_quiz.id
    session.status = "saved_as_draft"
    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(new_quiz)

    logger.info(f"Saved generated quiz paper [{new_quiz.id}] with {len(items)} questions as draft by [{admin.email}]")

    base_path = "/super-admin/quiz" if admin.is_super_admin else "/admin/quiz"
    return SaveAsDraftResponse(
        quiz_id=new_quiz.id,
        title=new_quiz.title,
        total_marks=total_marks,
        question_count=len(items),
        status="draft",
        redirect_url=f"{base_path}/{new_quiz.id}",
    )


def _to_generation_session_response(s: GenerationHistory, subject_name: str) -> GenerationSessionResponse:
    items = s.selected_questions or []
    question_items: List[SelectedQuestionItem] = []
    running_total = Decimal("0.00")

    for it in items:
        marks_dec = Decimal(str(it.get("marks", "1.00")))
        neg_dec = Decimal(str(it.get("negative_marks", "0.00")))
        running_total += marks_dec

        options = [
            SelectedQuestionOption(
                id=uuid.UUID(opt["id"]) if opt.get("id") else None,
                option_text=opt.get("option_text", ""),
                option_order=opt.get("option_order", 0),
                is_correct=opt.get("is_correct"),
            )
            for opt in it.get("options", [])
        ]

        question_items.append(SelectedQuestionItem(
            question_id=uuid.UUID(it["question_id"]),
            display_order=it.get("display_order", 1),
            marks=marks_dec,
            negative_marks=neg_dec,
            is_locked=bool(it.get("is_locked", False)),
            question_type=it.get("question_type", "single_choice"),
            difficulty=it.get("difficulty", "medium"),
            title=it.get("title"),
            question_text=it.get("question_text", ""),
            options=options,
            explanation=it.get("explanation"),
            short_answer_config=it.get("short_answer_config"),
            subject_id=uuid.UUID(it["subject_id"]) if it.get("subject_id") else None,
            subject_name=it.get("subject_name", subject_name),
            unit_id=uuid.UUID(it["unit_id"]) if it.get("unit_id") else None,
            unit_name=it.get("unit_name"),
            chapter_id=uuid.UUID(it["chapter_id"]) if it.get("chapter_id") else None,
            chapter_name=it.get("chapter_name"),
            topic_id=uuid.UUID(it["topic_id"]) if it.get("topic_id") else None,
            topic_name=it.get("topic_name"),
            is_mathematical=bool(it.get("is_mathematical", False)),
            code_language=it.get("code_language"),
        ))

    return GenerationSessionResponse(
        id=s.id,
        session_title=s.session_title,
        subject_id=s.subject_id,
        subject_name=subject_name,
        total_questions=len(question_items),
        total_marks=running_total,
        academic_scope=s.academic_scope or {},
        configuration=s.configuration or {},
        exam_settings=s.exam_settings or {},
        questions=question_items,
        validation_report=s.validation_report,
        seed=s.seed,
        status=s.status,
        saved_quiz_id=s.quiz_id,
        generated_by=s.generated_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )
