/**
 * Phase 10: Quiz Configuration, Scoring & Publishing Service
 * Handles unified configuration, validation, publishing, and lifecycle management for both Manual and Automatic Quizzes.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface QuizConfiguration {
  id: string;
  quiz_id: string;
  timezone: string;
  availability_mode: 'immediate' | 'scheduled' | 'restricted';
  start_time: string | null;
  end_time: string | null;
  reading_time_minutes: number;
  accommodations_extra_minutes: number;
  late_entry_minutes: number | null;
  early_access_minutes: number | null;
  grace_period_minutes: number;
  timer_type: 'per_student' | 'server_window';
  shuffle_questions: boolean;
  shuffle_options: boolean;
  question_grouping: 'preserve_order' | 'randomize_within_sections' | 'fixed';
  question_selection_mode: 'all_questions' | 'section_rules';
  passing_criteria_type: 'percentage' | 'fixed_marks';
  passing_marks: number | null;
  passing_percentage: number;
  negative_marking_type: 'none' | 'fixed' | 'question_specific';
  fixed_negative_marks: number;
  partial_marking_enabled: boolean;
  rounding_precision: number;
  evaluation_method: 'automatic' | 'manual' | 'mixed';
  require_manual_evaluation: boolean;
  navigation_mode: 'free' | 'sequential';
  allow_previous_nav: boolean;
  allow_answer_change: boolean;
  allow_mark_for_review: boolean;
  allow_skip_questions: boolean;
  show_question_palette: boolean;
  show_answered_stats: boolean;
  manual_submission_allowed: boolean;
  auto_submit_on_timeout: boolean;
  submission_confirmation_modal: boolean;
  submit_unanswered_questions: boolean;
  allow_attempt_reentry_on_disconnect: boolean;
  reentry_grace_minutes: number;
  result_release_policy: 'immediate' | 'after_close' | 'after_manual_eval' | 'after_approval' | 'never';
  release_date: string | null;
  show_score_immediately: boolean;
  show_question_breakdown: boolean;
  show_correct_answers: boolean;
  show_student_answers: boolean;
  show_explanations: boolean;
  show_percentile_rank: boolean;
  show_class_average: boolean;
  require_authenticated_student: boolean;
  enforce_access_code: boolean;
  ip_restriction_enabled: boolean;
  allowed_ip_ranges: string[];
  max_attempts: number;
  enable_tab_switch_detection: boolean;
  max_tab_switches_allowed: number;
  enable_copy_paste_prevention: boolean;
  enable_right_click_prevention: boolean;
  enable_fullscreen_enforcement: boolean;
  watermark_enabled: boolean;
  watermark_text: string | null;
  // Phase 22 Advanced Browser Examination Lockdown
  fullscreen_exit_policy?: 'warning_only' | 'record_incident' | 'pause_exam' | 'flag_review';
  max_focus_loss_count?: number;
  disable_copy?: boolean;
  disable_paste?: boolean;
  disable_context_menu?: boolean;
  print_restrictions?: boolean;
  navigation_warning?: boolean;
  network_interruption_policy?: 'buffer_and_resume' | 'pause_on_disconnect';
  require_invigilator_review?: boolean;
  // Phase 23 Screenshot, Screen Recording & Dynamic Watermark
  watermark_opacity?: number;
  watermark_font_size?: number;
  watermark_rotation_deg?: number;
  watermark_spacing_px?: number;
  watermark_update_interval_sec?: number;
  watermark_mask_student_id?: boolean;
  watermark_show_timestamp?: boolean;
  watermark_show_exam_id?: boolean;
  watermark_custom_text?: string | null;
  require_watermark_validation?: boolean;
  block_screen_capture_api?: boolean;
  track_screenshot_signals?: boolean;
  track_screen_recording_signals?: boolean;
  // Phase 24 Mobile Device Security & Native Examination Mode
  require_native_app?: boolean;
  android_secure_mode?: boolean;
  ios_secure_mode?: boolean;
  require_kiosk_mode?: boolean;
  min_android_version?: number;
  min_ios_version?: string;
  mobile_interruption_policy?: 'allow_with_event' | 'pause_on_interruption' | 'strict_flag_review';
  allow_device_recovery?: boolean;
  block_rooted_devices?: boolean;
  // Phase 25 Safe Exam Browser (SEB)
  require_seb?: boolean;
  seb_config_key?: string | null;
  seb_browser_exam_key?: string | null;
  seb_quit_password?: string | null;
  seb_allow_reload?: boolean;
  seb_show_reload_warning?: boolean;
  seb_show_time?: boolean;
  seb_enable_browser_window_toolbar?: boolean;
  // Phase 26 Advanced AI-Assisted Live Proctoring
  webcam_monitoring_enabled?: boolean;
  microphone_monitoring_enabled?: boolean;
  face_presence_detection?: boolean;
  multiple_person_detection?: boolean;
  head_position_detection?: boolean;
  audio_anomaly_detection?: boolean;
  proctoring_mandatory?: boolean;
  webcam_permission_required?: boolean;
  microphone_permission_required?: boolean;
  monitoring_interval_seconds?: number;
  proctoring_warning_threshold?: number;
  proctoring_critical_threshold?: number;
  proctoring_human_review_required?: boolean;
  recording_policy?: 'disabled' | 'incident_only' | 'continuous_consent';
  // Phase 32 Per-Quiz Webcam & Microphone Recording with Secure Supabase Storage
  recording_storage_enabled?: boolean;
  webcam_recording_enabled?: boolean;
  microphone_recording_enabled?: boolean;
  recording_quality?: 'standard' | 'high' | 'bandwidth_optimized';
  recording_retention_days?: number;
  allow_invigilator_recording_access?: boolean;
  allow_admin_recording_download?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ValidationCheckItem {
  category: 'content' | 'academic' | 'scoring' | 'schedule' | 'permissions';
  name: string;
  passed: boolean;
  level: 'error' | 'warning' | 'info';
  message: string;
}

export interface QuizValidationReport {
  quiz_id: string;
  is_valid: boolean;
  can_publish: boolean;
  checks: ValidationCheckItem[];
  summary: {
    total_checks: number;
    passed: number;
    warnings_count: number;
    errors_count: number;
    obtainable_marks: number;
    total_questions: number;
    total_sections: number;
  };
  scoring_summary?: any;
  errors?: string[];
  warnings?: string[];
  validated_at: string;
}

export interface QuizManagementItem {
  id: string;
  title: string;
  slug: string;
  description?: string | null;
  status: string;
  creation_mode: string;
  duration_minutes: number;
  total_marks?: number;
  maximum_marks?: number;
  passing_percentage: number;
  total_questions: number;
  total_sections?: number;
  published_version: number;
  is_draft?: boolean;
  created_by?: string;
  creator_name: string | null;
  subject_name: string | null;
  programme_name: string | null;
  start_time: string | null;
  end_time: string | null;
  availability_mode: string;
  last_validated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface QuizManagementListResponse {
  total: number;
  items: QuizManagementItem[];
}

export interface QuizPublishingHistoryItem {
  id: string;
  quiz_id: string;
  from_status: string;
  to_status: string;
  action: string;
  performed_by: string;
  performer_name: string | null;
  reason: string | null;
  created_at: string;
}

export const quizPublishingService = {
  async getQuizzesForManagement(
    token: string,
    params?: { status?: string; creation_mode?: string; search?: string; limit?: number; offset?: number }
  ): Promise<QuizManagementItem[]> {
    const url = new URL(`${API_BASE_URL}/quizzes/manage`);
    if (params?.status && params.status !== 'all') url.searchParams.set('status', params.status);
    if (params?.creation_mode && params.creation_mode !== 'all') url.searchParams.set('creation_mode', params.creation_mode);
    if (params?.search) url.searchParams.set('search', params.search);
    if (params?.limit) url.searchParams.set('limit', String(params.limit));
    if (params?.offset) url.searchParams.set('offset', String(params.offset));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load quizzes for management');
    }
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  },

  async getConfiguration(token: string, quizId: string): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/configuration`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load quiz configuration');
    }
    return res.json();
  },

  async updateConfiguration(token: string, quizId: string, payload: Partial<QuizConfiguration>): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/configuration`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update quiz configuration');
    }
    return res.json();
  },

  async updateSchedule(token: string, quizId: string, payload: any): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/schedule`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update schedule');
    }
    return res.json();
  },

  async updateScoring(token: string, quizId: string, payload: any): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/scoring`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update scoring');
    }
    return res.json();
  },

  async updateNavigation(token: string, quizId: string, payload: any): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/navigation`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update navigation settings');
    }
    return res.json();
  },

  async updateResultVisibility(token: string, quizId: string, payload: any): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/result-visibility`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update result visibility');
    }
    return res.json();
  },

  async updateSecurity(token: string, quizId: string, payload: any): Promise<QuizConfiguration> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/security`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update security settings');
    }
    return res.json();
  },

  async validateQuiz(token: string, quizId: string): Promise<QuizValidationReport> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/validate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to validate examination');
    }
    return res.json();
  },

  async getValidationReport(token: string, quizId: string): Promise<QuizValidationReport> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/validation-report`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load validation report');
    }
    return res.json();
  },

  async getFinalPreview(token: string, quizId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/final-preview`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load final review preview');
    }
    return res.json();
  },

  async publishQuiz(token: string, quizId: string, payload?: { change_log?: string; force_immediate?: boolean }): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/publish`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to publish examination');
    }
    return res.json();
  },

  async scheduleQuiz(token: string, quizId: string, payload: { start_time: string; end_time: string; timezone: string; change_log?: string }): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/schedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to schedule examination');
    }
    return res.json();
  },

  async unpublishQuiz(token: string, quizId: string, payload?: { reason?: string }): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/unpublish`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to unpublish examination');
    }
    return res.json();
  },

  async archiveQuiz(token: string, quizId: string, payload?: { reason?: string }): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/archive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to archive examination');
    }
    return res.json();
  },

  async getPublishingHistory(token: string, quizId: string): Promise<QuizPublishingHistoryItem[]> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/publishing-history`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load publishing history');
    }
    return res.json();
  },
};
