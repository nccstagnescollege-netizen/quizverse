import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.models.question_import_export import QuestionImportJob, QuestionImportRow
from backend.app.services.rbac_service import get_current_admin, require_permission, has_permission
from backend.app.services.question_import_export_service import (
    generate_csv_template,
    generate_xlsx_template,
    parse_and_validate_file,
    execute_import_job,
    generate_error_report_csv,
    export_questions_service,
    MAX_IMPORT_FILE_SIZE_BYTES,
)
from backend.app.schemas.question_import_export import (
    ImportJobSummaryResponse,
    ImportRowResponse,
    ImportJobPreviewResponse,
    ImportConfirmRequest,
    ExportQuestionsRequest,
)

router = APIRouter()


# ==============================================================================
# TEMPLATE DOWNLOADS
# ==============================================================================

@router.get("/import/template/csv", summary="Download CSV question import template")
async def download_csv_template(
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Download standardized CSV template with instructions and multi-type question examples."""
    csv_content = generate_csv_template()
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="QUIZVERSE_Question_Import_Template.csv"'},
    )


@router.get("/import/template/xlsx", summary="Download Excel question import template")
async def download_xlsx_template(
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Download standardized Excel .xlsx template with formatted columns and Instructions sheet."""
    xlsx_bytes = generate_xlsx_template()
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="QUIZVERSE_Question_Import_Template.xlsx"'},
    )


# ==============================================================================
# BULK IMPORT UPLOAD & VALIDATION
# ==============================================================================

@router.post("/import/upload", response_model=ImportJobSummaryResponse, summary="Upload question file for validation")
async def upload_question_import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """
    Upload an Excel or CSV file.
    Validates file format, size, checksum, column schema, question types, and academic hierarchy.
    Generates row-level validation reports before any database commit occurs.
    """
    filename = file.filename or "import.csv"
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in ("csv", "xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only Microsoft Excel (.xlsx) and CSV (.csv) files are permitted.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_IMPORT_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed upload size of {MAX_IMPORT_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Compute SHA-256 checksum
    file_checksum = hashlib.sha256(file_bytes).hexdigest()

    # Create staging job
    job = QuestionImportJob(
        id=uuid.uuid4(),
        uploaded_by=current_admin.id,
        file_name=filename,
        file_format=ext,
        file_size_bytes=len(file_bytes),
        file_checksum=file_checksum,
        status="uploaded",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run parser and validation engine
    validated_job = parse_and_validate_file(
        job_id=job.id,
        file_bytes=file_bytes,
        file_name=filename,
        admin=current_admin,
        db=db,
    )

    return validated_job


@router.get("/import/{job_id}/status", response_model=ImportJobSummaryResponse, summary="Get import job status")
async def get_import_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Get the current state and metrics for an import job."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view another administrator's import job.")

    return job


@router.get("/import/{job_id}/preview", response_model=ImportJobPreviewResponse, summary="Get import rows preview")
async def get_import_job_preview(
    job_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, description="valid, invalid, warning, duplicate"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Retrieve row-by-row validation results, questions, and detected warnings/errors."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="You do not have permission to inspect this import job.")

    query = db.query(QuestionImportRow).filter(QuestionImportRow.job_id == job_id)
    if status_filter:
        query = query.filter(QuestionImportRow.validation_status == status_filter)

    total_rows = query.count()
    rows = query.order_by(QuestionImportRow.row_number).offset(offset).limit(limit).all()

    return ImportJobPreviewResponse(
        job=job,
        rows=rows,
        total_rows_previewed=total_rows,
    )


@router.get("/import/{job_id}/errors", response_model=List[ImportRowResponse], summary="Get import errors only")
async def get_import_job_errors(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Retrieve only rows containing validation errors or duplicates."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    rows = db.query(QuestionImportRow).filter(
        QuestionImportRow.job_id == job_id,
        QuestionImportRow.validation_status.in_(["invalid", "duplicate"]),
    ).order_by(QuestionImportRow.row_number).all()

    return rows


@router.get("/import/{job_id}/error-report", summary="Download CSV error report")
async def download_error_report(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Download an actionable CSV error report mapping row numbers to exact validation errors."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    csv_data = generate_error_report_csv(job_id=job.id, db=db)
    return Response(
        content=csv_data.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="Import_Errors_{job.file_name}.csv"'},
    )


# ==============================================================================
# IMPORT CONFIRMATION & CANCELLATION
# ==============================================================================

@router.post("/import/{job_id}/confirm", response_model=ImportJobSummaryResponse, summary="Confirm and commit import job")
async def confirm_import_job(
    job_id: uuid.UUID,
    payload: ImportConfirmRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """
    Explicitly commit validated rows to the Question Bank under chosen policy (import_valid or all_or_nothing).
    """
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="You are not authorized to confirm this import job.")

    updated_job = execute_import_job(
        job_id=job.id,
        policy=payload.policy,
        duplicate_strategy=payload.duplicate_strategy,
        admin=current_admin,
        db=db,
    )
    return updated_job


@router.post("/import/{job_id}/cancel", response_model=ImportJobSummaryResponse, summary="Cancel an import job")
async def cancel_import_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Cancel a validated import job before confirmation."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    if job.status in ("completed", "importing"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a job in status '{job.status}'.")

    job.status = "cancelled"
    db.commit()
    db.refresh(job)
    return job


# ==============================================================================
# IMPORT HISTORY
# ==============================================================================

@router.get("/import/history", response_model=List[ImportJobSummaryResponse], summary="List import job history")
async def get_import_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """
    List historical import jobs.
    Super Admin views all jobs; User Admin views only their own jobs.
    """
    query = db.query(QuestionImportJob)
    if not current_admin.is_super_admin:
        query = query.filter(QuestionImportJob.uploaded_by == current_admin.id)

    jobs = query.order_by(desc(QuestionImportJob.created_at)).offset(offset).limit(limit).all()
    return jobs


@router.get("/import/history/{job_id}", response_model=ImportJobSummaryResponse, summary="Get historical import job detail")
async def get_import_history_detail(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("question.import")),
):
    """Retrieve full metadata for a specific historical import job."""
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if not current_admin.is_super_admin and job.uploaded_by != current_admin.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    return job


# ==============================================================================
# BULK EXPORT
# ==============================================================================

@router.post("/export", summary="Export questions to Excel or CSV")
async def export_questions_endpoint(
    payload: ExportQuestionsRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Export questions with academic filters, RBAC scoping, answer-key security, and formula injection protection.
    Question-only export excludes answers and explanations.
    Administrative answer-key export requires 'question.answer.view'.
    """
    filters = {
        "subject_id": payload.subject_id,
        "topic_id": payload.topic_id,
        "question_type": payload.question_type,
        "difficulty": payload.difficulty,
        "status": payload.status,
    }

    file_bytes, filename, media_type = export_questions_service(
        filters=filters,
        export_format=payload.export_format,
        export_mode=payload.export_mode,
        admin=current_admin,
        db=db,
    )

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
