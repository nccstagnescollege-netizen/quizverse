import { Institution, Subject, Topic, Unit, Chapter, Semester } from './academicService';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export type QuestionType = 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer' | 'numerical';
export type QuestionDifficulty = 'easy' | 'medium' | 'hard';
export type QuestionStatus = 'draft' | 'pending_review' | 'approved' | 'archived';

export interface QuestionOption {
  id: string;
  option_text: string;
  option_image_path?: string | null;
  option_order: number;
  is_correct?: boolean; // Only present if authorized with answer key
}

export interface QuestionTag {
  id: string;
  tag_name: string;
  description?: string | null;
}

export interface QuestionAttachment {
  id: string;
  question_id: string;
  file_name: string;
  file_path: string;
  file_type: string;
  file_size_bytes: number;
  is_student_visible: boolean;
  created_at: string;
}

export interface QuestionReview {
  id: string;
  question_id: string;
  reviewer_id?: string | null;
  reviewer_name?: string | null;
  action: 'submitted' | 'approved' | 'rejected';
  comments?: string | null;
  created_at: string;
}

export interface QuestionVersion {
  id: string;
  version_number: number;
  question_snapshot: Record<string, any>;
  change_summary?: string | null;
  changed_by?: string | null;
  changed_by_name?: string | null;
  created_at: string;
}

export interface ShortAnswerConfig {
  accepted_answers: string[];
  case_sensitive?: boolean;
  match_mode?: 'exact' | 'trimmed' | 'normalized';
}

export interface QuestionListItem {
  id: string;
  title?: string | null;
  question_text: string;
  question_type: QuestionType;
  difficulty: QuestionDifficulty;
  default_marks: number;
  default_negative_marks: number;
  status: QuestionStatus;
  is_mathematical: boolean;
  code_language?: string | null;
  topic_id: string;
  topic_name?: string | null;
  chapter_id?: string | null;
  chapter_name?: string | null;
  unit_id?: string | null;
  unit_name?: string | null;
  subject_id?: string | null;
  subject_name?: string | null;
  institution_id?: string | null;
  institution_name?: string | null;
  semester_id?: string | null;
  semester_name?: string | null;
  curriculum_id?: string | null;
  created_by?: string | null;
  created_by_name?: string | null;
  created_at: string;
  updated_at: string;
  options_count: number;
  tags: string[];
}

export interface QuestionDetail extends QuestionListItem {
  options: QuestionOption[];
  attachments: QuestionAttachment[];
  explanation?: string | null;
  short_answer_config?: ShortAnswerConfig | null;
  rejection_reason?: string | null;
  approved_by?: string | null;
  approved_by_name?: string | null;
  approved_at?: string | null;
  archived_at?: string | null;
  reviews?: QuestionReview[];
}

export interface QuestionStats {
  total_questions: number;
  draft: number;
  pending_review: number;
  approved: number;
  archived: number;
  by_type: Record<string, number>;
  by_difficulty: Record<string, number>;
}

export interface QuestionFilterParams {
  topic_id?: string;
  subject_id?: string;
  unit_id?: string;
  chapter_id?: string;
  semester_id?: string;
  institution_id?: string;
  status?: string;
  difficulty?: string;
  question_type?: string;
  search?: string;
  tag?: string;
  skip?: number;
  limit?: number;
}

export interface QuestionCreatePayload {
  title?: string;
  topic_id: string;
  chapter_id?: string;
  unit_id?: string;
  subject_id?: string;
  semester_id?: string;
  institution_id?: string;
  curriculum_id?: string;
  question_text: string;
  question_type: QuestionType;
  difficulty?: QuestionDifficulty;
  default_marks?: number;
  default_negative_marks?: number;
  explanation?: string;
  short_answer_config?: ShortAnswerConfig;
  is_mathematical?: boolean;
  code_language?: string;
  options?: Array<{
    option_text: string;
    option_image_path?: string;
    option_order?: number;
    is_correct: boolean;
  }>;
  tag_names?: string[];
}

export interface QuestionUpdatePayload {
  title?: string;
  topic_id?: string;
  chapter_id?: string;
  unit_id?: string;
  subject_id?: string;
  semester_id?: string;
  institution_id?: string;
  curriculum_id?: string;
  question_text?: string;
  question_type?: QuestionType;
  difficulty?: QuestionDifficulty;
  default_marks?: number;
  default_negative_marks?: number;
  explanation?: string;
  short_answer_config?: ShortAnswerConfig;
  is_mathematical?: boolean;
  code_language?: string;
  options?: Array<{
    option_text: string;
    option_image_path?: string;
    option_order?: number;
    is_correct: boolean;
  }>;
  tag_names?: string[];
  change_summary?: string;
}

async function fetchWithAuth<T>(
  endpoint: string,
  token?: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.error?.message || errorData.detail || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export const questionBankService = {
  // Query questions
  getQuestions: (params: QuestionFilterParams = {}, token?: string | null) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        searchParams.append(key, String(val));
      }
    });
    const qs = searchParams.toString();
    return fetchWithAuth<QuestionListItem[]>(`/questions${qs ? `?${qs}` : ''}`, token);
  },

  // Stats
  getStats: (token?: string | null) => fetchWithAuth<QuestionStats>('/questions/stats', token),

  // Single Question detail (includes answers if authorized)
  getQuestion: (id: string, token?: string | null) =>
    fetchWithAuth<QuestionDetail>(`/questions/${id}`, token),

  // Student-safe preview (never leaks answers/explanations)
  getPreview: (id: string, token?: string | null) =>
    fetchWithAuth<QuestionDetail>(`/questions/${id}/preview`, token),

  // Explicit Administrative Answer Key
  getAnswerKey: (id: string, token: string) =>
    fetchWithAuth<{
      question_id: string;
      question_type: QuestionType;
      explanation?: string;
      options: QuestionOption[];
      short_answer_config?: ShortAnswerConfig;
    }>(`/questions/${id}/answer-key`, token),

  // Create
  createQuestion: (payload: QuestionCreatePayload, token: string) =>
    fetchWithAuth<QuestionDetail>('/questions', token, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Update
  updateQuestion: (id: string, payload: QuestionUpdatePayload, token: string) =>
    fetchWithAuth<QuestionDetail>(`/questions/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Delete
  deleteQuestion: (id: string, token: string) =>
    fetchWithAuth<void>(`/questions/${id}`, token, {
      method: 'DELETE',
    }),

  // Duplicate
  duplicateQuestion: (id: string, token: string) =>
    fetchWithAuth<{ success: boolean; message: string; data: { id: string; title: string } }>(
      `/questions/${id}/duplicate`,
      token,
      { method: 'POST' }
    ),

  // Archive & Restore
  archiveQuestion: (id: string, token: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/questions/${id}/archive`, token, {
      method: 'POST',
    }),

  restoreQuestion: (id: string, token: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/questions/${id}/restore`, token, {
      method: 'POST',
    }),

  // Review Workflow
  submitForReview: (id: string, comments?: string, token?: string) =>
    fetchWithAuth<{ success: boolean; message: string; data: { id: string; status: string } }>(
      `/questions/${id}/submit-review`,
      token,
      {
        method: 'POST',
        body: JSON.stringify({ comments }),
      }
    ),

  approveQuestion: (id: string, comments?: string, token?: string) =>
    fetchWithAuth<{ success: boolean; message: string; data: { id: string; status: string } }>(
      `/questions/${id}/approve`,
      token,
      {
        method: 'POST',
        body: JSON.stringify({ comments }),
      }
    ),

  rejectQuestion: (id: string, comments: string, token: string) =>
    fetchWithAuth<{ success: boolean; message: string; data: { id: string; status: string } }>(
      `/questions/${id}/reject`,
      token,
      {
        method: 'POST',
        body: JSON.stringify({ comments }),
      }
    ),

  // Version History
  getVersionHistory: (id: string, token: string) =>
    fetchWithAuth<{ success: boolean; data: QuestionVersion[] }>(`/questions/${id}/history`, token),

  // Tags
  getTags: (search?: string, token?: string | null) =>
    fetchWithAuth<QuestionTag[]>(`/questions/tags/list${search ? `?search=${encodeURIComponent(search)}` : ''}`, token),

  createTag: (tag_name: string, description?: string, token?: string) =>
    fetchWithAuth<QuestionTag>('/questions/tags', token, {
      method: 'POST',
      body: JSON.stringify({ tag_name, description }),
    }),

  // Attachments
  uploadAttachment: (questionId: string, file: File, isStudentVisible: boolean = true, token: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_student_visible', String(isStudentVisible));
    return fetchWithAuth<QuestionAttachment>(`/questions/${questionId}/attachments`, token, {
      method: 'POST',
      body: formData,
    });
  },

  deleteAttachment: (questionId: string, attachmentId: string, token: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(
      `/questions/${questionId}/attachments/${attachmentId}`,
      token,
      { method: 'DELETE' }
    ),
};
