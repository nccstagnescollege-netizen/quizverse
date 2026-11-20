import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, and_, select, distinct

from backend.app.models.auth_rbac import Admin, AdminAcademicScope, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizQuestion
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.models.results import ExaminationResult, QuestionEvaluation, ResultCorrection, GradingAssignment
from backend.app.models.question_bank import Question
from backend.app.models.academic import Programme, Subject, Semester
from backend.app.models.analytics import AnalyticsSnapshot, ReportExport, SavedReportConfig, AnalyticsRefreshHistory
from backend.app.schemas.analytics import (
    AnalyticsFilterParams,
    AnalyticsOverviewResponse,
    PeriodComparisonMetric,
    ExaminationStatsResponse,
    ParticipationAnalyticsResponse,
    PerformanceAnalyticsResponse,
    PassFailAnalyticsResponse,
    ScoreDistributionResponse,
    ScoreBandItem,
    AcademicPerformanceResponse,
    ExaminationTrendsResponse,
    EvaluationAnalyticsResponse,
    QuestionBankAnalyticsResponse,
    QuestionEffectivenessResponse,
    QuestionEffectivenessItem,
    FilterOptionsResponse,
)
from backend.app.services.rbac_service import get_authorized_quiz_ids_subquery


def is_super_admin(admin: Admin) -> bool:
    if getattr(admin, "is_super_admin", False):
        return True
    for r in getattr(admin, "roles", []):
        r_name = getattr(r, "role_name", getattr(r, "name", ""))
        if "super" in r_name.lower():
            return True
    return False


def _get_authorized_quiz_ids(db: Session, admin: Admin) -> Optional[List[uuid.UUID]]:
    """Returns None for Super Admin (unrestricted); list of UUIDs for User Admin."""
    if is_super_admin(admin):
        return None
    subq = get_authorized_quiz_ids_subquery(admin)
    if subq is not None:
        rows = db.execute(subq).scalars().all()
        return list(rows)
    return []


def _apply_quiz_filter(query, quiz_id_column, authorized_ids: Optional[List[uuid.UUID]], specific_quiz_id: Optional[uuid.UUID] = None):
    if specific_quiz_id:
        if authorized_ids is not None and specific_quiz_id not in authorized_ids:
            # Not authorized for requested quiz
            return query.filter(quiz_id_column == uuid.UUID("00000000-0000-0000-0000-000000000000"))
        return query.filter(quiz_id_column == specific_quiz_id)

    if authorized_ids is not None:
        return query.filter(quiz_id_column.in_(authorized_ids))
    return query


class AnalyticsService:

    @staticmethod
    def get_overview(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> AnalyticsOverviewResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # 1. Base Quizzes Query
        q_query = db.query(Quiz)
        q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, filters.quiz_id)
        if filters.programme_id:
            q_query = q_query.filter(Quiz.programme_id == filters.programme_id)
        if filters.subject_id:
            q_query = q_query.filter(Quiz.subject_id == filters.subject_id)
        if filters.semester_id:
            q_query = q_query.filter(Quiz.semester_id == filters.semester_id)
        if filters.category:
            q_query = q_query.filter(Quiz.category == filters.category)
        if filters.status:
            q_query = q_query.filter(Quiz.status == filters.status)
        if filters.start_date:
            q_query = q_query.filter(Quiz.created_at >= filters.start_date)
        if filters.end_date:
            q_query = q_query.filter(Quiz.created_at <= filters.end_date)

        scoped_quizzes = q_query.all()
        total_quizzes = len(scoped_quizzes)
        published_quizzes = sum(1 for q in scoped_quizzes if q.status == "published")
        active_examinations = sum(1 for q in scoped_quizzes if q.status in ["published", "scheduled"])
        completed_examinations = sum(1 for q in scoped_quizzes if q.status == "closed")

        scoped_quiz_ids = [q.id for q in scoped_quizzes]

        if not scoped_quiz_ids:
            return AnalyticsOverviewResponse(
                freshness_timestamp=datetime.now(timezone.utc),
                period_label="Current Selection",
                total_quizzes=0,
                published_quizzes=0,
                active_examinations=0,
                completed_examinations=0,
                total_registered_participants=0,
                total_attempts=0,
                submitted_attempts=0,
                pending_evaluations=0,
                published_results=0,
                average_score_percentage=0.0,
                overall_pass_percentage=0.0,
                comparison=None,
            )

        # 2. Registered Participants
        part_query = db.query(func.count(QuizParticipant.id)).filter(QuizParticipant.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            part_query = part_query.filter(QuizParticipant.registered_at >= filters.start_date)
        if filters.end_date:
            part_query = part_query.filter(QuizParticipant.registered_at <= filters.end_date)
        total_registered = part_query.scalar() or 0

        # 3. Examination Attempts
        att_query = db.query(ExaminationAttempt).filter(ExaminationAttempt.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            att_query = att_query.filter(ExaminationAttempt.started_at >= filters.start_date)
        if filters.end_date:
            att_query = att_query.filter(ExaminationAttempt.started_at <= filters.end_date)
        attempts = att_query.all()
        total_attempts = len(attempts)
        submitted_attempts = sum(1 for a in attempts if a.status == "submitted")

        # 4. Results & Evaluations
        res_query = db.query(ExaminationResult).filter(ExaminationResult.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            res_query = res_query.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            res_query = res_query.filter(ExaminationResult.calculated_at <= filters.end_date)
        results = res_query.all()

        pending_evaluations = sum(1 for r in results if r.evaluation_status in ["PENDING", "MANUAL_PENDING"])
        published_results = sum(1 for r in results if r.is_published or r.evaluation_status == "RESULT_PUBLISHED")

        finalized = [r for r in results if r.evaluation_status in ["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]]
        if finalized:
            avg_score = sum(float(r.percentage or 0.0) for r in finalized) / len(finalized)
            passed = sum(1 for r in finalized if r.is_passed)
            pass_pct = (passed / len(finalized)) * 100.0
        else:
            avg_score = 0.0
            pass_pct = 0.0

        # 5. Period comparison if date range provided
        comparison = None
        if filters.start_date and filters.end_date:
            delta = filters.end_date - filters.start_date
            prev_start = filters.start_date - delta
            prev_end = filters.start_date

            prev_att_cnt = db.query(func.count(ExaminationAttempt.id)).filter(
                ExaminationAttempt.quiz_id.in_(scoped_quiz_ids),
                ExaminationAttempt.status == "submitted",
                ExaminationAttempt.started_at >= prev_start,
                ExaminationAttempt.started_at < prev_end,
            ).scalar() or 0

            prev_results = db.query(ExaminationResult).filter(
                ExaminationResult.quiz_id.in_(scoped_quiz_ids),
                ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]),
                ExaminationResult.calculated_at >= prev_start,
                ExaminationResult.calculated_at < prev_end,
            ).all()

            comparison = {}
            if prev_att_cnt > 0:
                pct_chg = ((submitted_attempts - prev_att_cnt) / prev_att_cnt) * 100.0
                comparison["submitted_attempts"] = PeriodComparisonMetric(
                    metric_name="Submitted Attempts",
                    current_value=float(submitted_attempts),
                    previous_value=float(prev_att_cnt),
                    percentage_change=round(pct_chg, 1),
                    trend="up" if pct_chg > 0 else ("down" if pct_chg < 0 else "neutral"),
                )
            else:
                comparison["submitted_attempts"] = PeriodComparisonMetric(
                    metric_name="Submitted Attempts",
                    current_value=float(submitted_attempts),
                    previous_value=None,
                    percentage_change=None,
                    trend="neutral",
                    note="No comparison available",
                )

            if prev_results:
                prev_avg = sum(float(r.percentage or 0.0) for r in prev_results) / len(prev_results)
                chg = avg_score - prev_avg
                comparison["average_score"] = PeriodComparisonMetric(
                    metric_name="Average Score",
                    current_value=round(avg_score, 1),
                    previous_value=round(prev_avg, 1),
                    percentage_change=round(chg, 1),
                    trend="up" if chg > 0 else ("down" if chg < 0 else "neutral"),
                )

        return AnalyticsOverviewResponse(
            freshness_timestamp=datetime.now(timezone.utc),
            period_label="Selected Scope",
            total_quizzes=total_quizzes,
            published_quizzes=published_quizzes,
            active_examinations=active_examinations,
            completed_examinations=completed_examinations,
            total_registered_participants=total_registered,
            total_attempts=total_attempts,
            submitted_attempts=submitted_attempts,
            pending_evaluations=pending_evaluations,
            published_results=published_results,
            average_score_percentage=round(avg_score, 1),
            overall_pass_percentage=round(pass_pct, 1),
            comparison=comparison,
        )

    @staticmethod
    def get_examination_stats(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> ExaminationStatsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)
        q = db.query(Quiz).options(joinedload(Quiz.configuration), joinedload(Quiz.quiz_questions))
        q = _apply_quiz_filter(q, Quiz.id, auth_quiz_ids, filters.quiz_id)

        if filters.programme_id:
            q = q.filter(Quiz.programme_id == filters.programme_id)
        if filters.subject_id:
            q = q.filter(Quiz.subject_id == filters.subject_id)
        if filters.start_date:
            q = q.filter(Quiz.created_at >= filters.start_date)
        if filters.end_date:
            q = q.filter(Quiz.created_at <= filters.end_date)

        quizzes = q.all()
        by_status = {"draft": 0, "published": 0, "scheduled": 0, "closed": 0, "archived": 0}
        by_category = {}
        total_questions = 0
        total_duration = 0

        for qz in quizzes:
            by_status[qz.status] = by_status.get(qz.status, 0) + 1
            cat = qz.category or "Regular"
            by_category[cat] = by_category.get(cat, 0) + 1
            total_questions += len(qz.quiz_questions or [])
            total_duration += qz.duration_minutes or 60

        total_quizzes = len(quizzes)
        avg_duration = round(total_duration / total_quizzes, 1) if total_quizzes > 0 else 60.0

        return ExaminationStatsResponse(
            total_quizzes=total_quizzes,
            quizzes_by_status=by_status,
            active_examinations=by_status.get("published", 0) + by_status.get("scheduled", 0),
            completed_examinations=by_status.get("closed", 0),
            avg_duration_minutes=avg_duration,
            total_questions_configured=total_questions,
            quizzes_by_category=by_category,
        )

    @staticmethod
    def get_participation_analytics(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> ParticipationAnalyticsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Scoped Quiz IDs
        q_query = db.query(Quiz.id)
        q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, filters.quiz_id)
        if filters.programme_id:
            q_query = q_query.filter(Quiz.programme_id == filters.programme_id)
        if filters.subject_id:
            q_query = q_query.filter(Quiz.subject_id == filters.subject_id)
        scoped_quiz_ids = [r[0] for r in q_query.all()]

        if not scoped_quiz_ids:
            return ParticipationAnalyticsResponse(
                registered_participants=0,
                eligible_participants=0,
                started_attempts=0,
                submitted_attempts=0,
                completed_participants=0,
                expired_attempts=0,
                cancelled_attempts=0,
                unstarted_participants=0,
                completion_rate=0.0,
                conversion_rate=0.0,
                college_distribution=[],
                academic_year_distribution=[],
            )

        # 1. Participants
        part_q = db.query(QuizParticipant).filter(QuizParticipant.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            part_q = part_q.filter(QuizParticipant.registered_at >= filters.start_date)
        if filters.end_date:
            part_q = part_q.filter(QuizParticipant.registered_at <= filters.end_date)
        participants = part_q.all()

        registered_cnt = len(participants)
        eligible_cnt = sum(1 for p in participants if p.status in ["enrolled", "approved", "completed"])

        colleges = {}
        acad_years = {}
        for p in participants:
            fd = getattr(p, "registration_data", None) or getattr(p, "form_data", None) or {}
            c_name = fd.get("college_name") or "Institutional Campus"
            ay = fd.get("academic_year") or "2025-2026"
            colleges[c_name] = colleges.get(c_name, 0) + 1
            acad_years[ay] = acad_years.get(ay, 0) + 1

        college_dist = [{"college": k, "count": v} for k, v in sorted(colleges.items(), key=lambda x: -x[1])[:8]]
        ay_dist = [{"academic_year": k, "count": v} for k, v in sorted(acad_years.items(), key=lambda x: -x[1])]

        # 2. Attempts
        att_q = db.query(ExaminationAttempt).filter(ExaminationAttempt.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            att_q = att_q.filter(ExaminationAttempt.started_at >= filters.start_date)
        if filters.end_date:
            att_q = att_q.filter(ExaminationAttempt.started_at <= filters.end_date)
        attempts = att_q.all()

        started_cnt = len(attempts)
        submitted_cnt = sum(1 for a in attempts if a.status == "submitted")
        expired_cnt = sum(1 for a in attempts if a.status == "expired")
        cancelled_cnt = sum(1 for a in attempts if a.status in ["cancelled", "invalidated"])

        completed_student_ids = {a.student_id for a in attempts if a.status == "submitted"}
        completed_cnt = len(completed_student_ids)

        started_student_ids = {a.student_id for a in attempts}
        unstarted_cnt = max(0, registered_cnt - len(started_student_ids))
        comp_rate = round((submitted_cnt / started_cnt * 100.0), 1) if started_cnt > 0 else 0.0
        conv_rate = round((completed_cnt / registered_cnt * 100.0), 1) if registered_cnt > 0 else 0.0

        return ParticipationAnalyticsResponse(
            registered_participants=registered_cnt,
            eligible_participants=eligible_cnt,
            started_attempts=started_cnt,
            submitted_attempts=submitted_cnt,
            completed_participants=completed_cnt,
            expired_attempts=expired_cnt,
            cancelled_attempts=cancelled_cnt,
            unstarted_participants=unstarted_cnt,
            completion_rate=comp_rate,
            conversion_rate=conv_rate,
            college_distribution=college_dist,
            academic_year_distribution=ay_dist,
        )

    @staticmethod
    def get_performance_analytics(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> PerformanceAnalyticsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Scoped Quiz IDs
        q_query = db.query(Quiz.id)
        q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, filters.quiz_id)
        if filters.programme_id:
            q_query = q_query.filter(Quiz.programme_id == filters.programme_id)
        if filters.subject_id:
            q_query = q_query.filter(Quiz.subject_id == filters.subject_id)
        scoped_quiz_ids = [r[0] for r in q_query.all()]

        if not scoped_quiz_ids:
            return PerformanceAnalyticsResponse(
                total_evaluated_students=0,
                passed_students=0,
                failed_students=0,
                average_marks=0.0,
                highest_marks=0.0,
                lowest_marks=0.0,
                median_marks=0.0,
                average_percentage=0.0,
                pass_percentage=0.0,
                failure_percentage=0.0,
                evaluation_completion_rate=0.0,
                provisional_results_count=0,
            )

        res_query = db.query(ExaminationResult).filter(ExaminationResult.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            res_query = res_query.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            res_query = res_query.filter(ExaminationResult.calculated_at <= filters.end_date)
        all_results = res_query.all()

        provisional_cnt = sum(1 for r in all_results if r.evaluation_status in ["PENDING", "MANUAL_PENDING"])
        finalized = [r for r in all_results if r.evaluation_status in ["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]]

        total_evaluated = len(finalized)
        if total_evaluated == 0:
            return PerformanceAnalyticsResponse(
                total_evaluated_students=0,
                passed_students=0,
                failed_students=0,
                average_marks=0.0,
                highest_marks=0.0,
                lowest_marks=0.0,
                median_marks=0.0,
                average_percentage=0.0,
                pass_percentage=0.0,
                failure_percentage=0.0,
                evaluation_completion_rate=0.0,
                provisional_results_count=provisional_cnt,
            )

        passed_cnt = sum(1 for r in finalized if r.is_passed)
        failed_cnt = total_evaluated - passed_cnt

        marks = [float(getattr(r, "score", None) or getattr(r, "total_marks_obtained", None) or 0.0) for r in finalized]
        pcts = [float(r.percentage or 0.0) for r in finalized]

        marks.sort()
        pcts.sort()

        avg_marks = sum(marks) / len(marks)
        avg_pct = sum(pcts) / len(pcts)
        high_marks = marks[-1]
        low_marks = marks[0]

        # Calculate median marks
        n = len(marks)
        if n % 2 == 1:
            median_marks = marks[n // 2]
        else:
            median_marks = (marks[n // 2 - 1] + marks[n // 2]) / 2.0

        pass_rate = (passed_cnt / total_evaluated) * 100.0
        fail_rate = (failed_cnt / total_evaluated) * 100.0

        submitted_cnt = db.query(func.count(ExaminationAttempt.id)).filter(
            ExaminationAttempt.quiz_id.in_(scoped_quiz_ids),
            ExaminationAttempt.status == "submitted",
        ).scalar() or total_evaluated

        eval_rate = (total_evaluated / submitted_cnt * 100.0) if submitted_cnt > 0 else 100.0

        return PerformanceAnalyticsResponse(
            total_evaluated_students=total_evaluated,
            passed_students=passed_cnt,
            failed_students=failed_cnt,
            average_marks=round(avg_marks, 2),
            highest_marks=round(high_marks, 2),
            lowest_marks=round(low_marks, 2),
            median_marks=round(median_marks, 2),
            average_percentage=round(avg_pct, 1),
            pass_percentage=round(pass_rate, 1),
            failure_percentage=round(fail_rate, 1),
            evaluation_completion_rate=round(min(100.0, eval_rate), 1),
            provisional_results_count=provisional_cnt,
        )

    @staticmethod
    def get_pass_rates(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> PassFailAnalyticsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        res_query = db.query(ExaminationResult).join(Quiz, ExaminationResult.quiz_id == Quiz.id).options(
            joinedload(ExaminationResult.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationResult.quiz).joinedload(Quiz.programme),
            joinedload(ExaminationResult.quiz).joinedload(Quiz.semester),
        ).filter(ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]))

        res_query = _apply_quiz_filter(res_query, ExaminationResult.quiz_id, auth_quiz_ids, filters.quiz_id)
        if filters.programme_id:
            res_query = res_query.filter(Quiz.programme_id == filters.programme_id)
        if filters.subject_id:
            res_query = res_query.filter(Quiz.subject_id == filters.subject_id)
        if filters.start_date:
            res_query = res_query.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            res_query = res_query.filter(ExaminationResult.calculated_at <= filters.end_date)

        results = res_query.all()
        total = len(results)
        if total == 0:
            return PassFailAnalyticsResponse(
                overall_pass_count=0,
                overall_fail_count=0,
                overall_pass_percentage=0.0,
                overall_fail_percentage=0.0,
                subject_wise=[],
                programme_wise=[],
                semester_wise=[],
                trend_over_time=[],
            )

        passed = sum(1 for r in results if r.is_passed)
        failed = total - passed
        pass_pct = round((passed / total) * 100.0, 1)
        fail_pct = round((failed / total) * 100.0, 1)

        # Subject-wise
        subj_map = {}
        for r in results:
            s_name = r.quiz.subject.subject_name if r.quiz and r.quiz.subject else "General Subject"
            if s_name not in subj_map:
                subj_map[s_name] = {"passed": 0, "total": 0}
            subj_map[s_name]["total"] += 1
            if r.is_passed:
                subj_map[s_name]["passed"] += 1

        subject_wise = [
            {
                "subject": k,
                "total": v["total"],
                "passed": v["passed"],
                "pass_percentage": round((v["passed"] / v["total"]) * 100.0, 1),
            }
            for k, v in subj_map.items()
        ]

        # Programme-wise
        prog_map = {}
        for r in results:
            p_name = (getattr(r.quiz.programme, "name", None) or getattr(r.quiz.programme, "programme_name", None)) if r.quiz and r.quiz.programme else "Default Programme"
            if p_name not in prog_map:
                prog_map[p_name] = {"passed": 0, "total": 0}
            prog_map[p_name]["total"] += 1
            if r.is_passed:
                prog_map[p_name]["passed"] += 1

        programme_wise = [
            {
                "programme": k,
                "total": v["total"],
                "passed": v["passed"],
                "pass_percentage": round((v["passed"] / v["total"]) * 100.0, 1),
            }
            for k, v in prog_map.items()
        ]

        # Semester-wise
        sem_map = {}
        for r in results:
            sem_name = r.quiz.semester.semester_name if r.quiz and r.quiz.semester else "Semester I"
            if sem_name not in sem_map:
                sem_map[sem_name] = {"passed": 0, "total": 0}
            sem_map[sem_name]["total"] += 1
            if r.is_passed:
                sem_map[sem_name]["passed"] += 1

        semester_wise = [
            {
                "semester": k,
                "total": v["total"],
                "passed": v["passed"],
                "pass_percentage": round((v["passed"] / v["total"]) * 100.0, 1),
            }
            for k, v in sem_map.items()
        ]

        return PassFailAnalyticsResponse(
            overall_pass_count=passed,
            overall_fail_count=failed,
            overall_pass_percentage=pass_pct,
            overall_fail_percentage=fail_pct,
            subject_wise=subject_wise,
            programme_wise=programme_wise,
            semester_wise=semester_wise,
            trend_over_time=[],
        )

    @staticmethod
    def get_score_distribution(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> ScoreDistributionResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        res_query = db.query(ExaminationResult.percentage).filter(
            ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"])
        )
        res_query = _apply_quiz_filter(res_query, ExaminationResult.quiz_id, auth_quiz_ids, filters.quiz_id)

        if filters.start_date:
            res_query = res_query.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            res_query = res_query.filter(ExaminationResult.calculated_at <= filters.end_date)

        rows = res_query.all()
        pcts = [float(r[0] or 0.0) for r in rows]
        total = len(pcts)

        bands_spec = [
            ("0–10%", 0.0, 10.0),
            ("11–20%", 10.01, 20.0),
            ("21–30%", 20.01, 30.0),
            ("31–40%", 30.01, 40.0),
            ("41–50%", 40.01, 50.0),
            ("51–60%", 50.01, 60.0),
            ("61–70%", 60.01, 70.0),
            ("71–80%", 70.01, 80.0),
            ("81–90%", 80.01, 90.0),
            ("91–100%", 90.01, 100.0),
        ]

        band_counts = [0] * len(bands_spec)
        for p in pcts:
            for idx, (label, b_min, b_max) in enumerate(bands_spec):
                if idx == 0 and p <= 10.0:
                    band_counts[0] += 1
                    break
                elif b_min <= p <= b_max:
                    band_counts[idx] += 1
                    break

        score_bands = [
            ScoreBandItem(
                band=label,
                min_pct=b_min,
                max_pct=b_max,
                count=band_counts[i],
                percentage=round((band_counts[i] / total * 100.0), 1) if total > 0 else 0.0,
            )
            for i, (label, b_min, b_max) in enumerate(bands_spec)
        ]

        if total > 0:
            pcts.sort()
            avg_p = sum(pcts) / total
            med_p = pcts[total // 2] if total % 2 == 1 else (pcts[total // 2 - 1] + pcts[total // 2]) / 2.0
            high_p = pcts[-1]
            low_p = pcts[0]
        else:
            avg_p = med_p = high_p = low_p = 0.0

        return ScoreDistributionResponse(
            score_bands=score_bands,
            average_percentage=round(avg_p, 1),
            median_percentage=round(med_p, 1),
            highest_percentage=round(high_p, 1),
            lowest_percentage=round(low_p, 1),
            total_results=total,
        )

    @staticmethod
    def get_academic_performance(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> AcademicPerformanceResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        q = db.query(ExaminationResult).join(Quiz, ExaminationResult.quiz_id == Quiz.id).options(
            joinedload(ExaminationResult.quiz).joinedload(Quiz.programme),
            joinedload(ExaminationResult.quiz).joinedload(Quiz.subject),
            joinedload(ExaminationResult.quiz).joinedload(Quiz.semester),
        ).filter(ExaminationResult.evaluation_status.in_(["RESULT_READY", "APPROVED", "RESULT_PUBLISHED"]))

        q = _apply_quiz_filter(q, ExaminationResult.quiz_id, auth_quiz_ids, filters.quiz_id)
        if filters.start_date:
            q = q.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            q = q.filter(ExaminationResult.calculated_at <= filters.end_date)

        results = q.all()

        prog_data = {}
        subj_data = {}
        sem_data = {}

        for r in results:
            p_name = (getattr(r.quiz.programme, "name", None) or getattr(r.quiz.programme, "programme_name", None)) if r.quiz and r.quiz.programme else "General Programme"
            s_name = r.quiz.subject.subject_name if r.quiz and r.quiz.subject else "General Subject"
            sem_name = r.quiz.semester.semester_name if r.quiz and r.quiz.semester else "Semester I"
            pct = float(r.percentage or 0.0)

            # Programme
            if p_name not in prog_data:
                prog_data[p_name] = {"scores": [], "passed": 0}
            prog_data[p_name]["scores"].append(pct)
            if r.is_passed:
                prog_data[p_name]["passed"] += 1

            # Subject
            if s_name not in subj_data:
                subj_data[s_name] = {"scores": [], "passed": 0}
            subj_data[s_name]["scores"].append(pct)
            if r.is_passed:
                subj_data[s_name]["passed"] += 1

            # Semester
            if sem_name not in sem_data:
                sem_data[sem_name] = {"scores": [], "passed": 0}
            sem_data[sem_name]["scores"].append(pct)
            if r.is_passed:
                sem_data[sem_name]["passed"] += 1

        by_prog = [
            {
                "programme": k,
                "total_students": len(v["scores"]),
                "average_percentage": round(sum(v["scores"]) / len(v["scores"]), 1),
                "pass_rate": round(v["passed"] / len(v["scores"]) * 100.0, 1),
            }
            for k, v in prog_data.items()
        ]

        by_subj = [
            {
                "subject": k,
                "total_students": len(v["scores"]),
                "average_percentage": round(sum(v["scores"]) / len(v["scores"]), 1),
                "pass_rate": round(v["passed"] / len(v["scores"]) * 100.0, 1),
            }
            for k, v in subj_data.items()
        ]

        by_sem = [
            {
                "semester": k,
                "total_students": len(v["scores"]),
                "average_percentage": round(sum(v["scores"]) / len(v["scores"]), 1),
                "pass_rate": round(v["passed"] / len(v["scores"]) * 100.0, 1),
            }
            for k, v in sem_data.items()
        ]

        return AcademicPerformanceResponse(
            by_programme=by_prog,
            by_subject=by_subj,
            by_semester=by_sem,
        )

    @staticmethod
    def get_examination_trends(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
        interval: str = "day",
    ) -> ExaminationTrendsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Look back 14 days by default if no date filter
        now = datetime.now(timezone.utc)
        start = filters.start_date or (now - timedelta(days=14))
        end = filters.end_date or now

        # Generate date points
        points = []
        cur = start.date()
        end_d = end.date()

        # Preload records in range
        q_created = db.query(Quiz.created_at).filter(Quiz.created_at >= start, Quiz.created_at <= end)
        q_created = _apply_quiz_filter(q_created, Quiz.id, auth_quiz_ids, filters.quiz_id).all()

        parts = db.query(QuizParticipant.registered_at, QuizParticipant.quiz_id).filter(
            QuizParticipant.registered_at >= start, QuizParticipant.registered_at <= end
        )
        parts = _apply_quiz_filter(parts, QuizParticipant.quiz_id, auth_quiz_ids, filters.quiz_id).all()

        atts = db.query(ExaminationAttempt.started_at, ExaminationAttempt.status, ExaminationAttempt.quiz_id).filter(
            ExaminationAttempt.started_at >= start, ExaminationAttempt.started_at <= end
        )
        atts = _apply_quiz_filter(atts, ExaminationAttempt.quiz_id, auth_quiz_ids, filters.quiz_id).all()

        res = db.query(ExaminationResult.calculated_at, ExaminationResult.is_published, ExaminationResult.quiz_id).filter(
            ExaminationResult.calculated_at >= start, ExaminationResult.calculated_at <= end
        )
        res = _apply_quiz_filter(res, ExaminationResult.quiz_id, auth_quiz_ids, filters.quiz_id).all()

        while cur <= end_d:
            cur_str = cur.strftime("%Y-%m-%d")
            qz_cnt = sum(1 for q in q_created if q[0] and q[0].date() == cur)
            reg_cnt = sum(1 for p in parts if p[0] and p[0].date() == cur)
            start_cnt = sum(1 for a in atts if a[0] and a[0].date() == cur)
            sub_cnt = sum(1 for a in atts if a[0] and a[0].date() == cur and a[1] == "submitted")
            pub_cnt = sum(1 for r in res if r[0] and r[0].date() == cur and r[1])

            points.append({
                "date": cur_str,
                "quizzes_created": qz_cnt,
                "registrations": reg_cnt,
                "attempts_started": start_cnt,
                "attempts_submitted": sub_cnt,
                "results_published": pub_cnt,
            })
            cur += timedelta(days=1)

        return ExaminationTrendsResponse(
            interval=interval,
            data_points=points,
        )

    @staticmethod
    def get_evaluation_analytics(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> EvaluationAnalyticsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Scoped Quiz IDs
        q_query = db.query(Quiz.id)
        q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids, filters.quiz_id)
        scoped_quiz_ids = [r[0] for r in q_query.all()]

        if not scoped_quiz_ids:
            return EvaluationAnalyticsResponse(
                auto_evaluations_completed=0,
                manual_evaluations_pending=0,
                manual_evaluations_completed=0,
                awaiting_moderation=0,
                awaiting_approval=0,
                published_results=0,
                evaluator_workload=[],
                result_corrections_count=0,
            )

        # Evaluations
        eval_q = (
            db.query(QuestionEvaluation)
            .join(QuizQuestion, QuestionEvaluation.quiz_question_id == QuizQuestion.id)
            .filter(QuizQuestion.quiz_id.in_(scoped_quiz_ids))
        )
        if filters.start_date:
            eval_q = eval_q.filter(QuestionEvaluation.created_at >= filters.start_date)
        if filters.end_date:
            eval_q = eval_q.filter(QuestionEvaluation.created_at <= filters.end_date)
        evals = eval_q.all()

        auto_cnt = sum(1 for e in evals if e.evaluation_type == "auto_objective")
        manual_pending = sum(
            1 for e in evals 
            if e.evaluation_type in ["manual_grading", "manual_descriptive"] and (e.marks_awarded is None or e.evaluator_id is None)
        )
        manual_comp = sum(
            1 for e in evals 
            if e.evaluation_type in ["manual_grading", "manual_descriptive"] and e.marks_awarded is not None
        )
        moderation_cnt = sum(1 for e in evals if getattr(e, "is_flagged_for_moderation", False) and getattr(e, "moderation_status", "") == "pending")

        # Results
        res_q = db.query(ExaminationResult).filter(ExaminationResult.quiz_id.in_(scoped_quiz_ids))
        if filters.start_date:
            res_q = res_q.filter(ExaminationResult.calculated_at >= filters.start_date)
        if filters.end_date:
            res_q = res_q.filter(ExaminationResult.calculated_at <= filters.end_date)
        results = res_q.all()

        awaiting_app = sum(1 for r in results if not r.is_approved and r.evaluation_status == "RESULT_READY")
        published_cnt = sum(1 for r in results if r.is_published or r.evaluation_status == "RESULT_PUBLISHED")

        # Corrections
        corr_cnt = db.query(func.count(ResultCorrection.id)).join(
            ExaminationResult, ResultCorrection.result_id == ExaminationResult.id
        ).filter(ExaminationResult.quiz_id.in_(scoped_quiz_ids)).scalar() or 0

        # Evaluator Workload
        evaluator_map = {}
        for e in evals:
            if getattr(e, "evaluator_id", None):
                e_id = str(e.evaluator_id)
                if e_id not in evaluator_map:
                    evaluator_map[e_id] = {"evaluator_id": e_id, "completed": 0, "pending": 0}
                if e.marks_awarded is not None:
                    evaluator_map[e_id]["completed"] += 1
                else:
                    evaluator_map[e_id]["pending"] += 1

        workload = list(evaluator_map.values())

        return EvaluationAnalyticsResponse(
            auto_evaluations_completed=auto_cnt,
            manual_evaluations_pending=manual_pending,
            manual_evaluations_completed=manual_comp,
            awaiting_moderation=moderation_cnt,
            awaiting_approval=awaiting_app,
            published_results=published_cnt,
            evaluator_workload=workload,
            result_corrections_count=corr_cnt,
        )

    @staticmethod
    def get_question_bank_analytics(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> QuestionBankAnalyticsResponse:
        # Check permissions & scopes
        q_query = db.query(Question)
        if not is_super_admin(admin):
            # Restrict by admin's subject scopes if configured
            scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
            allowed_subj_ids = {s.subject_id for s in scopes if s.subject_id}
            if allowed_subj_ids:
                q_query = q_query.filter(Question.subject_id.in_(allowed_subj_ids))

        if filters.subject_id:
            q_query = q_query.filter(Question.subject_id == filters.subject_id)

        all_questions = q_query.all()
        total_q = len(all_questions)

        approved = sum(1 for q in all_questions if q.status == "approved")
        draft = sum(1 for q in all_questions if q.status == "draft")
        archived = sum(1 for q in all_questions if q.status == "archived")

        by_diff = {"easy": 0, "medium": 0, "hard": 0}
        by_type = {}
        subj_counts = {}

        for q in all_questions:
            d = (getattr(q, "difficulty", None) or getattr(q, "difficulty_level", None) or "medium").lower()
            by_diff[d] = by_diff.get(d, 0) + 1

            t = q.question_type or "single_choice"
            by_type[t] = by_type.get(t, 0) + 1

            s_id = str(q.subject_id) if q.subject_id else "Unassigned"
            subj_counts[s_id] = subj_counts.get(s_id, 0) + 1

        by_subj = [{"subject_id": k, "count": v} for k, v in subj_counts.items()]

        # Usage in examinations: questions referenced in QuizQuestion for published quizzes
        from backend.app.models.quiz import QuizQuestion
        used_q_ids = db.query(distinct(QuizQuestion.question_id)).join(
            Quiz, QuizQuestion.quiz_id == Quiz.id
        ).filter(Quiz.status.in_(["published", "scheduled", "closed"])).all()
        used_count = len([x for x in used_q_ids if x[0] is not None])

        return QuestionBankAnalyticsResponse(
            total_questions=total_q,
            approved_questions=approved,
            draft_questions=draft,
            archived_questions=archived,
            by_difficulty=by_diff,
            by_type=by_type,
            by_subject=by_subj,
            used_in_examinations_count=used_count,
            most_used_questions=[],
        )

    @staticmethod
    def get_question_effectiveness(
        db: Session,
        admin: Admin,
        filters: AnalyticsFilterParams,
    ) -> QuestionEffectivenessResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Query QuestionEvaluations joining QuizQuestion and Question
        eval_q = (
            db.query(QuestionEvaluation)
            .join(QuizQuestion, QuestionEvaluation.quiz_question_id == QuizQuestion.id)
            .join(Question, QuizQuestion.question_id == Question.id)
            .options(
                joinedload(QuestionEvaluation.quiz_question).joinedload(QuizQuestion.question).joinedload(Question.subject)
            )
        )

        eval_q = _apply_quiz_filter(eval_q, QuizQuestion.quiz_id, auth_quiz_ids, filters.quiz_id)
        if filters.start_date:
            eval_q = eval_q.filter(QuestionEvaluation.created_at >= filters.start_date)
        if filters.end_date:
            eval_q = eval_q.filter(QuestionEvaluation.created_at <= filters.end_date)

        evals = eval_q.all()

        q_agg = {}
        for e in evals:
            qq = getattr(e, "quiz_question", None)
            qid = qq.question_id if qq else None
            q_obj = qq.question if qq else None
            if not qid:
                continue
            if qid not in q_agg:
                q_agg[qid] = {
                    "question": q_obj,
                    "times_presented": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "unanswered": 0,
                    "total_score_pct": [],
                }
            q_agg[qid]["times_presented"] += 1

            if e.is_correct:
                q_agg[qid]["correct"] += 1
            else:
                q_agg[qid]["incorrect"] += 1

            max_m = float(e.max_marks or 1.0)
            awd_m = float(e.marks_awarded or 0.0)
            pct = (awd_m / max_m * 100.0) if max_m > 0 else 0.0
            q_agg[qid]["total_score_pct"].append(pct)

        items = []
        for qid, data in q_agg.items():
            q_obj = data["question"]
            total = data["times_presented"]
            corr = data["correct"]
            inc = data["incorrect"]
            corr_pct = round((corr / total * 100.0), 1) if total > 0 else 0.0
            inc_pct = round((inc / total * 100.0), 1) if total > 0 else 0.0
            avg_score_pct = round(sum(data["total_score_pct"]) / len(data["total_score_pct"]), 1) if data["total_score_pct"] else 0.0

            # Observed difficulty: >75% correct = easy, 40-75% = medium, <40% = hard
            if corr_pct >= 75.0:
                obs_diff = "easy"
            elif corr_pct >= 40.0:
                obs_diff = "medium"
            else:
                obs_diff = "hard"

            assigned_diff = (getattr(q_obj, "difficulty", None) or getattr(q_obj, "difficulty_level", None) or "medium").lower() if q_obj else "medium"
            sample_warn = total < 10

            items.append(
                QuestionEffectivenessItem(
                    question_id=qid,
                    question_text=q_obj.question_text[:120] if q_obj and q_obj.question_text else "Question",
                    subject_name=q_obj.subject.subject_name if q_obj and q_obj.subject else None,
                    question_type=q_obj.question_type if q_obj else "single_choice",
                    times_presented=total,
                    valid_responses=total,
                    correct_percentage=corr_pct,
                    incorrect_percentage=inc_pct,
                    unanswered_percentage=0.0,
                    average_awarded_percentage=avg_score_pct,
                    assigned_difficulty=assigned_diff,
                    observed_difficulty=obs_diff,
                    sample_warning=sample_warn,
                    warning_message="Limited response data. Interpret this statistic cautiously." if sample_warn else None,
                )
            )

        # Sort by times presented descending
        items.sort(key=lambda x: -x.times_presented)

        return QuestionEffectivenessResponse(
            items=items[:50],  # Top 50 evaluated questions
            total_evaluated_questions=len(items),
        )

    @staticmethod
    def get_filter_options(db: Session, admin: Admin) -> FilterOptionsResponse:
        auth_quiz_ids = _get_authorized_quiz_ids(db, admin)

        # Quizzes
        q_query = db.query(Quiz.id, Quiz.title, Quiz.status).order_by(Quiz.created_at.desc())
        q_query = _apply_quiz_filter(q_query, Quiz.id, auth_quiz_ids)
        quizzes = [{"id": str(r[0]), "title": r[1], "status": r[2]} for r in q_query.all()]

        # Programmes & Subjects within scope
        prog_name_col = getattr(Programme, "name", getattr(Programme, "programme_name", None))
        prog_code_col = getattr(Programme, "code", getattr(Programme, "programme_code", None))
        prog_query = db.query(Programme.id, prog_name_col, prog_code_col).filter(Programme.status == "active")
        subj_query = db.query(Subject.id, Subject.subject_name, Subject.subject_code).filter(Subject.status == "active")
        sem_query = db.query(Semester.id, Semester.semester_name, Semester.semester_number).all()

        if not is_super_admin(admin):
            scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
            allowed_prog = {s.programme_id for s in scopes if s.programme_id}
            allowed_subj = {s.subject_id for s in scopes if s.subject_id}
            if allowed_prog:
                prog_query = prog_query.filter(Programme.id.in_(allowed_prog))
            if allowed_subj:
                subj_query = subj_query.filter(Subject.id.in_(allowed_subj))

        progs = [{"id": str(r[0]), "name": r[1], "code": r[2]} for r in prog_query.all()]
        subjs = [{"id": str(r[0]), "name": r[1], "code": r[2]} for r in subj_query.all()]
        sems = [{"id": str(r[0]), "name": r[1], "number": r[2]} for r in sem_query]

        academic_years = ["2026-2027", "2025-2026", "2024-2025"]

        return FilterOptionsResponse(
            programmes=progs,
            subjects=subjs,
            semesters=sems,
            academic_years=academic_years,
            quizzes=quizzes,
        )
