import io
import re
import csv
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_, func
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, AdminAcademicScope
from backend.app.models.academic import (
    Institution,
    Programme,
    Curriculum,
    AcademicSession,
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
)
from backend.app.models.question_import_export import (
    QuestionImportJob,
    QuestionImportRow,
    QuestionExportJob,
)
from backend.app.services.audit_service import log_audit_event
from backend.app.services.rbac_service import has_permission, get_admin_effective_permissions

# Configuration constants
MAX_IMPORT_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMPORT_ROWS = 1000
TEMPLATE_VERSION = "v1.0"

TEMPLATE_COLUMNS = [
    "institution_code",
    "programme_code",
    "curriculum_code",
    "academic_session",
    "semester_code",
    "subject_code",
    "unit_number",
    "chapter_number",
    "topic_code",
    "question_external_id",
    "question_text",
    "question_type",
    "difficulty",
    "marks",
    "negative_marks",
    "explanation",
    "tags",
    "status",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "correct_answers",
]

# Formula injection prefixes
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell_for_export(val: Any) -> Any:
    """Neutralize formula injection by prefixing triggering symbols with a single quote."""
    if val is None:
        return ""
    str_val = str(val)
    if str_val.startswith(FORMULA_PREFIXES):
        return f"'{str_val}"
    return str_val


def normalize_text(text_val: Optional[str]) -> str:
    """Normalize text for consistent duplicate matching."""
    if not text_val:
        return ""
    text_val = text_val.lower().strip()
    return re.sub(r"\s+", " ", text_val)


# ==============================================================================
# TEMPLATE GENERATION
# ==============================================================================

SAMPLE_ROWS = [
    {
        "institution_code": "STAGNES",
        "programme_code": "BCA",
        "curriculum_code": "V2026.1",
        "academic_session": "2026-2027",
        "semester_code": "SEM1",
        "subject_code": "CS101",
        "unit_number": 1,
        "chapter_number": 1,
        "topic_code": "DS-TIME-01",
        "question_external_id": "CS101-Q001",
        "question_text": "What is the worst-case time complexity of lookup in a standard Hash Table?",
        "question_type": "single_choice",
        "difficulty": "medium",
        "marks": 2.0,
        "negative_marks": 0.5,
        "explanation": "In the worst case with hash collisions, lookup degrades to O(N) linear time.",
        "tags": "hash table, time complexity, algorithms",
        "status": "draft",
        "option_a": "O(1)",
        "option_b": "O(log N)",
        "option_c": "O(N)",
        "option_d": "O(N log N)",
        "option_e": "",
        "correct_answers": "C",
    },
    {
        "institution_code": "STAGNES",
        "programme_code": "BCA",
        "curriculum_code": "V2026.1",
        "academic_session": "2026-2027",
        "semester_code": "SEM1",
        "subject_code": "CS101",
        "unit_number": 1,
        "chapter_number": 1,
        "topic_code": "DS-TREE-01",
        "question_external_id": "CS101-Q002",
        "question_text": "Which of the following are self-balancing Binary Search Trees? (Select all that apply)",
        "question_type": "multiple_choice",
        "difficulty": "hard",
        "marks": 3.0,
        "negative_marks": 1.0,
        "explanation": "AVL Trees and Red-Black Trees automatically maintain balance upon insertions.",
        "tags": "trees, bst, data structures",
        "status": "draft",
        "option_a": "AVL Tree",
        "option_b": "Standard BST",
        "option_c": "Red-Black Tree",
        "option_d": "Splay Tree",
        "option_e": "",
        "correct_answers": "A,C,D",
    },
    {
        "institution_code": "STAGNES",
        "programme_code": "BCA",
        "curriculum_code": "V2026.1",
        "academic_session": "2026-2027",
        "semester_code": "SEM1",
        "subject_code": "CS101",
        "unit_number": 1,
        "chapter_number": 2,
        "topic_code": "DS-STACK-01",
        "question_external_id": "CS101-Q003",
        "question_text": "A Queue data structure strictly follows the Last-In-First-Out (LIFO) order.",
        "question_type": "true_false",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "explanation": "False. A Queue follows First-In-First-Out (FIFO). A Stack follows LIFO.",
        "tags": "queue, stack, fundamentals",
        "status": "draft",
        "option_a": "True",
        "option_b": "False",
        "option_c": "",
        "option_d": "",
        "option_e": "",
        "correct_answers": "FALSE",
    },
    {
        "institution_code": "STAGNES",
        "programme_code": "BCA",
        "curriculum_code": "V2026.1",
        "academic_session": "2026-2027",
        "semester_code": "SEM1",
        "subject_code": "CS101",
        "unit_number": 2,
        "chapter_number": 1,
        "topic_code": "ALG-REC-01",
        "question_external_id": "CS101-Q004",
        "question_text": "Name the condition required in a recursive function to terminate recursive calls.",
        "question_type": "short_answer",
        "difficulty": "medium",
        "marks": 2.0,
        "negative_marks": 0.0,
        "explanation": "A base case or terminating condition is necessary to stop recursion.",
        "tags": "recursion, programming concepts",
        "status": "draft",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "option_e": "",
        "correct_answers": "Base Case|base case|terminating condition|base condition",
    },
]


def generate_csv_template() -> str:
    """Generate a CSV question import template with header and sample rows."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TEMPLATE_COLUMNS)
    writer.writeheader()
    for row in SAMPLE_ROWS:
        writer.writerow(row)
    return output.getvalue()


def generate_xlsx_template() -> bytes:
    """Generate an Excel .xlsx question import template with formatted columns and instructions sheet."""
    wb = openpyxl.Workbook()

    # Sheet 1: Template
    ws = wb.active
    ws.title = "Question Import"

    # Header styling
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy Blue
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border_thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    ws.append(TEMPLATE_COLUMNS)
    for col_idx in range(1, len(TEMPLATE_COLUMNS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border_thin

    # Append sample rows
    for row_data in SAMPLE_ROWS:
        ws.append([row_data.get(col, "") for col in TEMPLATE_COLUMNS])

    # Auto-fit column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    # Sheet 2: Instructions
    ws_inst = wb.create_sheet(title="Instructions")
    instructions = [
        ["QUIZVERSE QUESTION BANK IMPORT GUIDE (Template Version: v1.0)"],
        [""],
        ["Column Name", "Required?", "Accepted Values / Format", "Description"],
        ["institution_code", "Optional", "Text (e.g., STAGNES)", "Code of the institution"],
        ["programme_code", "Optional", "Text (e.g., BCA)", "Programme code"],
        ["curriculum_code", "Optional", "Text (e.g., V2026.1)", "Curriculum version code"],
        ["academic_session", "Optional", "Text (e.g., 2026-2027)", "Academic session year"],
        ["semester_code", "Optional", "Text (e.g., SEM1, 1)", "Semester identifier"],
        ["subject_code", "REQUIRED", "Valid Subject Code (e.g., CS101)", "Must exist in the academic hierarchy"],
        ["unit_number", "Optional", "Integer (1, 2, 3...)", "Unit number within the subject"],
        ["chapter_number", "Optional", "Integer (1, 2, 3...)", "Chapter number within the unit"],
        ["topic_code", "REQUIRED", "Valid Topic Code or Name", "Must belong to the resolved subject/chapter"],
        ["question_external_id", "Optional", "Unique String (e.g., CS101-Q001)", "Enables reliable updates and duplicate tracking"],
        ["question_text", "REQUIRED", "Text", "The examination question text"],
        ["question_type", "REQUIRED", "single_choice, multiple_choice, true_false, short_answer", "Supported question types"],
        ["difficulty", "REQUIRED", "easy, medium, hard", "Question difficulty tier (default: medium)"],
        ["marks", "REQUIRED", "Decimal >= 0 (e.g., 1.0, 2.5)", "Marks awarded for correct answer"],
        ["negative_marks", "REQUIRED", "Decimal >= 0 (e.g., 0.0, 0.5)", "Penalty deducted for wrong answer"],
        ["explanation", "Optional", "Text", "Explanation shown during post-exam review"],
        ["tags", "Optional", "Comma-separated text", "Search and categorization tags"],
        ["status", "Optional", "draft, pending_review, approved", "Initial question status (default: draft)"],
        ["option_a to option_e", "Type-Dependent", "Text", "Option choices for choice-based questions"],
        ["correct_answers", "REQUIRED", "A | A,C | TRUE/FALSE | answer1|answer2", "Correct answer specification depending on type"],
        [""],
        ["CORRECT ANSWER FORMATTING RULES:"],
        ["1. Single Choice: Use the option letter, e.g. 'A' or 'B'."],
        ["2. Multiple Choice: Use comma-separated option letters, e.g. 'A,C' or 'A,B,D'."],
        ["3. True/False: Use 'TRUE' or 'FALSE' (case-insensitive)."],
        ["4. Short Answer: Use pipe-separated accepted phrases, e.g. 'Base Case|base case|terminating condition'."],
    ]

    for row in instructions:
        ws_inst.append(row)

    ws_inst.cell(row=1, column=1).font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    for r in range(3, 24):
        for c in range(1, 5):
            ws_inst.cell(row=r, column=c).border = border_thin
            if r == 3:
                ws_inst.cell(row=r, column=c).font = Font(bold=True)
                ws_inst.cell(row=r, column=c).fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    for col in ws_inst.columns:
        col_letter = get_column_letter(col[0].column)
        ws_inst.column_dimensions[col_letter].width = 28

    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()


# ==============================================================================
# VALIDATION ENGINE
# ==============================================================================

def validate_question_row(
    row_num: int,
    raw_row: Dict[str, Any],
    db: Session,
    admin: Admin,
    academic_cache: Dict[str, Any],
    existing_external_ids: set,
    existing_texts_by_subject: Dict[uuid.UUID, set],
) -> Dict[str, Any]:
    """
    Validate a single imported row thoroughly against:
    - Required field existence
    - Question type constraints
    - Option identifiers & correct answers
    - Academic hierarchy resolution & user admin scope
    - Duplicate detection
    """
    errors: List[Dict[str, str]] = []
    warnings: List[str] = []

    # 1. Clean and normalize inputs
    def get_str(k: str) -> str:
        val = raw_row.get(k)
        return str(val).strip() if val is not None else ""

    q_text = get_str("question_text")
    q_type = get_str("question_type").lower()
    subject_code = get_str("subject_code")
    topic_identifier = get_str("topic_code")
    external_id = get_str("question_external_id")
    diff_val = get_str("difficulty").lower() or "medium"
    status_val = get_str("status").lower() or "draft"
    correct_raw = get_str("correct_answers")

    marks_str = get_str("marks") or "1.0"
    neg_marks_str = get_str("negative_marks") or "0.0"

    # Validate Question Text
    if not q_text:
        errors.append({"column": "question_text", "message": "Missing question text."})

    # Validate Question Type
    valid_types = {"single_choice", "multiple_choice", "true_false", "short_answer"}
    if q_type not in valid_types:
        errors.append({"column": "question_type", "message": f"Question type '{q_type}' is not supported. Must be one of: {', '.join(sorted(valid_types))}."})

    # Validate Difficulty
    valid_diffs = {"easy", "medium", "hard"}
    if diff_val not in valid_diffs:
        errors.append({"column": "difficulty", "message": f"Difficulty '{diff_val}' is invalid. Must be easy, medium, or hard."})

    # Validate Marks & Negative Marks
    try:
        marks = float(marks_str)
        if marks < 0:
            errors.append({"column": "marks", "message": "Marks cannot be negative."})
    except ValueError:
        errors.append({"column": "marks", "message": f"Marks '{marks_str}' must be a valid number."})
        marks = 1.0

    try:
        neg_marks = float(neg_marks_str)
        if neg_marks < 0:
            errors.append({"column": "negative_marks", "message": "Negative marks cannot be negative."})
    except ValueError:
        errors.append({"column": "negative_marks", "message": f"Negative marks '{neg_marks_str}' must be a valid number."})
        neg_marks = 0.0

    # 2. Academic Hierarchy Resolution
    subject = None
    topic = None

    if not subject_code:
        errors.append({"column": "subject_code", "message": "Subject code is mandatory for academic classification."})
    else:
        subject = academic_cache["subjects_by_code"].get(subject_code.upper())
        if not subject:
            errors.append({"column": "subject_code", "message": f"Subject code '{subject_code}' could not be found."})
        else:
            # Check User Admin scope restriction
            if not admin.is_super_admin:
                scoped_subjects = academic_cache["admin_scoped_subjects"]
                if subject.id not in scoped_subjects:
                    errors.append({"column": "subject_code", "message": f"You do not have administrative scope access to subject '{subject_code}'."})

    if subject and not topic_identifier:
        errors.append({"column": "topic_code", "message": "Topic code or topic name is required."})
    elif subject and topic_identifier:
        # Match topic by topic_code or topic_name belonging to this subject
        topic_key = f"{subject.id}:{topic_identifier.upper()}"
        topic = academic_cache["topics_by_subject_and_key"].get(topic_key)
        if not topic:
            errors.append({"column": "topic_code", "message": f"Topic '{topic_identifier}' does not belong to subject '{subject_code}'."})

    # 3. Question Options & Correct Answers Validation
    options_data: List[Dict[str, Any]] = []
    short_answer_cfg: Optional[Dict[str, Any]] = None

    if q_type in ("single_choice", "multiple_choice"):
        raw_options = [
            ("A", get_str("option_a")),
            ("B", get_str("option_b")),
            ("C", get_str("option_c")),
            ("D", get_str("option_d")),
            ("E", get_str("option_e")),
        ]
        non_empty = [(letter, opt_text) for letter, opt_text in raw_options if opt_text]

        if len(non_empty) < 2:
            errors.append({"column": "options", "message": f"{q_type.replace('_', ' ').title()} requires at least two non-empty options."})

        # Check duplicate option text
        seen_texts = set()
        for letter, opt_text in non_empty:
            norm_opt = opt_text.strip().lower()
            if norm_opt in seen_texts:
                warnings.append(f"Option {letter} contains duplicate text to an earlier option.")
            seen_texts.add(norm_opt)

        if not correct_raw:
            errors.append({"column": "correct_answers", "message": "Correct answers must be specified."})
        else:
            # Parse correct letters
            valid_letters = {letter for letter, _ in non_empty}
            entered_letters = [c.strip().upper() for c in correct_raw.split(",") if c.strip()]

            if q_type == "single_choice":
                if len(entered_letters) != 1:
                    errors.append({"column": "correct_answers", "message": f"Single choice question must have exactly one correct option. Found: '{correct_raw}'."})
                elif entered_letters[0] not in valid_letters:
                    errors.append({"column": "correct_answers", "message": f"Specified correct option '{entered_letters[0]}' does not exist among non-empty options ({', '.join(sorted(valid_letters))})."})
                else:
                    for idx, (letter, opt_text) in enumerate(non_empty):
                        options_data.append({
                            "option_text": opt_text,
                            "option_order": idx + 1,
                            "is_correct": (letter == entered_letters[0]),
                        })
            elif q_type == "multiple_choice":
                # Check duplicates in entered answers
                if len(entered_letters) != len(set(entered_letters)):
                    warnings.append("Duplicate correct answer identifiers were removed.")
                    entered_letters = list(dict.fromkeys(entered_letters))

                invalid_choices = [c for c in entered_letters if c not in valid_letters]
                if invalid_choices:
                    errors.append({"column": "correct_answers", "message": f"Correct option(s) {invalid_choices} do not exist among non-empty options."})
                elif len(entered_letters) < 1:
                    errors.append({"column": "correct_answers", "message": "Multiple choice questions require at least one valid correct option."})
                else:
                    for idx, (letter, opt_text) in enumerate(non_empty):
                        options_data.append({
                            "option_text": opt_text,
                            "option_order": idx + 1,
                            "is_correct": (letter in entered_letters),
                        })

    elif q_type == "true_false":
        # Normalize truth value
        norm_ans = correct_raw.strip().upper()
        if norm_ans in ("TRUE", "T", "1", "YES"):
            tf_bool = True
        elif norm_ans in ("FALSE", "F", "0", "NO"):
            tf_bool = False
        else:
            errors.append({"column": "correct_answers", "message": f"True/False question must have correct answer of TRUE or FALSE. Received '{correct_raw}'."})
            tf_bool = True

        options_data = [
            {"option_text": "True", "option_order": 1, "is_correct": tf_bool},
            {"option_text": "False", "option_order": 2, "is_correct": not tf_bool},
        ]

    elif q_type == "short_answer":
        if not correct_raw:
            errors.append({"column": "correct_answers", "message": "Short answer question requires at least one accepted answer."})
        else:
            accepted = [a.strip() for a in correct_raw.split("|") if a.strip()]
            if not accepted:
                accepted = [correct_raw.strip()]
            short_answer_cfg = {
                "accepted_answers": accepted,
                "case_sensitive": False,
                "match_mode": "exact",
            }

    # 4. Duplicate Detection
    is_duplicate = False
    dup_q_id = None

    if subject and q_text:
        # Check by external_id
        if external_id and external_id in existing_external_ids:
            is_duplicate = True
            warnings.append(f"Question with external ID '{external_id}' already exists in the system.")
        # Check by normalized question text in subject
        norm_q = normalize_text(q_text)
        subject_texts = existing_texts_by_subject.get(subject.id, set())
        if norm_q in subject_texts:
            is_duplicate = True
            warnings.append("A question with identical or near-identical text already exists in this subject.")

    # Status classification
    if errors:
        val_status = "invalid"
    elif is_duplicate:
        val_status = "duplicate"
    elif warnings:
        val_status = "warning"
    else:
        val_status = "valid"

    # Assemble cleaned parsed data
    parsed_data = {
        "question_text": q_text,
        "question_type": q_type,
        "difficulty": diff_val,
        "marks": marks,
        "negative_marks": neg_marks,
        "explanation": get_str("explanation"),
        "tags": [t.strip() for t in get_str("tags").split(",") if t.strip()],
        "status": status_val if status_val in ("draft", "pending_review", "approved") else "draft",
        "external_id": external_id or None,
        "subject_id": str(subject.id) if subject else None,
        "subject_code": subject.subject_code if subject else None,
        "subject_name": subject.subject_name if subject else None,
        "topic_id": str(topic.id) if topic else None,
        "topic_name": topic.topic_name if topic else None,
        "chapter_id": str(topic.chapter_id) if topic else None,
        "unit_id": str(topic.chapter.unit_id) if topic and topic.chapter else None,
        "options": options_data,
        "short_answer_config": short_answer_cfg,
    }

    return {
        "row_number": row_num,
        "raw_data": raw_row,
        "parsed_data": parsed_data,
        "validation_status": val_status,
        "is_duplicate": is_duplicate,
        "duplicate_question_id": dup_q_id,
        "errors": errors,
        "warnings": warnings,
    }


def parse_and_validate_file(
    job_id: uuid.UUID,
    file_bytes: bytes,
    file_name: str,
    admin: Admin,
    db: Session,
    column_mapping: Optional[Dict[str, str]] = None,
) -> QuestionImportJob:
    """
    Parse an uploaded CSV or XLSX file, validate all rows against the database,
    store row staging records, compute metrics, and return the updated job.
    """
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    job.status = "validating"
    db.commit()

    file_format = job.file_format.lower()
    raw_rows: List[Dict[str, Any]] = []

    # 1. Parse file content safely
    try:
        if file_format == "csv":
            # Detect encoding and parse CSV
            text_stream = io.StringIO(file_bytes.decode("utf-8-sig", errors="replace"))
            reader = csv.DictReader(text_stream)
            for row in reader:
                raw_rows.append(row)
        elif file_format in ("xlsx", "excel"):
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            # Find Question Import sheet or use active
            ws = wb["Question Import"] if "Question Import" in wb.sheetnames else wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = next(rows_iter, None)
            if not headers:
                raise ValueError("Excel file contains no header row.")
            header_keys = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(headers)]

            for row_vals in rows_iter:
                if any(v is not None and str(v).strip() for v in row_vals):
                    row_dict = {header_keys[i]: row_vals[i] for i in range(min(len(header_keys), len(row_vals)))}
                    raw_rows.append(row_dict)
            wb.close()
        else:
            raise ValueError(f"Unsupported file format '{file_format}'.")
    except Exception as e:
        logger.error(f"Failed to parse file for job [{job_id}]: {e}")
        job.status = "failed"
        job.error_summary = f"File parsing error: {str(e)}"
        db.commit()
        return job

    if len(raw_rows) > MAX_IMPORT_ROWS:
        job.status = "failed"
        job.error_summary = f"File contains {len(raw_rows)} rows, which exceeds maximum limit of {MAX_IMPORT_ROWS} rows."
        db.commit()
        return job

    if not raw_rows:
        job.status = "failed"
        job.error_summary = "Uploaded file contains no data rows."
        db.commit()
        return job

    # 2. Build Academic and Duplicate Detection Caches for Fast Processing
    subjects = db.query(Subject).all()
    subjects_by_code = {s.subject_code.upper(): s for s in subjects}

    topics = db.query(Topic).options(joinedload(Topic.chapter)).all()
    topics_by_subject_and_key = {}
    for t in topics:
        subj_id = t.chapter.unit.subject_id if t.chapter and t.chapter.unit else None
        if subj_id:
            if t.topic_code:
                topics_by_subject_and_key[f"{subj_id}:{t.topic_code.upper()}"] = t
            topics_by_subject_and_key[f"{subj_id}:{t.topic_name.upper()}"] = t

    # Admin scope check
    admin_scoped_subjects = set()
    if not admin.is_super_admin:
        scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
        admin_scoped_subjects = {s.subject_id for s in scopes if s.subject_id}

    academic_cache = {
        "subjects_by_code": subjects_by_code,
        "topics_by_subject_and_key": topics_by_subject_and_key,
        "admin_scoped_subjects": admin_scoped_subjects,
    }

    # Query existing external IDs & question texts for duplicate detection
    existing_q_records = db.query(Question.external_id, Question.question_text, Question.subject_id).all()
    existing_external_ids = {r[0] for r in existing_q_records if r[0]}
    existing_texts_by_subject: Dict[uuid.UUID, set] = {}
    for ext_id, txt, s_id in existing_q_records:
        if s_id:
            if s_id not in existing_texts_by_subject:
                existing_texts_by_subject[s_id] = set()
            existing_texts_by_subject[s_id].add(normalize_text(txt))

    # 3. Validate Rows
    valid_count = 0
    invalid_count = 0
    warning_count = 0
    duplicate_count = 0

    type_dist: Dict[str, int] = {}
    diff_dist: Dict[str, int] = {}
    subj_dist: Dict[str, int] = {}

    db_rows: List[QuestionImportRow] = []

    for idx, raw_row in enumerate(raw_rows, start=2):  # row 2 is first data row
        # Apply column mapping if provided
        if column_mapping:
            mapped_row = {column_mapping.get(k, k): v for k, v in raw_row.items()}
        else:
            mapped_row = raw_row

        val_result = validate_question_row(
            row_num=idx,
            raw_row=mapped_row,
            db=db,
            admin=admin,
            academic_cache=academic_cache,
            existing_external_ids=existing_external_ids,
            existing_texts_by_subject=existing_texts_by_subject,
        )

        st = val_result["validation_status"]
        if st == "valid":
            valid_count += 1
        elif st == "invalid":
            invalid_count += 1
        elif st == "warning":
            warning_count += 1
        elif st == "duplicate":
            duplicate_count += 1

        # Track distributions
        p_data = val_result["parsed_data"]
        q_t = p_data.get("question_type") or "unknown"
        type_dist[q_t] = type_dist.get(q_t, 0) + 1

        d_t = p_data.get("difficulty") or "medium"
        diff_dist[d_t] = diff_dist.get(d_t, 0) + 1

        s_code = p_data.get("subject_code") or "Unknown"
        subj_dist[s_code] = subj_dist.get(s_code, 0) + 1

        db_rows.append(QuestionImportRow(
            id=uuid.uuid4(),
            job_id=job.id,
            row_number=idx,
            raw_data=mapped_row,
            parsed_data=p_data,
            validation_status=st,
            is_duplicate=val_result["is_duplicate"],
            duplicate_question_id=val_result["duplicate_question_id"],
            errors=val_result["errors"],
            warnings=val_result["warnings"],
        ))

    # 4. Save rows and summary to database
    db.bulk_save_objects(db_rows)

    job.total_rows = len(raw_rows)
    job.valid_rows = valid_count
    job.invalid_rows = invalid_count
    job.warning_rows = warning_count
    job.duplicate_rows = duplicate_count
    job.summary_metadata = {
        "question_types": type_dist,
        "difficulties": diff_dist,
        "subjects": subj_dist,
    }
    job.status = "awaiting_confirmation" if invalid_count == 0 else "validation_completed"
    db.commit()
    db.refresh(job)

    log_audit_event(
        db,
        admin_id=admin.id,
        action="question_import.validated",
        entity_type="question_import_job",
        entity_id=str(job.id),
        details={"total": job.total_rows, "valid": valid_count, "invalid": invalid_count, "duplicates": duplicate_count},
    )

    return job


# ==============================================================================
# IMPORT CONFIRMATION & EXECUTION
# ==============================================================================

def execute_import_job(
    job_id: uuid.UUID,
    policy: str,
    duplicate_strategy: str,
    admin: Admin,
    db: Session,
) -> QuestionImportJob:
    """
    Execute the confirmed import job within an atomic database transaction.
    Policies:
    - 'import_valid': import valid rows and skip invalid/duplicate rows.
    - 'all_or_nothing': fail if any invalid rows exist.
    """
    job = db.query(QuestionImportJob).filter(QuestionImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    if job.status not in ("awaiting_confirmation", "validation_completed"):
        raise HTTPException(status_code=400, detail=f"Job cannot be confirmed in state '{job.status}'.")

    # Prevent duplicate confirmation
    if job.imported_rows > 0 or job.status == "importing":
        raise HTTPException(status_code=409, detail="Import job has already been processed or is currently executing.")

    # All-or-Nothing policy check
    if policy == "all_or_nothing" and job.invalid_rows > 0:
        raise HTTPException(
            status_code=400,
            detail=f"All-or-Nothing policy selected but {job.invalid_rows} invalid rows exist. Please fix errors and re-upload.",
        )

    job.status = "importing"
    job.import_policy = policy
    job.duplicate_strategy = duplicate_strategy
    db.commit()

    # Query all rows
    rows = db.query(QuestionImportRow).filter(QuestionImportRow.job_id == job_id).order_by(QuestionImportRow.row_number).all()

    imported_count = 0
    skipped_count = 0

    try:
        # Atomic execution
        for row in rows:
            st = row.validation_status

            # Handle duplicate strategy
            if row.is_duplicate:
                if duplicate_strategy == "skip":
                    row.validation_status = "skipped"
                    skipped_count += 1
                    continue
                elif duplicate_strategy == "import_as_new":
                    # Proceed to insert
                    pass
                elif duplicate_strategy == "update_existing":
                    # If external_id matched, update existing
                    ext_id = row.parsed_data.get("external_id")
                    if ext_id:
                        existing_q = db.query(Question).filter(Question.external_id == ext_id).first()
                        if existing_q:
                            existing_q.question_text = row.parsed_data["question_text"]
                            existing_q.difficulty = row.parsed_data["difficulty"]
                            existing_q.default_marks = row.parsed_data["marks"]
                            existing_q.default_negative_marks = row.parsed_data["negative_marks"]
                            existing_q.explanation = row.parsed_data["explanation"]
                            row.validation_status = "imported"
                            row.imported_question_id = existing_q.id
                            imported_count += 1
                            continue

            if st not in ("valid", "warning") and not (row.is_duplicate and duplicate_strategy == "import_as_new"):
                row.validation_status = "skipped"
                skipped_count += 1
                continue

            p = row.parsed_data
            q_id = uuid.uuid4()

            # Insert Question
            new_q = Question(
                id=q_id,
                external_id=p.get("external_id"),
                title=p.get("question_text", "")[:120],
                question_text=p["question_text"],
                question_type=p["question_type"],
                difficulty=p["difficulty"],
                default_marks=p["marks"],
                default_negative_marks=p["negative_marks"],
                explanation=p.get("explanation"),
                subject_id=uuid.UUID(p["subject_id"]) if p.get("subject_id") else None,
                topic_id=uuid.UUID(p["topic_id"]) if p.get("topic_id") else None,
                chapter_id=uuid.UUID(p["chapter_id"]) if p.get("chapter_id") else None,
                unit_id=uuid.UUID(p["unit_id"]) if p.get("unit_id") else None,
                short_answer_config=p.get("short_answer_config"),
                status=p.get("status", "draft"),
                created_by=admin.id,
            )
            db.add(new_q)
            db.flush()

            # Insert Options
            for opt in p.get("options", []):
                new_opt = QuestionOption(
                    id=uuid.uuid4(),
                    question_id=q_id,
                    option_text=opt["option_text"],
                    option_order=opt["option_order"],
                    is_correct=opt["is_correct"],
                )
                db.add(new_opt)

            # Insert Tags
            for tag_name in p.get("tags", []):
                clean_tag = tag_name.strip()
                if clean_tag:
                    tag_obj = db.query(QuestionTag).filter(QuestionTag.tag_name == clean_tag).first()
                    if not tag_obj:
                        tag_obj = QuestionTag(id=uuid.uuid4(), tag_name=clean_tag)
                        db.add(tag_obj)
                        db.flush()
                    db.add(QuestionTagRelation(question_id=q_id, tag_id=tag_obj.id))

            # Insert initial version snapshot (v1)
            snapshot = {
                "question_text": p["question_text"],
                "question_type": p["question_type"],
                "difficulty": p["difficulty"],
                "marks": p["marks"],
                "negative_marks": p["negative_marks"],
                "options": p.get("options", []),
                "import_job_id": str(job.id),
            }
            new_v = QuestionVersion(
                id=uuid.uuid4(),
                question_id=q_id,
                version_number=1,
                question_snapshot=snapshot,
                change_summary=f"Bulk imported via job [{job.file_name}]",
                changed_by=admin.id,
            )
            db.add(new_v)

            row.validation_status = "imported"
            row.imported_question_id = q_id
            imported_count += 1

        job.imported_rows = imported_count
        job.skipped_rows = skipped_count
        job.status = "completed" if job.invalid_rows == 0 else "completed_with_errors"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        log_audit_event(
            db,
            admin_id=admin.id,
            action="question_import.executed",
            entity_type="question_import_job",
            entity_id=str(job.id),
            details={"imported": imported_count, "skipped": skipped_count, "policy": policy},
        )

        return job

    except Exception as e:
        db.rollback()
        logger.error(f"Error executing import job [{job_id}]: {e}")
        job.status = "failed"
        job.error_summary = f"Transaction error during import: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to commit imported questions: {str(e)}")


# ==============================================================================
# ERROR REPORT GENERATION
# ==============================================================================

def generate_error_report_csv(job_id: uuid.UUID, db: Session) -> str:
    """Generate a downloadable CSV error report containing row numbers and exact error details."""
    rows = db.query(QuestionImportRow).filter(
        QuestionImportRow.job_id == job_id,
        or_(QuestionImportRow.validation_status.in_(["invalid", "duplicate", "warning"])),
    ).order_by(QuestionImportRow.row_number).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Validation Status", "Column", "Error Message", "Warnings", "Raw Question Text"])

    for r in rows:
        err_msgs = "; ".join([e.get("message", "") for e in (r.errors or [])])
        col_names = ", ".join(list({e.get("column", "") for e in (r.errors or [])}))
        warn_msgs = "; ".join(r.warnings or [])
        raw_text = r.raw_data.get("question_text", "")
        writer.writerow([r.row_number, r.validation_status, col_names, err_msgs, warn_msgs, sanitize_cell_for_export(raw_text)])

    return output.getvalue()


# ==============================================================================
# QUESTION EXPORT SYSTEM
# ==============================================================================

def export_questions_service(
    filters: Dict[str, Any],
    export_format: str,
    export_mode: str,
    admin: Admin,
    db: Session,
) -> Tuple[bytes, str, str]:
    """
    Export questions with academic filters, RBAC scoping, answer-key security, and formula injection protection.
    Returns: (file_bytes, filename, media_type)
    """
    # Verify Permissions
    if not has_permission(db, admin, "question.export"):
        raise HTTPException(status_code=403, detail="Permission 'question.export' required to export questions.")

    if export_mode == "administrative_answer_key":
        if not has_permission(db, admin, "question.answer.view"):
            raise HTTPException(
                status_code=403,
                detail="Permission 'question.answer.view' required for administrative answer-key export.",
            )

    # Base query with relations
    query = db.query(Question).options(
        joinedload(Question.subject),
        joinedload(Question.topic),
        joinedload(Question.options),
        joinedload(Question.tags),
    )

    # RBAC Scoping for User Admin
    if not admin.is_super_admin:
        scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
        scoped_subject_ids = [s.subject_id for s in scopes if s.subject_id]
        if scoped_subject_ids:
            query = query.filter(Question.subject_id.in_(scoped_subject_ids))
        else:
            # If User Admin has no scopes, return empty export safely
            query = query.filter(Question.id == uuid.uuid4())

    # Apply filters
    if filters.get("subject_id"):
        query = query.filter(Question.subject_id == uuid.UUID(str(filters["subject_id"])))
    if filters.get("topic_id"):
        query = query.filter(Question.topic_id == uuid.UUID(str(filters["topic_id"])))
    if filters.get("question_type"):
        query = query.filter(Question.question_type == filters["question_type"])
    if filters.get("difficulty"):
        query = query.filter(Question.difficulty == filters["difficulty"])
    if filters.get("status"):
        query = query.filter(Question.status == filters["status"])

    questions = query.order_by(Question.created_at.desc()).all()

    # Define export columns based on export_mode
    base_headers = [
        "question_external_id",
        "question_text",
        "question_type",
        "difficulty",
        "marks",
        "negative_marks",
        "subject_code",
        "subject_name",
        "topic_name",
        "tags",
        "status",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "option_e",
    ]

    if export_mode == "administrative_answer_key":
        headers = base_headers + ["correct_answers", "explanation"]
    else:
        headers = base_headers  # Question-only export: strictly excludes answers and explanations

    # Build row records
    rows_data: List[List[Any]] = []
    for q in questions:
        # Sort options
        opts = sorted(q.options, key=lambda o: o.option_order)
        opt_dict = {f"option_{chr(ord('a') + i)}": (opts[i].option_text if i < len(opts) else "") for i in range(5)}

        tag_str = ", ".join([t.tag_name for t in q.tags])

        row_vals = [
            sanitize_cell_for_export(q.external_id or ""),
            sanitize_cell_for_export(q.question_text),
            q.question_type,
            q.difficulty,
            float(q.default_marks),
            float(q.default_negative_marks),
            sanitize_cell_for_export(q.subject.subject_code if q.subject else ""),
            sanitize_cell_for_export(q.subject.subject_name if q.subject else ""),
            sanitize_cell_for_export(q.topic.topic_name if q.topic else ""),
            sanitize_cell_for_export(tag_str),
            q.status,
            sanitize_cell_for_export(opt_dict.get("option_a", "")),
            sanitize_cell_for_export(opt_dict.get("option_b", "")),
            sanitize_cell_for_export(opt_dict.get("option_c", "")),
            sanitize_cell_for_export(opt_dict.get("option_d", "")),
            sanitize_cell_for_export(opt_dict.get("option_e", "")),
        ]

        if export_mode == "administrative_answer_key":
            # Derive correct answer string
            if q.question_type in ("single_choice", "multiple_choice"):
                correct_letters = [chr(ord("A") + i) for i, o in enumerate(opts) if o.is_correct]
                ans_str = ",".join(correct_letters)
            elif q.question_type == "true_false":
                correct_opt = next((o for o in opts if o.is_correct), None)
                ans_str = correct_opt.option_text.upper() if correct_opt else "TRUE"
            elif q.question_type == "short_answer" and q.short_answer_config:
                ans_str = "|".join(q.short_answer_config.get("accepted_answers", []))
            else:
                ans_str = ""

            row_vals.extend([
                sanitize_cell_for_export(ans_str),
                sanitize_cell_for_export(q.explanation or ""),
            ])

        rows_data.append(row_vals)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    mode_prefix = "answer_key" if export_mode == "administrative_answer_key" else "questions_only"

    # Export formatting
    if export_format.lower() == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        for r in rows_data:
            writer.writerow(r)
        file_bytes = out.getvalue().encode("utf-8-sig")
        filename = f"quizverse_{mode_prefix}_{timestamp_str}.csv"
        media_type = "text/csv"
    else:  # xlsx
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Exported Questions"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        border_thin = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )

        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border_thin

        for r in rows_data:
            ws.append(r)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        stream = io.BytesIO()
        wb.save(stream)
        file_bytes = stream.getvalue()
        filename = f"quizverse_{mode_prefix}_{timestamp_str}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Log security audit event
    log_audit_event(
        db,
        admin_id=admin.id,
        action="question.exported",
        entity_type="question_export",
        entity_id=filename,
        details={"mode": export_mode, "format": export_format, "count": len(questions)},
    )

    return file_bytes, filename, media_type
