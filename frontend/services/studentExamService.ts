/**
 * Phase 12: Student Examination Service
 * Client API bindings for student landing, instructions, active attempt, question rendering,
 * answer saving, review, submission, and result retrieval.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface StudentQuestionOption {
  id: string;
  text: string;
  order: number;
  image_url?: string | null;
}

export interface StudentQuestionItem {
  id: string;
  section_id?: string | null;
  question_order: number;
  question_type: string; // single_choice, multiple_choice, true_false, short_answer, numerical
  question_text: string;
  marks: number;
  negative_marks: number;
  is_compulsory: boolean;
  code_language?: string | null;
  is_mathematical: boolean;
  attachments?: Array<{ file_name: string; file_path: string; file_type: string }> | null;
  options?: StudentQuestionOption[] | null;
}

export interface StudentSectionItem {
  id: string;
  title: string;
  description?: string | null;
  instructions?: string | null;
  section_order: number;
  selection_rule: string; // all_compulsory, answer_n_of_m, all_optional
  required_question_count?: number | null;
  total_questions_count: number;
  section_total_marks: number;
}

export interface StudentExamLandingDetails {
  quiz_id: string;
  quiz_title: string;
  subject_name?: string | null;
  description?: string | null;
  instructions?: string | null;
  total_marks: number;
  total_questions: number;
  total_sections: number;
  duration_minutes: number;
  start_time?: string | null;
  end_time?: string | null;
  timezone: string;
  max_attempts: number;
  attempts_used: number;
  availability_status: 'scheduled' | 'available' | 'active' | 'completed' | 'expired' | 'unavailable';
  requires_registration: boolean;
  is_registered: boolean;
  participant_status?: 'approved' | 'pending_approval' | 'rejected' | 'revoked' | null;
  can_start: boolean;
  can_resume: boolean;
  active_attempt_id?: string | null;
  candidate?: {
    id: string;
    name: string;
    email: string;
    register_number?: string | null;
    registration_code?: string | null;
  } | null;
  allowed_actions: Array<'register' | 'view_instructions' | 'start' | 'resume' | 'view_result'>;
}

export interface StudentExamInstructions {
  quiz_title: string;
  subject_name?: string | null;
  duration_minutes: number;
  total_marks: number;
  total_questions: number;
  total_sections: number;
  max_attempts: number;
  instructions?: string | null;
  sections_summary: Array<{
    id: string;
    title: string;
    question_count: number;
    marks: number;
    selection_rule: string;
    required_question_count?: number | null;
  }>;
  rules: string[];
  selection_rules_notice?: string | null;
  allow_previous_nav: boolean;
  allow_answer_change: boolean;
  allow_mark_for_review: boolean;
  navigation_mode: string;
  security_notice?: {
    quiz_id: string;
    quiz_title: string;
    track_tab_switch: boolean;
    track_focus_loss: boolean;
    require_fullscreen: boolean;
    track_fullscreen_exit: boolean;
    block_copy_paste: boolean;
    track_copy_paste: boolean;
    block_context_menu: boolean;
    enable_watermark: boolean;
    student_acknowledgement_required: boolean;
    notice_text: string;
    watermark_text?: string | null;
    candidate_name?: string | null;
    masked_identifier?: string | null;
  } | null;
  monitoring_required?: boolean;
}

export interface StudentExamStartResult {
  attempt_id: string;
  session_token: string;
  quiz_id: string;
  student_name: string;
  student_identifier?: string | null;
  attempt_number: number;
  started_at: string;
  expires_at: string;
  remaining_seconds: number;
  is_resumed: boolean;
  status: string;
}

export interface StudentSavedAnswer {
  selected_option_ids: string[];
  text_response?: string;
  is_flagged_for_review: boolean;
  time_spent_seconds: number;
  answered_at?: string;
}

export interface StudentAttemptDetail {
  attempt_id: string;
  quiz_title: string;
  subject_name?: string | null;
  student_name: string;
  student_identifier?: string | null;
  status: string;
  started_at: string;
  expires_at: string;
  remaining_seconds: number;
  server_time: string;
  navigation_mode: string;
  allow_previous_nav: boolean;
  allow_answer_change: boolean;
  allow_mark_for_review: boolean;
  show_question_palette: boolean;
  sections: StudentSectionItem[];
  questions: StudentQuestionItem[];
  answers: Record<string, StudentSavedAnswer>;
  watermark_text?: string | null;
  security_policy?: {
    track_tab_switch: boolean;
    track_focus_loss: boolean;
    require_fullscreen: boolean;
    track_fullscreen_exit: boolean;
    block_copy_paste: boolean;
    track_copy_paste: boolean;
    block_context_menu: boolean;
    enable_watermark: boolean;
    max_tab_switches_warning: number;
    single_session_enforced: boolean;
  } | null;
  monitoring_acknowledged?: boolean;
}

export interface StudentReviewSummary {
  total_questions: number;
  answered_count: number;
  unanswered_count: number;
  marked_for_review_count: number;
  sections: Array<{
    section_id: string;
    title: string;
    total: number;
    answered: number;
    unanswered: number;
    marked: number;
    selection_rule: string;
    required_question_count?: number | null;
    is_satisfied: boolean;
  }>;
  mandatory_unanswered: Array<{
    question_id: string;
    order: number;
    section_title: string;
  }>;
  can_submit: boolean;
}

export interface StudentResultDetail {
  is_released: boolean;
  message: string;
  quiz_title?: string;
  student_name?: string;
  student_identifier?: string;
  score?: number;
  total_marks?: number;
  percentage?: number;
  is_passed?: boolean;
  submission_status?: string;
  total_correct?: number;
  total_incorrect?: number;
  total_unanswered?: number;
}

export const studentExamService = {
  // -------------------------------------------------------------
  // Session Token Storage Helpers
  // -------------------------------------------------------------
  setSession(token: string, attemptId: string, sessionToken: string, candidateCode?: string) {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(`exam_sess_${token}`, sessionToken);
    sessionStorage.setItem(`exam_att_${token}`, attemptId);
    if (candidateCode) {
      localStorage.setItem(`exam_reg_code_${token}`, candidateCode);
    }
  },

  getSession(token: string): { sessionToken: string | null; attemptId: string | null; registrationCode: string | null } {
    if (typeof window === 'undefined') {
      return { sessionToken: null, attemptId: null, registrationCode: null };
    }
    return {
      sessionToken: sessionStorage.getItem(`exam_sess_${token}`),
      attemptId: sessionStorage.getItem(`exam_att_${token}`),
      registrationCode: localStorage.getItem(`exam_reg_code_${token}`),
    };
  },

  clearSession(token: string) {
    if (typeof window === 'undefined') return;
    sessionStorage.removeItem(`exam_sess_${token}`);
    sessionStorage.removeItem(`exam_att_${token}`);
  },

  // -------------------------------------------------------------
  // API Calls
  // -------------------------------------------------------------
  async getExamLandingDetails(token: string, registrationCode?: string, email?: string): Promise<StudentExamLandingDetails> {
    const url = new URL(`${API_BASE_URL}/student/exams/${token}/details`);
    if (registrationCode) url.searchParams.set('registration_code', registrationCode);
    if (email) url.searchParams.set('email', email);

    const res = await fetch(url.toString(), { cache: 'no-store' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to fetch examination details');
    }
    return res.json();
  },

  async getExamInstructions(token: string): Promise<StudentExamInstructions> {
    const res = await fetch(`${API_BASE_URL}/student/exams/${token}/instructions`, { cache: 'no-store' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to fetch examination instructions');
    }
    return res.json();
  },

  async startOrResumeExam(
    token: string,
    payload: { registration_code?: string; student_identifier?: string; email?: string }
  ): Promise<StudentExamStartResult> {
    try {
      const res = await fetch(`${API_BASE_URL}/student/exams/${token}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error?.message || err.detail || 'Failed to start examination');
      }
      const data: StudentExamStartResult = await res.json();
      this.setSession(token, data.attempt_id, data.session_token, payload.registration_code);
      return data;
    } catch (err: any) {
      if (err.name === 'TypeError' || err.message?.includes('fetch') || err.message?.includes('Failed to fetch')) {
        throw new Error('Connection failed: The backend server is currently spinning up from cold sleep or completing deployment. Please wait a few seconds and try again.');
      }
      throw err;
    }
  },

  async getAttemptQuestions(attemptId: string, sessionToken: string): Promise<StudentAttemptDetail> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/questions`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load examination questions');
    }
    return res.json();
  },

  async saveAttemptAnswer(
    attemptId: string,
    sessionToken: string,
    payload: {
      quiz_question_id: string;
      selected_option_ids?: string[];
      text_response?: string;
      is_flagged_for_review: boolean;
      time_spent_seconds?: number;
    }
  ): Promise<{ success: boolean; is_answered: boolean; is_flagged_for_review: boolean }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/answers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to save answer');
    }
    return res.json();
  },

  async logAttemptEvent(attemptId: string, sessionToken: string, eventType: string, metadata?: Record<string, any>): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ event_type: eventType, metadata }),
      });
    } catch {
      // Telemetry errors should not interrupt candidate workflow
    }
  },

  async getAttemptReviewSummary(attemptId: string, sessionToken: string): Promise<StudentReviewSummary> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/review`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to generate answer review summary');
    }
    return res.json();
  },

  async toggleReviewFlag(
    attemptId: string,
    sessionToken: string,
    questionId: string,
    isFlagged: boolean
  ): Promise<{ success: boolean; quiz_question_id: string; is_flagged_for_review: boolean }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/questions/${questionId}/review`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ is_flagged_for_review: isFlagged }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to update review status');
    }
    return res.json();
  },

  async deleteAnswer(
    attemptId: string,
    sessionToken: string,
    answerId: string
  ): Promise<{ success: boolean; answer_id: string; version: number; answer_status: string }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/answers/${answerId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to clear answer');
    }
    return res.json();
  },

  async batchSaveAnswers(
    attemptId: string,
    sessionToken: string,
    operations: Array<{
      quiz_question_id: string;
      selected_option_ids?: string[];
      text_response?: string;
      is_flagged_for_review?: boolean;
      time_spent_seconds?: number;
      version?: number;
      idempotency_key?: string;
    }>
  ): Promise<{ success: boolean; total_processed: number; saved_answers: any[]; server_time: string }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/answers/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ operations }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to batch synchronize answers');
    }
    return res.json();
  },

  async getAttemptProgress(attemptId: string, sessionToken: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/progress`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to fetch attempt progress');
    }
    return res.json();
  },

  async sendHeartbeat(attemptId: string, sessionToken: string): Promise<{ server_time: string; remaining_seconds: number; deadline_at: string; status: string; is_active_session: boolean }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/heartbeat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ client_time: new Date().toISOString() }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Heartbeat sync failed');
    }
    return res.json();
  },

  async submitAttempt(attemptId: string, sessionToken: string, submissionReason: string = 'STUDENT_SUBMITTED'): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ confirm: true, submission_reason: submissionReason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to submit examination');
    }
    return res.json();
  },

  async getAttemptResult(attemptId: string, sessionToken: string): Promise<StudentResultDetail> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/result`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to retrieve examination results');
    }
    return res.json();
  },

  async getPublicExamResult(
    token: string,
    registrationCode?: string,
    email?: string,
    studentIdentifier?: string
  ): Promise<StudentResultDetail> {
    const url = new URL(`${API_BASE_URL}/student/exams/${token}/result`);
    if (registrationCode) url.searchParams.set('registration_code', registrationCode);
    if (email) url.searchParams.set('email', email);
    if (studentIdentifier) url.searchParams.set('student_identifier', studentIdentifier);

    const res = await fetch(url.toString(), { cache: 'no-store' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to retrieve examination results');
    }
    return res.json();
  },
};
