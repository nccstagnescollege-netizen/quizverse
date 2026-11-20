/**
 * Phase 16: Admin Analytics Dashboard & Examination Reports Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface AnalyticsFilterParams {
  start_date?: string;
  end_date?: string;
  quiz_id?: string;
  programme_id?: string;
  subject_id?: string;
  semester_id?: string;
  academic_year?: string;
  category?: string;
  status?: string;
}

export interface PeriodComparisonMetric {
  metric_name: string;
  current_value: number;
  previous_value?: number | null;
  percentage_change?: number | null;
  trend: 'up' | 'down' | 'neutral';
  note?: string | null;
}

export interface AnalyticsOverviewResponse {
  freshness_timestamp: string;
  period_label: string;
  total_quizzes: number;
  published_quizzes: number;
  active_examinations: number;
  completed_examinations: number;
  total_registered_participants: number;
  total_attempts: number;
  submitted_attempts: number;
  pending_evaluations: number;
  published_results: number;
  average_score_percentage: number;
  overall_pass_percentage: number;
  comparison?: Record<string, PeriodComparisonMetric>;
}

export interface ExaminationStatsResponse {
  total_quizzes: number;
  quizzes_by_status: Record<string, number>;
  active_examinations: number;
  completed_examinations: number;
  avg_duration_minutes: number;
  total_questions_configured: number;
  quizzes_by_category: Record<string, number>;
}

export interface ParticipationAnalyticsResponse {
  registered_participants: number;
  eligible_participants: number;
  started_attempts: number;
  submitted_attempts: number;
  completed_participants: number;
  expired_attempts: number;
  cancelled_attempts: number;
  unstarted_participants: number;
  completion_rate: number;
  conversion_rate: number;
  college_distribution: Array<{ name: string; count: number }>;
  academic_year_distribution: Array<{ name: string; count: number }>;
}

export interface PerformanceAnalyticsResponse {
  total_evaluated_students: number;
  passed_students: number;
  failed_students: number;
  average_marks: number;
  highest_marks: number;
  lowest_marks: number;
  median_marks: number;
  average_percentage: number;
  pass_percentage: number;
  failure_percentage: number;
  evaluation_completion_rate: number;
  provisional_results_count: number;
}

export interface PassFailAnalyticsResponse {
  overall_pass_count: number;
  overall_fail_count: number;
  overall_pass_percentage: number;
  overall_fail_percentage: number;
  subject_wise: Array<{ name: string; passed: number; failed: number; pass_percentage: number }>;
  programme_wise: Array<{ name: string; passed: number; failed: number; pass_percentage: number }>;
  semester_wise: Array<{ name: string; passed: number; failed: number; pass_percentage: number }>;
  trend_over_time: Array<{ date: string; passed: number; failed: number }>;
}

export interface ScoreBandItem {
  band: string;
  min_pct: number;
  max_pct: number;
  count: number;
  percentage: number;
}

export interface ScoreDistributionResponse {
  score_bands: ScoreBandItem[];
  average_percentage: number;
  median_percentage: number;
  highest_percentage: number;
  lowest_percentage: number;
  total_results: number;
}

export interface AcademicPerformanceResponse {
  by_programme: Array<{ id: string; name: string; students: number; average_percentage: number; pass_rate: number }>;
  by_subject: Array<{ id: string; name: string; students: number; average_percentage: number; pass_rate: number }>;
  by_semester: Array<{ id: string; name: string; students: number; average_percentage: number; pass_rate: number }>;
}

export interface ExaminationTrendsResponse {
  interval: string;
  data_points: Array<{
    timestamp: string;
    label: string;
    total_quizzes: number;
    participants: number;
    attempts: number;
    completed: number;
    average_score: number;
  }>;
}

export interface EvaluationAnalyticsResponse {
  auto_evaluations_completed: number;
  manual_evaluations_pending: number;
  manual_evaluations_completed: number;
  awaiting_moderation: number;
  awaiting_approval: number;
  published_results: number;
  evaluator_workload: Array<{ evaluator_id: string; evaluator_name: string; evaluated_count: number; pending_count: number }>;
  result_corrections_count: number;
}

export interface QuestionBankAnalyticsResponse {
  total_questions: number;
  approved_questions: number;
  draft_questions: number;
  archived_questions: number;
  by_difficulty: Record<string, number>;
  by_type: Record<string, number>;
  by_subject: Array<{ subject_name: string; question_count: number }>;
  used_in_examinations_count: number;
  most_used_questions: Array<{ id: string; title: string; count: number }>;
}

export interface QuestionEffectivenessItem {
  question_id: string;
  question_text: string;
  subject_name?: string | null;
  question_type: string;
  times_presented: number;
  valid_responses: number;
  correct_percentage: number;
  incorrect_percentage: number;
  unanswered_percentage: number;
  average_awarded_percentage: number;
  assigned_difficulty: string;
  observed_difficulty: string;
  sample_warning: boolean;
  warning_message?: string | null;
}

export interface QuestionEffectivenessResponse {
  items: QuestionEffectivenessItem[];
  total_evaluated_questions: number;
}

export interface FilterOptionsResponse {
  programmes: Array<{ id: string; name: string; code: string }>;
  subjects: Array<{ id: string; name: string; code: string }>;
  semesters: Array<{ id: string; name: string; number: number }>;
  academic_years: string[];
  quizzes: Array<{ id: string; title: string; code: string }>;
}

export interface ReportGenerateRequest {
  report_type: 'examination_summary' | 'student_performance' | 'academic_performance' | 'evaluation_summary' | 'question_bank' | 'examination_activity';
  export_format: 'csv' | 'xlsx' | 'pdf';
  filters?: Record<string, any>;
  include_columns?: string[];
}

export interface ReportExportItem {
  id: string;
  report_type: string;
  export_format: string;
  status: string;
  file_name: string;
  file_size: number;
  download_url?: string | null;
  row_count: number;
  created_at: string;
  expires_at?: string | null;
  error_message?: string | null;
}

export interface ReportExportListResponse {
  items: ReportExportItem[];
  total: number;
}

function buildQueryString(params?: Record<string, any>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      searchParams.set(key, String(value));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : '';
}

export const analyticsService = {
  async getOverview(token: string, filters?: AnalyticsFilterParams): Promise<AnalyticsOverviewResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/overview${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load analytics overview');
    }
    return res.json();
  },

  async getExaminationStats(token: string, filters?: AnalyticsFilterParams): Promise<ExaminationStatsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/examinations${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load examination statistics');
    }
    return res.json();
  },

  async getParticipation(token: string, filters?: AnalyticsFilterParams): Promise<ParticipationAnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/participation${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load participation analytics');
    }
    return res.json();
  },

  async getPerformance(token: string, filters?: AnalyticsFilterParams): Promise<PerformanceAnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/performance${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load performance analytics');
    }
    return res.json();
  },

  async getPassFail(token: string, filters?: AnalyticsFilterParams): Promise<PassFailAnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/pass-fail${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load pass/fail analytics');
    }
    return res.json();
  },

  async getScoreDistribution(token: string, filters?: AnalyticsFilterParams): Promise<ScoreDistributionResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/score-distribution${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load score distribution');
    }
    return res.json();
  },

  async getAcademicPerformance(token: string, filters?: AnalyticsFilterParams): Promise<AcademicPerformanceResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/academic-performance${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load academic performance');
    }
    return res.json();
  },

  async getExaminationTrends(token: string, filters?: AnalyticsFilterParams, interval: string = 'day'): Promise<ExaminationTrendsResponse> {
    const params = { ...(filters || {}), interval };
    const res = await fetch(`${API_BASE_URL}/analytics/examination-trends${buildQueryString(params)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load examination trends');
    }
    return res.json();
  },

  async getEvaluations(token: string, filters?: AnalyticsFilterParams): Promise<EvaluationAnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/evaluations${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load evaluation analytics');
    }
    return res.json();
  },

  async getQuestionBankAnalytics(token: string, filters?: AnalyticsFilterParams): Promise<QuestionBankAnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/question-bank${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load question bank analytics');
    }
    return res.json();
  },

  async getQuestionEffectiveness(token: string, filters?: AnalyticsFilterParams): Promise<QuestionEffectivenessResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/question-effectiveness${buildQueryString(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load question effectiveness');
    }
    return res.json();
  },

  async getFilterOptions(token: string): Promise<FilterOptionsResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/filter-options`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load filter options');
    }
    return res.json();
  },

  async listReports(token: string, limit: number = 50): Promise<ReportExportListResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/reports?limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load reports');
    }
    return res.json();
  },

  async generateReport(token: string, payload: ReportGenerateRequest): Promise<ReportExportItem> {
    const res = await fetch(`${API_BASE_URL}/analytics/reports/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to generate report');
    }
    return res.json();
  },

  async downloadReport(token: string, exportId: string, fileName: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/analytics/reports/${exportId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to download report');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  },
};
