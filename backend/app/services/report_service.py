import csv
import io
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from backend.app.models.auth_rbac import Admin
from backend.app.models.analytics import ReportExport
from backend.app.models.quiz import Quiz, QuizQuestion
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.results import ExaminationResult, QuestionEvaluation
from backend.app.models.question_bank import Question
from backend.app.models.academic import Programme, Subject, Semester
from backend.app.schemas.analytics import ReportGenerateRequest, ReportExportItem
from backend.app.services.analytics_service import is_super_admin, _get_authorized_quiz_ids, _apply_quiz_filter

# Report storage directory
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "reports"))
os.makedirs(REPORTS_DIR, exist_ok=True)


def sanitize_csv_cell(val: Any) -> str:
    """Protects against spreadsheet formula-injection (CSV Injection / CWE-1236)."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


class ReportService:

    @staticmethod
    def generate_report(
        db: Session,
        admin: Admin,
        req: ReportGenerateRequest,
    ) -> ReportExportItem:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)
        filters = req.filters or {}

        # 1. Gather report data
        headers, rows = ReportService._fetch_report_data(db, admin, req.report_type, auth_quiz_ids, filters)

        # 2. Build file according to format
        export_id = uuid.uuid4()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_type = req.report_type.replace("_", "-")

        if req.export_format.lower() == "csv":
            ext = "csv"
            file_name = f"quizverse_{safe_type}_{timestamp_str}.csv"
            file_path = os.path.join(REPORTS_DIR, f"{export_id}_{file_name}")
            ReportService._write_csv(headers, rows, file_path)

        elif req.export_format.lower() in ["xlsx", "excel"]:
            ext = "xlsx"
            file_name = f"quizverse_{safe_type}_{timestamp_str}.xlsx"
            file_path = os.path.join(REPORTS_DIR, f"{export_id}_{file_name}")
            ReportService._write_excel(headers, rows, file_path, req.report_type)

        elif req.export_format.lower() == "pdf":
            ext = "pdf"
            file_name = f"quizverse_{safe_type}_{timestamp_str}.pdf"
            file_path = os.path.join(REPORTS_DIR, f"{export_id}_{file_name}")
            ReportService._write_pdf(headers, rows, file_path, req.report_type, admin)

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format '{req.export_format}'")

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # 3. Create database tracking record
        export_rec = ReportExport(
            id=export_id,
            admin_id=admin.id,
            report_type=req.report_type,
            export_format=ext,
            status="completed",
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            download_url=f"/api/v1/analytics/reports/{export_id}/download",
            filter_params=filters,
            row_count=len(rows),
            expires_at=expires_at,
        )
        db.add(export_rec)
        db.commit()
        db.refresh(export_rec)

        return ReportExportItem.model_validate(export_rec)

    @staticmethod
    def _fetch_report_data(
        db: Session,
        admin: Admin,
        report_type: str,
        auth_quiz_ids: Optional[List[uuid.UUID]],
        filters: Dict[str, Any],
    ) -> Tuple[List[str], List[List[Any]]]:
        specific_quiz_id = uuid.UUID(filters["quiz_id"]) if filters.get("quiz_id") else None

        # -------------------------------------------------------------
        # A. Examination Summary Report
        # -------------------------------------------------------------
        if report_type == "examination_summary":
            q_query = db.query(Quiz).options(joinedload(Quiz.subject), joinedload(Quiz.configuration)).order_by(Quiz.created_at.desc())
            q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, specific_quiz_id)
            quizzes = q_query.all()

            headers = [
                "Quiz ID",
                "Examination Title",
                "Status",
                "Subject",
                "Duration (Mins)",
                "Total Marks",
                "Passing %",
                "Registered Participants",
                "Attempts Started",
                "Attempts Submitted",
                "Completion Rate",
                "Created Date",
            ]
            rows = []
            for q in quizzes:
                subj_name = q.subject.subject_name if q.subject else "General"
                part_cnt = db.query(func.count(QuizParticipant.id)).filter(QuizParticipant.quiz_id == q.id).scalar() or 0
                att_started = db.query(func.count(ExaminationAttempt.id)).filter(ExaminationAttempt.quiz_id == q.id).scalar() or 0
                att_sub = db.query(func.count(ExaminationAttempt.id)).filter(
                    ExaminationAttempt.quiz_id == q.id, ExaminationAttempt.status == "submitted"
                ).scalar() or 0
                comp_rate = f"{round((att_sub / att_started * 100.0), 1)}%" if att_started > 0 else "0.0%"

                rows.append([
                    str(q.id)[:8],
                    q.title,
                    q.status.capitalize(),
                    subj_name,
                    q.duration_minutes or 60,
                    float(q.total_marks or 0.0),
                    f"{float(q.passing_percentage or 50.0)}%",
                    part_cnt,
                    att_started,
                    att_sub,
                    comp_rate,
                    q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else "",
                ])
            return headers, rows

        # -------------------------------------------------------------
        # B. Student Performance Report
        # -------------------------------------------------------------
        elif report_type == "student_performance":
            res_query = db.query(ExaminationResult).join(Quiz, ExaminationResult.quiz_id == Quiz.id).options(
                joinedload(ExaminationResult.student),
                joinedload(ExaminationResult.quiz),
            ).filter(ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]))
            res_query = _apply_quiz_filter(res_query, ExaminationResult.quiz_id, auth_quiz_ids, specific_quiz_id)
            results = res_query.all()

            headers = [
                "Result ID",
                "Student Name",
                "Register Number",
                "Email",
                "Examination Title",
                "Marks Obtained",
                "Maximum Marks",
                "Percentage",
                "Pass / Fail",
                "Evaluation Status",
                "Approval",
                "Evaluation Date",
            ]
            rows = []
            for r in results:
                st = r.student
                s_name = st.full_name if st else "Anonymous Candidate"
                s_reg = (st.profile.student_identifier if (st and getattr(st, "profile", None)) else None) or getattr(st, "register_number", "N/A")
                s_email = st.email if st else "N/A"
                q_title = r.quiz.title if r.quiz else "Examination"

                rows.append([
                    str(r.id)[:8],
                    s_name,
                    s_reg,
                    s_email,
                    q_title,
                    float(getattr(r, "score", None) or getattr(r, "total_marks_obtained", None) or 0.0),
                    float(r.maximum_marks or 100.0),
                    f"{float(r.percentage or 0.0):.1f}%",
                    "PASSED" if r.is_passed else "FAILED",
                    r.evaluation_status,
                    "Approved" if r.is_approved else "Pending Approval",
                    r.calculated_at.strftime("%Y-%m-%d %H:%M") if getattr(r, "calculated_at", None) else "",
                ])
            return headers, rows

        # -------------------------------------------------------------
        # C. Academic Performance Report
        # -------------------------------------------------------------
        elif report_type == "academic_performance":
            res_query = db.query(ExaminationResult).join(Quiz, ExaminationResult.quiz_id == Quiz.id).options(
                joinedload(ExaminationResult.quiz).joinedload(Quiz.programme),
                joinedload(ExaminationResult.quiz).joinedload(Quiz.subject),
                joinedload(ExaminationResult.quiz).joinedload(Quiz.semester),
            ).filter(ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]))
            res_query = _apply_quiz_filter(res_query, ExaminationResult.quiz_id, auth_quiz_ids, specific_quiz_id)
            results = res_query.all()

            headers = [
                "Programme",
                "Subject Code",
                "Subject Name",
                "Semester",
                "Candidates Evaluated",
                "Passed",
                "Failed",
                "Average Score (%)",
                "Pass Rate (%)",
            ]
            agg = {}
            for r in results:
                p_name = (getattr(r.quiz.programme, "name", None) or getattr(r.quiz.programme, "programme_name", None)) if r.quiz and r.quiz.programme else "General Programme"
                s_code = r.quiz.subject.subject_code if r.quiz and r.quiz.subject else "GEN"
                s_name = r.quiz.subject.subject_name if r.quiz and r.quiz.subject else "General Subject"
                sem = r.quiz.semester.semester_name if r.quiz and r.quiz.semester else "Semester I"
                key = (p_name, s_code, s_name, sem)

                if key not in agg:
                    agg[key] = {"scores": [], "passed": 0}
                agg[key]["scores"].append(float(r.percentage or 0.0))
                if r.is_passed:
                    agg[key]["passed"] += 1

            rows = []
            for (p_name, s_code, s_name, sem), d in agg.items():
                total_c = len(d["scores"])
                avg_pct = sum(d["scores"]) / total_c if total_c > 0 else 0.0
                pass_rate = (d["passed"] / total_c * 100.0) if total_c > 0 else 0.0
                failed_c = total_c - d["passed"]
                rows.append([
                    p_name,
                    s_code,
                    s_name,
                    sem,
                    total_c,
                    d["passed"],
                    failed_c,
                    f"{avg_pct:.1f}%",
                    f"{pass_rate:.1f}%",
                ])
            return headers, rows

        # -------------------------------------------------------------
        # D. Evaluation & Grading Summary Report
        # -------------------------------------------------------------
        elif report_type == "evaluation_summary":
            q_query = db.query(Quiz).order_by(Quiz.created_at.desc())
            q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, specific_quiz_id)
            quizzes = q_query.all()

            headers = [
                "Quiz Title",
                "Status",
                "Total Evaluations",
                "Auto Objective",
                "Manual Pending",
                "Manual Completed",
                "Flagged Moderation",
                "Results Approved",
                "Results Published",
            ]
            rows = []
            for q in quizzes:
                evals = (
                    db.query(QuestionEvaluation)
                    .join(QuizQuestion, QuestionEvaluation.quiz_question_id == QuizQuestion.id)
                    .filter(QuizQuestion.quiz_id == q.id)
                    .all()
                )
                auto_cnt = sum(1 for e in evals if e.evaluation_type == "auto_objective")
                man_pending = sum(1 for e in evals if e.evaluation_type in ["manual_grading", "manual_descriptive"] and (e.marks_awarded is None or e.evaluator_id is None))
                man_comp = sum(1 for e in evals if e.evaluation_type in ["manual_grading", "manual_descriptive"] and e.marks_awarded is not None)
                mod_cnt = sum(1 for e in evals if getattr(e, "is_flagged_for_moderation", False))

                results = db.query(ExaminationResult).filter(ExaminationResult.quiz_id == q.id).all()
                approved_cnt = sum(1 for r in results if r.is_approved)
                pub_cnt = sum(1 for r in results if r.is_published or r.evaluation_status == "RESULT_PUBLISHED")

                rows.append([
                    q.title,
                    q.status.capitalize(),
                    len(evals),
                    auto_cnt,
                    man_pending,
                    man_comp,
                    mod_cnt,
                    approved_cnt,
                    pub_cnt,
                ])
            return headers, rows

        # -------------------------------------------------------------
        # E. Question Bank Report
        # -------------------------------------------------------------
        elif report_type == "question_bank":
            q_query = db.query(Question).options(joinedload(Question.subject)).order_by(Question.created_at.desc()).limit(200)
            questions = q_query.all()

            headers = [
                "Question ID",
                "Question Text Snippet",
                "Question Type",
                "Difficulty",
                "Subject",
                "Status",
                "Times Answered",
                "Created Date",
            ]
            rows = []
            for q in questions:
                ans_cnt = db.query(func.count(AttemptAnswer.id)).filter(AttemptAnswer.quiz_question_id == q.id).scalar() or 0
                s_name = q.subject.subject_name if q.subject else "General"
                snippet = (q.question_text[:80] + "...") if len(q.question_text) > 80 else q.question_text

                rows.append([
                    str(q.id)[:8],
                    snippet,
                    q.question_type,
                    (getattr(q, "difficulty", None) or getattr(q, "difficulty_level", None) or "medium").capitalize(),
                    s_name,
                    q.status.capitalize(),
                    ans_cnt,
                    q.created_at.strftime("%Y-%m-%d") if q.created_at else "",
                ])
            return headers, rows

        # -------------------------------------------------------------
        # F. Examination Activity Report
        # -------------------------------------------------------------
        else:
            headers = ["Date", "Quizzes Created", "Registrations", "Attempts Started", "Attempts Submitted", "Results Finalized"]
            now = datetime.now(timezone.utc)
            rows = []
            for i in range(14, -1, -1):
                d = (now - timedelta(days=i)).date()
                d_str = d.strftime("%Y-%m-%d")

                qz_c = db.query(func.count(Quiz.id)).filter(func.date(Quiz.created_at) == d).scalar() or 0
                reg_c = db.query(func.count(QuizParticipant.id)).filter(func.date(QuizParticipant.registered_at) == d).scalar() or 0
                att_s = db.query(func.count(ExaminationAttempt.id)).filter(func.date(ExaminationAttempt.started_at) == d).scalar() or 0
                att_sub = db.query(func.count(ExaminationAttempt.id)).filter(
                    func.date(ExaminationAttempt.started_at) == d, ExaminationAttempt.status == "submitted"
                ).scalar() or 0
                res_f = db.query(func.count(ExaminationResult.id)).filter(
                    func.date(ExaminationResult.calculated_at) == d,
                    ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"])
                ).scalar() or 0

                rows.append([d_str, qz_c, reg_c, att_s, att_sub, res_f])
            return headers, rows

    @staticmethod
    def _write_csv(headers: List[str], rows: List[List[Any]], file_path: str) -> None:
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([sanitize_csv_cell(h) for h in headers])
            for r in rows:
                writer.writerow([sanitize_csv_cell(c) for c in r])

    @staticmethod
    def _write_excel(headers: List[str], rows: List[List[Any]], file_path: str, report_type: str) -> None:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report_type[:31].replace("_", " ").title()

        # Header Title Banner
        ws.merge_cells("A1:E1")
        title_cell = ws["A1"]
        title_cell.value = f"QUIZVERSE — {report_type.replace('_', ' ').upper()} REPORT"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="left", vertical="center")

        ws["A2"] = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Total Records: {len(rows)}"
        ws["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")

        # Table Column Headers
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        border_side = Side(style="thin", color="CBD5E1")
        cell_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)

        row_idx = 4
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cell_border

        # Data Rows
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        row_idx = 5
        for r in rows:
            for col_idx, val in enumerate(r, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = Font(name="Calibri", size=10)
                cell.border = cell_border
                if row_idx % 2 == 0:
                    cell.fill = alt_fill
            row_idx += 1

        # Adjust Column Widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(file_path)

    @staticmethod
    def _write_pdf(headers: List[str], rows: List[List[Any]], file_path: str, report_type: str, admin: Admin) -> None:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        # Landscape layout for multi-column data tables
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(letter),
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
        )
        meta_style = ParagraphStyle(
            "ReportMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )

        story = []
        story.append(Paragraph(f"QUIZVERSE — {report_type.replace('_', ' ').upper()} REPORT", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Administrator: {admin.full_name or admin.email} | Scope: Authorized Platform Records",
            meta_style,
        ))
        story.append(Spacer(1, 14))

        # Format rows with Paragraphs for wrapping
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
        hdr_style = ParagraphStyle(
            "TableHdr",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        table_data = [[Paragraph(str(h), hdr_style) for h in headers]]
        for r in rows[:100]:  # Limit top 100 rows per single PDF export to prevent overflow
            table_data.append([Paragraph(str(c), cell_style) for c in r])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ]))

        story.append(table)
        doc.build(story)

    @staticmethod
    def list_reports(db: Session, admin: Admin) -> List[ReportExportItem]:
        q = db.query(ReportExport).order_by(ReportExport.created_at.desc())
        if not is_super_admin(admin):
            q = q.filter(ReportExport.admin_id == admin.id)
        return [ReportExportItem.model_validate(r) for r in q.limit(50).all()]

    @staticmethod
    def get_report_download(db: Session, admin: Admin, export_id: uuid.UUID) -> Tuple[str, str, str]:
        rec = db.query(ReportExport).filter(ReportExport.id == export_id).first()
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report export not found")

        if not is_super_admin(admin) and rec.admin_id != admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to download this report")

        if not rec.file_path or not os.path.exists(rec.file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file has expired or is unavailable")

        # Media types
        media_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        }
        media_type = media_types.get(rec.export_format.lower(), "application/octet-stream")
        return rec.file_path, rec.file_name, media_type
