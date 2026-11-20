import uuid
import statistics
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy import func, or_, and_, desc, asc
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizQuestion, QuizSection, QuizConfiguration
from backend.app.models.registration import QuizParticipant
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer, AttemptSession
from backend.app.models.results import ExaminationResult, QuestionEvaluation
from backend.app.models.security_audit import SecurityEvent, SecurityAlert
from backend.app.models.analytics import QuestionReviewFlag
from backend.app.schemas.quiz_analytics import (
    QuizMetadataInfo,
    QuizOverviewAnalyticsResponse,
    QuizParticipantAnalyticsResponse,
    ParticipantDetailItem,
    StudentPerformanceItem,
    StudentPerformanceListResponse,
    StudentQuestionPerformanceItem,
    StudentSectionPerformanceItem,
    StudentProfileAnalyticsResponse,
    QuestionOptionStat,
    QuestionAnalysisItem,
    QuizQuestionAnalysisResponse,
    SectionAnalysisItem,
    QuizSectionAnalysisResponse,
    AcademicTopicAnalysisItem,
    QuizAcademicAnalysisResponse,
    DifficultyAnalysisItem,
    QuizDifficultyAnalysisResponse,
    QuestionTypeAnalysisItem,
    QuizQuestionTypeAnalysisResponse,
    TimeAnalysisResponse,
    NegativeMarkingAnalysisResponse,
    SecuritySummaryResponse,
    StudentComparisonItem,
    StudentComparisonResponse,
    QuestionReviewFlagCreateRequest,
    QuestionReviewFlagResponse,
    ScoreBandItem,
)


class QuizAnalyticsService:

    @staticmethod
    def check_quiz_access(db: Session, admin: Admin, quiz_id: uuid.UUID) -> Quiz:
        """
        Enforce strict RBAC:
        Super Admin: access to all quizzes.
        User Admin: must have created the quiz or be explicitly assigned to it.
        """
        quiz = (
            db.query(Quiz)
            .options(
                joinedload(Quiz.subject),
                joinedload(Quiz.programme),
                joinedload(Quiz.semester),
                joinedload(Quiz.configuration),
            )
            .filter(Quiz.id == quiz_id)
            .first()
        )
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Examination quiz with ID '{quiz_id}' not found.",
            )

        if admin.is_super_admin:
            return quiz

        # User Admin ownership or assignment check
        if quiz.created_by == admin.id:
            return quiz

        assignment = (
            db.query(AdminQuizAssignment)
            .filter(
                AdminQuizAssignment.admin_id == admin.id,
                AdminQuizAssignment.quiz_id == quiz.id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have administrative authorization to access analytics for this examination.",
            )

        return quiz

    @staticmethod
    def get_overview(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> QuizOverviewAnalyticsResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        # 1. Base Quiz Metadata
        qq_count = db.query(func.count(QuizQuestion.id)).filter(QuizQuestion.quiz_id == quiz.id).scalar() or 0
        cfg = quiz.configuration
        max_marks = float(quiz.total_marks or 0.0)
        duration_minutes = quiz.duration_minutes or 60

        quiz_info = QuizMetadataInfo(
            id=quiz.id,
            title=quiz.title,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            programme_name=quiz.programme.name if quiz.programme else None,
            semester_name=quiz.semester.semester_name if quiz.semester else None,
            creation_mode=quiz.creation_mode,
            published_version=quiz.published_version or 1,
            max_marks=max_marks,
            duration_minutes=duration_minutes,
            total_questions=qq_count,
            status=quiz.status,
            created_at=quiz.created_at,
        )

        # 2. Participant & Attempt Counts
        total_registered = (
            db.query(func.count(QuizParticipant.id))
            .filter(QuizParticipant.quiz_id == quiz.id)
            .scalar()
            or 0
        )
        total_eligible = (
            db.query(func.count(QuizParticipant.id))
            .filter(QuizParticipant.quiz_id == quiz.id, QuizParticipant.status != "rejected")
            .scalar()
            or 0
        )

        attempts = (
            db.query(ExaminationAttempt)
            .filter(ExaminationAttempt.quiz_id == quiz.id)
            .all()
        )
        started_attempts = sum(1 for a in attempts if a.started_at is not None)
        submitted_attempts = sum(1 for a in attempts if a.status in ("submitted", "time_expired"))
        
        # Submission status counts
        status_breakdown: Dict[str, int] = {}
        for a in attempts:
            status_breakdown[a.status] = status_breakdown.get(a.status, 0) + 1

        # 3. Results Metrics
        results = (
            db.query(ExaminationResult)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        completed_evaluations = sum(1 for r in results if r.evaluation_status in ("evaluated", "approved", "published"))
        pending_evaluations = sum(1 for a in attempts if a.status in ("submitted", "time_expired")) - completed_evaluations
        pending_evaluations = max(0, pending_evaluations)

        pass_count = sum(1 for r in results if r.is_passed is True)
        fail_count = sum(1 for r in results if r.is_passed is False)
        
        percentages = [float(r.percentage or 0.0) for r in results if r.percentage is not None]
        avg_pct = round(statistics.mean(percentages), 2) if percentages else 0.0
        high_pct = round(max(percentages), 2) if percentages else 0.0
        low_pct = round(min(percentages), 2) if percentages else 0.0
        median_pct = round(statistics.median(percentages), 2) if percentages else 0.0
        pass_pct = round((pass_count / len(results) * 100), 2) if results else 0.0
        completion_rate = round((submitted_attempts / started_attempts * 100), 2) if started_attempts else 0.0

        # Pass / Fail chart
        pass_fail_chart = {"Passed": pass_count, "Failed": fail_count}

        # Score distribution histogram (10 bands: 0-10, 11-20, ..., 91-100)
        bands_def = [
            ("0-10%", 0.0, 10.0),
            ("11-20%", 10.01, 20.0),
            ("21-30%", 20.01, 30.0),
            ("31-40%", 30.01, 40.0),
            ("41-50%", 40.01, 50.0),
            ("51-60%", 50.01, 60.0),
            ("61-70%", 60.01, 70.0),
            ("71-80%", 70.01, 80.0),
            ("81-90%", 80.01, 90.0),
            ("91-100%", 90.01, 100.0),
        ]
        score_distribution = []
        for label, b_min, b_max in bands_def:
            cnt = sum(1 for p in percentages if b_min <= p <= b_max)
            score_distribution.append(ScoreBandItem(band=label, min_pct=b_min, max_pct=b_max, count=cnt))

        # Participation Funnel
        published_results = sum(1 for r in results if r.is_published)
        participation_funnel = [
            {"stage": "Registered", "count": total_registered},
            {"stage": "Eligible", "count": total_eligible},
            {"stage": "Started", "count": started_attempts},
            {"stage": "Submitted", "count": submitted_attempts},
            {"stage": "Evaluated", "count": completed_evaluations},
            {"stage": "Result Published", "count": published_results},
        ]

        # Section Performance comparison
        sections = (
            db.query(QuizSection)
            .filter(QuizSection.quiz_id == quiz.id)
            .order_by(QuizSection.section_order.asc())
            .all()
        )
        section_comparison = []
        for sec in sections:
            # Gather question evaluations in this section
            sec_qq_ids = [
                qq.id
                for qq in db.query(QuizQuestion.id)
                .filter(QuizQuestion.section_id == sec.id)
                .all()
            ]
            if sec_qq_ids:
                sec_evals = (
                    db.query(QuestionEvaluation)
                    .filter(QuestionEvaluation.quiz_question_id.in_(sec_qq_ids))
                    .all()
                )
                sec_awarded = sum(float(e.marks_awarded or 0.0) for e in sec_evals)
                sec_max = sum(float(e.max_marks or 0.0) for e in sec_evals)
                sec_pct = round((sec_awarded / sec_max * 100), 2) if sec_max > 0 else 0.0
                section_comparison.append({
                    "section_id": str(sec.id),
                    "section_title": sec.title,
                    "average_percentage": sec_pct,
                    "total_questions": len(sec_qq_ids),
                })

        # Difficulty Accuracy breakdown
        diff_map: Dict[str, List[bool]] = {"easy": [], "medium": [], "hard": []}
        all_qqs = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        qq_diff_lookup = {}
        for qq in all_qqs:
            snap = qq.question_snapshot or {}
            d = (snap.get("difficulty") or "medium").lower()
            if d not in diff_map:
                diff_map[d] = []
            qq_diff_lookup[qq.id] = d

        evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        for e in evals:
            d = qq_diff_lookup.get(e.quiz_question_id, "medium")
            if d in diff_map:
                diff_map[d].append(bool(e.is_correct))

        difficulty_accuracy = {}
        for d, bools in diff_map.items():
            if bools:
                difficulty_accuracy[d] = round((sum(bools) / len(bools) * 100), 2)
            else:
                difficulty_accuracy[d] = 0.0

        is_provisional = any(r.evaluation_status != "published" for r in results)

        return QuizOverviewAnalyticsResponse(
            quiz_info=quiz_info,
            freshness_timestamp=datetime.now(timezone.utc),
            is_provisional=is_provisional,
            total_registered=total_registered,
            total_eligible=total_eligible,
            started_attempts=started_attempts,
            submitted_attempts=submitted_attempts,
            completed_evaluations=completed_evaluations,
            pending_evaluations=pending_evaluations,
            pass_count=pass_count,
            fail_count=fail_count,
            average_percentage=avg_pct,
            highest_percentage=high_pct,
            lowest_percentage=low_pct,
            median_percentage=median_pct,
            pass_percentage=pass_pct,
            completion_rate=completion_rate,
            pass_fail_chart=pass_fail_chart,
            score_distribution=score_distribution,
            participation_funnel=participation_funnel,
            submission_status_breakdown=status_breakdown,
            section_comparison=section_comparison,
            difficulty_accuracy=difficulty_accuracy,
            records_count=len(results),
        )

    @staticmethod
    def get_participants(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> QuizParticipantAnalyticsResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        # Base query
        query = (
            db.query(QuizParticipant)
            .options(
                joinedload(QuizParticipant.student).joinedload(Student.profile),
                joinedload(QuizParticipant.invitation),
            )
            .filter(QuizParticipant.quiz_id == quiz.id)
        )

        if status_filter and status_filter.lower() != "all":
            query = query.filter(QuizParticipant.status == status_filter.lower())

        total = query.count()
        participants = query.offset((page - 1) * limit).limit(limit).all()

        # Gather attempts and results for these participants
        student_ids = [p.student_id for p in participants]
        attempts_map = {}
        results_map = {}
        if student_ids:
            all_attempts = (
                db.query(ExaminationAttempt)
                .filter(
                    ExaminationAttempt.quiz_id == quiz.id,
                    ExaminationAttempt.student_id.in_(student_ids),
                )
                .all()
            )
            for a in all_attempts:
                # Store latest attempt
                attempts_map[a.student_id] = a

            all_results = (
                db.query(ExaminationResult)
                .filter(
                    ExaminationResult.quiz_id == quiz.id,
                    ExaminationResult.student_id.in_(student_ids),
                )
                .all()
            )
            for r in all_results:
                results_map[r.student_id] = r

        items = []
        for p in participants:
            stu = p.student
            prof = stu.profile if stu else None
            stu_name = stu.full_name if (stu and stu.full_name) else (stu.email if stu else "Unknown Candidate")
            reg_num = getattr(prof, "student_identifier", getattr(prof, "roll_number", None)) if prof else None
            
            att = attempts_map.get(p.student_id)
            res = results_map.get(p.student_id)

            res_status = "unstarted"
            if att:
                if res:
                    res_status = res.evaluation_status
                else:
                    res_status = "pending_evaluation" if att.status in ("submitted", "time_expired") else "in_progress"

            items.append(
                ParticipantDetailItem(
                    student_id=p.student_id,
                    student_name=stu_name,
                    student_email=stu.email if stu else None,
                    register_number=reg_num,
                    registration_status=p.status,
                    invitation_name=p.invitation.name if p.invitation else None,
                    registered_at=p.registered_at,
                    attempt_status=att.status if att else None,
                    attempt_id=att.id if att else None,
                    started_at=att.started_at if att else None,
                    submitted_at=att.submitted_at if att else None,
                    obtained_score=float(res.score) if res and res.score is not None else None,
                    percentage=float(res.percentage) if res and res.percentage is not None else None,
                    is_passed=res.is_passed if res else None,
                    result_status=res_status,
                )
            )

        # Overview counters
        all_parts = db.query(QuizParticipant).filter(QuizParticipant.quiz_id == quiz.id).all()
        total_registered = len(all_parts)
        total_eligible = sum(1 for p in all_parts if p.status != "rejected")
        approved_count = sum(1 for p in all_parts if p.status == "approved")
        rejected_count = sum(1 for p in all_parts if p.status == "rejected")

        all_atts = db.query(ExaminationAttempt).filter(ExaminationAttempt.quiz_id == quiz.id).all()
        started_count = sum(1 for a in all_atts if a.started_at is not None)
        submitted_count = sum(1 for a in all_atts if a.status in ("submitted", "time_expired"))
        unstarted_count = max(0, total_eligible - started_count)
        expired_count = sum(1 for a in all_atts if a.status == "time_expired")
        terminated_count = sum(1 for a in all_atts if a.status == "terminated")
        unique_students = len(set(p.student_id for p in all_parts))

        funnel = [
            {"stage": "Registered", "count": total_registered},
            {"stage": "Eligible", "count": total_eligible},
            {"stage": "Started", "count": started_count},
            {"stage": "Submitted", "count": submitted_count},
        ]

        return QuizParticipantAnalyticsResponse(
            total_registered=total_registered,
            total_eligible=total_eligible,
            approved_count=approved_count,
            rejected_count=rejected_count,
            started_count=started_count,
            submitted_count=submitted_count,
            unstarted_count=unstarted_count,
            expired_count=expired_count,
            terminated_count=terminated_count,
            unique_students_count=unique_students,
            total_attempts_count=len(all_atts),
            funnel=funnel,
            participants=items,
            total=total,
            page=page,
            limit=limit,
        )

    @staticmethod
    def get_student_performance_table(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        result_status: Optional[str] = None,
        evaluation_status: Optional[str] = None,
        sort_by: str = "percentage",
        sort_dir: str = "desc",
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> StudentPerformanceListResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        # Query all attempts with results
        query = (
            db.query(ExaminationAttempt)
            .options(
                joinedload(ExaminationAttempt.student).joinedload(Student.profile),
                joinedload(ExaminationAttempt.result),
            )
            .filter(ExaminationAttempt.quiz_id == quiz.id)
        )

        all_attempts = query.all()

        # Build comprehensive list of performance rows
        rows: List[Dict[str, Any]] = []
        for att in all_attempts:
            stu = att.student
            prof = stu.profile if stu else None
            stu_name = stu.full_name if (stu and stu.full_name) else (stu.email if stu else "Unknown")
            reg_num = getattr(prof, "student_identifier", getattr(prof, "roll_number", None)) if prof else None
            res = att.result

            # Filter search
            if search:
                s_lower = search.strip().lower()
                name_match = s_lower in stu_name.lower()
                reg_match = reg_num and s_lower in reg_num.lower()
                if not (name_match or reg_match):
                    continue

            # Status filtering
            if evaluation_status and evaluation_status.lower() != "all":
                eval_st = res.evaluation_status if res else "pending"
                if eval_st.lower() != evaluation_status.lower():
                    continue

            if result_status and result_status.lower() != "all":
                if result_status.lower() == "passed" and (not res or not res.is_passed):
                    continue
                if result_status.lower() == "failed" and (not res or res.is_passed is not False):
                    continue

            rows.append({
                "student_id": att.student_id,
                "student_name": stu_name,
                "register_number": reg_num,
                "programme_name": quiz.programme.name if quiz.programme else None,
                "class_name": getattr(prof, "academic_year", None) if prof else None,
                "attempt_id": att.id,
                "attempt_number": att.attempt_number,
                "submission_status": att.status,
                "evaluation_status": res.evaluation_status if res else "pending",
                "max_marks": float(res.maximum_marks or quiz.total_marks or 0.0) if res else float(quiz.total_marks or 0.0),
                "obtained_marks": float(res.score or 0.0) if res else 0.0,
                "percentage": float(res.percentage or 0.0) if res else 0.0,
                "is_passed": res.is_passed if res else None,
                "submission_time": att.submitted_at,
                "is_published": res.is_published if res else False,
            })

        # Calculate Ranking based on finalized percentage (standard competition ranking: 1, 1, 3 for ties)
        # Exclude unfinalized/draft attempts from official ranks
        ranked_rows = sorted(
            [r for r in rows if r["evaluation_status"] in ("evaluated", "approved", "published")],
            key=lambda x: x["percentage"],
            reverse=True,
        )

        current_rank = 1
        for idx, r in enumerate(ranked_rows):
            if idx > 0 and r["percentage"] == ranked_rows[idx - 1]["percentage"]:
                r["rank"] = ranked_rows[idx - 1]["rank"]
            else:
                r["rank"] = idx + 1

        rank_lookup = {r["attempt_id"]: r["rank"] for r in ranked_rows}
        for r in rows:
            r["rank"] = rank_lookup.get(r["attempt_id"])

        # Sorting
        reverse = (sort_dir.lower() == "desc")
        if sort_by == "marks":
            rows.sort(key=lambda x: x["obtained_marks"], reverse=reverse)
        elif sort_by == "submission_time":
            rows.sort(key=lambda x: (x["submission_time"] is not None, x["submission_time"]), reverse=reverse)
        elif sort_by == "student_name":
            rows.sort(key=lambda x: x["student_name"].lower(), reverse=reverse)
        else:  # percentage
            rows.sort(key=lambda x: x["percentage"], reverse=reverse)

        total_count = len(rows)
        start_idx = (page - 1) * limit
        paginated_rows = rows[start_idx : start_idx + limit]

        items = [StudentPerformanceItem(**r) for r in paginated_rows]

        return StudentPerformanceListResponse(
            items=items,
            total=total_count,
            page=page,
            limit=limit,
            ranking_policy="standard_competition",
        )

    @staticmethod
    def get_student_profile(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> StudentProfileAnalyticsResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        stu = (
            db.query(Student)
            .options(joinedload(Student.profile))
            .filter(Student.id == student_id)
            .first()
        )
        if not stu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student candidate not found.",
            )

        prof = stu.profile
        stu_name = stu.full_name if (stu and stu.full_name) else (stu.email or "Unknown Candidate")
        reg_num = getattr(prof, "student_identifier", getattr(prof, "roll_number", None)) if prof else None

        # Fetch attempt & result
        att = (
            db.query(ExaminationAttempt)
            .options(joinedload(ExaminationAttempt.result))
            .filter(
                ExaminationAttempt.quiz_id == quiz.id,
                ExaminationAttempt.student_id == stu.id,
            )
            .order_by(desc(ExaminationAttempt.attempt_number))
            .first()
        )
        if not att:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No examination attempt records found for this student on the selected quiz.",
            )

        res = att.result

        # Question evaluations & Attempt answers
        qqs = (
            db.query(QuizQuestion)
            .options(joinedload(QuizQuestion.section))
            .filter(QuizQuestion.quiz_id == quiz.id)
            .order_by(QuizQuestion.question_order.asc())
            .all()
        )
        answers_map = {
            a.quiz_question_id: a
            for a in db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == att.id).all()
        }
        evals_map = {}
        if res:
            evals_map = {
                e.quiz_question_id: e
                for e in db.query(QuestionEvaluation).filter(QuestionEvaluation.result_id == res.id).all()
            }

        q_breakdown: List[StudentQuestionPerformanceItem] = []
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        flagged_count = 0
        partial_count = 0
        neg_marks_total = 0.0

        for qq in qqs:
            snap = qq.question_snapshot or {}
            ans = answers_map.get(qq.id)
            e = evals_map.get(qq.id)

            is_correct = bool(e.is_correct) if e else False
            is_partial = bool(e.is_partially_correct) if e else False
            awarded = float(e.marks_awarded or 0.0) if e else 0.0
            max_m = float(e.max_marks or qq.marks or 1.0) if e else float(qq.marks or 1.0)
            neg_ded = float(e.negative_deduction or 0.0) if e else 0.0
            is_flagged = bool(ans.is_flagged_for_review) if ans else False
            time_spent = ans.time_spent_seconds if ans else 0

            # Answer text/selection representation
            student_answer = None
            if ans:
                if ans.selected_option_ids:
                    student_answer = ans.selected_option_ids
                elif ans.text_response:
                    student_answer = ans.text_response

            is_unanswered = (ans is None) or (ans.answer_status == "NOT_ANSWERED" and not student_answer)
            if is_unanswered:
                unanswered_count += 1
            elif is_correct:
                correct_count += 1
            else:
                incorrect_count += 1

            if is_partial:
                partial_count += 1
            if is_flagged:
                flagged_count += 1
            neg_marks_total += neg_ded

            q_breakdown.append(
                StudentQuestionPerformanceItem(
                    question_order=qq.question_order,
                    quiz_question_id=qq.id,
                    question_type=snap.get("question_type") or "single_choice",
                    question_text=snap.get("question_text") or snap.get("text") or f"Question {qq.question_order}",
                    max_marks=max_m,
                    obtained_marks=awarded,
                    is_correct=is_correct,
                    is_partially_correct=is_partial,
                    negative_deduction=neg_ded,
                    time_spent_seconds=time_spent,
                    is_flagged_for_review=is_flagged,
                    student_answer=student_answer,
                    assigned_difficulty=snap.get("difficulty"),
                    unit=snap.get("unit"),
                    topic=snap.get("topic"),
                )
            )

        # Section Breakdown
        sec_map: Dict[str, Dict[str, Any]] = {}
        for qq in qqs:
            sec_name = qq.section.title if qq.section else "General Section"
            if sec_name not in sec_map:
                sec_map[sec_name] = {
                    "section_id": qq.section_id,
                    "section_name": sec_name,
                    "max_marks": 0.0,
                    "obtained_marks": 0.0,
                    "answered_count": 0,
                    "unanswered_count": 0,
                }
            ans = answers_map.get(qq.id)
            e = evals_map.get(qq.id)
            sec_map[sec_name]["max_marks"] += float(qq.marks or 1.0)
            if e:
                sec_map[sec_name]["obtained_marks"] += float(e.marks_awarded or 0.0)
            if ans and (ans.selected_option_ids or ans.text_response):
                sec_map[sec_name]["answered_count"] += 1
            else:
                sec_map[sec_name]["unanswered_count"] += 1

        sec_breakdown = []
        for s in sec_map.values():
            pct = round((s["obtained_marks"] / s["max_marks"] * 100), 2) if s["max_marks"] > 0 else 0.0
            sec_breakdown.append(
                StudentSectionPerformanceItem(
                    section_id=s["section_id"],
                    section_name=s["section_name"],
                    max_marks=round(s["max_marks"], 2),
                    obtained_marks=round(s["obtained_marks"], 2),
                    percentage=pct,
                    answered_count=s["answered_count"],
                    unanswered_count=s["unanswered_count"],
                )
            )

        # Academic Breakdown (Units & Difficulties for this student)
        unit_perf: Dict[str, Dict[str, float]] = {}
        diff_perf: Dict[str, Dict[str, float]] = {}
        for item in q_breakdown:
            u = item.unit or "Not classified"
            if u not in unit_perf:
                unit_perf[u] = {"awarded": 0.0, "max": 0.0}
            unit_perf[u]["awarded"] += item.obtained_marks
            unit_perf[u]["max"] += item.max_marks

            d = (item.assigned_difficulty or "medium").lower()
            if d not in diff_perf:
                diff_perf[d] = {"correct": 0, "total": 0}
            if item.is_correct:
                diff_perf[d]["correct"] += 1
            diff_perf[d]["total"] += 1

        academic_breakdown = {
            "unit_performance": {
                u: round((v["awarded"] / v["max"] * 100), 2) if v["max"] > 0 else 0.0
                for u, v in unit_perf.items()
            },
            "difficulty_accuracy": {
                d: round((v["correct"] / v["total"] * 100), 2) if v["total"] > 0 else 0.0
                for d, v in diff_perf.items()
            },
        }

        # Calculate Rank among peers
        peer_results = (
            db.query(ExaminationResult.student_id, ExaminationResult.percentage)
            .filter(
                ExaminationResult.quiz_id == quiz.id,
                ExaminationResult.evaluation_status.in_(("evaluated", "approved", "published")),
            )
            .order_by(desc(ExaminationResult.percentage))
            .all()
        )
        total_ranked = len(peer_results)
        rank = None
        for idx, (p_sid, _) in enumerate(peer_results):
            if p_sid == stu.id:
                rank = idx + 1
                break

        summary = {
            "correct_answers": correct_count,
            "incorrect_answers": incorrect_count,
            "unanswered_questions": unanswered_count,
            "questions_marked_for_review": flagged_count,
            "partial_credit_answers": partial_count,
            "negative_marks_received": round(neg_marks_total, 2),
        }

        return StudentProfileAnalyticsResponse(
            student_id=stu.id,
            student_name=stu_name,
            register_number=reg_num,
            email=stu.email,
            programme_name=quiz.programme.name if quiz.programme else None,
            class_name=getattr(prof, "academic_year", None) if prof else None,
            subject_name=quiz.subject.subject_name if quiz.subject else None,
            quiz_title=quiz.title,
            attempt_id=att.id,
            attempt_number=att.attempt_number,
            submission_time=att.submitted_at,
            evaluation_time=getattr(res, "calculated_at", getattr(res, "updated_at", None)) if res else None,
            max_marks=float(res.maximum_marks or quiz.total_marks or 0.0) if res else float(quiz.total_marks or 0.0),
            obtained_marks=float(res.score or 0.0) if res else 0.0,
            percentage=float(res.percentage or 0.0) if res else 0.0,
            is_passed=res.is_passed if res else None,
            is_published=res.is_published if res else False,
            rank=rank,
            total_students_ranked=total_ranked,
            summary=summary,
            question_breakdown=q_breakdown,
            section_breakdown=sec_breakdown,
            academic_breakdown=academic_breakdown,
        )

    @staticmethod
    def get_question_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        unit: Optional[str] = None,
    ) -> QuizQuestionAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        qqs = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz.id)
            .order_by(QuizQuestion.question_order.asc())
            .all()
        )

        # Gather all attempts and results for discrimination calculation
        all_results = (
            db.query(ExaminationResult)
            .filter(
                ExaminationResult.quiz_id == quiz.id,
                ExaminationResult.evaluation_status.in_(("evaluated", "approved", "published")),
            )
            .order_by(desc(ExaminationResult.score))
            .all()
        )
        sample_size = len(all_results)
        sample_adequate = sample_size >= 6

        # Determine Upper 27% and Lower 27% result IDs
        upper_result_ids = set()
        lower_result_ids = set()
        group_size = 1
        if sample_adequate:
            k = max(1, int(round(sample_size * 0.27)))
            group_size = k
            upper_result_ids = {r.id for r in all_results[:k]}
            lower_result_ids = {r.id for r in all_results[-k:]}

        # Gather evaluations by quiz_question_id
        evals_by_qq: Dict[uuid.UUID, List[QuestionEvaluation]] = {}
        all_evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        for e in all_evals:
            evals_by_qq.setdefault(e.quiz_question_id, []).append(e)

        # Gather answers by quiz_question_id
        answers_by_qq: Dict[uuid.UUID, List[AttemptAnswer]] = {}
        all_answers = (
            db.query(AttemptAnswer)
            .join(ExaminationAttempt, AttemptAnswer.attempt_id == ExaminationAttempt.id)
            .filter(ExaminationAttempt.quiz_id == quiz.id)
            .all()
        )
        for a in all_answers:
            answers_by_qq.setdefault(a.quiz_question_id, []).append(a)

        items: List[QuestionAnalysisItem] = []
        for qq in qqs:
            snap = qq.question_snapshot or {}
            q_type = snap.get("question_type") or "single_choice"
            q_diff = (snap.get("difficulty") or "medium").lower()
            q_unit = snap.get("unit") or "Not classified"
            q_chapter = snap.get("chapter")
            q_topic = snap.get("topic")

            # Filters
            if question_type and question_type.lower() != "all" and q_type.lower() != question_type.lower():
                continue
            if difficulty and difficulty.lower() != "all" and q_diff != difficulty.lower():
                continue
            if unit and unit.lower() != "all" and q_unit.lower() != unit.lower():
                continue

            q_evals = evals_by_qq.get(qq.id, [])
            q_ans = answers_by_qq.get(qq.id, [])

            presentations = max(len(q_ans), sample_size)
            responses = [
                a for a in q_ans
                if (a.selected_option_ids or a.text_response) and a.answer_status != "NOT_ANSWERED"
            ]
            resp_count = len(responses)
            unanswered_count = max(0, presentations - resp_count)

            correct_count = sum(1 for e in q_evals if e.is_correct)
            incorrect_count = sum(1 for e in q_evals if not e.is_correct and e.marks_awarded == 0 and e in responses)
            awarded_marks = [float(e.marks_awarded or 0.0) for e in q_evals]
            avg_awarded = round(statistics.mean(awarded_marks), 2) if awarded_marks else 0.0

            # Correct % (Accuracy) & Unanswered %
            accuracy = round((correct_count / resp_count * 100), 2) if resp_count > 0 else 0.0
            inc_pct = round((incorrect_count / resp_count * 100), 2) if resp_count > 0 else 0.0
            unans_pct = round((unanswered_count / presentations * 100), 2) if presentations > 0 else 0.0

            # Psychometric Item Analysis
            # 1. Difficulty Index (P-value: proportion of valid responses correct)
            p_value = round((correct_count / resp_count), 2) if resp_count > 0 else 0.0

            # 2. Discrimination Index (D = (Upper_correct - Lower_correct) / Group_size)
            disc_index = None
            disc_status = "insufficient_sample"
            if sample_adequate:
                upper_correct = sum(1 for e in q_evals if e.result_id in upper_result_ids and e.is_correct)
                lower_correct = sum(1 for e in q_evals if e.result_id in lower_result_ids and e.is_correct)
                d_val = round((upper_correct - lower_correct) / group_size, 2)
                disc_index = max(-1.0, min(1.0, d_val))
                if disc_index >= 0.40:
                    disc_status = "excellent"
                elif disc_index >= 0.30:
                    disc_status = "good"
                elif disc_index >= 0.15:
                    disc_status = "acceptable"
                elif disc_index >= 0.0:
                    disc_status = "weak"
                else:
                    disc_status = "negative"

            # 3. Distractor Analysis
            distractor_stats: List[QuestionOptionStat] = []
            options = snap.get("options") or []
            if isinstance(options, list) and options:
                # Count option selections
                opt_counts = {str(opt.get("id") or opt.get("option_id") or idx): 0 for idx, opt in enumerate(options)}
                for a in q_ans:
                    if isinstance(a.selected_option_ids, list):
                        for oid in a.selected_option_ids:
                            s_oid = str(oid)
                            if s_oid in opt_counts:
                                opt_counts[s_oid] += 1

                for idx, opt in enumerate(options):
                    oid = str(opt.get("id") or opt.get("option_id") or idx)
                    o_text = opt.get("text") or opt.get("option_text") or f"Option {idx + 1}"
                    is_corr = bool(opt.get("is_correct") or opt.get("correct"))
                    cnt = opt_counts.get(oid, 0)
                    sel_pct = round((cnt / resp_count * 100), 2) if resp_count > 0 else 0.0
                    is_rare = (not is_corr) and (resp_count >= 10) and (sel_pct < 5.0)
                    distractor_stats.append(
                        QuestionOptionStat(
                            option_id=oid,
                            option_text=o_text,
                            is_correct=is_corr,
                            selection_count=cnt,
                            selection_percentage=sel_pct,
                            is_rarely_selected=is_rare,
                        )
                    )

            # 4. Review Flags
            review_flags = []
            if resp_count >= 5 and accuracy < 30.0:
                review_flags.append("Low Accuracy (< 30%) - Review question difficulty or ambiguity")
            if presentations >= 5 and unans_pct > 40.0:
                review_flags.append("High Unanswered Rate (> 40%) - Review question clarity or syllabus placement")
            if sample_adequate and disc_index is not None and disc_index < 0.15:
                review_flags.append(f"Weak/Negative Discrimination (D={disc_index}) - Poor separation between top and bottom cohorts")
            if any(d.is_rarely_selected for d in distractor_stats):
                review_flags.append("Ineffective Distractor - One or more options chosen by fewer than 5% of students")
            if any(float(e.negative_deduction or 0.0) > 0 for e in q_evals):
                review_flags.append("Frequent Negative Penalties - Candidates frequently lost marks on this question")

            items.append(
                QuestionAnalysisItem(
                    quiz_question_id=qq.id,
                    question_order=qq.question_order,
                    question_type=q_type,
                    question_text=snap.get("question_text") or snap.get("text") or f"Question {qq.question_order}",
                    max_marks=float(qq.marks or 1.0),
                    assigned_difficulty=q_diff,
                    unit=q_unit,
                    chapter=q_chapter,
                    topic=q_topic,
                    presentations_count=presentations,
                    responses_count=resp_count,
                    correct_count=correct_count,
                    incorrect_count=incorrect_count,
                    unanswered_count=unanswered_count,
                    average_awarded_marks=avg_awarded,
                    correct_percentage=accuracy,
                    incorrect_percentage=inc_pct,
                    unanswered_percentage=unans_pct,
                    difficulty_index=p_value,
                    discrimination_index=disc_index,
                    discrimination_status=disc_status,
                    sample_size_adequate=sample_adequate,
                    distractors=distractor_stats,
                    review_flags=review_flags,
                )
            )

        # Overview Insights
        insights = {
            "total_questions_analyzed": len(items),
            "highest_accuracy_question": max(items, key=lambda x: x.correct_percentage).question_order if items else None,
            "lowest_accuracy_question": min(items, key=lambda x: x.correct_percentage).question_order if items else None,
            "highest_unanswered_question": max(items, key=lambda x: x.unanswered_percentage).question_order if items else None,
            "questions_requiring_review_count": sum(1 for i in items if len(i.review_flags) > 0),
        }

        return QuizQuestionAnalysisResponse(
            items=items,
            total_questions=len(items),
            insights=insights,
        )

    @staticmethod
    def get_section_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> QuizSectionAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        sections = (
            db.query(QuizSection)
            .filter(QuizSection.quiz_id == quiz.id)
            .order_by(QuizSection.section_order.asc())
            .all()
        )

        all_results = (
            db.query(ExaminationResult)
            .filter(
                ExaminationResult.quiz_id == quiz.id,
                ExaminationResult.evaluation_status.in_(("evaluated", "approved", "published")),
            )
            .all()
        )

        items: List[SectionAnalysisItem] = []
        for sec in sections:
            sec_qqs = (
                db.query(QuizQuestion)
                .filter(QuizQuestion.section_id == sec.id)
                .all()
            )
            sec_qq_ids = [q.id for q in sec_qqs]
            sec_max = sum(float(q.marks or 1.0) for q in sec_qqs)

            # Scores in this section across attempts
            sec_scores = []
            for r in all_results:
                sb = r.section_scores or {}
                # match by section id or section title
                sc = sb.get(str(sec.id)) or sb.get(sec.title)
                if isinstance(sc, (int, float, Decimal)):
                    sec_scores.append(float(sc))
                elif isinstance(sc, dict):
                    sec_scores.append(float(sc.get("obtained_score", 0.0)))

            avg_score = round(statistics.mean(sec_scores), 2) if sec_scores else 0.0
            high_score = round(max(sec_scores), 2) if sec_scores else 0.0
            low_score = round(min(sec_scores), 2) if sec_scores else 0.0
            avg_pct = round((avg_score / sec_max * 100), 2) if sec_max > 0 else 0.0

            # Attempted / Unanswered stats
            total_ans = (
                db.query(func.count(AttemptAnswer.id))
                .filter(
                    AttemptAnswer.quiz_question_id.in_(sec_qq_ids),
                    AttemptAnswer.answer_status != "NOT_ANSWERED",
                )
                .scalar()
                or 0
            )
            attempts_count = max(1, len(all_results))
            attempted_avg = round(total_ans / attempts_count, 1) if sec_qq_ids else 0.0
            unanswered_avg = max(0.0, round(len(sec_qq_ids) - attempted_avg, 1))

            # Manual grading status
            manual_pending = (
                db.query(QuestionEvaluation)
                .filter(
                    QuestionEvaluation.quiz_question_id.in_(sec_qq_ids),
                    QuestionEvaluation.evaluation_type == "manual_grading",
                    QuestionEvaluation.marks_awarded == 0,
                    QuestionEvaluation.scoring_reason.is_(None),
                )
                .count()
            )

            items.append(
                SectionAnalysisItem(
                    section_id=sec.id,
                    section_title=sec.title,
                    display_order=sec.section_order,
                    total_questions=len(sec_qqs),
                    compulsory_questions=sec.required_question_count or len(sec_qqs),
                    max_marks=sec_max,
                    average_marks=avg_score,
                    average_percentage=avg_pct,
                    highest_marks=high_score,
                    lowest_marks=low_score,
                    questions_attempted_avg=attempted_avg,
                    questions_unanswered_avg=unanswered_avg,
                    manual_grading_complete=(manual_pending == 0),
                )
            )

        return QuizSectionAnalysisResponse(
            sections=items,
            total_sections=len(items),
        )

    @staticmethod
    def get_academic_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> QuizAcademicAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        qqs = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        evals_by_qq: Dict[uuid.UUID, List[QuestionEvaluation]] = {}
        for e in evals:
            evals_by_qq.setdefault(e.quiz_question_id, []).append(e)

        def _aggregate(category_key: str) -> List[AcademicTopicAnalysisItem]:
            grouped: Dict[str, Dict[str, Any]] = {}
            for qq in qqs:
                snap = qq.question_snapshot or {}
                name = snap.get(category_key) or "Not classified"
                if name not in grouped:
                    grouped[name] = {
                        "count": 0,
                        "max_marks": 0.0,
                        "awarded_marks": [],
                        "correct_count": 0,
                        "valid_responses": 0,
                        "unanswered_count": 0,
                    }
                grouped[name]["count"] += 1
                grouped[name]["max_marks"] += float(qq.marks or 1.0)
                
                qq_evals = evals_by_qq.get(qq.id, [])
                for e in qq_evals:
                    grouped[name]["valid_responses"] += 1
                    grouped[name]["awarded_marks"].append(float(e.marks_awarded or 0.0))
                    if e.is_correct:
                        grouped[name]["correct_count"] += 1

            result = []
            for name, d in grouped.items():
                v_resp = d["valid_responses"]
                acc = round((d["correct_count"] / v_resp * 100), 2) if v_resp > 0 else 0.0
                avg_m = round(statistics.mean(d["awarded_marks"]), 2) if d["awarded_marks"] else 0.0
                unans_rate = round(max(0.0, 100.0 - acc), 2)
                result.append(
                    AcademicTopicAnalysisItem(
                        category=category_key,
                        name=name,
                        questions_count=d["count"],
                        max_possible_marks=round(d["max_marks"], 2),
                        average_accuracy_percentage=acc,
                        average_awarded_marks=avg_m,
                        unanswered_rate=unans_rate,
                    )
                )
            return sorted(result, key=lambda x: x.average_accuracy_percentage, reverse=True)

        return QuizAcademicAnalysisResponse(
            units=_aggregate("unit"),
            chapters=_aggregate("chapter"),
            topics=_aggregate("topic"),
        )

    @staticmethod
    def get_difficulty_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> QuizDifficultyAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        qqs = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        evals_by_qq: Dict[uuid.UUID, List[QuestionEvaluation]] = {}
        for e in evals:
            evals_by_qq.setdefault(e.quiz_question_id, []).append(e)

        grouped: Dict[str, Dict[str, Any]] = {
            "easy": {"count": 0, "max": 0.0, "awarded": [], "correct": 0, "total": 0},
            "medium": {"count": 0, "max": 0.0, "awarded": [], "correct": 0, "total": 0},
            "hard": {"count": 0, "max": 0.0, "awarded": [], "correct": 0, "total": 0},
        }

        for qq in qqs:
            snap = qq.question_snapshot or {}
            d = (snap.get("difficulty") or "medium").lower()
            if d not in grouped:
                grouped[d] = {"count": 0, "max": 0.0, "awarded": [], "correct": 0, "total": 0}

            grouped[d]["count"] += 1
            grouped[d]["max"] += float(qq.marks or 1.0)
            for e in evals_by_qq.get(qq.id, []):
                grouped[d]["total"] += 1
                grouped[d]["awarded"].append(float(e.marks_awarded or 0.0))
                if e.is_correct:
                    grouped[d]["correct"] += 1

        items = []
        for level in ("easy", "medium", "hard"):
            data = grouped.get(level, {"count": 0, "max": 0.0, "awarded": [], "correct": 0, "total": 0})
            total = data["total"]
            acc = round((data["correct"] / total * 100), 2) if total > 0 else 0.0
            avg_m = round(statistics.mean(data["awarded"]), 2) if data["awarded"] else 0.0
            inc = round(100.0 - acc, 2) if total > 0 else 0.0
            items.append(
                DifficultyAnalysisItem(
                    difficulty_level=level,
                    questions_count=data["count"],
                    max_marks=round(data["max"], 2),
                    average_accuracy=acc,
                    average_awarded_marks=avg_m,
                    incorrect_rate=inc,
                    unanswered_rate=0.0,
                )
            )

        return QuizDifficultyAnalysisResponse(levels=items)

    @staticmethod
    def get_question_type_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> QuizQuestionTypeAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        qqs = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )
        evals_by_qq: Dict[uuid.UUID, List[QuestionEvaluation]] = {}
        for e in evals:
            evals_by_qq.setdefault(e.quiz_question_id, []).append(e)

        grouped: Dict[str, Dict[str, Any]] = {}
        for qq in qqs:
            snap = qq.question_snapshot or {}
            t = snap.get("question_type") or "single_choice"
            if t not in grouped:
                grouped[t] = {
                    "count": 0,
                    "max": 0.0,
                    "attempted": 0,
                    "awarded": [],
                    "correct": 0,
                    "partial": 0,
                    "subjective": t in ("descriptive", "short_answer"),
                }

            grouped[t]["count"] += 1
            grouped[t]["max"] += float(qq.marks or 1.0)
            for e in evals_by_qq.get(qq.id, []):
                grouped[t]["attempted"] += 1
                grouped[t]["awarded"].append(float(e.marks_awarded or 0.0))
                if e.is_correct:
                    grouped[t]["correct"] += 1
                if e.is_partially_correct:
                    grouped[t]["partial"] += 1

        items = []
        for t, d in grouped.items():
            att = d["attempted"]
            acc = round((d["correct"] / att * 100), 2) if att > 0 else 0.0
            avg_m = round(statistics.mean(d["awarded"]), 2) if d["awarded"] else 0.0
            items.append(
                QuestionTypeAnalysisItem(
                    question_type=t,
                    questions_count=d["count"],
                    max_marks=round(d["max"], 2),
                    attempted_count=att,
                    accuracy_or_score_percentage=acc,
                    average_marks=avg_m,
                    partial_credit_count=d["partial"],
                    is_subjective=d["subjective"],
                )
            )

        return QuizQuestionTypeAnalysisResponse(types=items)

    @staticmethod
    def get_time_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> TimeAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)
        cfg = quiz.configuration
        duration_minutes = quiz.duration_minutes or 60

        attempts = (
            db.query(ExaminationAttempt)
            .filter(
                ExaminationAttempt.quiz_id == quiz.id,
                ExaminationAttempt.status.in_(("submitted", "time_expired")),
            )
            .all()
        )

        spent_times = [
            a.time_spent_seconds
            for a in attempts
            if a.time_spent_seconds is not None and a.time_spent_seconds > 0
        ]
        avg_time = round(statistics.mean(spent_times), 1) if spent_times else 0.0
        med_time = round(statistics.median(spent_times), 1) if spent_times else 0.0
        rem_time = max(0.0, round((duration_minutes * 60) - avg_time, 1))

        # Question interaction times
        answers = (
            db.query(AttemptAnswer)
            .join(ExaminationAttempt, AttemptAnswer.attempt_id == ExaminationAttempt.id)
            .filter(ExaminationAttempt.quiz_id == quiz.id)
            .all()
        )
        q_times = [a.time_spent_seconds for a in answers if a.time_spent_seconds and a.time_spent_seconds > 0]
        avg_q_time = round(statistics.mean(q_times), 1) if q_times else 0.0
        longest_q = max(q_times) if q_times else 0.0
        shortest_q = min(q_times) if q_times else 0.0

        # Section-wise time
        sections = db.query(QuizSection).filter(QuizSection.quiz_id == quiz.id).all()
        sec_times = []
        for s in sections:
            s_qq_ids = [q.id for q in db.query(QuizQuestion.id).filter(QuizQuestion.section_id == s.id).all()]
            sec_ans_times = [
                a.time_spent_seconds
                for a in answers
                if a.quiz_question_id in s_qq_ids and a.time_spent_seconds
            ]
            sec_avg = round(statistics.mean(sec_ans_times), 1) if sec_ans_times else 0.0
            sec_times.append({
                "section_id": str(s.id),
                "section_title": s.title,
                "average_time_seconds": sec_avg,
            })

        is_telemetry = len(q_times) > 0
        label = "Actual Session Telemetry" if is_telemetry else "Estimated from Attempt Timestamps"

        return TimeAnalysisResponse(
            configured_duration_minutes=duration_minutes,
            average_time_spent_seconds=avg_time,
            median_time_spent_seconds=med_time,
            average_time_remaining_seconds=rem_time,
            average_time_per_question_seconds=avg_q_time,
            section_time_spent=sec_times,
            longest_question_seconds=longest_q,
            shortest_question_seconds=shortest_q,
            data_reliability_label=label,
            is_estimated=not is_telemetry,
        )

    @staticmethod
    def get_negative_marking_analysis(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> NegativeMarkingAnalysisResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        evals = (
            db.query(QuestionEvaluation)
            .join(ExaminationResult, QuestionEvaluation.result_id == ExaminationResult.id)
            .filter(ExaminationResult.quiz_id == quiz.id)
            .all()
        )

        total_ded = sum(float(e.negative_deduction or 0.0) for e in evals)
        affected_students = len({e.result_id for e in evals if float(e.negative_deduction or 0.0) > 0})
        total_evals_count = len({e.result_id for e in evals})
        avg_neg = round(total_ded / total_evals_count, 2) if total_evals_count > 0 else 0.0

        # Percentage of total potential marks lost to negative marking
        total_max_marks = sum(float(e.max_marks or 1.0) for e in evals)
        pct_lost = round((total_ded / total_max_marks * 100), 2) if total_max_marks > 0 else 0.0

        # Top penalized questions
        qq_penalties: Dict[uuid.UUID, float] = {}
        for e in evals:
            ded = float(e.negative_deduction or 0.0)
            if ded > 0:
                qq_penalties[e.quiz_question_id] = qq_penalties.get(e.quiz_question_id, 0.0) + ded

        top_qqs = sorted(qq_penalties.items(), key=lambda x: x[1], reverse=True)[:5]
        top_penalized = []
        for qq_id, ded_sum in top_qqs:
            qq = db.query(QuizQuestion).filter(QuizQuestion.id == qq_id).first()
            snap = qq.question_snapshot if qq else {}
            top_penalized.append({
                "quiz_question_id": str(qq_id),
                "question_order": qq.question_order if qq else 0,
                "question_text": snap.get("question_text") or snap.get("text") or "Question",
                "total_negative_marks_deducted": round(ded_sum, 2),
            })

        return NegativeMarkingAnalysisResponse(
            total_negative_marks_deducted=round(total_ded, 2),
            average_negative_marks_per_attempt=avg_neg,
            students_affected_count=affected_students,
            percentage_of_marks_lost=pct_lost,
            top_penalized_questions=top_penalized,
        )

    @staticmethod
    def get_security_summary(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
    ) -> SecuritySummaryResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        # Get all attempt IDs for this quiz
        att_ids = [
            a.id
            for a in db.query(ExaminationAttempt.id)
            .filter(ExaminationAttempt.quiz_id == quiz.id)
            .all()
        ]

        if not att_ids:
            return SecuritySummaryResponse()

        events = (
            db.query(SecurityEvent)
            .filter(SecurityEvent.attempt_id.in_(att_ids))
            .all()
        )
        alerts = (
            db.query(SecurityAlert)
            .filter(SecurityAlert.attempt_id.in_(att_ids))
            .all()
        )

        low_ev = sum(1 for e in events if getattr(e, "severity", "low").lower() == "low")
        med_ev = sum(1 for e in events if getattr(e, "severity", "low").lower() == "medium")
        high_ev = sum(1 for e in events if getattr(e, "severity", "low").lower() == "high")

        unreviewed = sum(1 for a in alerts if not a.is_resolved)
        resolved = sum(1 for a in alerts if a.is_resolved)
        flagged_attempts = len({e.attempt_id for e in events})

        status_label = "clean"
        if high_ev > 0:
            status_label = "investigation_recommended"
        elif med_ev > 0 or unreviewed > 0:
            status_label = "minor_flags"

        return SecuritySummaryResponse(
            total_security_events=len(events),
            low_severity_events=low_ev,
            medium_severity_events=med_ev,
            high_severity_events=high_ev,
            unreviewed_alerts=unreviewed,
            resolved_alerts=resolved,
            session_conflicts=0,
            integrity_status=status_label,
            attempts_with_security_flags=flagged_attempts,
        )

    @staticmethod
    def compare_students(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        student_ids: List[uuid.UUID],
    ) -> StudentComparisonResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        compared: List[StudentComparisonItem] = []
        for sid in student_ids[:5]:  # compare up to 5 students
            try:
                prof_data = QuizAnalyticsService.get_student_profile(db, admin, quiz_id, sid)
                sec_dict = {s.section_name: s.percentage for s in prof_data.section_breakdown}
                diff_dict = prof_data.academic_breakdown.get("difficulty_accuracy", {})
                compared.append(
                    StudentComparisonItem(
                        student_id=prof_data.student_id,
                        student_name=prof_data.student_name,
                        register_number=prof_data.register_number,
                        percentage=prof_data.percentage,
                        total_score=prof_data.obtained_marks,
                        rank=prof_data.rank,
                        section_scores=sec_dict,
                        difficulty_accuracy=diff_dict,
                    )
                )
            except HTTPException:
                continue

        radar_attrs = ["Overall Score", "Easy Accuracy", "Medium Accuracy", "Hard Accuracy"]

        return StudentComparisonResponse(
            compared_students=compared,
            radar_attributes=radar_attrs,
        )

    @staticmethod
    def flag_question_review(
        db: Session,
        admin: Admin,
        quiz_id: uuid.UUID,
        req: QuestionReviewFlagCreateRequest,
    ) -> QuestionReviewFlagResponse:
        quiz = QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)

        qq = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.id == req.quiz_question_id, QuizQuestion.quiz_id == quiz.id)
            .first()
        )
        if not qq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz question not found in this examination.",
            )

        flag = (
            db.query(QuestionReviewFlag)
            .filter(
                QuestionReviewFlag.quiz_id == quiz.id,
                QuestionReviewFlag.quiz_question_id == qq.id,
            )
            .first()
        )
        if not flag:
            flag = QuestionReviewFlag(
                quiz_id=quiz.id,
                quiz_question_id=qq.id,
                admin_id=admin.id,
                flag_type=req.flag_type,
                status=req.status,
                internal_notes=req.internal_notes,
            )
            db.add(flag)
        else:
            flag.status = req.status
            if req.internal_notes:
                flag.internal_notes = req.internal_notes
            flag.admin_id = admin.id

        db.commit()
        db.refresh(flag)
        return QuestionReviewFlagResponse.model_validate(flag)
