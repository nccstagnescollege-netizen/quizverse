/**
 * Phase 17: Individual Quiz Analytics & Detailed Student Performance Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ScoreBandItem {
  band: string;
  min_pct: number;
  max_pct: number;
  count: number;
}

export interface QuizMetadataInfo {
  id: string;
  title: string;
  subject_name?: string | null;
  programme_name?: string | null;
  semester_name?: string | null;
  creation_mode?: string | null;
  published_version?: number | null;
  max_marks: number;
  duration_minutes: number;
  total_questions: number;
  status: string;
  created_at?: string | null;
}

export interface QuizOverviewAnalytics {
  quiz_info: QuizMetadataInfo;
  freshness_timestamp: string;
  is_provisional: boolean;
  total_registered: number;
  total_eligible: number;
  started_attempts: number;
  submitted_attempts: number;
  completed_evaluations: number;
  pending_evaluations: number;
  pass_count: number;
  fail_count: number;
  average_percentage: number;
  highest_percentage: number;
  lowest_percentage: number;
  median_percentage: number;
  pass_percentage: number;
  completion_rate: number;
  pass_fail_chart: Record<string, number>;
  score_distribution: ScoreBandItem[];
  participation_funnel: Array<{ stage: string; count: number; percentage: number }>;
  submission_status_breakdown: Record<string, number>;
  section_comparison: Array<{ section_title: string; avg_score: number; max_score: number; avg_percentage: number }>;
  difficulty_accuracy: Record<string, number>;
  records_count: number;
}

export interface ParticipantDetailItem {
  student_id: string;
  student_name: string;
  student_email?: string | null;
  register_number?: string | null;
  registration_status: string;
  invitation_name?: string | null;
  registered_at?: string | null;
  attempt_status?: string | null;
  attempt_id?: string | null;
  started_at?: string | null;
  submitted_at?: string | null;
  obtained_score?: number | null;
  percentage?: number | null;
  is_passed?: boolean | null;
  result_status?: string | null;
}

export interface QuizParticipantAnalytics {
  total_registered: number;
  total_eligible: number;
  approved_count: number;
  rejected_count: number;
  started_count: number;
  submitted_count: number;
  unstarted_count: number;
  expired_count: number;
  terminated_count: number;
  unique_students_count: number;
  total_attempts_count: number;
  funnel: Array<{ stage: string; count: number; percentage: number }>;
  participants: ParticipantDetailItem[];
  total: number;
  page: number;
  limit: number;
}

export interface StudentPerformanceItem {
  student_id: string;
  student_name: string;
  register_number?: string | null;
  programme_name?: string | null;
  class_name?: string | null;
  attempt_id: string;
  attempt_number: number;
  submission_status: string;
  evaluation_status: string;
  max_marks: number;
  obtained_marks: number;
  percentage: number;
  is_passed?: boolean | null;
  submission_time?: string | null;
  is_published: boolean;
  rank?: number | null;
}

export interface StudentPerformanceListResponse {
  items: StudentPerformanceItem[];
  total: number;
  page: number;
  limit: number;
  ranking_policy: string;
}

export interface StudentQuestionPerformanceItem {
  question_order: number;
  quiz_question_id: string;
  question_type: string;
  question_text: string;
  max_marks: number;
  obtained_marks: number;
  is_correct: boolean;
  is_partially_correct: boolean;
  negative_deduction: number;
  time_spent_seconds: number;
  is_flagged_for_review: boolean;
  student_answer?: any;
  assigned_difficulty?: string | null;
  unit?: string | null;
  topic?: string | null;
}

export interface StudentSectionPerformanceItem {
  section_id?: string | null;
  section_name: string;
  max_marks: number;
  obtained_marks: number;
  percentage: number;
  answered_count: number;
  unanswered_count: number;
}

export interface StudentProfileAnalytics {
  student_id: string;
  student_name: string;
  register_number?: string | null;
  email?: string | null;
  programme_name?: string | null;
  class_name?: string | null;
  subject_name?: string | null;
  quiz_title: string;
  attempt_id: string;
  attempt_number: number;
  submission_time?: string | null;
  evaluation_time?: string | null;
  max_marks: number;
  obtained_marks: number;
  percentage: number;
  is_passed?: boolean | null;
  is_published: boolean;
  rank?: number | null;
  total_students_ranked: number;
  summary: Record<string, any>;
  question_breakdown: StudentQuestionPerformanceItem[];
  section_breakdown: StudentSectionPerformanceItem[];
  academic_breakdown: Record<string, any>;
}

export interface QuestionOptionStat {
  option_id: string;
  option_text: string;
  is_correct: boolean;
  selection_count: number;
  selection_percentage: number;
  is_rarely_selected: boolean;
}

export interface QuestionAnalysisItem {
  quiz_question_id: string;
  question_order: number;
  question_type: string;
  question_text: string;
  max_marks: number;
  assigned_difficulty: string;
  unit?: string | null;
  chapter?: string | null;
  topic?: string | null;
  presentations_count: number;
  responses_count: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  average_awarded_marks: number;
  correct_percentage: number;
  incorrect_percentage: number;
  unanswered_percentage: number;
  difficulty_index: number;
  discrimination_index?: number | null;
  discrimination_status: string;
  sample_size_adequate: boolean;
  distractors: QuestionOptionStat[];
  review_flags: string[];
}

export interface QuizQuestionAnalysisResponse {
  items: QuestionAnalysisItem[];
  total_questions: number;
  insights: Record<string, any>;
}

export interface SectionAnalysisItem {
  section_id?: string | null;
  section_title: string;
  display_order: number;
  total_questions: number;
  compulsory_questions: number;
  max_marks: number;
  average_marks: number;
  average_percentage: number;
  highest_marks: number;
  lowest_marks: number;
  questions_attempted_avg: number;
  questions_unanswered_avg: number;
  manual_grading_complete: boolean;
}

export interface QuizSectionAnalysisResponse {
  sections: SectionAnalysisItem[];
  total_sections: number;
}

export interface AcademicTopicAnalysisItem {
  category: string;
  name: string;
  questions_count: number;
  max_possible_marks: number;
  average_accuracy_percentage: number;
  average_awarded_marks: number;
  unanswered_rate: number;
}

export interface QuizAcademicAnalysisResponse {
  units: AcademicTopicAnalysisItem[];
  chapters: AcademicTopicAnalysisItem[];
  topics: AcademicTopicAnalysisItem[];
}

export interface DifficultyAnalysisItem {
  difficulty_level: string;
  questions_count: number;
  max_marks: number;
  average_accuracy: number;
  average_awarded_marks: number;
  incorrect_rate: number;
  unanswered_rate: number;
}

export interface QuizDifficultyAnalysisResponse {
  levels: DifficultyAnalysisItem[];
}

export interface QuestionTypeAnalysisItem {
  question_type: string;
  questions_count: number;
  max_marks: number;
  attempted_count: number;
  accuracy_or_score_percentage: number;
  average_marks: number;
  partial_credit_count: number;
  is_subjective: boolean;
}

export interface QuizQuestionTypeAnalysisResponse {
  types: QuestionTypeAnalysisItem[];
}

export interface TimeAnalysisResponse {
  configured_duration_minutes: number;
  average_time_spent_seconds: number;
  median_time_spent_seconds: number;
  average_time_remaining_seconds: number;
  average_time_per_question_seconds: number;
  section_time_spent: Array<{ section_title: string; avg_time_seconds: number }>;
  longest_question_seconds: number;
  shortest_question_seconds: number;
  data_reliability_label: string;
  is_estimated: boolean;
}

export interface NegativeMarkingAnalysisResponse {
  total_negative_marks_deducted: number;
  average_negative_marks_per_attempt: number;
  students_affected_count: number;
  percentage_of_marks_lost: number;
  top_penalized_questions: Array<{
    quiz_question_id: string;
    question_order: number;
    question_text: string;
    total_negative_marks: number;
    incorrect_count: number;
  }>;
}

export interface SecuritySummaryResponse {
  total_security_events: number;
  low_severity_events: number;
  medium_severity_events: number;
  high_severity_events: number;
  unreviewed_alerts: number;
  resolved_alerts: number;
  session_conflicts: number;
  integrity_status: string;
  attempts_with_security_flags: number;
}

export interface StudentComparisonItem {
  student_id: string;
  student_name: string;
  register_number?: string | null;
  percentage: number;
  total_score: number;
  rank?: number | null;
  section_scores: Record<string, number>;
  difficulty_accuracy: Record<string, number>;
}

export interface StudentComparisonResponse {
  compared_students: StudentComparisonItem[];
  radar_attributes: string[];
}

export interface ReportItem {
  id: string;
  report_type: string;
  export_format: string;
  status: string;
  file_name?: string | null;
  file_size_bytes?: number | null;
  download_url?: string | null;
  created_at: string;
  filter_params?: Record<string, any> | null;
}

export const quizAnalyticsService = {
  async getOverview(token: string, quizId: string): Promise<QuizOverviewAnalytics> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/overview`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load quiz overview analytics');
    }
    return res.json();
  },

  async getParticipants(
    token: string,
    quizId: string,
    params?: { status?: string; page?: number; limit?: number }
  ): Promise<QuizParticipantAnalytics> {
    const url = new URL(`${API_BASE_URL}/analytics/quizzes/${quizId}/participants`);
    if (params?.status) url.searchParams.set('status', params.status);
    if (params?.page) url.searchParams.set('page', String(params.page));
    if (params?.limit) url.searchParams.set('limit', String(params.limit));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load participant analytics');
    }
    return res.json();
  },

  async getStudentPerformance(
    token: string,
    quizId: string,
    params?: {
      result_status?: string;
      evaluation_status?: string;
      sort_by?: string;
      sort_dir?: string;
      search?: string;
      page?: number;
      limit?: number;
    }
  ): Promise<StudentPerformanceListResponse> {
    const url = new URL(`${API_BASE_URL}/analytics/quizzes/${quizId}/students`);
    if (params?.result_status) url.searchParams.set('result_status', params.result_status);
    if (params?.evaluation_status) url.searchParams.set('evaluation_status', params.evaluation_status);
    if (params?.sort_by) url.searchParams.set('sort_by', params.sort_by);
    if (params?.sort_dir) url.searchParams.set('sort_dir', params.sort_dir);
    if (params?.search) url.searchParams.set('search', params.search);
    if (params?.page) url.searchParams.set('page', String(params.page));
    if (params?.limit) url.searchParams.set('limit', String(params.limit));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load student performance');
    }
    return res.json();
  },

  async getStudentProfile(token: string, quizId: string, studentId: string): Promise<StudentProfileAnalytics> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/students/${studentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load student performance profile');
    }
    return res.json();
  },

  async compareStudents(token: string, quizId: string, studentIds: string[]): Promise<StudentComparisonResponse> {
    const url = new URL(`${API_BASE_URL}/analytics/quizzes/${quizId}/students/compare`);
    studentIds.forEach((id) => url.searchParams.append('student_ids', id));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to compare students');
    }
    return res.json();
  },

  async getQuestionAnalysis(
    token: string,
    quizId: string,
    params?: { question_type?: string; difficulty?: string; unit?: string }
  ): Promise<QuizQuestionAnalysisResponse> {
    const url = new URL(`${API_BASE_URL}/analytics/quizzes/${quizId}/questions`);
    if (params?.question_type) url.searchParams.set('question_type', params.question_type);
    if (params?.difficulty) url.searchParams.set('difficulty', params.difficulty);
    if (params?.unit) url.searchParams.set('unit', params.unit);

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load question analysis');
    }
    return res.json();
  },

  async flagQuestionReview(
    token: string,
    quizId: string,
    payload: { quiz_question_id: string; flag_type?: string; status?: string; internal_notes?: string }
  ): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/questions/review-flag`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to save question review flag');
    }
    return res.json();
  },

  async getSectionAnalysis(token: string, quizId: string): Promise<QuizSectionAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/sections`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load section analysis');
    }
    return res.json();
  },

  async getAcademicAnalysis(token: string, quizId: string): Promise<QuizAcademicAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/academic`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load academic topic analysis');
    }
    return res.json();
  },

  async getDifficultyAnalysis(token: string, quizId: string): Promise<QuizDifficultyAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/difficulty`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load difficulty analysis');
    }
    return res.json();
  },

  async getQuestionTypeAnalysis(token: string, quizId: string): Promise<QuizQuestionTypeAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/question-types`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load question type analysis');
    }
    return res.json();
  },

  async getTimeAnalysis(token: string, quizId: string): Promise<TimeAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/time`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load time analysis');
    }
    return res.json();
  },

  async getNegativeMarkingAnalysis(token: string, quizId: string): Promise<NegativeMarkingAnalysisResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/negative-marking`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load negative marking analysis');
    }
    return res.json();
  },

  async getSecuritySummary(token: string, quizId: string): Promise<SecuritySummaryResponse> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/security`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to load security summary');
    }
    return res.json();
  },

  async listReports(token: string, quizId: string): Promise<{ items: ReportItem[]; total: number }> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/reports`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to list reports');
    }
    return res.json();
  },

  async generateReport(
    token: string,
    quizId: string,
    payload: {
      report_type: 'quiz_performance' | 'detailed_student' | 'question_analysis' | 'academic_performance' | 'time_analysis' | 'security_summary';
      export_format: 'csv' | 'xlsx' | 'pdf';
      date_from?: string;
      date_to?: string;
    }
  ): Promise<ReportItem> {
    const res = await fetch(`${API_BASE_URL}/analytics/quizzes/${quizId}/reports/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to generate report');
    }
    return res.json();
  },

  getDownloadUrl(reportId: string, token: string): string {
    return `${API_BASE_URL}/analytics/reports/${reportId}/download?auth_token=${encodeURIComponent(token)}`;
  },
};
