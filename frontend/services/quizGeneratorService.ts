const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface AcademicOptionItem {
  id: string;
  name?: string;
  code?: string;
  session_name?: string;
  semester_name?: string;
  semester_number?: number;
  subject_name?: string;
  subject_code?: string;
  unit_name?: string;
  unit_number?: number;
  programme_id?: string;
  institution_id?: string;
  subject_id?: string;
}

export interface AcademicOptionsResponse {
  institutions: AcademicOptionItem[];
  programmes: AcademicOptionItem[];
  academic_sessions: AcademicOptionItem[];
  semesters: AcademicOptionItem[];
  subjects: AcademicOptionItem[];
  units: AcademicOptionItem[];
}

export interface SyllabusTopicNode {
  id: string;
  name: string;
  code?: string;
  questions_count: number;
}

export interface SyllabusChapterNode {
  id: string;
  name: string;
  code?: string;
  topics: SyllabusTopicNode[];
}

export interface SyllabusUnitNode {
  id: string;
  name: string;
  unit_number: number;
  chapters: SyllabusChapterNode[];
}

export interface SyllabusHierarchyResponse {
  subject_id: string;
  subject_name: string;
  subject_code: string;
  units: SyllabusUnitNode[];
}

export interface AcademicScopePayload {
  institution_id?: string;
  programme_id?: string;
  academic_session_id?: string;
  semester_id?: string;
  subject_id: string;
  selected_unit_ids: string[];
  selected_chapter_ids: string[];
  selected_topic_ids: string[];
}

export interface DifficultyConfigPayload {
  easy_pct: number;
  medium_pct: number;
  hard_pct: number;
}

export interface MarksConfigPayload {
  mode: 'default' | 'uniform' | 'by_type';
  uniform_marks?: number;
  type_marks?: Record<string, number>;
  target_total_marks?: number;
}

export interface NegativeMarkingPayload {
  enabled: boolean;
  mode: 'default' | 'custom' | 'by_type';
  custom_value?: number;
  type_negative_marks?: Record<string, number>;
}

export interface UnitDistributionPayload {
  mode: 'equal' | 'custom' | 'weighted';
  unit_quotas?: Record<string, number>;
}

export interface ExamSettingsPayload {
  title: string;
  description?: string;
  instructions?: string;
  duration_minutes: number;
  passing_percentage: number;
  shuffle_questions: boolean;
  shuffle_options: boolean;
}

export interface PreflightCheckPayload {
  academic_scope: AcademicScopePayload;
  total_questions: number;
  difficulty: DifficultyConfigPayload;
  question_types: string[];
  unit_distribution?: UnitDistributionPayload;
  reuse_policy: 'allow_all' | 'prefer_unused' | 'unused_only';
}

export interface ShortfallItem {
  category: string;
  requested: number;
  available: number;
  missing: number;
  reason?: string;
}

export interface PreflightCheckResponse {
  is_valid: boolean;
  requested_total: number;
  available_total: number;
  difficulty_quotas: Record<string, number>;
  difficulty_available: Record<string, number>;
  type_quotas: Record<string, number>;
  type_available: Record<string, number>;
  unit_quotas: Record<string, number>;
  unit_available: Record<string, number>;
  shortfalls: ShortfallItem[];
  suggestions: string[];
  message: string;
}

export interface GeneratePaperPayload {
  academic_scope: AcademicScopePayload;
  total_questions: number;
  difficulty: DifficultyConfigPayload;
  question_types: string[];
  marks_config: MarksConfigPayload;
  negative_marking: NegativeMarkingPayload;
  unit_distribution: UnitDistributionPayload;
  reuse_policy: 'allow_all' | 'prefer_unused' | 'unused_only';
  exam_settings: ExamSettingsPayload;
  seed?: string;
}

export interface SelectedOption {
  id?: string;
  option_text: string;
  option_order: number;
  is_correct?: boolean;
}

export interface GeneratedQuestionItem {
  question_id: string;
  display_order: number;
  marks: number | string;
  negative_marks: number | string;
  is_locked: boolean;
  question_type: string;
  difficulty: string;
  title?: string;
  question_text: string;
  options: SelectedOption[];
  explanation?: string;
  short_answer_config?: any;
  subject_id?: string;
  subject_name?: string;
  unit_id?: string;
  unit_name?: string;
  chapter_id?: string;
  chapter_name?: string;
  topic_id?: string;
  topic_name?: string;
  is_mathematical?: boolean;
  code_language?: string;
}

export interface GenerationSession {
  id: string;
  session_title?: string;
  subject_id?: string;
  subject_name?: string;
  total_questions: number;
  total_marks: number | string;
  academic_scope: Record<string, any>;
  configuration: Record<string, any>;
  exam_settings: Record<string, any>;
  questions: GeneratedQuestionItem[];
  validation_report?: Record<string, any>;
  seed?: string;
  status: string;
  saved_quiz_id?: string;
  generated_by?: string;
  created_at: string;
  updated_at: string;
}

export interface ReplacementCandidate {
  id: string;
  title?: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  default_marks: number;
  topic_name?: string;
  unit_name?: string;
}

export type ReplacementCandidateItem = ReplacementCandidate;

export interface GenerationHistorySummary {
  id: string;
  session_title: string;
  subject_id?: string;
  subject_name?: string;
  questions_selected_count: number;
  status: string;
  saved_quiz_id?: string;
  generated_by?: string;
  generator_name?: string;
  created_at?: string;
}

export interface SaveAsDraftResponse {
  quiz_id: string;
  title: string;
  total_marks: number;
  question_count: number;
  status: string;
  redirect_url: string;
}

function getStoredAdminToken(explicitToken?: string | null): string | null {
  if (explicitToken) return explicitToken;
  if (typeof window === 'undefined') return null;
  const lsToken =
    localStorage.getItem('quizverse_admin_token') ||
    localStorage.getItem('quizverse_token');
  if (lsToken) return lsToken;

  try {
    const match = document.cookie.match(/(?:^|;\s*)quizverse_admin_token=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
  } catch {}

  return null;
}

async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {},
  explicitToken?: string | null
): Promise<T> {
  const token = getStoredAdminToken(explicitToken);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData.detail?.message ||
      (typeof errorData.detail === 'string' ? errorData.detail : null) ||
      errorData.message ||
      `Request failed (${res.status})`;
    const error: any = new Error(message);
    error.status = res.status;
    error.payload = errorData;
    throw error;
  }

  return res.json();
}

export const quizGeneratorService = {
  getAcademicOptions: async (token?: string | null): Promise<AcademicOptionsResponse> => {
    return fetchWithAuth<AcademicOptionsResponse>('/quiz-generator/academic-options', {}, token);
  },

  getSyllabusHierarchy: async (subjectId: string, token?: string | null): Promise<SyllabusHierarchyResponse> => {
    return fetchWithAuth<SyllabusHierarchyResponse>(`/quiz-generator/syllabus-hierarchy/${subjectId}`, {}, token);
  },

  checkAvailability: async (payload: PreflightCheckPayload, token?: string | null): Promise<PreflightCheckResponse> => {
    return fetchWithAuth<PreflightCheckResponse>(
      '/quiz-generator/check-availability',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      token
    );
  },

  generatePaper: async (payload: GeneratePaperPayload, token?: string | null): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(
      '/quiz-generator/generate',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      token
    );
  },

  getSession: async (generationId: string, token?: string | null): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(`/quiz-generator/sessions/${generationId}`, {}, token);
  },

  listSessions: async (limit: number = 50, token?: string | null): Promise<GenerationHistorySummary[]> => {
    return fetchWithAuth<GenerationHistorySummary[]>(`/quiz-generator/sessions?limit=${limit}`, {}, token);
  },

  getReplacementCandidates: async (
    generationId: string,
    questionId: string,
    filters: { matchDifficulty?: boolean; matchType?: boolean; matchTopic?: boolean } = {},
    token?: string | null
  ): Promise<ReplacementCandidateItem[]> => {
    const params = new URLSearchParams({
      match_difficulty: String(filters.matchDifficulty ?? true),
      match_type: String(filters.matchType ?? true),
      match_topic: String(filters.matchTopic ?? false),
    });
    return fetchWithAuth<ReplacementCandidate[]>(
      `/quiz-generator/sessions/${generationId}/candidates/${questionId}?${params.toString()}`,
      {},
      token
    );
  },

  replaceQuestion: async (
    generationId: string,
    questionId: string,
    replacementQuestionId?: string,
    token?: string | null
  ): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(
      `/quiz-generator/sessions/${generationId}/replace`,
      {
        method: 'POST',
        body: JSON.stringify({
          question_id: questionId,
          replacement_question_id: replacementQuestionId,
        }),
      },
      token
    );
  },

  reorderQuestions: async (
    generationId: string,
    orderList: string[],
    token?: string | null
  ): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(
      `/quiz-generator/sessions/${generationId}/reorder`,
      {
        method: 'PATCH',
        body: JSON.stringify({ question_ids_order: orderList }),
      },
      token
    );
  },

  updateQuestionSettings: async (
    generationId: string,
    questionId: string,
    settings: { marks?: number; negative_marks?: number; is_locked?: boolean },
    token?: string | null
  ): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(
      `/quiz-generator/sessions/${generationId}/question-settings`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          question_id: questionId,
          marks: settings.marks,
          negative_marks: settings.negative_marks,
          is_locked: settings.is_locked,
        }),
      },
      token
    );
  },

  regeneratePaper: async (
    generationId: string,
    preserveLocked: boolean = true,
    newSeed?: string,
    token?: string | null
  ): Promise<GenerationSession> => {
    return fetchWithAuth<GenerationSession>(
      `/quiz-generator/sessions/${generationId}/regenerate`,
      {
        method: 'POST',
        body: JSON.stringify({
          preserve_locked: preserveLocked,
          new_seed: newSeed,
        }),
      },
      token
    );
  },

  saveAsDraft: async (
    generationId: string,
    settings?: {
      exam_title?: string;
      exam_description?: string;
      instructions?: string;
      duration_minutes?: number;
      passing_percentage?: number;
    },
    token?: string | null
  ): Promise<SaveAsDraftResponse> => {
    return fetchWithAuth<SaveAsDraftResponse>(
      `/quiz-generator/sessions/${generationId}/save-draft`,
      {
        method: 'POST',
        body: JSON.stringify(settings || {}),
      },
      token
    );
  },

  listHistory: async (
    limit: number = 50,
    token?: string | null
  ): Promise<GenerationHistorySummary[]> => {
    return fetchWithAuth<GenerationHistorySummary[]>(
      `/quiz-generator/sessions?limit=${limit}`,
      { method: 'GET' },
      token
    );
  },
};
