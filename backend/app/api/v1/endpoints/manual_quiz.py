import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.models.quiz import Quiz, QuizAttachment
from backend.app.services.rbac_service import get_current_admin, require_permission
from backend.app.schemas.manual_quiz import (
    ManualQuizCreateRequest,
    QuizDetailsUpdateRequest,
    QuizSectionCreateRequest,
    QuizSectionUpdateRequest,
    ManualQuestionCreateRequest,
    AddQuestionsFromBankRequest,
    UpdateQuizQuestionRequest,
    ReorderQuestionsRequest,
    ReorderSectionsRequest,
    SaveDraftRequest,
    SaveToQuestionBankRequest,
    QuizSectionResponse,
    QuizQuestionItemResponse,
    QuizEditorResponse,
    QuizValidationResponse,
    QuizPreviewResponse,
)
from backend.app.services.manual_quiz_service import (
    create_manual_quiz,
    update_quiz_details,
    create_quiz_section,
    update_quiz_section,
    delete_quiz_section,
    reorder_quiz_sections,
    add_manual_question,
    add_questions_from_bank,
    save_manual_question_to_bank,
    update_quiz_question,
    delete_quiz_question,
    reorder_quiz_questions,
    get_quiz_editor_data,
    calculate_scoring_summary,
    save_quiz_draft,
    get_quiz_preview,
    verify_quiz_access,
)

router = APIRouter()


@router.post("/manual", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, summary="Create manual quiz")
def api_create_manual_quiz(
    payload: ManualQuizCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.create")),
):
    """
    Creates a new quiz in manual authoring mode with draft status.
    """
    quiz = create_manual_quiz(db, admin, payload)
    return {
        "success": True,
        "message": "Manual quiz created successfully.",
        "quiz_id": str(quiz.id),
        "slug": quiz.slug,
        "status": quiz.status,
    }


@router.get("/{quiz_id}/editor", response_model=QuizEditorResponse, summary="Get full quiz editor state")
def api_get_quiz_editor(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    Retrieves full editor state for the manual quiz authoring workspace.
    """
    return get_quiz_editor_data(db, admin, quiz_id)


@router.patch("/{quiz_id}/details", response_model=Dict[str, Any], summary="Update quiz details")
def api_update_quiz_details(
    quiz_id: uuid.UUID,
    payload: QuizDetailsUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Updates quiz academic metadata, title, instructions, and duration.
    """
    quiz = update_quiz_details(db, admin, quiz_id, payload)
    return {
        "success": True,
        "message": "Quiz details updated successfully.",
        "quiz_id": str(quiz.id),
        "title": quiz.title,
        "updated_at": quiz.updated_at.isoformat() if quiz.updated_at else None,
    }


@router.post("/{quiz_id}/sections", response_model=QuizSectionResponse, status_code=status.HTTP_201_CREATED, summary="Add section to quiz")
def api_create_quiz_section(
    quiz_id: uuid.UUID,
    payload: QuizSectionCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Creates a new section (e.g. Part A, Part B) within the quiz.
    """
    sec = create_quiz_section(db, admin, quiz_id, payload)
    return QuizSectionResponse(
        id=sec.id,
        quiz_id=sec.quiz_id,
        title=sec.title,
        description=sec.description,
        instructions=sec.instructions,
        section_order=sec.section_order,
        selection_rule=sec.selection_rule,
        required_question_count=sec.required_question_count,
        total_questions_count=sec.total_questions_count,
        default_marks_per_question=float(sec.default_marks_per_question) if sec.default_marks_per_question is not None else None,
        default_negative_marks_per_question=float(sec.default_negative_marks_per_question) if sec.default_negative_marks_per_question is not None else None,
        section_total_marks=float(sec.section_total_marks),
        created_at=sec.created_at,
        updated_at=sec.updated_at,
    )


@router.patch("/{quiz_id}/sections/{section_id}", response_model=QuizSectionResponse, summary="Update quiz section")
def api_update_quiz_section(
    quiz_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: QuizSectionUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Updates configuration and selection rules of an examination section.
    """
    sec = update_quiz_section(db, admin, quiz_id, section_id, payload)
    return QuizSectionResponse(
        id=sec.id,
        quiz_id=sec.quiz_id,
        title=sec.title,
        description=sec.description,
        instructions=sec.instructions,
        section_order=sec.section_order,
        selection_rule=sec.selection_rule,
        required_question_count=sec.required_question_count,
        total_questions_count=sec.total_questions_count,
        default_marks_per_question=float(sec.default_marks_per_question) if sec.default_marks_per_question is not None else None,
        default_negative_marks_per_question=float(sec.default_negative_marks_per_question) if sec.default_negative_marks_per_question is not None else None,
        section_total_marks=float(sec.section_total_marks),
        created_at=sec.created_at,
        updated_at=sec.updated_at,
    )


@router.delete("/{quiz_id}/sections/{section_id}", response_model=Dict[str, Any], summary="Delete quiz section")
def api_delete_quiz_section(
    quiz_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Removes a section and detaches its questions to standalone.
    """
    delete_quiz_section(db, admin, quiz_id, section_id)
    return {"success": True, "message": "Quiz section deleted successfully."}


@router.post("/{quiz_id}/sections/reorder", response_model=Dict[str, Any], summary="Reorder quiz sections")
def api_reorder_quiz_sections(
    quiz_id: uuid.UUID,
    payload: ReorderSectionsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Reorders examination sections.
    """
    reorder_quiz_sections(db, admin, quiz_id, payload.section_orders)
    return {"success": True, "message": "Quiz sections reordered successfully."}


@router.post("/{quiz_id}/questions/manual", response_model=QuizQuestionItemResponse, status_code=status.HTTP_201_CREATED, summary="Create manual question")
def api_add_manual_question(
    quiz_id: uuid.UUID,
    payload: ManualQuestionCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Method A: Authors a question directly inside the quiz draft.
    """
    qq = add_manual_question(db, admin, quiz_id, payload)
    return QuizQuestionItemResponse(
        id=qq.id,
        quiz_id=qq.quiz_id,
        question_id=qq.question_id,
        section_id=qq.section_id,
        question_order=qq.question_order,
        marks=float(qq.marks),
        negative_marks=float(qq.negative_marks),
        is_compulsory=qq.is_compulsory,
        is_manual=qq.is_manual,
        source_type=qq.source_type,
        custom_instructions=qq.custom_instructions,
        scoring_settings=qq.scoring_settings,
        question_snapshot=qq.question_snapshot,
        created_at=qq.created_at,
    )


@router.post("/{quiz_id}/questions/from-bank", response_model=List[QuizQuestionItemResponse], status_code=status.HTTP_201_CREATED, summary="Add questions from Question Bank")
def api_add_questions_from_bank(
    quiz_id: uuid.UUID,
    payload: AddQuestionsFromBankRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Method B: Selects questions from Question Bank and attaches them to the quiz.
    """
    added = add_questions_from_bank(db, admin, quiz_id, payload)
    return [
        QuizQuestionItemResponse(
            id=qq.id,
            quiz_id=qq.quiz_id,
            question_id=qq.question_id,
            section_id=qq.section_id,
            question_order=qq.question_order,
            marks=float(qq.marks),
            negative_marks=float(qq.negative_marks),
            is_compulsory=qq.is_compulsory,
            is_manual=qq.is_manual,
            source_type=qq.source_type,
            custom_instructions=qq.custom_instructions,
            scoring_settings=qq.scoring_settings,
            question_snapshot=qq.question_snapshot,
            created_at=qq.created_at,
        )
        for qq in added
    ]


@router.post("/{quiz_id}/questions/{quiz_question_id}/save-to-bank", response_model=Dict[str, Any], summary="Promote manual question to Question Bank")
def api_save_to_question_bank(
    quiz_id: uuid.UUID,
    quiz_question_id: uuid.UUID,
    payload: SaveToQuestionBankRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("question.create")),
):
    """
    Promotes a manually authored question from the quiz into the shared Question Bank.
    """
    new_q = save_manual_question_to_bank(db, admin, quiz_id, quiz_question_id, payload)
    return {
        "success": True,
        "message": "Question successfully saved to Question Bank.",
        "question_id": str(new_q.id),
        "status": new_q.status,
    }


@router.patch("/{quiz_id}/questions/{quiz_question_id}", response_model=QuizQuestionItemResponse, summary="Update quiz question")
def api_update_quiz_question(
    quiz_id: uuid.UUID,
    quiz_question_id: uuid.UUID,
    payload: UpdateQuizQuestionRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Updates marks, negative marks, compulsory flag, section, or manual question content.
    """
    qq = update_quiz_question(db, admin, quiz_id, quiz_question_id, payload)
    return QuizQuestionItemResponse(
        id=qq.id,
        quiz_id=qq.quiz_id,
        question_id=qq.question_id,
        section_id=qq.section_id,
        question_order=qq.question_order,
        marks=float(qq.marks),
        negative_marks=float(qq.negative_marks),
        is_compulsory=qq.is_compulsory,
        is_manual=qq.is_manual,
        source_type=qq.source_type,
        custom_instructions=qq.custom_instructions,
        scoring_settings=qq.scoring_settings,
        question_snapshot=qq.question_snapshot,
        created_at=qq.created_at,
    )


@router.delete("/{quiz_id}/questions/{quiz_question_id}", response_model=Dict[str, Any], summary="Delete question from quiz")
def api_delete_quiz_question(
    quiz_id: uuid.UUID,
    quiz_question_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Removes a question from the quiz draft.
    """
    delete_quiz_question(db, admin, quiz_id, quiz_question_id)
    return {"success": True, "message": "Question removed from quiz successfully."}


@router.post("/{quiz_id}/questions/reorder", response_model=Dict[str, Any], summary="Reorder questions in quiz")
def api_reorder_quiz_questions(
    quiz_id: uuid.UUID,
    payload: ReorderQuestionsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Updates question display sequence and section associations.
    """
    reorder_quiz_questions(db, admin, quiz_id, payload.items)
    return {"success": True, "message": "Questions reordered successfully."}


@router.post("/{quiz_id}/validate", response_model=QuizValidationResponse, summary="Validate quiz scoring and rules")
def api_validate_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    Runs rule validation across all sections, compulsory questions, and marks.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)

    summary = calculate_scoring_summary(db, quiz_id)
    return QuizValidationResponse(
        is_valid=summary.is_valid,
        errors=summary.validation_errors,
        warnings=summary.validation_warnings,
        scoring_summary=summary,
    )


@router.post("/{quiz_id}/save-draft", response_model=Dict[str, Any], summary="Save draft snapshot")
def api_save_draft(
    quiz_id: uuid.UUID,
    payload: SaveDraftRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Persists an authoritative draft snapshot into quiz_draft_versions.
    """
    draft = save_quiz_draft(db, admin, quiz_id, payload)
    return {
        "success": True,
        "message": f"Draft version {draft.version_number} saved successfully.",
        "version_number": draft.version_number,
        "saved_at": draft.created_at.isoformat() if draft.created_at else None,
    }


@router.get("/{quiz_id}/preview", response_model=QuizPreviewResponse, summary="Live examination paper preview")
def api_get_quiz_preview(
    quiz_id: uuid.UUID,
    mode: str = Query("student"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    Generates preview of the examination paper.
    - student: Strips all correct answers and explanations.
    - answer_key: Includes full answer key for authorized administrators.
    """
    if mode not in ["student", "answer_key"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid preview mode. Must be 'student' or 'answer_key'.")
    return get_quiz_preview(db, admin, quiz_id, mode=mode)


@router.post("/{quiz_id}/attachments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, summary="Upload attachment for quiz")
def api_upload_quiz_attachment(
    quiz_id: uuid.UUID,
    quiz_question_id: Optional[uuid.UUID] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Uploads an image, diagram, or attachment for a quiz or specific question.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    content = file.file.read()
    file_size = len(content)
    file_name = file.filename or "attachment"
    file_type = file.content_type or "application/octet-stream"

    # Enforce file size limit (10MB)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds maximum allowed size of 10MB.")

    # Validate file extension
    allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf"}
    ext = Path(file_name).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File extension {ext} not permitted.")

    uploads_dir = Path("uploads/quiz_attachments")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file_name}"
    file_path = str(uploads_dir / stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    att = QuizAttachment(
        quiz_id=quiz_id,
        quiz_question_id=quiz_question_id,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size,
        uploaded_by=admin.id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    return {
        "success": True,
        "message": "Attachment uploaded successfully.",
        "attachment": {
            "id": str(att.id),
            "file_name": att.file_name,
            "file_path": att.file_path,
            "file_type": att.file_type,
            "file_size_bytes": att.file_size_bytes,
            "url": f"/api/v1/uploads/quiz_attachments/{stored_name}",
        },
    }
