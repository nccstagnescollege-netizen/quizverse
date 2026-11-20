import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, and_
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.models.base import utc_now
from backend.app.models.auth_rbac import Admin
from backend.app.models.academic import Subject
from backend.app.models.student import Student, StudentProfile
from backend.app.models.quiz import (
    Quiz,
    QuizConfiguration,
    QuizSection,
    QuizQuestion,
    QuizPublishedVersion,
)
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
)
from backend.app.models.results import (
    ExaminationResult,
    QuestionEvaluation,
    GradingRubric,
    GradingCriterion,
    GradingRubricVersion,
    GradingAssignment,
    EvaluationJob,
    ResultCorrection,
)
from backend.app.schemas.evaluation import (
    GradingCriterionCreate,
    GradingCriterionResponse,
    GradingRubricCreate,
    GradingRubricUpdate,
    GradingRubricResponse,
    GradingRubricVersionResponse,
    GradingAssignmentCreate,
    GradingAssignmentResponse,
    ManualGradingQuestionItem,
    ManualGradingWorkspaceResponse,
    SaveManualEvaluationRequest,
    ModerationEvaluationItem,
    ModerationActionRequest,
    EvaluationJobResponse,
    EvaluationTaskItem,
    SectionScoreDetail,
    QuestionEvaluationDetail,
    ResultCorrectionDetail,
    ResultListItemResponse,
    ResultListResponse,
    ResultDetailResponse,
    StudentResultResponse,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _round_decimal(val: Decimal, precision: int = 2) -> Decimal:
    fmt = "0." + "0" * precision if precision > 0 else "0"
    return val.quantize(Decimal(fmt), rounding=ROUND_HALF_UP)


class EvaluationService:

    # ====================================================================
    # PERMISSION & SCOPING HELPERS
    # ====================================================================

    @staticmethod
    def check_quiz_access(db: Session, admin: Admin, quiz: Quiz) -> bool:
        """Verify if admin has permission to view or manage quiz results/grading."""
        if admin.is_super_admin:
            return True
        return quiz.created_by == admin.id

    @staticmethod
    def is_assigned_evaluator(db: Session, admin: Admin, quiz_id: uuid.UUID) -> bool:
        """Check if admin is explicitly assigned as an evaluator for this quiz."""
        if admin.is_super_admin:
            return True
        assignment = db.query(GradingAssignment).filter(
            GradingAssignment.quiz_id == quiz_id,
            GradingAssignment.evaluator_id == admin.id,
            GradingAssignment.status == "active",
        ).first()
        return assignment is not None

    # ====================================================================
    # 1. EVALUATION JOB MANAGER & ORCHESTRATION
    # ====================================================================

    @staticmethod
    def get_or_create_job(db: Session, attempt: ExaminationAttempt) -> EvaluationJob:
        """Idempotently fetch or create the EvaluationJob record for an attempt."""
        job = db.query(EvaluationJob).filter(EvaluationJob.attempt_id == attempt.id).first()
        if not job:
            job = EvaluationJob(
                attempt_id=attempt.id,
                quiz_id=attempt.quiz_id,
                student_id=attempt.student_id,
                status="pending",
                total_questions=0,
                auto_evaluated_count=0,
                manual_eval_count=0,
                manual_eval_completed=0,
            )
            db.add(job)
            db.flush()
        return job

    @staticmethod
    def run_evaluation(
        db: Session,
        attempt_id: uuid.UUID,
        triggered_by: Optional[Admin] = None,
    ) -> ExaminationResult:
        """
        Authoritative Evaluation Engine:
        1. Verifies attempt is submitted.
        2. Evaluates all objective questions (Single Choice, Multiple Choice with methods, True/False, Short Answer exact match).
        3. Identifies descriptive/essay questions requiring manual evaluation.
        4. Calculates section-wise and overall provisional scores.
        5. Updates EvaluationJob and ExaminationResult.
        Idempotent and safe to retry without double-scoring.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.sections),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.quiz_questions),
            joinedload(ExaminationAttempt.answers),
            joinedload(ExaminationAttempt.student),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=404, detail="Examination attempt not found")

        quiz = attempt.quiz
        cfg = quiz.configuration
        job = EvaluationService.get_or_create_job(db, attempt)
        job.status = "processing"
        db.flush()

        # Scoring config
        total_quiz_marks = Decimal(str(quiz.total_marks or "100.00"))
        rounding_prec = cfg.rounding_precision if cfg and cfg.rounding_precision is not None else 2
        passing_pct = Decimal(str(cfg.passing_percentage if cfg and cfg.passing_percentage is not None else "40.00"))
        passing_marks_cfg = Decimal(str(cfg.passing_marks)) if cfg and cfg.passing_marks is not None else None
        neg_marking_type = cfg.negative_marking_type if cfg else "none"
        fixed_neg_marks = Decimal(str(cfg.fixed_negative_marks or "0.00")) if cfg else Decimal("0.00")
        allow_partial_marking = cfg.partial_marking_enabled if cfg else True

        # Map existing answers by quiz_question_id
        answers_by_qq = {a.quiz_question_id: a for a in attempt.answers}

        # Existing or new ExaminationResult
        result = db.query(ExaminationResult).filter(ExaminationResult.attempt_id == attempt.id).first()
        if not result:
            result = ExaminationResult(
                attempt_id=attempt.id,
                quiz_id=quiz.id,
                student_id=attempt.student_id,
                maximum_marks=total_quiz_marks,
                passing_marks=passing_marks_cfg,
                evaluation_status="PENDING",
            )
            db.add(result)
            db.flush()

        existing_evals = {e.quiz_question_id: e for e in result.evaluations}

        total_questions_count = len(quiz.quiz_questions)
        auto_evaluated_count = 0
        manual_eval_count = 0
        manual_completed_count = 0

        total_correct = 0
        total_incorrect = 0
        total_unanswered = 0
        total_objective_marks = Decimal("0.00")
        total_manual_marks = Decimal("0.00")
        total_negative_marks = Decimal("0.00")

        # Process each quiz question
        for qq in quiz.quiz_questions:
            snap = qq.question_snapshot or {}
            qtype = snap.get("question_type", "single_choice")
            q_marks = Decimal(str(qq.marks or snap.get("marks") or "1.00"))
            
            # Negative marks resolution
            if neg_marking_type == "none":
                q_neg_marks = Decimal("0.00")
            elif neg_marking_type == "fixed":
                q_neg_marks = fixed_neg_marks
            else:  # question_specific
                q_neg_marks = Decimal(str(qq.negative_marks or snap.get("negative_marks") or "0.00"))

            ans = answers_by_qq.get(qq.id)
            eval_record = existing_evals.get(qq.id)
            if not eval_record:
                eval_record = QuestionEvaluation(
                    result_id=result.id,
                    quiz_question_id=qq.id,
                    attempt_answer_id=ans.id if ans else None,
                    max_marks=q_marks,
                )
                db.add(eval_record)
                db.flush()
            else:
                eval_record.max_marks = q_marks
                if ans:
                    eval_record.attempt_answer_id = ans.id

            is_answered = ans and (
                (ans.selected_option_ids and len(ans.selected_option_ids) > 0) or
                (ans.text_response and ans.text_response.strip())
            )

            # --- A. OBJECTIVE QUESTION TYPES ---
            if qtype in ["single_choice", "true_false"]:
                auto_evaluated_count += 1
                eval_record.evaluation_type = "auto_objective"

                if not is_answered:
                    total_unanswered += 1
                    eval_record.marks_awarded = Decimal("0.00")
                    eval_record.negative_deduction = Decimal("0.00")
                    eval_record.is_correct = False
                    eval_record.is_partially_correct = False
                    eval_record.scoring_reason = "Unanswered question"
                else:
                    correct_opts = [
                        str(opt.get("id") or opt.get("option_id"))
                        for opt in (snap.get("options") or [])
                        if opt.get("is_correct")
                    ]
                    if not correct_opts and snap.get("correct_answers"):
                        correct_opts = [str(x) for x in snap.get("correct_answers")]

                    user_selected = [str(x) for x in (ans.selected_option_ids or [])]

                    if correct_opts and user_selected and set(user_selected) == set(correct_opts):
                        total_correct += 1
                        eval_record.marks_awarded = q_marks
                        eval_record.negative_deduction = Decimal("0.00")
                        eval_record.is_correct = True
                        eval_record.is_partially_correct = False
                        eval_record.scoring_reason = "Correct option selected"
                        total_objective_marks += q_marks
                    else:
                        total_incorrect += 1
                        eval_record.marks_awarded = Decimal("0.00")
                        eval_record.negative_deduction = q_neg_marks
                        eval_record.is_correct = False
                        eval_record.is_partially_correct = False
                        eval_record.scoring_reason = f"Incorrect option selected (-{q_neg_marks} deduction)"
                        total_negative_marks += q_neg_marks

            elif qtype == "multiple_choice":
                auto_evaluated_count += 1
                eval_record.evaluation_type = "auto_objective"

                if not is_answered:
                    total_unanswered += 1
                    eval_record.marks_awarded = Decimal("0.00")
                    eval_record.negative_deduction = Decimal("0.00")
                    eval_record.is_correct = False
                    eval_record.is_partially_correct = False
                    eval_record.scoring_reason = "Unanswered question"
                else:
                    correct_opts = set(
                        str(opt.get("id") or opt.get("option_id"))
                        for opt in (snap.get("options") or [])
                        if opt.get("is_correct")
                    )
                    if not correct_opts and snap.get("correct_answers"):
                        correct_opts = set(str(x) for x in snap.get("correct_answers"))

                    user_selected = set(str(x) for x in (ans.selected_option_ids or []))

                    mc_method = (
                        (qq.scoring_settings or {}).get("multiple_choice_method") or
                        (getattr(cfg, "scoring_settings", None) or {}).get("multiple_choice_method") or
                        ("partial_credit" if allow_partial_marking else "all_or_nothing")
                    )

                    if mc_method == "all_or_nothing":
                        if user_selected == correct_opts and len(correct_opts) > 0:
                            total_correct += 1
                            eval_record.marks_awarded = q_marks
                            eval_record.negative_deduction = Decimal("0.00")
                            eval_record.is_correct = True
                            eval_record.is_partially_correct = False
                            eval_record.scoring_reason = "All or Nothing: All correct options selected"
                            total_objective_marks += q_marks
                        else:
                            total_incorrect += 1
                            eval_record.marks_awarded = Decimal("0.00")
                            eval_record.negative_deduction = q_neg_marks
                            eval_record.is_correct = False
                            eval_record.is_partially_correct = False
                            eval_record.scoring_reason = f"All or Nothing: Selection incorrect (-{q_neg_marks})"
                            total_negative_marks += q_neg_marks

                    elif mc_method == "exact_match":
                        if user_selected == correct_opts and len(correct_opts) > 0:
                            total_correct += 1
                            eval_record.marks_awarded = q_marks
                            eval_record.negative_deduction = Decimal("0.00")
                            eval_record.is_correct = True
                            eval_record.is_partially_correct = False
                            eval_record.scoring_reason = "Exact Match: Options matched exactly"
                            total_objective_marks += q_marks
                        else:
                            total_incorrect += 1
                            eval_record.marks_awarded = Decimal("0.00")
                            eval_record.negative_deduction = q_neg_marks
                            eval_record.is_correct = False
                            eval_record.is_partially_correct = False
                            eval_record.scoring_reason = f"Exact Match: Selection did not match (-{q_neg_marks})"
                            total_negative_marks += q_neg_marks

                    else:  # partial_credit
                        num_correct = len(correct_opts)
                        if num_correct > 0:
                            correct_selected = len(user_selected & correct_opts)
                            incorrect_selected = len(user_selected - correct_opts)
                            mark_per_correct = q_marks / Decimal(num_correct)
                            penalty_per_incorrect = (q_neg_marks / Decimal(num_correct)) if q_neg_marks > 0 else (mark_per_correct * Decimal("0.5"))

                            raw_marks = (Decimal(correct_selected) * mark_per_correct) - (Decimal(incorrect_selected) * penalty_per_incorrect)
                            awarded = max(Decimal("0.00"), min(q_marks, _round_decimal(raw_marks, rounding_prec)))

                            if user_selected == correct_opts:
                                total_correct += 1
                                eval_record.is_correct = True
                                eval_record.is_partially_correct = False
                                eval_record.scoring_reason = "Partial Credit: Full credit achieved"
                            elif awarded > 0:
                                total_correct += 1
                                eval_record.is_correct = False
                                eval_record.is_partially_correct = True
                                eval_record.scoring_reason = f"Partial Credit: {correct_selected}/{num_correct} correct, {incorrect_selected} incorrect"
                            else:
                                total_incorrect += 1
                                eval_record.is_correct = False
                                eval_record.is_partially_correct = False
                                eval_record.scoring_reason = "Partial Credit: Zero net marks"

                            eval_record.marks_awarded = awarded
                            eval_record.negative_deduction = Decimal("0.00")
                            total_objective_marks += awarded
                        else:
                            eval_record.marks_awarded = Decimal("0.00")
                            eval_record.negative_deduction = Decimal("0.00")

            # --- B. SHORT ANSWER WITH EXACT MATCHING OR MANUAL ---
            elif qtype == "short_answer":
                exact_match_enabled = (
                    snap.get("exact_matching") or
                    (qq.scoring_settings or {}).get("exact_matching") or
                    (snap.get("accepted_answers") and len(snap.get("accepted_answers")) > 0)
                )

                if exact_match_enabled and is_answered:
                    auto_evaluated_count += 1
                    eval_record.evaluation_type = "auto_short_answer"

                    user_text = re.sub(r'\s+', ' ', (ans.text_response or "").strip()).lower()
                    accepted = snap.get("accepted_answers") or [snap.get("correct_answer")]
                    normalized_accepted = [re.sub(r'\s+', ' ', str(x).strip()).lower() for x in accepted if x]

                    if user_text in normalized_accepted:
                        total_correct += 1
                        eval_record.marks_awarded = q_marks
                        eval_record.negative_deduction = Decimal("0.00")
                        eval_record.is_correct = True
                        eval_record.is_partially_correct = False
                        eval_record.scoring_reason = f"Exact match with accepted answer '{user_text}'"
                        total_objective_marks += q_marks
                    else:
                        total_incorrect += 1
                        eval_record.marks_awarded = Decimal("0.00")
                        eval_record.negative_deduction = q_neg_marks
                        eval_record.is_correct = False
                        eval_record.is_partially_correct = False
                        eval_record.scoring_reason = f"Did not match accepted answers (-{q_neg_marks})"
                        total_negative_marks += q_neg_marks
                elif not is_answered:
                    auto_evaluated_count += 1
                    total_unanswered += 1
                    eval_record.evaluation_type = "auto_short_answer"
                    eval_record.marks_awarded = Decimal("0.00")
                    eval_record.negative_deduction = Decimal("0.00")
                    eval_record.is_correct = False
                    eval_record.is_partially_correct = False
                    eval_record.scoring_reason = "Unanswered short answer"
                else:
                    # Routes to manual grading workspace
                    manual_eval_count += 1
                    eval_record.evaluation_type = "manual_grading"
                    if eval_record.evaluator_id or eval_record.marks_awarded > 0:
                        manual_completed_count += 1
                        total_manual_marks += eval_record.marks_awarded
                    else:
                        eval_record.scoring_reason = "Awaiting manual evaluator grading"

            # --- C. DESCRIPTIVE / ESSAY (Always Manual Grading) ---
            else:
                manual_eval_count += 1
                eval_record.evaluation_type = "manual_grading"
                if not is_answered:
                    total_unanswered += 1
                    eval_record.marks_awarded = Decimal("0.00")
                    eval_record.scoring_reason = "Unanswered descriptive question"
                    manual_completed_count += 1
                elif eval_record.evaluator_id or eval_record.marks_awarded > 0:
                    manual_completed_count += 1
                    total_manual_marks += eval_record.marks_awarded
                else:
                    eval_record.scoring_reason = "Awaiting manual evaluator grading"

        # --- SECTION-WISE & COMPULSORY/OPTIONAL CALCULATION ---
        section_breakdowns = []
        earned_score = Decimal("0.00")

        # Group questions by section
        section_map: Dict[Optional[uuid.UUID], List[QuizQuestion]] = {}
        for qq in quiz.quiz_questions:
            sec_id = qq.section_id
            if sec_id not in section_map:
                section_map[sec_id] = []
            section_map[sec_id].append(qq)

        sections = quiz.sections or []
        sections_by_id = {s.id: s for s in sections}

        for sec_id, qq_list in section_map.items():
            sec = sections_by_id.get(sec_id) if sec_id else None
            sec_title = sec.title if sec else "General Section"
            sec_rule = sec.selection_rule if sec else "all_compulsory"
            req_count = sec.required_question_count if sec else len(qq_list)

            # Collect scores for questions in this section
            scored_items = []
            for qq in qq_list:
                ev = existing_evals.get(qq.id) or next((e for e in result.evaluations if e.quiz_question_id == qq.id), None)
                awarded = ev.marks_awarded if ev else Decimal("0.00")
                scored_items.append((qq, awarded))

            # Optional questions: "answer_n_of_m"
            if sec_rule == "answer_n_of_m" and req_count and req_count < len(qq_list):
                # Pick the top N highest scoring answers
                scored_items.sort(key=lambda x: x[1], reverse=True)
                counted_items = scored_items[:req_count]
                sec_obtained = sum(x[1] for x in counted_items)
                def_m = Decimal(str(sec.default_marks_per_question or "1.00")) if sec else Decimal("1.00")
                sec_effective_max = Decimal(str(sec.section_total_marks or (Decimal(req_count) * def_m)))
            else:
                counted_items = scored_items
                sec_obtained = sum(x[1] for x in counted_items)
                sec_effective_max = sum(Decimal(str(x.marks or "1.00")) for x in qq_list)

            sec_obtained_capped = min(sec_effective_max, max(Decimal("0.00"), sec_obtained))
            earned_score += sec_obtained_capped

            attempted_in_sec = sum(
                1 for qq in qq_list
                if answers_by_qq.get(qq.id) and (
                    answers_by_qq[qq.id].selected_option_ids or
                    (answers_by_qq[qq.id].text_response and answers_by_qq[qq.id].text_response.strip())
                )
            )

            section_breakdowns.append({
                "section_id": str(sec_id) if sec_id else "default",
                "title": sec_title,
                "max_marks": float(sec_effective_max),
                "obtained_marks": float(_round_decimal(sec_obtained_capped, rounding_prec)),
                "questions_count": len(qq_list),
                "attempted_count": attempted_in_sec,
                "compulsory_count": req_count if sec_rule == "answer_n_of_m" else len(qq_list),
            })

        # Apply negative marks to net score
        net_score = earned_score - total_negative_marks
        # Floor policy: examination total cannot be negative unless explicitly permitted
        final_score = max(Decimal("0.00"), _round_decimal(net_score, rounding_prec))

        if total_quiz_marks > 0:
            percentage = _round_decimal((final_score / total_quiz_marks) * Decimal("100.00"), rounding_prec)
        else:
            percentage = Decimal("0.00")

        # Determine passing status
        if passing_marks_cfg is not None:
            is_passed = (final_score >= passing_marks_cfg)
        else:
            is_passed = (percentage >= passing_pct)

        # Update ExaminationResult
        result.score = final_score
        result.maximum_marks = total_quiz_marks
        result.passing_marks = passing_marks_cfg
        result.percentage = percentage
        result.is_passed = is_passed
        result.objective_marks = _round_decimal(total_objective_marks, rounding_prec)
        result.manual_marks = _round_decimal(total_manual_marks, rounding_prec)
        result.negative_marks = _round_decimal(total_negative_marks, rounding_prec)
        result.total_correct = total_correct
        result.total_incorrect = total_incorrect
        result.total_unanswered = total_unanswered
        result.section_scores = section_breakdowns
        result.calculated_at = datetime.now(timezone.utc)
        result.scoring_policy_snapshot = {
            "multiple_choice_method": (getattr(cfg, "scoring_settings", None) or {}).get("multiple_choice_method", "partial_credit"),
            "negative_marking_type": neg_marking_type,
            "fixed_negative_marks": float(fixed_neg_marks),
            "partial_marking_enabled": allow_partial_marking,
            "rounding_precision": rounding_prec,
            "passing_percentage": float(passing_pct),
        }

        # Determine evaluation lifecycle status
        if manual_eval_count > 0 and manual_completed_count < manual_eval_count:
            eval_status = "MANUAL_PENDING"
            job_status = "manual_pending"
        elif manual_eval_count > 0 and any(e.is_flagged_for_moderation and e.moderation_status != "approved" for e in result.evaluations):
            eval_status = "MODERATION_PENDING"
            job_status = "manual_pending"
        else:
            eval_status = "RESULT_READY"
            job_status = "completed"

        result.evaluation_status = eval_status
        if attempt.status not in ["submitted", "expired", "invalidated"]:
            attempt.status = "submitted"

        # Update Job stats
        job.status = job_status
        job.total_questions = total_questions_count
        job.auto_evaluated_count = auto_evaluated_count
        job.manual_eval_count = manual_eval_count
        job.manual_eval_completed = manual_completed_count
        if job_status == "completed":
            job.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(result)
        db.refresh(job)
        return result

    @staticmethod
    def retry_evaluation(db: Session, attempt_id: uuid.UUID, admin: Admin) -> ExaminationResult:
        """Administrative trigger to re-run evaluation job with updated rules or after failure."""
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if not EvaluationService.check_quiz_access(db, admin, attempt.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to re-evaluate this attempt")

        job = EvaluationService.get_or_create_job(db, attempt)
        job.retry_count += 1
        db.commit()

        return EvaluationService.run_evaluation(db, attempt_id, triggered_by=admin)

    @staticmethod
    def get_evaluation_status(db: Session, attempt_id: uuid.UUID, admin: Admin) -> EvaluationJobResponse:
        """Fetch evaluation job progress and execution counts."""
        job = db.query(EvaluationJob).filter(EvaluationJob.attempt_id == attempt_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="No evaluation job found for this attempt")
        if not EvaluationService.check_quiz_access(db, admin, job.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to view evaluation status")
        return job

    @staticmethod
    def list_manual_tasks(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
    ) -> List[EvaluationTaskItem]:
        """List examination attempts with pending manual grading for authorized evaluators."""
        is_super = admin.is_super_admin
        query = db.query(EvaluationJob).join(Quiz).options(
            joinedload(EvaluationJob.quiz).joinedload(Quiz.subject),
            joinedload(EvaluationJob.student),
            joinedload(EvaluationJob.attempt),
        ).filter(EvaluationJob.status == "manual_pending")

        if not is_super:
            # Must own quiz or have an active grading assignment
            assigned_quiz_ids = [
                a.quiz_id for a in db.query(GradingAssignment.quiz_id).filter(
                    GradingAssignment.evaluator_id == admin.id,
                    GradingAssignment.status == "active",
                ).all()
            ]
            query = query.filter(or_(Quiz.created_by == admin.id, Quiz.id.in_(assigned_quiz_ids)))

        if quiz_id:
            query = query.filter(EvaluationJob.quiz_id == quiz_id)

        jobs = query.order_by(EvaluationJob.created_at.asc()).all()
        tasks = []
        for j in jobs:
            stud = j.student
            stud_ident = stud.full_name if stud else "Unknown Candidate"
            tasks.append(EvaluationTaskItem(
                attempt_id=j.attempt_id,
                quiz_id=j.quiz_id,
                quiz_title=j.quiz.title if j.quiz else "Untitled Examination",
                subject_name=j.quiz.subject.subject_name if j.quiz and j.quiz.subject else None,
                student_identifier=stud_ident,
                total_questions=j.total_questions,
                pending_manual_count=max(0, j.manual_eval_count - j.manual_eval_completed),
                submitted_at=j.attempt.submitted_at if j.attempt else None,
                status=j.status,
            ))
        return tasks

    # ====================================================================
    # 2. MANUAL GRADING WORKSPACE
    # ====================================================================

    @staticmethod
    def get_manual_grading_workspace(
        db: Session,
        attempt_id: uuid.UUID,
        admin: Admin,
    ) -> ManualGradingWorkspaceResponse:
        """
        Load candidate responses, questions, and assigned rubrics for authorized evaluators.
        Enforces anonymous/blind grading when configured.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationAttempt.student).joinedload(Student.profile),
            joinedload(ExaminationAttempt.answers),
            joinedload(ExaminationAttempt.result).joinedload(ExaminationResult.evaluations),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=404, detail="Examination attempt not found")

        quiz = attempt.quiz
        if not EvaluationService.check_quiz_access(db, admin, quiz) and not EvaluationService.is_assigned_evaluator(db, admin, quiz.id):
            raise HTTPException(status_code=403, detail="Not authorized to grade this examination")

        # Check anonymous grading setting
        assignment = db.query(GradingAssignment).filter(
            GradingAssignment.quiz_id == quiz.id,
            GradingAssignment.evaluator_id == admin.id,
            GradingAssignment.status == "active",
        ).first()
        is_anonymous = (assignment.anonymous_grading if assignment else False) and not admin.is_super_admin

        student = attempt.student
        if is_anonymous:
            stud_ident = f"CAND-{str(attempt.student_id)[:6].upper()}"
            stud_email = None
            stud_roll = None
        else:
            stud_ident = student.full_name if student else "Candidate"
            stud_email = student.email if student else None
            stud_roll = student.profile.roll_number if student and student.profile else None

        answers_by_qq = {a.quiz_question_id: a for a in attempt.answers}
        evals_by_qq = {e.quiz_question_id: e for e in (attempt.result.evaluations if attempt.result else [])}

        qq_list = db.query(QuizQuestion).options(
            joinedload(QuizQuestion.section),
        ).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.question_order.asc()).all()

        manual_questions = []
        graded_count = 0

        for qq in qq_list:
            snap = qq.question_snapshot or {}
            qtype = snap.get("question_type", "single_choice")
            ans = answers_by_qq.get(qq.id)
            ev = evals_by_qq.get(qq.id)

            # Skip auto-evaluated objective questions in manual workspace
            if qtype in ["single_choice", "true_false", "multiple_choice"]:
                continue
            if qtype == "short_answer" and snap.get("exact_matching"):
                continue

            q_max = Decimal(str(qq.marks or snap.get("marks") or "1.00"))
            q_neg = Decimal(str(qq.negative_marks or snap.get("negative_marks") or "0.00"))

            is_eval = (ev is not None and ev.evaluator_id is not None)
            if is_eval:
                graded_count += 1

            # Fetch associated rubric if configured
            rubric_resp = None
            rubric_id = (qq.scoring_settings or {}).get("rubric_id") or (ev.rubric_id if ev else None)
            if rubric_id:
                rubric = db.query(GradingRubric).options(joinedload(GradingRubric.criteria)).filter(GradingRubric.id == rubric_id).first()
                if rubric:
                    rubric_resp = GradingRubricResponse.model_validate(rubric)

            manual_questions.append(ManualGradingQuestionItem(
                evaluation_id=ev.id if ev else uuid.uuid4(),
                quiz_question_id=qq.id,
                question_order=qq.question_order,
                section_title=qq.section.title if qq.section else "General Section",
                question_text=snap.get("question_text", "Descriptive Question"),
                question_type=qtype,
                max_marks=q_max,
                negative_marks=q_neg,
                student_answer_text=ans.text_response if ans else None,
                student_selected_options=ans.selected_option_ids if ans else None,
                attachments=snap.get("attachments") or [],
                rubric=rubric_resp,
                marks_awarded=ev.marks_awarded if ev else Decimal("0.00"),
                is_evaluated=is_eval,
                is_partially_correct=ev.is_partially_correct if ev else False,
                feedback=ev.feedback if ev else None,
                private_notes=ev.private_notes if ev else None,
                criterion_scores=ev.criterion_scores if ev else None,
                is_flagged_for_moderation=ev.is_flagged_for_moderation if ev else False,
                moderation_status=ev.moderation_status if ev else None,
            ))

        return ManualGradingWorkspaceResponse(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            student_identifier=stud_ident,
            student_email=stud_email,
            student_roll_no=stud_roll,
            submitted_at=attempt.submitted_at,
            total_manual_questions=len(manual_questions),
            graded_count=graded_count,
            evaluation_status=attempt.result.evaluation_status if attempt.result else "PENDING",
            questions=manual_questions,
        )

    @staticmethod
    def save_manual_evaluation(
        db: Session,
        evaluation_id: uuid.UUID,
        req: SaveManualEvaluationRequest,
        admin: Admin,
    ) -> QuestionEvaluation:
        """Save evaluator awarded marks, criterion breakdown, and feedback for a descriptive response."""
        ev = db.query(QuestionEvaluation).options(
            joinedload(QuestionEvaluation.result).joinedload(ExaminationResult.quiz),
            joinedload(QuestionEvaluation.quiz_question),
        ).filter(QuestionEvaluation.id == evaluation_id).first()

        if not ev:
            raise HTTPException(status_code=404, detail="Question evaluation record not found")

        quiz = ev.result.quiz
        if not EvaluationService.check_quiz_access(db, admin, quiz) and not EvaluationService.is_assigned_evaluator(db, admin, quiz.id):
            raise HTTPException(status_code=403, detail="Not authorized to grade this question")

        # Validate awarded score limits
        if req.marks_awarded > ev.max_marks:
            raise HTTPException(status_code=400, detail=f"Awarded marks ({req.marks_awarded}) cannot exceed maximum ({ev.max_marks})")

        ev.marks_awarded = req.marks_awarded
        ev.is_partially_correct = req.is_partially_correct or (req.marks_awarded > 0 and req.marks_awarded < ev.max_marks)
        ev.is_correct = (req.marks_awarded == ev.max_marks)
        ev.feedback = req.feedback
        ev.private_notes = req.private_notes
        ev.evaluator_id = admin.id
        ev.evaluation_type = "manual_grading"
        ev.scoring_reason = f"Graded manually by {admin.full_name}"
        ev.criterion_scores = req.criterion_scores
        ev.is_flagged_for_moderation = req.flag_for_moderation
        if req.flag_for_moderation:
            ev.moderation_status = "pending"

        if req.rubric_id:
            rubric = db.query(GradingRubric).filter(GradingRubric.id == req.rubric_id).first()
            if rubric:
                ev.rubric_id = rubric.id
                ev.rubric_version = rubric.version

        db.commit()
        db.refresh(ev)

        # Recalculate provisional total score for this attempt
        EvaluationService.run_evaluation(db, ev.result.attempt_id, triggered_by=admin)
        return ev

    # ====================================================================
    # 3. RUBRIC & MARKING SCHEME MANAGER
    # ====================================================================

    @staticmethod
    def create_rubric(db: Session, admin: Admin, req: GradingRubricCreate) -> GradingRubricResponse:
        """Create a new grading rubric with criteria."""
        # Verify criteria max marks equal rubric total max marks if criteria provided
        if req.criteria:
            crit_sum = sum(c.max_marks for c in req.criteria)
            if crit_sum != req.total_max_marks:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sum of criteria max marks ({crit_sum}) must equal rubric total ({req.total_max_marks})"
                )

        rubric = GradingRubric(
            subject_id=req.subject_id,
            title=req.title,
            description=req.description,
            applicable_question_types=req.applicable_question_types,
            total_max_marks=req.total_max_marks,
            status=req.status,
            version=1,
            grading_instructions=req.grading_instructions,
            created_by=admin.id,
        )
        db.add(rubric)
        db.flush()

        for idx, c in enumerate(req.criteria):
            crit = GradingCriterion(
                rubric_id=rubric.id,
                title=c.title,
                description=c.description,
                max_marks=c.max_marks,
                criterion_order=c.criterion_order or idx,
                partial_credit_levels=c.partial_credit_levels,
            )
            db.add(crit)

        db.commit()
        db.refresh(rubric)
        return GradingRubricResponse.model_validate(rubric)

    @staticmethod
    def update_rubric(db: Session, admin: Admin, rubric_id: uuid.UUID, req: GradingRubricUpdate) -> GradingRubricResponse:
        """Update rubric and create a version snapshot so historical gradings are preserved."""
        rubric = db.query(GradingRubric).options(joinedload(GradingRubric.criteria)).filter(GradingRubric.id == rubric_id).first()
        if not rubric:
            raise HTTPException(status_code=404, detail="Rubric not found")

        # Snapshot current version before updating
        snapshot = {
            "title": rubric.title,
            "description": rubric.description,
            "total_max_marks": float(rubric.total_max_marks),
            "criteria": [
                {"title": c.title, "max_marks": float(c.max_marks), "levels": c.partial_credit_levels}
                for c in rubric.criteria
            ],
        }
        hist_version = GradingRubricVersion(
            rubric_id=rubric.id,
            version_number=rubric.version,
            snapshot_data=snapshot,
            created_by=admin.id,
        )
        db.add(hist_version)

        rubric.version += 1
        if req.title is not None:
            rubric.title = req.title
        if req.description is not None:
            rubric.description = req.description
        if req.subject_id is not None:
            rubric.subject_id = req.subject_id
        if req.applicable_question_types is not None:
            rubric.applicable_question_types = req.applicable_question_types
        if req.total_max_marks is not None:
            rubric.total_max_marks = req.total_max_marks
        if req.status is not None:
            rubric.status = req.status
        if req.grading_instructions is not None:
            rubric.grading_instructions = req.grading_instructions

        if req.criteria is not None:
            crit_sum = sum(c.max_marks for c in req.criteria)
            if crit_sum != rubric.total_max_marks:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sum of criteria max marks ({crit_sum}) must equal rubric total ({rubric.total_max_marks})"
                )
            # Replace criteria
            db.query(GradingCriterion).filter(GradingCriterion.rubric_id == rubric.id).delete()
            for idx, c in enumerate(req.criteria):
                db.add(GradingCriterion(
                    rubric_id=rubric.id,
                    title=c.title,
                    description=c.description,
                    max_marks=c.max_marks,
                    criterion_order=c.criterion_order or idx,
                    partial_credit_levels=c.partial_credit_levels,
                ))

        db.commit()
        db.refresh(rubric)
        return GradingRubricResponse.model_validate(rubric)

    @staticmethod
    def list_rubrics(
        db: Session,
        admin: Admin,
        subject_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> List[GradingRubricResponse]:
        """List grading rubrics with criteria."""
        query = db.query(GradingRubric).options(
            joinedload(GradingRubric.criteria),
            joinedload(GradingRubric.subject),
            joinedload(GradingRubric.author),
        )
        if subject_id:
            query = query.filter(GradingRubric.subject_id == subject_id)
        if search:
            query = query.filter(GradingRubric.title.ilike(f"%{search}%"))

        rubrics = query.order_by(GradingRubric.updated_at.desc()).all()
        result = []
        for r in rubrics:
            dto = GradingRubricResponse(
                id=r.id,
                title=r.title,
                description=r.description,
                subject_id=r.subject_id,
                subject_name=r.subject.subject_name if r.subject else None,
                applicable_question_types=r.applicable_question_types,
                total_max_marks=r.total_max_marks,
                status=r.status,
                version=r.version,
                grading_instructions=r.grading_instructions,
                created_by=r.created_by,
                created_by_name=r.author.full_name if r.author else None,
                created_at=r.created_at,
                updated_at=r.updated_at,
                criteria=[GradingCriterionResponse.model_validate(c) for c in r.criteria],
            )
            result.append(dto)
        return result

    # ====================================================================
    # 4. EVALUATOR ASSIGNMENTS
    # ====================================================================

    @staticmethod
    def create_grading_assignment(
        db: Session,
        admin: Admin,
        req: GradingAssignmentCreate,
    ) -> GradingAssignmentResponse:
        """Assign an evaluator to a quiz, section, or student group."""
        quiz = db.query(Quiz).filter(Quiz.id == req.quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if not EvaluationService.check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Not authorized to assign evaluators for this quiz")

        evaluator = db.query(Admin).filter(Admin.id == req.evaluator_id).first()
        if not evaluator:
            raise HTTPException(status_code=404, detail="Evaluator not found")

        assignment = GradingAssignment(
            quiz_id=req.quiz_id,
            evaluator_id=req.evaluator_id,
            assigned_by=admin.id,
            assignment_scope=req.assignment_scope,
            target_section_id=req.target_section_id,
            target_quiz_question_id=req.target_quiz_question_id,
            target_student_group=req.target_student_group,
            target_attempt_id=req.target_attempt_id,
            anonymous_grading=req.anonymous_grading,
            deadline_at=req.deadline_at,
            status="active",
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        return GradingAssignmentResponse(
            id=assignment.id,
            quiz_id=assignment.quiz_id,
            quiz_title=quiz.title,
            evaluator_id=assignment.evaluator_id,
            evaluator_name=evaluator.full_name,
            assigned_by=assignment.assigned_by,
            assigned_by_name=admin.full_name,
            assignment_scope=assignment.assignment_scope,
            target_section_id=assignment.target_section_id,
            target_quiz_question_id=assignment.target_quiz_question_id,
            target_student_group=assignment.target_student_group,
            target_attempt_id=assignment.target_attempt_id,
            anonymous_grading=assignment.anonymous_grading,
            deadline_at=assignment.deadline_at,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )

    @staticmethod
    def list_grading_assignments(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
    ) -> List[GradingAssignmentResponse]:
        """List active grading assignments for quiz or current evaluator."""
        is_super = admin.is_super_admin
        query = db.query(GradingAssignment).join(Quiz).options(
            joinedload(GradingAssignment.quiz),
            joinedload(GradingAssignment.evaluator),
            joinedload(GradingAssignment.assigner),
        )
        if not is_super:
            query = query.filter(or_(Quiz.created_by == admin.id, GradingAssignment.evaluator_id == admin.id))
        if quiz_id:
            query = query.filter(GradingAssignment.quiz_id == quiz_id)

        assignments = query.order_by(GradingAssignment.created_at.desc()).all()
        result = []
        for a in assignments:
            result.append(GradingAssignmentResponse(
                id=a.id,
                quiz_id=a.quiz_id,
                quiz_title=a.quiz.title if a.quiz else "Untitled Examination",
                evaluator_id=a.evaluator_id,
                evaluator_name=a.evaluator.full_name if a.evaluator else None,
                assigned_by=a.assigned_by,
                assigned_by_name=a.assigner.full_name if a.assigner else None,
                assignment_scope=a.assignment_scope,
                target_section_id=a.target_section_id,
                target_quiz_question_id=a.target_quiz_question_id,
                target_student_group=a.target_student_group,
                target_attempt_id=a.target_attempt_id,
                anonymous_grading=a.anonymous_grading,
                deadline_at=a.deadline_at,
                status=a.status,
                created_at=a.created_at,
                updated_at=a.updated_at,
            ))
        return result

    # ====================================================================
    # 5. MODERATION & REVIEW
    # ====================================================================

    @staticmethod
    def list_moderation_evaluations(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
    ) -> List[ModerationEvaluationItem]:
        """List evaluations requiring moderation review or marks override."""
        is_super = admin.is_super_admin
        query = db.query(QuestionEvaluation).join(ExaminationResult).join(Quiz).options(
            joinedload(QuestionEvaluation.result).joinedload(ExaminationResult.attempt).joinedload(ExaminationAttempt.student),
            joinedload(QuestionEvaluation.quiz_question),
            joinedload(QuestionEvaluation.evaluator),
            joinedload(QuestionEvaluation.attempt_answer),
        ).filter(
            or_(
                QuestionEvaluation.is_flagged_for_moderation == True,
                QuestionEvaluation.moderation_status == "pending",
            )
        )
        if not is_super:
            query = query.filter(Quiz.created_by == admin.id)
        if quiz_id:
            query = query.filter(ExaminationResult.quiz_id == quiz_id)

        evals = query.order_by(QuestionEvaluation.created_at.asc()).all()
        items = []
        for e in evals:
            res = e.result
            stud = res.student if res else None
            qq = e.quiz_question
            snap = qq.question_snapshot if qq else {}
            items.append(ModerationEvaluationItem(
                evaluation_id=e.id,
                result_id=res.id,
                attempt_id=res.attempt_id,
                quiz_id=res.quiz_id,
                quiz_title=res.quiz.title if res and res.quiz else "Examination",
                student_identifier=stud.full_name if stud else "Candidate",
                quiz_question_id=e.quiz_question_id,
                question_text=snap.get("question_text", "Question"),
                question_type=snap.get("question_type", "descriptive"),
                max_marks=e.max_marks,
                student_answer_text=e.attempt_answer.text_response if e.attempt_answer else None,
                evaluator_id=e.evaluator_id,
                evaluator_name=e.evaluator.full_name if e.evaluator else None,
                marks_awarded=e.marks_awarded,
                feedback=e.feedback,
                private_notes=e.private_notes,
                is_flagged_for_moderation=e.is_flagged_for_moderation,
                moderation_status=e.moderation_status,
                override_reason=e.override_reason,
                created_at=e.created_at,
            ))
        return items

    @staticmethod
    def process_moderation_action(
        db: Session,
        evaluation_id: uuid.UUID,
        req: ModerationActionRequest,
        admin: Admin,
    ) -> QuestionEvaluation:
        """Approve, return, or override manually graded marks with an audit trail."""
        ev = db.query(QuestionEvaluation).options(
            joinedload(QuestionEvaluation.result).joinedload(ExaminationResult.quiz),
        ).filter(QuestionEvaluation.id == evaluation_id).first()

        if not ev:
            raise HTTPException(status_code=404, detail="Question evaluation record not found")

        quiz = ev.result.quiz
        if not EvaluationService.check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Not authorized to moderate evaluations for this quiz")

        res = ev.result
        old_score = res.score
        old_pct = res.percentage

        ev.moderator_id = admin.id
        ev.moderation_status = req.action

        if req.action == "approve":
            ev.is_flagged_for_moderation = False
            ev.moderation_status = "approved"

        elif req.action == "return":
            if not req.reason:
                raise HTTPException(status_code=400, detail="Reason required to return evaluation for review")
            ev.moderation_status = "returned"
            ev.private_notes = f"[RETURNED BY {admin.full_name}]: {req.reason}\n" + (ev.private_notes or "")

        elif req.action == "override":
            if req.new_marks is None:
                raise HTTPException(status_code=400, detail="new_marks is required for moderation override")
            if req.new_marks > ev.max_marks:
                raise HTTPException(status_code=400, detail=f"Override marks ({req.new_marks}) cannot exceed maximum ({ev.max_marks})")
            if not req.reason:
                raise HTTPException(status_code=400, detail="Documented reason required for marks override")

            ev.original_marks = ev.marks_awarded
            ev.marks_awarded = req.new_marks
            ev.is_partially_correct = (req.new_marks > 0 and req.new_marks < ev.max_marks)
            ev.is_correct = (req.new_marks == ev.max_marks)
            ev.override_reason = req.reason
            ev.is_flagged_for_moderation = False
            ev.moderation_status = "overridden"

        db.commit()

        # Recalculate result
        EvaluationService.run_evaluation(db, res.attempt_id, triggered_by=admin)
        db.refresh(res)

        # Log correction if marks changed
        if req.action == "override":
            correction = ResultCorrection(
                result_id=res.id,
                quiz_id=res.quiz_id,
                student_id=res.student_id,
                previous_score=old_score,
                new_score=res.score,
                previous_percentage=old_pct,
                new_percentage=res.percentage,
                previous_status=res.evaluation_status,
                new_status=res.evaluation_status,
                reason=f"Moderation override: {req.reason}",
                corrected_by=admin.id,
                correction_type="moderation_override",
            )
            db.add(correction)
            db.commit()

        return ev

    # ====================================================================
    # 6. RESULTS MANAGEMENT, APPROVAL & PUBLICATION
    # ====================================================================

    @staticmethod
    def list_results(
        db: Session,
        admin: Admin,
        quiz_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        is_approved: Optional[bool] = None,
        is_passed: Optional[bool] = None,
        page: int = 1,
        limit: int = 25,
    ) -> ResultListResponse:
        """List examination results with filters, search, and scoping."""
        is_super = admin.is_super_admin
        query = db.query(ExaminationResult).join(Quiz).join(Student).options(
            joinedload(ExaminationResult.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationResult.student).joinedload(Student.profile),
        )

        if not is_super:
            query = query.filter(Quiz.created_by == admin.id)
        if quiz_id:
            query = query.filter(ExaminationResult.quiz_id == quiz_id)
        if is_published is not None:
            query = query.filter(ExaminationResult.is_published == is_published)
        if is_approved is not None:
            query = query.filter(ExaminationResult.is_approved == is_approved)
        if is_passed is not None:
            query = query.filter(ExaminationResult.is_passed == is_passed)
        if search:
            query = query.filter(
                or_(
                    Student.full_name.ilike(f"%{search}%"),
                    Student.email.ilike(f"%{search}%"),
                    Quiz.title.ilike(f"%{search}%"),
                )
            )

        total = query.count()
        pages = (total + limit - 1) // limit if total > 0 else 1
        records = query.order_by(ExaminationResult.calculated_at.desc()).offset((page - 1) * limit).limit(limit).all()

        items = []
        for r in records:
            stud = r.student
            prof = stud.profile if stud else None
            items.append(ResultListItemResponse(
                id=r.id,
                attempt_id=r.attempt_id,
                quiz_id=r.quiz_id,
                quiz_title=r.quiz.title if r.quiz else "Examination",
                subject_name=r.quiz.subject.subject_name if r.quiz and r.quiz.subject else None,
                student_id=r.student_id,
                student_name=stud.full_name if stud else "Unknown Candidate",
                student_email=stud.email if stud else "",
                student_roll_no=prof.roll_number if prof else None,
                score=r.score,
                maximum_marks=r.maximum_marks,
                percentage=r.percentage,
                is_passed=r.is_passed,
                evaluation_status=r.evaluation_status,
                is_approved=r.is_approved,
                is_published=r.is_published,
                calculated_at=r.calculated_at,
            ))

        return ResultListResponse(items=items, total=total, page=page, limit=limit, pages=pages)

    @staticmethod
    def get_result_detail(db: Session, result_id: uuid.UUID, admin: Admin) -> ResultDetailResponse:
        """Fetch exhaustive score breakdown, question evaluations, and correction history."""
        res = db.query(ExaminationResult).options(
            joinedload(ExaminationResult.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationResult.student).joinedload(Student.profile),
            joinedload(ExaminationResult.approver),
            joinedload(ExaminationResult.publisher),
            joinedload(ExaminationResult.evaluations).joinedload(QuestionEvaluation.quiz_question),
            joinedload(ExaminationResult.evaluations).joinedload(QuestionEvaluation.attempt_answer),
            joinedload(ExaminationResult.corrections).joinedload(ResultCorrection.author),
        ).filter(ExaminationResult.id == result_id).first()

        if not res:
            raise HTTPException(status_code=404, detail="Examination result not found")

        if not EvaluationService.check_quiz_access(db, admin, res.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to access this examination result")

        eval_details = []
        for e in sorted(res.evaluations, key=lambda x: x.quiz_question.question_order if x.quiz_question else 0):
            qq = e.quiz_question
            snap = qq.question_snapshot if qq else {}
            ans = e.attempt_answer
            correct_opts = [
                str(opt.get("text") or opt.get("id"))
                for opt in (snap.get("options") or [])
                if opt.get("is_correct")
            ]
            eval_details.append(QuestionEvaluationDetail(
                evaluation_id=e.id,
                quiz_question_id=e.quiz_question_id,
                question_order=qq.question_order if qq else 0,
                question_text=snap.get("question_text", "Question"),
                question_type=snap.get("question_type", "single_choice"),
                max_marks=e.max_marks,
                marks_awarded=e.marks_awarded,
                negative_deduction=e.negative_deduction,
                is_correct=e.is_correct,
                is_partially_correct=e.is_partially_correct,
                feedback=e.feedback,
                evaluation_type=e.evaluation_type,
                scoring_reason=e.scoring_reason,
                user_selected_options=ans.selected_option_ids if ans else None,
                user_text_response=ans.text_response if ans else None,
                correct_answers=correct_opts if correct_opts else None,
                explanations=snap.get("explanation"),
            ))

        correction_details = []
        for c in res.corrections:
            correction_details.append(ResultCorrectionDetail(
                id=c.id,
                previous_score=c.previous_score,
                new_score=c.new_score,
                previous_percentage=c.previous_percentage,
                new_percentage=c.new_percentage,
                reason=c.reason,
                corrected_by_name=c.author.full_name if c.author else None,
                correction_type=c.correction_type,
                created_at=c.created_at,
            ))

        stud = res.student
        prof = stud.profile if stud else None
        return ResultDetailResponse(
            id=res.id,
            attempt_id=res.attempt_id,
            quiz_id=res.quiz_id,
            quiz_title=res.quiz.title if res.quiz else "Examination",
            subject_name=res.quiz.subject.subject_name if res.quiz and res.quiz.subject else None,
            student_id=res.student_id,
            student_name=stud.full_name if stud else "Candidate",
            student_email=stud.email if stud else "",
            student_roll_no=prof.roll_number if prof else None,
            score=res.score,
            maximum_marks=res.maximum_marks,
            passing_marks=res.passing_marks,
            percentage=res.percentage,
            is_passed=res.is_passed,
            objective_marks=res.objective_marks,
            manual_marks=res.manual_marks,
            negative_marks=res.negative_marks,
            total_correct=res.total_correct,
            total_incorrect=res.total_incorrect,
            total_unanswered=res.total_unanswered,
            rank=res.rank,
            percentile=res.percentile,
            evaluation_status=res.evaluation_status,
            is_approved=res.is_approved,
            approved_at=res.approved_at,
            approved_by_name=res.approver.full_name if res.approver else None,
            approval_notes=res.approval_notes,
            is_published=res.is_published,
            published_at=res.published_at,
            published_by_name=res.publisher.full_name if res.publisher else None,
            result_version=res.result_version,
            section_scores=[SectionScoreDetail(**s) for s in (res.section_scores or [])],
            evaluations=eval_details,
            corrections=correction_details,
            calculated_at=res.calculated_at,
        )

    @staticmethod
    def approve_result(
        db: Session,
        result_id: uuid.UUID,
        admin: Admin,
        approval_notes: Optional[str] = None,
    ) -> ExaminationResult:
        """Approve examination result after verifying manual grading is completed."""
        res = db.query(ExaminationResult).options(
            joinedload(ExaminationResult.quiz),
            joinedload(ExaminationResult.evaluations),
        ).filter(ExaminationResult.id == result_id).first()

        if not res:
            raise HTTPException(status_code=404, detail="Result not found")
        if not EvaluationService.check_quiz_access(db, admin, res.quiz):
            raise HTTPException(status_code=403, detail="Not authorized to approve results for this quiz")

        # Do not approve if pending manual grading remains
        has_pending = any(e.evaluation_type == "manual_grading" and e.evaluator_id is None for e in res.evaluations)
        if has_pending:
            raise HTTPException(status_code=400, detail="Cannot approve result while manual evaluations are incomplete")

        res.is_approved = True
        res.approved_at = datetime.now(timezone.utc)
        res.approved_by = admin.id
        res.approval_notes = approval_notes
        res.evaluation_status = "APPROVED"

        db.commit()
        db.refresh(res)
        return res

    @staticmethod
    def batch_approve_results(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        approval_notes: Optional[str] = None,
    ) -> int:
        """Approve all eligible completed results for a quiz."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if not EvaluationService.check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Not authorized")

        results = db.query(ExaminationResult).options(
            joinedload(ExaminationResult.evaluations),
        ).filter(
            ExaminationResult.quiz_id == quiz_id,
            ExaminationResult.is_approved == False,
        ).all()

        approved_count = 0
        now = datetime.now(timezone.utc)
        for r in results:
            has_pending = any(e.evaluation_type == "manual_grading" and e.evaluator_id is None for e in r.evaluations)
            if not has_pending:
                r.is_approved = True
                r.approved_at = now
                r.approved_by = admin.id
                r.approval_notes = approval_notes or "Batch approved"
                r.evaluation_status = "APPROVED"
                approved_count += 1

        db.commit()
        return approved_count

    @staticmethod
    def publish_result(
        db: Session,
        result_id: uuid.UUID,
        admin: Admin,
        publish: bool = True,
    ) -> ExaminationResult:
        """Publish or unpublish an approved examination result."""
        res = db.query(ExaminationResult).options(
            joinedload(ExaminationResult.quiz),
        ).filter(ExaminationResult.id == result_id).first()

        if not res:
            raise HTTPException(status_code=404, detail="Result not found")
        if not EvaluationService.check_quiz_access(db, admin, res.quiz):
            raise HTTPException(status_code=403, detail="Not authorized")

        if publish:
            res.is_published = True
            res.published_at = datetime.now(timezone.utc)
            res.published_by = admin.id
            res.evaluation_status = "RESULT_PUBLISHED"
        else:
            res.is_published = False
            res.evaluation_status = "APPROVED" if res.is_approved else "RESULT_READY"

        db.commit()
        db.refresh(res)
        return res

    @staticmethod
    def batch_publish_results(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        publish: bool = True,
    ) -> int:
        """Batch publish all approved results for a quiz."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if not EvaluationService.check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Not authorized")

        query = db.query(ExaminationResult).filter(
            ExaminationResult.quiz_id == quiz_id,
            ExaminationResult.is_approved == True,
        )
        results = query.all()
        now = datetime.now(timezone.utc)
        count = 0
        for r in results:
            if publish:
                r.is_published = True
                r.published_at = now
                r.published_by = admin.id
                r.evaluation_status = "RESULT_PUBLISHED"
            else:
                r.is_published = False
                r.evaluation_status = "APPROVED"
            count += 1

        db.commit()
        return count

    @staticmethod
    def override_result(
        db: Session,
        result_id: uuid.UUID,
        admin: Admin,
        new_score: Decimal,
        reason: str,
    ) -> ExaminationResult:
        """Administrative mark override with immutable audit history."""
        res = db.query(ExaminationResult).options(
            joinedload(ExaminationResult.quiz).joinedload(Quiz.configuration),
        ).filter(ExaminationResult.id == result_id).first()

        if not res:
            raise HTTPException(status_code=404, detail="Result not found")
        if not EvaluationService.check_quiz_access(db, admin, res.quiz):
            raise HTTPException(status_code=403, detail="Not authorized")
        if new_score > res.maximum_marks:
            raise HTTPException(status_code=400, detail=f"New score ({new_score}) cannot exceed maximum ({res.maximum_marks})")

        old_score = res.score
        old_pct = res.percentage
        old_status = res.evaluation_status

        cfg = res.quiz.configuration
        rounding_prec = cfg.rounding_precision if cfg and cfg.rounding_precision is not None else 2
        passing_pct = Decimal(str(cfg.passing_percentage if cfg and cfg.passing_percentage is not None else "40.00"))

        new_pct = _round_decimal((new_score / res.maximum_marks) * Decimal("100.00"), rounding_prec) if res.maximum_marks > 0 else Decimal("0.00")
        is_passed = (new_pct >= passing_pct)

        res.score = new_score
        res.percentage = new_pct
        res.is_passed = is_passed
        res.result_version += 1

        correction = ResultCorrection(
            result_id=res.id,
            quiz_id=res.quiz_id,
            student_id=res.student_id,
            previous_score=old_score,
            new_score=new_score,
            previous_percentage=old_pct,
            new_percentage=new_pct,
            previous_status=old_status,
            new_status=res.evaluation_status,
            reason=reason,
            corrected_by=admin.id,
            correction_type="manual_override",
        )
        db.add(correction)
        db.commit()
        db.refresh(res)
        return res

    # ====================================================================
    # 7. STUDENT RESULT EXPERIENCE (PRIVACY & RELEASE POLICIES)
    # ====================================================================

    @staticmethod
    def get_student_result(
        db: Session,
        attempt_id: uuid.UUID,
        session_student_id: Optional[uuid.UUID] = None,
    ) -> StudentResultResponse:
        """
        Student-facing result view:
        - Validates student identity and attempt ownership.
        - Respects result_release_policy from Phase 10:
          'immediate', 'after_close', 'after_manual_eval', 'after_admin_approval', 'never'
        - Hides internal notes, answer keys, and explanations unless authorized.
        """
        attempt = db.query(ExaminationAttempt).options(
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.configuration),
            joinedload(ExaminationAttempt.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationAttempt.student).joinedload(Student.profile),
            joinedload(ExaminationAttempt.result).joinedload(ExaminationResult.evaluations).joinedload(QuestionEvaluation.quiz_question),
            joinedload(ExaminationAttempt.result).joinedload(ExaminationResult.evaluations).joinedload(QuestionEvaluation.attempt_answer),
        ).filter(ExaminationAttempt.id == attempt_id).first()

        if not attempt:
            raise HTTPException(status_code=404, detail="Examination attempt not found")

        # Student ownership check
        if session_student_id and attempt.student_id != session_student_id:
            raise HTTPException(status_code=403, detail="Not authorized to view results for this candidate")

        quiz = attempt.quiz
        cfg = quiz.configuration
        res = attempt.result

        now = datetime.now(timezone.utc)
        release_policy = cfg.result_release_policy if cfg else "immediate"
        show_score_cfg = cfg.show_score_immediately if cfg else True
        show_correct_cfg = cfg.show_correct_answers if cfg else False
        show_keys_cfg = cfg.show_answer_keys if cfg else False
        show_expl_cfg = cfg.show_explanations if cfg else False
        show_sec_cfg = cfg.show_section_breakdown if cfg else True

        # Determine release eligibility
        is_released = False
        status_msg = "Official results are being prepared."

        if not res:
            is_released = False
            status_msg = "Your examination has been submitted. Evaluation is currently in progress."
        elif release_policy == "never":
            is_released = False
            status_msg = "Results for this examination are confidential and will not be displayed online."
        elif res.is_published:
            is_released = True
            status_msg = "Official examination results published."
        elif release_policy == "immediate":
            if res.evaluation_status in ["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]:
                is_released = True
                status_msg = "Official examination result ready."
            else:
                is_released = False
                status_msg = "Your examination has been submitted successfully. Some answers are awaiting manual evaluation. Your final result will be available after evaluation and approval."
        elif release_policy == "after_close":
            quiz_closed = (cfg and cfg.end_time and _ensure_utc(cfg.end_time) <= now)
            if quiz_closed and res.evaluation_status in ["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]:
                is_released = True
                status_msg = "Examination window closed. Official results released."
            else:
                is_released = False
                status_msg = "Results will become available after the examination window closes."
        elif release_policy == "after_manual_eval":
            if res.evaluation_status in ["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]:
                is_released = True
                status_msg = "Manual evaluation completed. Results released."
            else:
                is_released = False
                status_msg = "Your responses are currently undergoing manual evaluation by the examiner."
        elif release_policy == "after_admin_approval":
            if res.is_approved:
                is_released = True
                status_msg = "Results approved and released by the examination administrator."
            else:
                is_released = False
                status_msg = "Examination results are pending administrative approval."

        stud = attempt.student
        stud_name = stud.full_name if stud else "Candidate"
        stud_roll = stud.profile.roll_number if stud and stud.profile else None
        masked_reg = (stud_roll[:2] + "****" + stud_roll[-2:]) if stud_roll and len(stud_roll) > 4 else stud_roll

        # Question breakdowns if permitted
        question_breakdowns = None
        if is_released and (show_correct_cfg or show_keys_cfg or show_expl_cfg) and res:
            question_breakdowns = []
            for e in sorted(res.evaluations, key=lambda x: x.quiz_question.question_order if x.quiz_question else 0):
                qq = e.quiz_question
                snap = qq.question_snapshot if qq else {}
                ans = e.attempt_answer
                correct_opts = [
                    str(opt.get("text") or opt.get("id"))
                    for opt in (snap.get("options") or [])
                    if opt.get("is_correct")
                ] if show_correct_cfg else None

                question_breakdowns.append(QuestionEvaluationDetail(
                    evaluation_id=e.id,
                    quiz_question_id=e.quiz_question_id,
                    question_order=qq.question_order if qq else 0,
                    question_text=snap.get("question_text", "Question"),
                    question_type=snap.get("question_type", "single_choice"),
                    max_marks=e.max_marks,
                    marks_awarded=e.marks_awarded,
                    negative_deduction=e.negative_deduction,
                    is_correct=e.is_correct,
                    is_partially_correct=e.is_partially_correct,
                    feedback=e.feedback,
                    evaluation_type=e.evaluation_type,
                    scoring_reason=e.scoring_reason if show_expl_cfg else None,
                    user_selected_options=ans.selected_option_ids if ans else None,
                    user_text_response=ans.text_response if ans else None,
                    correct_answers=correct_opts,
                    explanations=snap.get("explanation") if show_expl_cfg else None,
                ))

        section_scores = [SectionScoreDetail(**s) for s in (res.section_scores or [])] if (res and show_sec_cfg) else None

        return StudentResultResponse(
            quiz_title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            student_name=stud_name,
            student_masked_reg=masked_reg,
            examination_date=attempt.submitted_at or attempt.started_at,
            obtained_marks=res.score if (res and is_released and show_score_cfg) else Decimal("0.00"),
            maximum_marks=res.maximum_marks if res else Decimal("100.00"),
            percentage=res.percentage if (res and is_released and show_score_cfg) else Decimal("0.00"),
            is_passed=res.is_passed if (res and is_released) else False,
            pass_fail_label=("PASSED" if res and res.is_passed else "NEEDS IMPROVEMENT") if (res and is_released) else "PENDING",
            evaluation_status=res.evaluation_status if res else "PENDING",
            is_provisional=not is_released or (res and not res.is_approved),
            status_message=status_msg,
            is_released=is_released,
            show_score=is_released and show_score_cfg,
            show_section_breakdown=is_released and show_sec_cfg,
            show_correct_answers=is_released and show_correct_cfg,
            show_answer_keys=is_released and show_keys_cfg,
            show_explanations=is_released and show_expl_cfg,
            section_scores=section_scores,
            questions=question_breakdowns,
        )
