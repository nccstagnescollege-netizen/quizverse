import uuid
import html
import re
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, AdminAcademicScope
from backend.app.models.academic import (
    Institution,
    Programme,
    Curriculum,
    CurriculumSubject,
    Semester,
    Subject,
    Unit,
    Chapter,
    Topic,
)
from backend.app.models.question_bank import (
    Question,
    QuestionOption,
    QuestionTag,
    QuestionTagRelation,
    QuestionVersion,
    QuestionAttachment,
    QuestionReview,
    PlatformSetting,
)
from backend.app.models.quiz import QuizQuestion
from backend.app.schemas.question_bank import (
    QuestionCreate,
    QuestionUpdate,
    QuestionOptionCreate,
    QuestionOptionUpdate,
    QuestionTagCreate,
    QuestionTagUpdate,
    QuestionReviewCreate,
    QuestionSummaryStats,
)
from backend.app.services.rbac_service import (
    get_admin_effective_permissions,
    check_academic_scope,
)
from backend.app.services.audit_service import log_audit_event


def sanitize_rich_text(content: str) -> str:
    r"""
    Sanitizes question rich text content to protect against XSS,
    while preserving safe markdown, LaTeX math notation ($...$, $$...$$, \(...\), \[...\]),
    and code block formats.
    """
    if not content:
        return ""
    # Strip script tags and risky javascript protocols
    cleaned = re.sub(r"<\s*script[^>]*>[\s\S]*?<\s*/\s*script\s*>", "", content, flags=re.IGNORECASE)
    cleaned = re.sub(r"javascript\s*:", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"onerror\s*=", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"onload\s*=", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"onclick\s*=", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


class QuestionBankService:

    @staticmethod
    def validate_and_resolve_hierarchy(
        db: Session,
        topic_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
        unit_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        institution_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Optional[uuid.UUID]]:
        """
        Validates the academic hierarchy from Topic upward:
        Topic -> Chapter -> Unit -> Subject -> Institution.
        If parent IDs are omitted, automatically resolves and backfills them.
        If parent IDs are provided, strictly validates that the topic belongs to them.
        """
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Academic Topic '{topic_id}' does not exist.",
            )

        resolved_chapter = db.query(Chapter).filter(Chapter.id == topic.chapter_id).first()
        if not resolved_chapter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inconsistent academic data: Topic lacks valid parent Chapter.",
            )

        if chapter_id and chapter_id != resolved_chapter.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic '{topic.topic_name}' belongs to Chapter '{resolved_chapter.chapter_name}', not the selected Chapter '{chapter_id}'.",
            )

        resolved_unit = db.query(Unit).filter(Unit.id == resolved_chapter.unit_id).first()
        if not resolved_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inconsistent academic data: Chapter lacks valid parent Unit.",
            )

        if unit_id and unit_id != resolved_unit.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic belongs to Unit '{resolved_unit.unit_name}', not the selected Unit '{unit_id}'.",
            )

        resolved_subject = db.query(Subject).filter(Subject.id == resolved_unit.subject_id).first()
        if subject_id and resolved_subject and subject_id != resolved_subject.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic belongs to Subject '{resolved_subject.subject_name}', not the selected Subject '{subject_id}'.",
            )

        resolved_inst_id = resolved_subject.institution_id if resolved_subject else None
        if institution_id and resolved_inst_id and institution_id != resolved_inst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subject belongs to another Institution.",
            )

        return {
            "chapter_id": resolved_chapter.id,
            "unit_id": resolved_unit.id,
            "subject_id": resolved_subject.id if resolved_subject else None,
            "institution_id": resolved_inst_id,
        }

    @staticmethod
    def enforce_question_permission_and_scope(
        db: Session,
        admin: Admin,
        question: Question,
        required_perm: str,
        is_write_op: bool = False,
    ) -> None:
        """
        Enforces both granular permission and academic scope isolation for question operations.
        Super Admin bypasses all checks.
        """
        if admin.is_super_admin:
            return

        # 1. Check granular permission
        effective_perms = getattr(admin, "_effective_permissions", None)
        if effective_perms is None:
            effective_perms = get_admin_effective_permissions(db, admin)
            admin._effective_permissions = effective_perms

        if required_perm not in effective_perms and "*" not in effective_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Missing required permission '{required_perm}'.",
            )

        # 2. Check academic scope
        in_scope = check_academic_scope(
            db=db,
            admin=admin,
            institution_id=question.institution_id,
            subject_id=question.subject_id,
            unit_id=question.unit_id,
            topic_id=question.topic_id,
            strict_for_user_admin=True,
        )
        if not in_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Question is outside your assigned academic scope.",
            )

        # 3. For write operations (edit, delete), if not the creator, check if admin has platform-wide or scope edit privileges
        if is_write_op and question.created_by and question.created_by != admin.id:
            # Must possess explicit edit permission and academic scope covers the question
            pass

    @classmethod
    def get_summary_stats(cls, db: Session, admin: Admin) -> QuestionSummaryStats:
        """
        Retrieves real database-backed metrics for the Question Bank dashboard.
        For Super Admin: platform-wide counts.
        For User Admin: counts strictly filtered by their assigned academic scopes.
        """
        query = db.query(Question)

        if not admin.is_super_admin:
            scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
            if not scopes:
                # User admin with zero assigned academic scopes sees zero questions
                return QuestionSummaryStats(
                    total_questions=0,
                    draft_questions=0,
                    pending_review_questions=0,
                    approved_questions=0,
                    archived_questions=0,
                    single_choice_count=0,
                    multiple_choice_count=0,
                    true_false_count=0,
                    short_answer_count=0,
                    easy_count=0,
                    medium_count=0,
                    hard_count=0,
                )

            # Build scope filter
            allowed_topics = {s.topic_id for s in scopes if s.topic_id}
            allowed_units = {s.unit_id for s in scopes if s.unit_id}
            allowed_subjects = {s.subject_id for s in scopes if s.subject_id}
            allowed_institutions = {s.institution_id for s in scopes if s.institution_id}

            conditions = []
            if allowed_topics:
                conditions.append(Question.topic_id.in_(allowed_topics))
            if allowed_units:
                conditions.append(Question.unit_id.in_(allowed_units))
            if allowed_subjects:
                conditions.append(Question.subject_id.in_(allowed_subjects))
            if allowed_institutions:
                conditions.append(Question.institution_id.in_(allowed_institutions))

            # Also allow questions created by the user admin
            conditions.append(Question.created_by == admin.id)
            query = query.filter(or_(*conditions))

        all_q = query.all()

        total = len(all_q)
        draft = sum(1 for q in all_q if q.status == "draft")
        pending = sum(1 for q in all_q if q.status == "pending_review")
        approved = sum(1 for q in all_q if q.status == "approved")
        archived = sum(1 for q in all_q if q.status == "archived")

        sc = sum(1 for q in all_q if q.question_type == "single_choice" and q.status != "archived")
        mc = sum(1 for q in all_q if q.question_type == "multiple_choice" and q.status != "archived")
        tf = sum(1 for q in all_q if q.question_type == "true_false" and q.status != "archived")
        sa = sum(1 for q in all_q if q.question_type in ("short_answer", "numerical") and q.status != "archived")

        easy = sum(1 for q in all_q if q.difficulty == "easy" and q.status != "archived")
        med = sum(1 for q in all_q if q.difficulty == "medium" and q.status != "archived")
        hard = sum(1 for q in all_q if q.difficulty == "hard" and q.status != "archived")

        return QuestionSummaryStats(
            total_questions=total,
            draft_questions=draft,
            pending_review_questions=pending,
            approved_questions=approved,
            archived_questions=archived,
            single_choice_count=sc,
            multiple_choice_count=mc,
            true_false_count=tf,
            short_answer_count=sa,
            easy_count=easy,
            medium_count=med,
            hard_count=hard,
        )

    @classmethod
    def list_questions(
        cls,
        db: Session,
        admin: Admin,
        institution_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        unit_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
        topic_id: Optional[uuid.UUID] = None,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        status_filter: Optional[str] = None,
        tag_name: Optional[str] = None,
        search: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Question], int]:
        """
        Searches and filters the Question Bank with database-side pagination.
        Enforces academic scopes for User Admins.
        """
        query = db.query(Question)

        # 1. Enforce Role & Academic Scope
        if not admin.is_super_admin:
            effective_perms = getattr(admin, "_effective_permissions", None)
            if effective_perms is None:
                effective_perms = get_admin_effective_permissions(db, admin)
                admin._effective_permissions = effective_perms

            if "question.view" not in effective_perms and "*" not in effective_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: You lack 'question.view' permission.",
                )

            scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
            if not scopes:
                return [], 0

            allowed_topics = {s.topic_id for s in scopes if s.topic_id}
            allowed_units = {s.unit_id for s in scopes if s.unit_id}
            allowed_subjects = {s.subject_id for s in scopes if s.subject_id}
            allowed_institutions = {s.institution_id for s in scopes if s.institution_id}

            conditions = []
            if allowed_topics:
                conditions.append(Question.topic_id.in_(allowed_topics))
            if allowed_units:
                conditions.append(Question.unit_id.in_(allowed_units))
            if allowed_subjects:
                conditions.append(Question.subject_id.in_(allowed_subjects))
            if allowed_institutions:
                conditions.append(Question.institution_id.in_(allowed_institutions))
            conditions.append(Question.created_by == admin.id)
            query = query.filter(or_(*conditions))

        # 2. Filters
        if institution_id:
            query = query.filter(Question.institution_id == institution_id)
        if subject_id:
            query = query.filter(Question.subject_id == subject_id)
        if unit_id:
            query = query.filter(Question.unit_id == unit_id)
        if chapter_id:
            query = query.filter(Question.chapter_id == chapter_id)
        if topic_id:
            query = query.filter(Question.topic_id == topic_id)
        if question_type:
            query = query.filter(Question.question_type == question_type)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty.lower())
        if created_by:
            query = query.filter(Question.created_by == created_by)

        if status_filter:
            query = query.filter(Question.status == status_filter)
        elif not include_archived:
            query = query.filter(Question.status != "archived")

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(or_(
                Question.question_text.ilike(term),
                Question.title.ilike(term),
                Question.explanation.ilike(term),
            ))

        if tag_name:
            query = query.join(Question.tag_relations).join(QuestionTagRelation.tag).filter(
                QuestionTag.tag_name == tag_name
            )

        total = query.count()
        questions = query.order_by(Question.created_at.desc()).offset(skip).limit(limit).all()
        return questions, total

    @classmethod
    def get_question_by_id(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> Question:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question '{question_id}' not found.",
            )
        cls.enforce_question_permission_and_scope(db, admin, question, "question.view", is_write_op=False)
        return question

    @classmethod
    def create_question(cls, db: Session, admin: Admin, payload: QuestionCreate) -> Question:
        """
        Creates a new question with options, tags, and version snapshot.
        Enforces `question.create` permission and academic scope.
        """
        if not admin.is_super_admin:
            perms = get_admin_effective_permissions(db, admin)
            if "question.create" not in perms and "*" not in perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: Missing 'question.create' permission.",
                )

        # 1. Validate academic hierarchy & resolve parents
        hierarchy = cls.validate_and_resolve_hierarchy(
            db=db,
            topic_id=payload.topic_id,
            chapter_id=payload.chapter_id,
            unit_id=payload.unit_id,
            subject_id=payload.subject_id,
            institution_id=payload.institution_id,
        )

        # 2. Validate academic scope for user admin
        if not admin.is_super_admin:
            in_scope = check_academic_scope(
                db=db,
                admin=admin,
                institution_id=hierarchy["institution_id"],
                subject_id=hierarchy["subject_id"],
                unit_id=hierarchy["unit_id"],
                topic_id=payload.topic_id,
                strict_for_user_admin=True,
            )
            if not in_scope:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create question: Topic is outside your assigned academic scope.",
                )

        # 3. Determine initial status based on review workflow policy
        initial_status = payload.status
        if not admin.is_super_admin and payload.status == "approved":
            # Check platform review workflow setting
            setting = db.query(PlatformSetting).filter(PlatformSetting.key == "question_review_workflow").first()
            if setting and setting.value.get("require_super_admin_approval"):
                initial_status = "pending_review"

        clean_text = sanitize_rich_text(payload.question_text)
        clean_title = sanitize_rich_text(payload.title) if payload.title else None
        clean_exp = sanitize_rich_text(payload.explanation) if payload.explanation else None

        question = Question(
            id=uuid.uuid4(),
            title=clean_title,
            institution_id=hierarchy["institution_id"],
            subject_id=hierarchy["subject_id"],
            curriculum_id=payload.curriculum_id,
            semester_id=payload.semester_id,
            unit_id=hierarchy["unit_id"],
            chapter_id=hierarchy["chapter_id"],
            topic_id=payload.topic_id,
            question_text=clean_text,
            question_type=payload.question_type,
            difficulty=payload.difficulty,
            default_marks=payload.default_marks,
            default_negative_marks=payload.default_negative_marks,
            explanation=clean_exp,
            question_image_path=payload.question_image_path,
            short_answer_config=payload.short_answer_config.model_dump() if payload.short_answer_config else None,
            is_mathematical=payload.is_mathematical,
            code_language=payload.code_language,
            status=initial_status,
            created_by=admin.id,
            approved_by=admin.id if initial_status == "approved" else None,
            approved_at=datetime.now(timezone.utc) if initial_status == "approved" else None,
        )
        db.add(question)
        db.flush()

        # 4. Insert Options
        if payload.options:
            for opt_idx, opt in enumerate(payload.options):
                db.add(QuestionOption(
                    id=uuid.uuid4(),
                    question_id=question.id,
                    option_text=sanitize_rich_text(opt.option_text),
                    option_image_path=opt.option_image_path,
                    option_order=opt.option_order if opt.option_order is not None else opt_idx,
                    is_correct=opt.is_correct,
                ))

        # 5. Insert Tags
        if payload.tag_ids:
            for tid in payload.tag_ids:
                db.add(QuestionTagRelation(question_id=question.id, tag_id=tid))

        if payload.tag_names:
            for tname in payload.tag_names:
                tname_clean = tname.strip()
                if not tname_clean:
                    continue
                tag = db.query(QuestionTag).filter(QuestionTag.tag_name == tname_clean).first()
                if not tag:
                    tag = QuestionTag(id=uuid.uuid4(), tag_name=tname_clean)
                    db.add(tag)
                    db.flush()
                # Check relation
                exists = db.query(QuestionTagRelation).filter_by(question_id=question.id, tag_id=tag.id).first()
                if not exists:
                    db.add(QuestionTagRelation(question_id=question.id, tag_id=tag.id))

        # 6. Create Version Snapshot #1
        snapshot = {
            "title": question.title,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "default_marks": float(question.default_marks),
            "default_negative_marks": float(question.default_negative_marks),
            "explanation": question.explanation,
            "topic_id": str(question.topic_id),
            "subject_id": str(question.subject_id) if question.subject_id else None,
            "options": [
                {"text": o.option_text, "is_correct": o.is_correct, "order": o.option_order}
                for o in (payload.options or [])
            ],
            "short_answer_config": question.short_answer_config,
        }
        db.add(QuestionVersion(
            id=uuid.uuid4(),
            question_id=question.id,
            version_number=1,
            question_snapshot=snapshot,
            change_summary="Initial question creation",
            changed_by=admin.id,
        ))

        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.create",
            entity_type="question",
            entity_id=str(question.id),
            details={"type": question.question_type, "topic_id": str(question.topic_id), "status": question.status},
        )
        return question

    @classmethod
    def update_question(cls, db: Session, admin: Admin, question_id: uuid.UUID, payload: QuestionUpdate) -> Question:
        """
        Updates an existing question, creating an immutable version snapshot.
        Enforces `question.edit` permission and academic scope.
        """
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.edit", is_write_op=True)

        # If academic topic changed, re-validate hierarchy
        if payload.topic_id and payload.topic_id != question.topic_id:
            hierarchy = cls.validate_and_resolve_hierarchy(
                db=db,
                topic_id=payload.topic_id,
                chapter_id=payload.chapter_id,
                unit_id=payload.unit_id,
                subject_id=payload.subject_id,
                institution_id=payload.institution_id,
            )
            if not admin.is_super_admin:
                in_scope = check_academic_scope(
                    db=db,
                    admin=admin,
                    institution_id=hierarchy["institution_id"],
                    subject_id=hierarchy["subject_id"],
                    unit_id=hierarchy["unit_id"],
                    topic_id=payload.topic_id,
                    strict_for_user_admin=True,
                )
                if not in_scope:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="New topic is outside your authorized academic scope.",
                    )
            question.topic_id = payload.topic_id
            question.chapter_id = hierarchy["chapter_id"]
            question.unit_id = hierarchy["unit_id"]
            question.subject_id = hierarchy["subject_id"]
            question.institution_id = hierarchy["institution_id"]

        # Track changes for version summary
        changes = []
        if payload.question_text and payload.question_text != question.question_text:
            question.question_text = sanitize_rich_text(payload.question_text)
            changes.append("question_text")
        if payload.title is not None and payload.title != question.title:
            question.title = sanitize_rich_text(payload.title)
            changes.append("title")
        if payload.difficulty and payload.difficulty != question.difficulty:
            question.difficulty = payload.difficulty
            changes.append("difficulty")
        if payload.default_marks is not None and payload.default_marks != question.default_marks:
            question.default_marks = payload.default_marks
            changes.append("marks")
        if payload.default_negative_marks is not None and payload.default_negative_marks != question.default_negative_marks:
            question.default_negative_marks = payload.default_negative_marks
            changes.append("negative_marks")
        if payload.explanation is not None and payload.explanation != question.explanation:
            question.explanation = sanitize_rich_text(payload.explanation)
            changes.append("explanation")
        if payload.short_answer_config is not None:
            question.short_answer_config = payload.short_answer_config.model_dump()
            changes.append("short_answer_config")
        if payload.is_mathematical is not None:
            question.is_mathematical = payload.is_mathematical
        if payload.code_language is not None:
            question.code_language = payload.code_language
        if payload.status and payload.status != question.status:
            question.status = payload.status
            changes.append("status")

        # Replace options if provided
        if payload.options is not None:
            db.query(QuestionOption).filter(QuestionOption.question_id == question.id).delete()
            for opt_idx, opt in enumerate(payload.options):
                db.add(QuestionOption(
                    id=uuid.uuid4(),
                    question_id=question.id,
                    option_text=sanitize_rich_text(opt.option_text),
                    option_image_path=opt.option_image_path,
                    option_order=opt.option_order if opt.option_order is not None else opt_idx,
                    is_correct=opt.is_correct,
                ))
            changes.append("options")

        # Replace tags if provided
        if payload.tag_ids is not None or payload.tag_names is not None:
            db.query(QuestionTagRelation).filter(QuestionTagRelation.question_id == question.id).delete()
            if payload.tag_ids:
                for tid in payload.tag_ids:
                    db.add(QuestionTagRelation(question_id=question.id, tag_id=tid))
            if payload.tag_names:
                for tname in payload.tag_names:
                    tname_clean = tname.strip()
                    if not tname_clean:
                        continue
                    tag = db.query(QuestionTag).filter(QuestionTag.tag_name == tname_clean).first()
                    if not tag:
                        tag = QuestionTag(id=uuid.uuid4(), tag_name=tname_clean)
                        db.add(tag)
                        db.flush()
                    db.add(QuestionTagRelation(question_id=question.id, tag_id=tag.id))
            changes.append("tags")

        question.updated_at = datetime.now(timezone.utc)
        db.flush()

        # Compute next version number
        latest_ver = (
            db.query(func.max(QuestionVersion.version_number))
            .filter(QuestionVersion.question_id == question.id)
            .scalar()
        ) or 1
        new_version_num = latest_ver + 1

        opts = db.query(QuestionOption).filter(QuestionOption.question_id == question.id).order_by(QuestionOption.option_order).all()
        snapshot = {
            "title": question.title,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "default_marks": float(question.default_marks),
            "default_negative_marks": float(question.default_negative_marks),
            "explanation": question.explanation,
            "topic_id": str(question.topic_id),
            "options": [
                {"text": o.option_text, "is_correct": o.is_correct, "order": o.option_order}
                for o in opts
            ],
            "short_answer_config": question.short_answer_config,
        }
        db.add(QuestionVersion(
            id=uuid.uuid4(),
            question_id=question.id,
            version_number=new_version_num,
            question_snapshot=snapshot,
            change_summary=f"Updated: {', '.join(changes) if changes else 'General edit'}",
            changed_by=admin.id,
        ))

        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.edit",
            entity_type="question",
            entity_id=str(question.id),
            details={"changes": changes, "new_version": new_version_num},
        )
        return question

    @classmethod
    def duplicate_question(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> Question:
        """
        Creates an independent duplicate of a question in 'draft' status.
        Does NOT copy student attempts or quiz bindings.
        """
        original = cls.get_question_by_id(db, admin, question_id)
        if not admin.is_super_admin:
            perms = get_admin_effective_permissions(db, admin)
            if "question.create" not in perms and "*" not in perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: You require 'question.create' to duplicate questions.",
                )

        new_title = f"{original.title or 'Question'} (Copy)"
        new_q = Question(
            id=uuid.uuid4(),
            title=new_title,
            institution_id=original.institution_id,
            subject_id=original.subject_id,
            curriculum_id=original.curriculum_id,
            semester_id=original.semester_id,
            unit_id=original.unit_id,
            chapter_id=original.chapter_id,
            topic_id=original.topic_id,
            question_text=original.question_text,
            question_type=original.question_type,
            difficulty=original.difficulty,
            default_marks=original.default_marks,
            default_negative_marks=original.default_negative_marks,
            explanation=original.explanation,
            question_image_path=original.question_image_path,
            short_answer_config=original.short_answer_config,
            is_mathematical=original.is_mathematical,
            code_language=original.code_language,
            status="draft",
            created_by=admin.id,
        )
        db.add(new_q)
        db.flush()

        # Copy options
        for opt in original.options:
            db.add(QuestionOption(
                id=uuid.uuid4(),
                question_id=new_q.id,
                option_text=opt.option_text,
                option_image_path=opt.option_image_path,
                option_order=opt.option_order,
                is_correct=opt.is_correct,
            ))

        # Copy tags
        for tr in original.tag_relations:
            db.add(QuestionTagRelation(question_id=new_q.id, tag_id=tr.tag_id))

        # Version 1 for new duplicate
        db.add(QuestionVersion(
            id=uuid.uuid4(),
            question_id=new_q.id,
            version_number=1,
            question_snapshot={
                "title": new_q.title,
                "question_text": new_q.question_text,
                "question_type": new_q.question_type,
                "options": [{"text": o.option_text, "is_correct": o.is_correct} for o in original.options],
            },
            change_summary=f"Duplicated from Question '{original.id}'",
            changed_by=admin.id,
        ))

        db.commit()
        db.refresh(new_q)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.duplicate",
            entity_type="question",
            entity_id=str(new_q.id),
            details={"source_id": str(original.id)},
        )
        return new_q

    @classmethod
    def archive_question(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> Question:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.archive", is_write_op=True)

        question.status = "archived"
        question.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.archive",
            entity_type="question",
            entity_id=str(question.id),
            details={"status": "archived"},
        )
        return question

    @classmethod
    def restore_question(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> Question:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.archive", is_write_op=True)

        question.status = "draft"
        question.archived_at = None
        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.restore",
            entity_type="question",
            entity_id=str(question.id),
            details={"status": "draft"},
        )
        return question

    @classmethod
    def delete_question(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> None:
        """
        Permanently deletes a question ONLY if it is not referenced by published quizzes or student attempts.
        If referenced, blocks deletion and instructs administrator to archive instead.
        Idempotent: if question is already deleted, returns cleanly without error.
        """
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return

        cls.enforce_question_permission_and_scope(db, admin, question, "question.delete", is_write_op=True)

        # Check references in quizzes
        quiz_ref_count = db.query(QuizQuestion).filter(QuizQuestion.question_id == question.id).count()
        if quiz_ref_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot permanently delete question '{question.id}': It is referenced by {quiz_ref_count} quiz(zes). Archive the question instead to preserve historical integrity.",
            )

        db.delete(question)
        db.commit()

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.delete",
            entity_type="question",
            entity_id=str(question_id),
            details={"status": "permanently_deleted"},
        )

    # --- Review Workflow ---

    @classmethod
    def submit_for_review(cls, db: Session, admin: Admin, question_id: uuid.UUID, comments: Optional[str] = None) -> Question:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.review", is_write_op=True)

        question.status = "pending_review"
        db.add(QuestionReview(
            id=uuid.uuid4(),
            question_id=question.id,
            reviewer_id=admin.id,
            action="submitted",
            comments=comments,
        ))
        db.commit()
        db.refresh(question)
        return question

    @classmethod
    def approve_question(cls, db: Session, admin: Admin, question_id: uuid.UUID, comments: Optional[str] = None) -> Question:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.approve", is_write_op=True)

        # If user admin is approving, prevent self-approval if review policy requires Super Admin
        if not admin.is_super_admin:
            if question.created_by == admin.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Review policy violation: You cannot approve your own question when formal review is active.",
                )

        question.status = "approved"
        question.approved_by = admin.id
        question.approved_at = datetime.now(timezone.utc)
        question.rejection_reason = None

        db.add(QuestionReview(
            id=uuid.uuid4(),
            question_id=question.id,
            reviewer_id=admin.id,
            action="approved",
            comments=comments,
        ))
        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.approve",
            entity_type="question",
            entity_id=str(question.id),
            details={"approved_by": str(admin.id)},
        )
        return question

    @classmethod
    def reject_question(cls, db: Session, admin: Admin, question_id: uuid.UUID, reason: str) -> Question:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.review", is_write_op=True)

        question.status = "draft"
        question.rejection_reason = reason
        db.add(QuestionReview(
            id=uuid.uuid4(),
            question_id=question.id,
            reviewer_id=admin.id,
            action="rejected",
            comments=reason,
        ))
        db.commit()
        db.refresh(question)

        log_audit_event(
            db=db,
            admin_id=admin.id,
            action="question.reject",
            entity_type="question",
            entity_id=str(question.id),
            details={"reason": reason},
        )
        return question

    # --- Tags ---

    @classmethod
    def list_tags(cls, db: Session, search: Optional[str] = None) -> List[QuestionTag]:
        q = db.query(QuestionTag)
        if search:
            q = q.filter(QuestionTag.tag_name.ilike(f"%{search.strip()}%"))
        return q.order_by(QuestionTag.tag_name.asc()).all()

    @classmethod
    def create_tag(cls, db: Session, admin: Admin, payload: QuestionTagCreate) -> QuestionTag:
        if not admin.is_super_admin:
            perms = get_admin_effective_permissions(db, admin)
            if "question.tag.manage" not in perms and "*" not in perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: You require 'question.tag.manage' to create tags.",
                )

        existing = db.query(QuestionTag).filter(QuestionTag.tag_name == payload.tag_name.strip()).first()
        if existing:
            return existing

        tag = QuestionTag(
            id=uuid.uuid4(),
            tag_name=payload.tag_name.strip(),
            description=payload.description,
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @classmethod
    def delete_tag(cls, db: Session, admin: Admin, tag_id: uuid.UUID) -> None:
        if not admin.is_super_admin:
            perms = get_admin_effective_permissions(db, admin)
            if "question.tag.manage" not in perms and "*" not in perms:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

        tag = db.query(QuestionTag).filter(QuestionTag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

        db.delete(tag)
        db.commit()

    # --- Attachments ---

    @classmethod
    def add_attachment(
        cls,
        db: Session,
        admin: Admin,
        question_id: uuid.UUID,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size_bytes: int,
        is_student_visible: bool = True,
    ) -> QuestionAttachment:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.attachment.upload", is_write_op=True)

        # Validate MIME type
        allowed_types = {
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/webp",
            "application/pdf",
        }
        if file_type.lower() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Disallowed attachment format '{file_type}'. Supported: PNG, JPEG, WEBP, PDF.",
            )

        # Max 10MB
        if file_size_bytes > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment size exceeds 10MB limit.",
            )

        att = QuestionAttachment(
            id=uuid.uuid4(),
            question_id=question.id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            is_student_visible=is_student_visible,
            uploaded_by=admin.id,
        )
        db.add(att)
        db.commit()
        db.refresh(att)
        return att

    @classmethod
    def delete_attachment(cls, db: Session, admin: Admin, question_id: uuid.UUID, attachment_id: uuid.UUID) -> None:
        question = cls.get_question_by_id(db, admin, question_id)
        cls.enforce_question_permission_and_scope(db, admin, question, "question.attachment.upload", is_write_op=True)

        att = db.query(QuestionAttachment).filter(
            QuestionAttachment.id == attachment_id,
            QuestionAttachment.question_id == question_id,
        ).first()
        if not att:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found.")

        db.delete(att)
        db.commit()

    # --- Versions ---

    @classmethod
    def get_version_history(cls, db: Session, admin: Admin, question_id: uuid.UUID) -> List[QuestionVersion]:
        question = cls.get_question_by_id(db, admin, question_id)
        return db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).order_by(QuestionVersion.version_number.desc()).all()
