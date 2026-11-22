import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.quiz import (
    Quiz,
    QuizSection,
    QuizQuestion,
    QuizConfiguration,
)
from backend.app.models.auth_rbac import Admin, AdminAcademicScope, AdminQuizAssignment
from backend.app.schemas.quiz_publishing import ValidationCheckItem, QuizValidationReport


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_or_create_quiz_configuration(db: Session, quiz: Quiz) -> QuizConfiguration:
    config = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).first()
    if not config:
        config = QuizConfiguration(
            quiz_id=quiz.id,
            passing_percentage=quiz.passing_percentage if hasattr(quiz, "passing_percentage") and quiz.passing_percentage is not None else Decimal("40.00"),
            shuffle_questions=quiz.shuffle_questions if hasattr(quiz, "shuffle_questions") and quiz.shuffle_questions is not None else True,
            shuffle_options=quiz.shuffle_options if hasattr(quiz, "shuffle_options") and quiz.shuffle_options is not None else True,
            start_time=quiz.start_time if hasattr(quiz, "start_time") else None,
            end_time=quiz.end_time if hasattr(quiz, "end_time") else None,
        )
        db.add(config)
        db.flush()
    return config


def validate_quiz_for_publishing(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
) -> QuizValidationReport:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    config = get_or_create_quiz_configuration(db, quiz)
    checks: List[ValidationCheckItem] = []

    # ---------------------------------------------------------
    # 1. Permissions & Access Checks
    # ---------------------------------------------------------
    can_publish = False
    if admin.is_super_admin:
        can_publish = True
        checks.append(
            ValidationCheckItem(
                category="permissions",
                name="Super Admin Authority",
                passed=True,
                level="info",
                message="Super Administrator has platform-wide publishing authority.",
            )
        )
    else:
        # Check ownership or assignment
        is_owner = str(quiz.created_by) == str(admin.id)
        assignment = (
            db.query(AdminQuizAssignment)
            .filter(
                AdminQuizAssignment.admin_id == admin.id,
                AdminQuizAssignment.quiz_id == quiz.id,
                AdminQuizAssignment.access_level.in_(["owner", "editor"]),
            )
            .first()
        )
        if is_owner or assignment:
            can_publish = True
            checks.append(
                ValidationCheckItem(
                    category="permissions",
                    name="Administrator Quiz Ownership",
                    passed=True,
                    level="info",
                    message="You are authorized to configure and publish this examination.",
                )
            )
        else:
            checks.append(
                ValidationCheckItem(
                    category="permissions",
                    name="Administrator Quiz Ownership",
                    passed=False,
                    level="error",
                    message="Access Denied: You do not have publishing rights for this quiz.",
                )
            )

    # ---------------------------------------------------------
    # 2. Quiz Content & Questions Checks
    # ---------------------------------------------------------
    title_valid = bool(quiz.title and len(quiz.title.strip()) >= 3)
    checks.append(
        ValidationCheckItem(
            category="content",
            name="Quiz Title Verification",
            passed=title_valid,
            level="error" if not title_valid else "info",
            message="Title is valid." if title_valid else "Quiz title must be at least 3 characters long.",
        )
    )

    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.question_order.asc())
        .all()
    )
    has_questions = len(questions) > 0
    checks.append(
        ValidationCheckItem(
            category="content",
            name="Question Count Verification",
            passed=has_questions,
            level="error" if not has_questions else "info",
            message=f"Quiz has {len(questions)} question(s)." if has_questions else "Examination must contain at least 1 question before it can be published.",
        )
    )

    # Deep validate each question
    invalid_questions = []
    missing_answers = []
    for idx, qq in enumerate(questions):
        snap = qq.question_snapshot or {}
        q_text = snap.get("question_text", "").strip()
        q_type = snap.get("question_type", "single_choice")
        if not q_text:
            invalid_questions.append(f"Q#{idx + 1} has an empty question statement.")

        if q_type in ["single_choice", "multiple_choice", "true_false"]:
            opts = snap.get("options", [])
            if len(opts) < 2:
                missing_answers.append(f"Q#{idx + 1} ({q_type}) requires at least 2 options.")
            correct = [o for o in opts if o.get("is_correct") is True]
            if len(correct) == 0:
                missing_answers.append(f"Q#{idx + 1} ({q_type}) has no correct answer configured.")

    content_errors = invalid_questions + missing_answers
    checks.append(
        ValidationCheckItem(
            category="content",
            name="Question Integrity & Answer Configuration",
            passed=len(content_errors) == 0,
            level="error" if len(content_errors) > 0 else "info",
            message="All questions and answer keys are fully configured." if len(content_errors) == 0 else f"Issues found in {len(content_errors)} question configuration(s): {', '.join(content_errors[:3])}",
        )
    )

    # ---------------------------------------------------------
    # 3. Sections & Selection Rules Checks
    # ---------------------------------------------------------
    sections = (
        db.query(QuizSection)
        .filter(QuizSection.quiz_id == quiz.id)
        .order_by(QuizSection.section_order.asc())
        .all()
    )

    section_issues = []
    for sec in sections:
        sec_q_count = len([q for q in questions if q.section_id == sec.id])
        if sec.selection_rule == "answer_n_of_m":
            req = sec.required_question_count or 0
            if req > sec_q_count:
                section_issues.append(
                    f"Section '{sec.title}' requires candidates to answer {req} questions, but only {sec_q_count} question(s) are present."
                )

    checks.append(
        ValidationCheckItem(
            category="academic",
            name="Section Structure & Selection Rules",
            passed=len(section_issues) == 0,
            level="error" if len(section_issues) > 0 else "info",
            message="Section question selection rules are consistent." if len(section_issues) == 0 else " ".join(section_issues),
        )
    )

    # ---------------------------------------------------------
    # 4. Scoring & Passing Criteria Checks
    # ---------------------------------------------------------
    # Calculate Obtainable Marks
    total_obtainable_marks = 0.0
    if len(sections) > 0:
        for sec in sections:
            sec_qs = [q for q in questions if q.section_id == sec.id]
            if sec.selection_rule == "answer_n_of_m":
                req = min(sec.required_question_count or len(sec_qs), len(sec_qs))
                marks_sorted = sorted([float(q.marks) for q in sec_qs], reverse=True)
                total_obtainable_marks += sum(marks_sorted[:req])
            elif sec.selection_rule == "all_optional":
                total_obtainable_marks += sum(float(q.marks) for q in sec_qs)
            else:
                total_obtainable_marks += sum(float(q.marks) for q in sec_qs)
        unsectioned = [q for q in questions if not q.section_id]
        total_obtainable_marks += sum(float(q.marks) for q in unsectioned)
    else:
        total_obtainable_marks = sum(float(q.marks) for q in questions)

    marks_valid = total_obtainable_marks > 0
    checks.append(
        ValidationCheckItem(
            category="scoring",
            name="Maximum Obtainable Marks",
            passed=marks_valid,
            level="error" if not marks_valid else "info",
            message=f"Total obtainable marks: {total_obtainable_marks:.2f}m." if marks_valid else "Total obtainable marks must be greater than 0.",
        )
    )

    # Passing Criteria Check
    passing_valid = True
    passing_msg = ""
    if config.passing_criteria_type == "percentage":
        pct = float(config.passing_percentage)
        passing_valid = 0 <= pct <= 100
        passing_msg = f"Passing target configured as {pct:.1f}%." if passing_valid else "Passing percentage must be between 0% and 100%."
    else:
        pm = float(config.passing_marks or 0.0)
        passing_valid = 0 < pm <= total_obtainable_marks if total_obtainable_marks > 0 else False
        passing_msg = f"Passing target configured as {pm:.2f} marks." if passing_valid else f"Passing marks ({pm}) cannot exceed total obtainable marks ({total_obtainable_marks:.2f})."

    checks.append(
        ValidationCheckItem(
            category="scoring",
            name="Passing Cutoff Criteria",
            passed=passing_valid,
            level="error" if not passing_valid else "info",
            message=passing_msg,
        )
    )

    # ---------------------------------------------------------
    # 5. Schedule & Timing Checks
    # ---------------------------------------------------------
    schedule_valid = True
    schedule_msg = "Availability set to immediate."

    # Validate timezone
    tz_val = (config.timezone or "UTC").strip()
    if tz_val.upper() in ["UTC", "GMT", "ETC/UTC", "ETC/GMT"]:
        tz_valid = True
    else:
        try:
            ZoneInfo(tz_val)
            tz_valid = True
        except Exception:
            tz_valid = False

    checks.append(
        ValidationCheckItem(
            category="schedule",
            name="Timezone Configuration",
            passed=tz_valid,
            level="error" if not tz_valid else "info",
            message=f"Valid timezone: '{config.timezone}'." if tz_valid else f"Invalid timezone identifier: '{config.timezone}'.",
        )
    )

    if config.availability_mode in ["scheduled", "restricted"]:
        st = _ensure_utc(config.start_time)
        et = _ensure_utc(config.end_time)
        if not st or not et:
            schedule_valid = False
            schedule_msg = "Scheduled examination requires both start time and end time."
        elif et <= st:
            schedule_valid = False
            schedule_msg = "Scheduled end time must be chronologically after start time."
        else:
            window_minutes = (et - st).total_seconds() / 60
            if window_minutes < quiz.duration_minutes:
                schedule_valid = False
                schedule_msg = f"Examination window ({int(window_minutes)} mins) cannot be shorter than examination duration ({quiz.duration_minutes} mins)."
            else:
                schedule_msg = f"Valid examination window ({int(window_minutes)} mins) from {st.isoformat()} to {et.isoformat()}."

    checks.append(
        ValidationCheckItem(
            category="schedule",
            name="Examination Schedule Window",
            passed=schedule_valid,
            level="error" if not schedule_valid else "info",
            message=schedule_msg,
        )
    )

    # ---------------------------------------------------------
    # 6. Summary Calculation
    # ---------------------------------------------------------
    errors = [c for c in checks if not c.passed and c.level == "error"]
    warnings = [c for c in checks if not c.passed and c.level == "warning"]
    passed_count = len([c for c in checks if c.passed])

    is_overall_valid = len(errors) == 0
    final_can_publish = is_overall_valid and can_publish

    scoring_summary = None
    try:
        from backend.app.services.manual_quiz_service import calculate_scoring_summary
        scoring_obj = calculate_scoring_summary(db, quiz.id)
        scoring_summary = scoring_obj.model_dump() if hasattr(scoring_obj, "model_dump") else scoring_obj.dict()
    except Exception:
        scoring_summary = None

    summary = {
        "total_checks": len(checks),
        "passed": passed_count,
        "warnings_count": len(warnings),
        "errors_count": len(errors),
        "obtainable_marks": total_obtainable_marks,
        "total_questions": len(questions),
        "total_sections": len(sections),
    }

    # Persist validation summary on quiz
    quiz.last_validated_at = datetime.now(timezone.utc)
    quiz.validation_summary = summary
    if is_overall_valid and quiz.status == "draft":
        quiz.status = "ready_to_publish"
    db.commit()

    return QuizValidationReport(
        quiz_id=quiz.id,
        is_valid=is_overall_valid,
        can_publish=final_can_publish,
        checks=checks,
        summary=summary,
        scoring_summary=scoring_summary,
        errors=[c.message for c in errors],
        warnings=[c.message for c in warnings],
        validated_at=datetime.now(timezone.utc),
    )
