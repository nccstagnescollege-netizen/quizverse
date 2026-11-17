import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import (
    get_current_admin,
    get_admin_effective_permissions,
)
from backend.app.services.question_bank_service import QuestionBankService
from backend.app.schemas.question_bank import (
    QuestionCreate,
    QuestionUpdate,
    QuestionListItemResponse,
    QuestionDetailResponse,
    QuestionAdminDetailResponse,
    QuestionSummaryStats,
    QuestionOptionResponse,
    QuestionOptionAdminResponse,
    QuestionOptionCreate,
    QuestionOptionUpdate,
    QuestionTagCreate,
    QuestionTagResponse,
    QuestionAttachmentResponse,
    QuestionVersionResponse,
    QuestionReviewCreate,
)
from backend.app.models.question_bank import QuestionOption

router = APIRouter()


# ==============================================================================
# 1. SUMMARY STATS (DASHBOARD)
# ==============================================================================

@router.get("/stats", response_model=QuestionSummaryStats)
def get_question_bank_stats(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves real database-backed metrics for the Question Bank dashboard.
    Platform-wide for Super Admin; scoped to assigned academic hierarchy for User Admins.
    """
    return QuestionBankService.get_summary_stats(db, admin)


# ==============================================================================
# 2. QUESTION LIBRARY (LIST & SEARCH)
# ==============================================================================

@router.get("", response_model=dict)
def list_questions(
    institution_id: Optional[uuid.UUID] = None,
    subject_id: Optional[uuid.UUID] = None,
    unit_id: Optional[uuid.UUID] = None,
    chapter_id: Optional[uuid.UUID] = None,
    topic_id: Optional[uuid.UUID] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    created_by: Optional[uuid.UUID] = None,
    include_archived: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Search and filter questions in the Question Bank with database pagination.
    """
    skip = (page - 1) * limit
    questions, total = QuestionBankService.list_questions(
        db=db,
        admin=admin,
        institution_id=institution_id,
        subject_id=subject_id,
        unit_id=unit_id,
        chapter_id=chapter_id,
        topic_id=topic_id,
        question_type=question_type,
        difficulty=difficulty,
        status_filter=status,
        tag_name=tag,
        search=search,
        created_by=created_by,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
    )

    items = []
    for q in questions:
        tag_names = [r.tag.tag_name for r in q.tag_relations if r.tag]
        items.append({
            "id": q.id,
            "title": q.title,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "default_marks": q.default_marks,
            "default_negative_marks": q.default_negative_marks,
            "status": q.status,
            "topic_id": q.topic_id,
            "topic_name": q.topic.topic_name if q.topic else None,
            "subject_id": q.subject_id,
            "subject_name": q.subject.subject_name if q.subject else None,
            "institution_name": q.institution.name if q.institution else None,
            "options_count": len(q.options),
            "tags": tag_names,
            "created_by": q.created_by,
            "created_by_name": q.creator.full_name if q.creator else None,
            "created_at": q.created_at,
            "updated_at": q.updated_at,
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1,
        }
    }


# ==============================================================================
# 3. QUESTION CREATION & DETAILS
# ==============================================================================

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Creates a new question with options and tags.
    Requires 'question.create' permission and matching academic scope.
    """
    question = QuestionBankService.create_question(db, admin, payload)
    return {
        "success": True,
        "message": "Question created successfully.",
        "data": {"id": question.id, "title": question.title, "status": question.status},
    }


@router.get("/{question_id}", response_model=dict)
def get_question_details(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves full question details.
    If the administrator has 'question.answer.view' or is Super Admin, returns the answer key.
    Otherwise, returns the question with answers masked.
    """
    q = QuestionBankService.get_question_by_id(db, admin, question_id)

    perms = get_admin_effective_permissions(db, admin)
    can_view_answer = admin.is_super_admin or "question.answer.view" in perms or "*" in perms

    tag_names = [r.tag.tag_name for r in q.tag_relations if r.tag]

    opts = []
    for o in q.options:
        opt_data = {
            "id": o.id,
            "question_id": o.question_id,
            "option_text": o.option_text,
            "option_image_path": o.option_image_path,
            "option_order": o.option_order,
        }
        if can_view_answer:
            opt_data["is_correct"] = o.is_correct
        else:
            opt_data["is_correct"] = None
        opts.append(opt_data)

    data = {
        "id": q.id,
        "title": q.title,
        "question_text": q.question_text,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "default_marks": q.default_marks,
        "default_negative_marks": q.default_negative_marks,
        "status": q.status,
        "is_mathematical": q.is_mathematical,
        "code_language": q.code_language,
        "question_image_path": q.question_image_path,
        "institution_id": q.institution_id,
        "institution_name": q.institution.name if q.institution else None,
        "subject_id": q.subject_id,
        "subject_name": q.subject.subject_name if q.subject else None,
        "curriculum_id": q.curriculum_id,
        "semester_id": q.semester_id,
        "semester_name": q.semester.semester_name if q.semester else None,
        "unit_id": q.unit_id,
        "unit_name": q.unit.unit_name if q.unit else None,
        "chapter_id": q.chapter_id,
        "chapter_name": q.chapter.chapter_name if q.chapter else None,
        "topic_id": q.topic_id,
        "topic_name": q.topic.topic_name if q.topic else None,
        "options": opts,
        "tags": tag_names,
        "attachments": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "file_name": a.file_name,
                "file_path": a.file_path,
                "file_type": a.file_type,
                "file_size_bytes": a.file_size_bytes,
                "is_student_visible": a.is_student_visible,
                "created_at": a.created_at,
            }
            for a in q.attachments
        ],
        "created_by": q.created_by,
        "created_by_name": q.creator.full_name if q.creator else None,
        "created_at": q.created_at,
        "updated_at": q.updated_at,
    }

    if can_view_answer:
        data["explanation"] = q.explanation
        data["short_answer_config"] = q.short_answer_config
        data["rejection_reason"] = q.rejection_reason
        data["approved_by"] = q.approved_by
        data["approved_by_name"] = q.approver.full_name if q.approver else None
        data["approved_at"] = q.approved_at
        data["archived_at"] = q.archived_at
        data["reviews"] = [
            {
                "id": r.id,
                "question_id": r.question_id,
                "reviewer_id": r.reviewer_id,
                "reviewer_name": r.reviewer.full_name if r.reviewer else None,
                "action": r.action,
                "comments": r.comments,
                "created_at": r.created_at,
            }
            for r in q.reviews
        ]

    return {"success": True, "data": data}


@router.get("/{question_id}/preview", response_model=dict)
def get_question_student_preview(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Renders question preview as a student would see it during an examination.
    GUARANTEE: NEVER leaks correct answer, explanation, or internal review metadata.
    """
    q = QuestionBankService.get_question_by_id(db, admin, question_id)

    # Sanitize and omit answers
    student_options = [
        {
            "id": o.id,
            "option_text": o.option_text,
            "option_image_path": o.option_image_path,
            "option_order": o.option_order,
            # Notice: is_correct is strictly omitted
        }
        for o in q.options
    ]

    visible_attachments = [
        {
            "id": a.id,
            "file_name": a.file_name,
            "file_path": a.file_path,
            "file_type": a.file_type,
            "file_size_bytes": a.file_size_bytes,
        }
        for a in q.attachments
        if a.is_student_visible
    ]

    return {
        "success": True,
        "data": {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "default_marks": q.default_marks,
            "default_negative_marks": q.default_negative_marks,
            "is_mathematical": q.is_mathematical,
            "code_language": q.code_language,
            "question_image_path": q.question_image_path,
            "options": student_options,
            "attachments": visible_attachments,
        }
    }


@router.get("/{question_id}/answer-key", response_model=dict)
def get_question_answer_key(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves the authoritative answer key and official explanation.
    Strictly protected: requires 'question.answer.view' permission.
    """
    q = QuestionBankService.get_question_by_id(db, admin, question_id)
    QuestionBankService.enforce_question_permission_and_scope(db, admin, q, "question.answer.view")

    correct_options = [
        {
            "id": o.id,
            "option_text": o.option_text,
            "option_order": o.option_order,
            "is_correct": o.is_correct,
        }
        for o in q.options
        if o.is_correct
    ]

    return {
        "success": True,
        "data": {
            "question_id": q.id,
            "question_type": q.question_type,
            "correct_options": correct_options,
            "all_options": [
                {"id": o.id, "option_text": o.option_text, "is_correct": o.is_correct, "order": o.option_order}
                for o in q.options
            ],
            "short_answer_config": q.short_answer_config,
            "explanation": q.explanation,
        }
    }


# ==============================================================================
# 4. QUESTION UPDATES, DUPLICATION, ARCHIVING & DELETION
# ==============================================================================

@router.patch("/{question_id}", response_model=dict)
@router.put("/{question_id}", response_model=dict)
def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Updates a question and records a version snapshot.
    Requires 'question.edit' permission and matching academic scope.
    """
    question = QuestionBankService.update_question(db, admin, question_id, payload)
    return {
        "success": True,
        "message": "Question updated successfully.",
        "data": {"id": question.id, "status": question.status},
    }


@router.post("/{question_id}/duplicate", response_model=dict, status_code=status.HTTP_201_CREATED)
def duplicate_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Creates an independent duplicate of a question in 'draft' status.
    Requires 'question.create' permission and matching academic scope.
    """
    new_q = QuestionBankService.duplicate_question(db, admin, question_id)
    return {
        "success": True,
        "message": "Question duplicated successfully as draft.",
        "data": {"id": new_q.id, "title": new_q.title},
    }


@router.post("/{question_id}/archive", response_model=dict)
def archive_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Archives a question.
    Requires 'question.archive' permission.
    """
    q = QuestionBankService.archive_question(db, admin, question_id)
    return {
        "success": True,
        "message": f"Question '{q.id}' archived successfully.",
    }


@router.post("/{question_id}/restore", response_model=dict)
def restore_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Restores an archived question to 'draft'.
    Requires 'question.archive' permission.
    """
    q = QuestionBankService.restore_question(db, admin, question_id)
    return {
        "success": True,
        "message": f"Question '{q.id}' restored to draft status.",
    }


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Permanently deletes a question only if safe (not referenced by published quizzes/attempts).
    Requires 'question.delete' permission.
    """
    QuestionBankService.delete_question(db, admin, question_id)
    return None


# ==============================================================================
# 5. REVIEW WORKFLOW
# ==============================================================================

@router.post("/{question_id}/submit-review", response_model=dict)
def submit_question_for_review(
    question_id: uuid.UUID,
    payload: Optional[QuestionReviewCreate] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    comments = payload.comments if payload else None
    q = QuestionBankService.submit_for_review(db, admin, question_id, comments)
    return {
        "success": True,
        "message": "Question submitted for formal review.",
        "data": {"id": q.id, "status": q.status},
    }


@router.post("/{question_id}/approve", response_model=dict)
def approve_question(
    question_id: uuid.UUID,
    payload: Optional[QuestionReviewCreate] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    comments = payload.comments if payload else None
    q = QuestionBankService.approve_question(db, admin, question_id, comments)
    return {
        "success": True,
        "message": "Question approved for examination inclusion.",
        "data": {"id": q.id, "status": q.status, "approved_by": q.approved_by},
    }


@router.post("/{question_id}/reject", response_model=dict)
def reject_question(
    question_id: uuid.UUID,
    payload: QuestionReviewCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    reason = payload.comments or "Changes requested"
    q = QuestionBankService.reject_question(db, admin, question_id, reason)
    return {
        "success": True,
        "message": "Question returned to draft with rejection comments.",
        "data": {"id": q.id, "status": q.status},
    }


# ==============================================================================
# 6. VERSION HISTORY
# ==============================================================================

@router.get("/{question_id}/history", response_model=dict)
def get_question_history(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves full immutable version history and snapshots for a question.
    """
    versions = QuestionBankService.get_version_history(db, admin, question_id)
    return {
        "success": True,
        "data": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "question_snapshot": v.question_snapshot,
                "change_summary": v.change_summary,
                "changed_by": v.changed_by,
                "changed_by_name": v.author.full_name if v.author else None,
                "created_at": v.created_at,
            }
            for v in versions
        ]
    }


# ==============================================================================
# 7. TAGS MANAGEMENT
# ==============================================================================

@router.get("/tags/all", response_model=dict)
@router.get("/tags/list", response_model=dict)
def list_tags(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    tags = QuestionBankService.list_tags(db, search)
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "tag_name": t.tag_name,
                "description": t.description,
                "created_at": t.created_at,
                "questions_count": len(t.tag_relations),
            }
            for t in tags
        ]
    }


@router.post("/tags", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: QuestionTagCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    tag = QuestionBankService.create_tag(db, admin, payload)
    return {
        "success": True,
        "message": f"Tag '{tag.tag_name}' created.",
        "data": {"id": tag.id, "tag_name": tag.tag_name},
    }


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    QuestionBankService.delete_tag(db, admin, tag_id)
    return None


# ==============================================================================
# 8. ATTACHMENTS
# ==============================================================================

@router.get("/{question_id}/attachments", response_model=dict)
def get_question_attachments(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    q = QuestionBankService.get_question_by_id(db, admin, question_id)
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "file_name": a.file_name,
                "file_path": a.file_path,
                "file_type": a.file_type,
                "file_size_bytes": a.file_size_bytes,
                "is_student_visible": a.is_student_visible,
                "uploaded_by": a.uploaded_by,
                "created_at": a.created_at,
            }
            for a in q.attachments
        ]
    }


@router.delete("/{question_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    question_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    QuestionBankService.delete_attachment(db, admin, question_id, attachment_id)
    return None


@router.post("/{question_id}/attachments", response_model=dict, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    question_id: uuid.UUID,
    file: UploadFile = File(...),
    is_student_visible: bool = Form(True),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Uploads a new attachment file for the given question.
    """
    content = file.file.read()
    file_size = len(content)
    file_name = file.filename or "attachment"
    file_type = file.content_type or "application/octet-stream"

    uploads_dir = Path("uploads/questions")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file_name}"
    file_path = str(uploads_dir / stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    att = QuestionBankService.add_attachment(
        db=db,
        admin=admin,
        question_id=question_id,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size,
        is_student_visible=is_student_visible,
    )
    return {
        "success": True,
        "message": "Attachment uploaded successfully.",
        "data": {
            "id": str(att.id),
            "question_id": str(att.question_id),
            "file_name": att.file_name,
            "file_path": att.file_path,
            "file_type": att.file_type,
            "file_size_bytes": att.file_size_bytes,
            "is_student_visible": att.is_student_visible,
            "created_at": att.created_at.isoformat() if att.created_at else None,
        },
    }
