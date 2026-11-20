/**
 * Phase 15: Automatic Evaluation, Manual Grading & Results Management Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface GradingCriterion {
  id?: string;
  rubric_id?: string;
  title: string;
  description?: string | null;
  max_marks: number;
  criterion_order?: number;
  partial_credit_levels?: Array<{ label: string; marks: number; description?: string }> | null;
}

export interface GradingRubric {
  id: string;
  subject_id?: string | null;
  title: string;
  description?: string | null;
  applicable_question_types: string[];
  total_max_marks: number;
  status: string;
  version: number;
  grading_instructions?: string | null;
  criteria: GradingCriterion[];
  created_at: string;
  updated_at: string;
}

export interface GradingAssignment {
  id: string;
  quiz_id: string;
  quiz_title?: string;
  evaluator_id: string;
  evaluator_name?: string;
  evaluator_email?: string;
  assignment_scope: string;
  section_id?: string | null;
  student_group_tag?: string | null;
  assigned_question_ids?: string[] | null;
  anonymous_grading: boolean;
  deadline_at?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ManualGradingQuestionItem {
  evaluation_id: string;
  quiz_question_id: string;
  question_order: number;
  section_title?: string | null;
  question_text: string;
  question_type: string;
  max_marks: number;
  negative_marks: number;
  student_answer_text?: string | null;
  student_selected_options?: string[] | null;
  attachments?: any[] | null;
  rubric?: GradingRubric | null;
  marks_awarded: number;
  is_evaluated: boolean;
  is_partially_correct: boolean;
  feedback?: string | null;
  private_notes?: string | null;
  criterion_scores?: Array<{ criterion_title: string; awarded_marks: number; max_marks: number }> | null;
  is_flagged_for_moderation: boolean;
  moderation_status?: string | null;
}

export interface ManualGradingWorkspace {
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_identifier: string;
  student_email?: string | null;
  student_roll_no?: string | null;
  submitted_at?: string | null;
  total_manual_questions: number;
  graded_count: number;
  evaluation_status: string;
  questions: ManualGradingQuestionItem[];
}

export interface ModerationEvaluationItem {
  evaluation_id: string;
  result_id: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  student_identifier: string;
  quiz_question_id: string;
  question_text: string;
  question_type: string;
  max_marks: number;
  student_answer_text?: string | null;
  evaluator_id?: string | null;
  evaluator_name?: string | null;
  marks_awarded: number;
  feedback?: string | null;
  private_notes?: string | null;
  is_flagged_for_moderation: boolean;
  moderation_status?: string | null;
  override_reason?: string | null;
  created_at: string;
}

export interface EvaluationJobStatus {
  id?: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title?: string;
  student_id: string;
  status: string;
  total_questions: number;
  auto_evaluated_count: number;
  manual_eval_count: number;
  manual_eval_completed: number;
  error_message?: string | null;
  created_at?: string;
  completed_at?: string | null;
}

export interface EvaluationTaskItem {
  job_id: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_identifier: string;
  submitted_at: string;
  pending_questions_count: number;
}

export interface ResultListItem {
  id: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_id: string;
  student_name: string;
  student_email: string;
  student_roll_no?: string | null;
  score: number;
  maximum_marks: number;
  percentage: number;
  is_passed: boolean;
  evaluation_status: string;
  is_approved: boolean;
  is_published: boolean;
  calculated_at: string;
}

export interface ResultListResponse {
  total: number;
  page: number;
  limit: number;
  pages: number;
  items: ResultListItem[];
}

export interface SectionScoreDetail {
  section_id: string;
  title: string;
  max_marks: number;
  obtained_marks: number;
  questions_count: number;
  attempted_count: number;
  compulsory_count?: number;
}

export interface QuestionEvaluationDetail {
  quiz_question_id: string;
  question_type: string;
  marks_awarded: number;
  max_marks: number;
  negative_deduction: number;
  is_correct: boolean;
  is_partially_correct: boolean;
  scoring_reason?: string | null;
  feedback?: string | null;
  evaluation_type: string;
  evaluator_name?: string | null;
}

export interface ResultCorrectionDetail {
  id: string;
  previous_score: number;
  new_score: number;
  previous_percentage: number;
  new_percentage: number;
  previous_status?: string | null;
  new_status?: string | null;
  reason: string;
  corrected_by_name?: string | null;
  corrected_at: string;
}

export interface ResultDetail {
  id: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_id: string;
  student_name: string;
  student_email: string;
  student_roll_no?: string | null;
  score: number;
  maximum_marks: number;
  passing_marks?: number | null;
  percentage: number;
  is_passed: boolean;
  objective_marks: number;
  manual_marks: number;
  negative_marks: number;
  total_correct: number;
  total_incorrect: number;
  total_unanswered: number;
  rank?: number | null;
  percentile?: number | null;
  evaluation_status: string;
  is_approved: boolean;
  approved_at?: string | null;
  approved_by_name?: string | null;
  approval_notes?: string | null;
  is_published: boolean;
  published_at?: string | null;
  published_by_name?: string | null;
  result_version: number;
  section_scores?: SectionScoreDetail[];
  section_breakdown?: SectionScoreDetail[];
  evaluations: QuestionEvaluationDetail[];
  question_evaluations?: QuestionEvaluationDetail[];
  corrections: ResultCorrectionDetail[];
  correction_history?: ResultCorrectionDetail[];
  calculated_at: string;
}

export interface StudentResultResponse {
  attempt_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_name: string;
  student_roll_no?: string | null;
  score?: number | null;
  maximum_marks?: number | null;
  percentage?: number | null;
  is_passed?: boolean | null;
  pass_fail_label: string;
  evaluation_status: string;
  is_provisional: boolean;
  status_message: string;
  is_released: boolean;
  show_score: boolean;
  show_section_breakdown: boolean;
  show_correct_answers: boolean;
  show_answer_keys: boolean;
  show_explanations: boolean;
  section_scores?: SectionScoreDetail[];
  evaluations?: any[];
}

export const evaluationService = {
  // 1. Evaluation Jobs
  async getEvaluationStatus(token: string, attemptId: string): Promise<EvaluationJobStatus> {
    const res = await fetch(`${API_BASE_URL}/evaluations/attempts/${attemptId}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch evaluation status');
    return res.json();
  },

  async startEvaluation(token: string, attemptId: string): Promise<EvaluationJobStatus> {
    const res = await fetch(`${API_BASE_URL}/evaluations/attempts/${attemptId}/start`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to start evaluation');
    return res.json();
  },

  async retryEvaluation(token: string, attemptId: string): Promise<EvaluationJobStatus> {
    const res = await fetch(`${API_BASE_URL}/evaluations/attempts/${attemptId}/retry`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to retry evaluation');
    return res.json();
  },

  async listManualTasks(token: string, quizId?: string): Promise<EvaluationTaskItem[]> {
    const url = quizId ? `${API_BASE_URL}/evaluations/tasks?quiz_id=${quizId}` : `${API_BASE_URL}/evaluations/tasks`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to list manual grading tasks');
    return res.json();
  },

  // 2. Manual Grading Workspace
  async getGradingWorkspace(token: string, attemptId: string): Promise<ManualGradingWorkspace> {
    const res = await fetch(`${API_BASE_URL}/grading/workspaces/${attemptId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch grading workspace');
    return res.json();
  },

  async saveManualEvaluation(
    token: string,
    payload: {
      attempt_id: string;
      quiz_question_id: string;
      marks_awarded: number;
      is_partially_correct?: boolean;
      feedback?: string;
      private_notes?: string;
      rubric_id?: string;
      criterion_scores?: Array<{ criterion_title: string; awarded_marks: number; max_marks: number }>;
      flag_for_moderation?: boolean;
    }
  ): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/grading/workspace/evaluate`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to save evaluation marks');
    return res.json();
  },

  // 3. Rubrics
  async listRubrics(token: string, subjectId?: string, search?: string): Promise<GradingRubric[]> {
    const params = new URLSearchParams();
    if (subjectId) params.append('subject_id', subjectId);
    if (search) params.append('search', search);
    const qs = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE_URL}/grading/rubrics${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to list rubrics');
    return res.json();
  },

  async createRubric(token: string, payload: any): Promise<GradingRubric> {
    const res = await fetch(`${API_BASE_URL}/grading/rubrics`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create rubric');
    return res.json();
  },

  async updateRubric(token: string, rubricId: string, payload: any): Promise<GradingRubric> {
    const res = await fetch(`${API_BASE_URL}/grading/rubrics/${rubricId}`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to update rubric');
    return res.json();
  },

  // 4. Assignments
  async listAssignments(token: string, quizId?: string): Promise<GradingAssignment[]> {
    const url = quizId ? `${API_BASE_URL}/grading/assignments?quiz_id=${quizId}` : `${API_BASE_URL}/grading/assignments`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to list grading assignments');
    return res.json();
  },

  async createAssignment(token: string, payload: any): Promise<GradingAssignment> {
    const res = await fetch(`${API_BASE_URL}/grading/assignments`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to assign evaluator');
    return res.json();
  },

  // 5. Moderation
  async listModerationQueue(token: string, quizId?: string): Promise<ModerationEvaluationItem[]> {
    const url = quizId ? `${API_BASE_URL}/evaluations/moderation?quiz_id=${quizId}` : `${API_BASE_URL}/evaluations/moderation`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch moderation queue');
    return res.json();
  },

  async processModerationAction(
    token: string,
    evaluationId: string,
    action: 'approve' | 'return' | 'override',
    newMarks?: number,
    reason?: string
  ): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/evaluations/moderation/${evaluationId}/action`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action,
        new_marks: newMarks,
        reason,
        override_reason: reason,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to process moderation action');
    return res.json();
  },

  // 6. Results
  async listResults(
    token: string,
    params?: {
      quiz_id?: string;
      search?: string;
      is_published?: boolean;
      is_approved?: boolean;
      is_passed?: boolean;
      page?: number;
      limit?: number;
    }
  ): Promise<ResultListResponse> {
    const qp = new URLSearchParams();
    if (params?.quiz_id) qp.append('quiz_id', params.quiz_id);
    if (params?.search) qp.append('search', params.search);
    if (params?.is_published !== undefined) qp.append('is_published', String(params.is_published));
    if (params?.is_approved !== undefined) qp.append('is_approved', String(params.is_approved));
    if (params?.is_passed !== undefined) qp.append('is_passed', String(params.is_passed));
    if (params?.page) qp.append('page', String(params.page));
    if (params?.limit) qp.append('limit', String(params.limit));
    const qs = qp.toString() ? `?${qp.toString()}` : '';

    const res = await fetch(`${API_BASE_URL}/results${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to list results');
    return res.json();
  },

  async getResultDetail(token: string, resultId: string): Promise<ResultDetail> {
    const res = await fetch(`${API_BASE_URL}/results/${resultId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch result detail');
    return res.json();
  },

  async approveResult(token: string, resultId: string, approvalNotes?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/results/${resultId}/approve`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ approval_notes: approvalNotes || null }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to approve result');
    return res.json();
  },

  async batchApproveResults(token: string, quizId: string, approvalNotes?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/results/batch-approve`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ quiz_id: quizId, approval_notes: approvalNotes || null }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to batch approve results');
    return res.json();
  },

  async publishResult(token: string, resultId: string, publish: boolean = true): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/results/${resultId}/publish`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ publish }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to publish result');
    return res.json();
  },

  async batchPublishResults(token: string, quizId: string, publish: boolean = true): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/results/batch-publish`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ quiz_id: quizId, publish }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to batch publish results');
    return res.json();
  },

  async overrideResult(token: string, resultId: string, newScore: number, reason: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/results/${resultId}/override`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ new_score: newScore, reason }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to override result score');
    return res.json();
  },

  async getStudentResult(attemptId: string): Promise<StudentResultResponse> {
    const res = await fetch(`${API_BASE_URL}/results/student/${attemptId}`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch examination result');
    return res.json();
  },
};
