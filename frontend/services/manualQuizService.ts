const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface QuizSectionItem {
  id: string;
  quiz_id: string;
  title: string;
  description?: string | null;
  instructions?: string | null;
  section_order: number;
  selection_rule: 'all_compulsory' | 'all_optional' | 'answer_n_of_m';
  required_question_count: number;
  total_questions_count: number;
  default_marks_per_question: number;
  default_negative_marks_per_question: number;
  section_total_marks: number;
  created_at: string;
  updated_at: string;
}

export interface QuizQuestionItem {
  id: string;
  quiz_id: string;
  question_id?: string | null;
  section_id?: string | null;
  question_order: number;
  marks: number;
  negative_marks: number;
  is_compulsory: boolean;
  is_manual: boolean;
  source_type: 'bank' | 'manual' | 'generated';
  custom_instructions?: string | null;
  question_snapshot: {
    title?: string;
    question_text: string;
    question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer';
    difficulty?: string;
    marks?: number;
    negative_marks?: number;
    options?: Array<{
      id?: string;
      option_text: string;
      option_order?: number;
      is_correct?: boolean;
      explanation?: string | null;
      image_url?: string | null;
    }>;
    correct_answers?: string[];
    short_answer_config?: {
      accepted_variants?: string[];
      case_sensitive?: boolean;
      manual_evaluation?: boolean;
    };
    explanation?: string | null;
    subject_id?: string | null;
    subject_name?: string | null;
    unit_id?: string | null;
    unit_name?: string | null;
    topic_id?: string | null;
    topic_name?: string | null;
    tags?: string[];
    is_mathematical?: boolean;
    code_language?: string | null;
    source?: string;
    bank_question_id?: string | null;
  };
  scoring_settings?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface QuizScoringSummary {
  total_questions: number;
  total_sections: number;
  compulsory_questions: number;
  optional_questions: number;
  max_possible_marks: number;
  obtainable_marks: number;
  negative_marking_exposure: number;
  question_type_distribution: Record<string, number>;
  difficulty_distribution: Record<string, number>;
  is_valid: boolean;
  validation_errors: string[];
}

export interface QuizEditorResponse {
  quiz: {
    id: string;
    title: string;
    slug?: string;
    description?: string | null;
    category?: string | null;
    reference_code?: string | null;
    cover_image_url?: string | null;
    institution_id?: string | null;
    programme_id?: string | null;
    academic_session_id?: string | null;
    semester_id?: string | null;
    subject_id?: string | null;
    subject_name?: string | null;
    academic_scope?: Record<string, unknown>;
    scoring_policy?: Record<string, unknown>;
    instructions?: string | null;
    duration_minutes: number;
    total_marks: number;
    passing_marks: number;
    shuffle_questions: boolean;
    shuffle_options: boolean;
    is_draft: boolean;
    draft_version: number;
    status: string;
    created_at: string;
    updated_at: string;
  };
  sections: QuizSectionItem[];
  questions: QuizQuestionItem[];
  scoring_summary: QuizScoringSummary;
}

export interface QuizPreviewQuestion {
  quiz_question_id: string;
  section_id?: string | null;
  section_title?: string | null;
  question_order: number;
  question_text: string;
  question_type: string;
  difficulty?: string;
  marks: number;
  negative_marks: number;
  is_compulsory: boolean;
  source_type: string;
  options: Array<{
    id?: string;
    option_text: string;
    option_order?: number;
    is_correct?: boolean; // Strictly omitted in student view
    image_url?: string | null;
  }>;
  correct_answers?: string[]; // Strictly omitted in student view
  short_answer_config?: Record<string, unknown>;
  explanation?: string | null; // Strictly omitted in student view
  is_mathematical?: boolean;
  code_language?: string | null;
  custom_instructions?: string | null;
}

export interface QuizPreviewResponse {
  mode: 'student' | 'answer_key';
  quiz: {
    id: string;
    title: string;
    description?: string | null;
    instructions?: string | null;
    duration_minutes: number;
    total_marks: number;
    passing_marks: number;
    subject_name?: string | null;
    sections_count: number;
    questions_count: number;
  };
  sections: Array<{
    id: string;
    title: string;
    description?: string | null;
    instructions?: string | null;
    section_order: number;
    selection_rule: string;
    required_question_count: number;
    total_questions_count: number;
    section_total_marks: number;
  }>;
  questions: QuizPreviewQuestion[];
}

class ManualQuizService {
  private async request<T>(endpoint: string, options: RequestInit = {}, token?: string): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        errorMsg = body.error?.message || body.detail || body.message || errorMsg;
      } catch {
        // ignore json parse error
      }
      throw new Error(errorMsg);
    }

    return res.json();
  }

  // 1. Create a blank manual quiz
  async createManualQuiz(data: {
    title: string;
    description?: string;
    institution_id?: string;
    programme_id?: string;
    academic_session_id?: string;
    semester_id?: string;
    subject_id?: string;
    category?: string;
    reference_code?: string;
    instructions?: string;
    duration_minutes?: number;
    passing_percentage?: number;
  }, token: string): Promise<{ quiz_id: string; title: string; is_draft: boolean }> {
    return this.request('/quizzes/manual', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);
  }

  // 2. Fetch full quiz editor data
  async getEditorState(quizId: string, token: string): Promise<QuizEditorResponse> {
    return this.request(`/quizzes/${quizId}/editor`, { method: 'GET' }, token);
  }

  // 3. Update quiz details & metadata
  async updateQuizDetails(quizId: string, details: Record<string, unknown>, token: string): Promise<Record<string, unknown>> {
    return this.request(`/quizzes/${quizId}/details`, {
      method: 'PATCH',
      body: JSON.stringify(details),
    }, token);
  }

  // 4. Section CRUD
  async createSection(quizId: string, payload: {
    title: string;
    description?: string;
    instructions?: string;
    selection_rule?: 'all_compulsory' | 'all_optional' | 'answer_n_of_m';
    required_question_count?: number;
    default_marks_per_question?: number;
    default_negative_marks_per_question?: number;
  }, token: string): Promise<QuizSectionItem> {
    return this.request(`/quizzes/${quizId}/sections`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }, token);
  }

  async updateSection(quizId: string, sectionId: string, payload: Record<string, unknown>, token: string): Promise<QuizSectionItem> {
    return this.request(`/quizzes/${quizId}/sections/${sectionId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }, token);
  }

  async deleteSection(quizId: string, sectionId: string, token: string): Promise<{ success: boolean }> {
    return this.request(`/quizzes/${quizId}/sections/${sectionId}`, {
      method: 'DELETE',
    }, token);
  }

  async reorderSections(quizId: string, items: Array<{ id: string; section_order: number }>, token: string): Promise<{ success: boolean; sections: QuizSectionItem[] }> {
    return this.request(`/quizzes/${quizId}/sections/reorder`, {
      method: 'POST',
      body: JSON.stringify({ items }),
    }, token);
  }

  // 5. Method A: Add manual question
  async addManualQuestion(quizId: string, payload: {
    question_text: string;
    question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer';
    section_id?: string | null;
    title?: string;
    difficulty?: string;
    marks?: number;
    negative_marks?: number;
    is_compulsory?: boolean;
    options?: Array<{
      option_text: string;
      is_correct?: boolean;
      explanation?: string;
      image_url?: string;
    }>;
    short_answer_config?: {
      accepted_variants?: string[];
      case_sensitive?: boolean;
      manual_evaluation?: boolean;
    };
    explanation?: string;
    is_mathematical?: boolean;
    code_language?: string;
    custom_instructions?: string;
    topic_id?: string;
  }, token: string): Promise<QuizQuestionItem> {
    return this.request(`/quizzes/${quizId}/questions/manual`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }, token);
  }

  // 6. Method B: Add from Question Bank
  async addFromQuestionBank(quizId: string, payload: {
    question_ids: string[];
    section_id?: string | null;
    default_marks?: number;
    default_negative_marks?: number;
    is_compulsory?: boolean;
  }, token: string): Promise<QuizQuestionItem[]> {
    return this.request(`/quizzes/${quizId}/questions/from-bank`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }, token);
  }

  // 7. Promote manual question to shared Question Bank
  async saveToQuestionBank(quizId: string, quizQuestionId: string, targetTopicId?: string, token?: string): Promise<{ success: boolean; question_id: string; status: string; message: string }> {
    return this.request(`/quizzes/${quizId}/questions/${quizQuestionId}/save-to-bank`, {
      method: 'POST',
      body: JSON.stringify({ target_topic_id: targetTopicId }),
    }, token);
  }

  // 8. Update question in quiz
  async updateQuizQuestion(quizId: string, quizQuestionId: string, payload: {
    section_id?: string | null;
    marks?: number;
    negative_marks?: number;
    is_compulsory?: boolean;
    custom_instructions?: string | null;
    question_snapshot?: Record<string, unknown>;
  }, token: string): Promise<QuizQuestionItem> {
    return this.request(`/quizzes/${quizId}/questions/${quizQuestionId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }, token);
  }

  // 9. Delete question from quiz
  async deleteQuizQuestion(quizId: string, quizQuestionId: string, token: string): Promise<{ success: boolean }> {
    return this.request(`/quizzes/${quizId}/questions/${quizQuestionId}`, {
      method: 'DELETE',
    }, token);
  }

  // 10. Reorder / move questions across sections
  async reorderQuestions(quizId: string, items: Array<{ id: string; question_order: number; section_id?: string | null }>, token: string): Promise<{ success: boolean; questions: QuizQuestionItem[] }> {
    return this.request(`/quizzes/${quizId}/questions/reorder`, {
      method: 'POST',
      body: JSON.stringify({ items }),
    }, token);
  }

  // 11. Validate quiz scoring & rules
  async validateQuiz(quizId: string, token: string): Promise<{
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    scoring_summary: QuizScoringSummary;
  }> {
    return this.request(`/quizzes/${quizId}/validate`, { method: 'POST' }, token);
  }

  // 12. Save Draft snapshot
  async saveDraft(quizId: string, changeSummary?: string, token?: string): Promise<{
    success: boolean;
    version_number: number;
    saved_at: string;
    message: string;
  }> {
    return this.request(`/quizzes/${quizId}/save-draft`, {
      method: 'POST',
      body: JSON.stringify({ change_summary: changeSummary }),
    }, token);
  }

  // 13. Live Preview (Student vs Answer Key)
  async getPreview(quizId: string, mode: 'student' | 'answer_key' = 'student', token?: string): Promise<QuizPreviewResponse> {
    return this.request(`/quizzes/${quizId}/preview?mode=${mode}`, { method: 'GET' }, token);
  }

  // 14. File attachment upload
  async uploadAttachment(quizId: string, file: File, quizQuestionId?: string, token?: string): Promise<{
    id: string;
    file_name: string;
    file_path: string;
    file_type: string;
    file_size_bytes: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    if (quizQuestionId) {
      formData.append('quiz_question_id', quizQuestionId);
    }

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/attachments`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      let errorMsg = `Upload failed (${res.status})`;
      try {
        const body = await res.json();
        errorMsg = body.error?.message || body.detail || body.message || errorMsg;
      } catch {
        // ignore
      }
      throw new Error(errorMsg);
    }

    return res.json();
  }
}

export const manualQuizService = new ManualQuizService();
