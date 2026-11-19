/**
 * Phase 14: Advanced Examination Security & Anti-Cheating Service
 * Client API bindings for Security Policies, Real-Time Telemetry, Risk Scores,
 * Alert Resolution, Investigation Timelines, and Dashboard Analytics.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SecurityPolicy {
  id: string;
  quiz_id?: string | null;
  policy_scope: 'platform' | 'quiz';
  track_tab_switch: boolean;
  track_focus_loss: boolean;
  require_fullscreen: boolean;
  track_fullscreen_exit: boolean;
  block_copy_paste: boolean;
  track_copy_paste: boolean;
  block_context_menu: boolean;
  track_page_reload: boolean;
  enable_watermark: boolean;
  watermark_pattern: string;
  max_tab_switches_warning: number;
  max_tab_switches_critical: number;
  max_focus_losses_warning: number;
  max_fullscreen_exits_warning: number;
  single_session_enforced: boolean;
  allow_session_recovery: boolean;
  randomize_question_order: boolean;
  randomize_option_order: boolean;
  student_notice_text?: string | null;
  student_acknowledgement_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface SecurityNotice {
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
}

export interface SecurityAlert {
  id: string;
  attempt_id: string;
  quiz_id: string;
  quiz_title?: string;
  student_id: string;
  student_name?: string;
  masked_identifier?: string;
  alert_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  occurrences_count: number;
  first_observed_at: string;
  last_observed_at: string;
  status: 'UNREVIEWED' | 'UNDER_REVIEW' | 'RESOLVED' | 'DISMISSED' | 'ESCALATED';
  resolution_reason?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SecurityAlertListResponse {
  total: number;
  page: number;
  limit: number;
  unreviewed_count: number;
  alerts: SecurityAlert[];
}

export interface SecurityTimelineEvent {
  id: string;
  timestamp: string;
  event_category: string;
  event_name: string;
  severity: string;
  description?: string;
  duration_ms?: number | null;
  sequence_number: number;
  metadata?: Record<string, any>;
}

export interface SecurityInvestigationNote {
  id: string;
  created_at: string;
  admin_id?: string | null;
  admin_name?: string | null;
  note_text: string;
  action_taken: string;
  alert_id?: string | null;
}

export interface SecurityInvestigationDetail {
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  student_id: string;
  student_name: string;
  masked_identifier: string;
  attempt_status: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  started_at?: string | null;
  submitted_at?: string | null;
  monitoring_acknowledged_at?: string | null;
  events_count: number;
  timeline: SecurityTimelineEvent[];
  alerts: SecurityAlert[];
  notes: SecurityInvestigationNote[];
}

export interface SecurityDashboardSummary {
  total_monitored_attempts: number;
  active_alerts_count: number;
  unreviewed_alerts_count: number;
  high_risk_candidates_count: number;
  medium_risk_candidates_count: number;
  low_risk_candidates_count: number;
  event_distribution: Record<string, number>;
  recent_alerts: SecurityAlert[];
}

export interface SecurityEventPayload {
  event_category: string;
  event_name: string;
  client_timestamp?: string;
  duration_ms?: number;
  sequence_number?: number;
  event_metadata?: Record<string, any>;
}

export interface SecurityEventSubmitResponse {
  success: boolean;
  recorded_count: number;
  current_risk_score: number;
  current_risk_level: string;
  active_alerts_count: number;
  warnings: string[];
}

export const securityService = {
  // -------------------------------------------------------------
  // Administrative Policy Management
  // -------------------------------------------------------------
  async getPlatformPolicy(adminToken: string): Promise<SecurityPolicy> {
    const res = await fetch(`${API_BASE_URL}/security/policies`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch platform security policy');
    }
    return res.json();
  },

  async getQuizPolicy(adminToken: string, quizId: string): Promise<SecurityPolicy> {
    const res = await fetch(`${API_BASE_URL}/security/policies/${quizId}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch quiz security policy');
    }
    return res.json();
  },

  async updateQuizPolicy(
    adminToken: string,
    quizId: string,
    policyData: Partial<SecurityPolicy>
  ): Promise<SecurityPolicy> {
    const res = await fetch(`${API_BASE_URL}/security/policies/${quizId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(policyData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update quiz security policy');
    }
    return res.json();
  },

  async updatePlatformPolicy(
    adminToken: string,
    policyData: Partial<SecurityPolicy>
  ): Promise<SecurityPolicy> {
    const res = await fetch(`${API_BASE_URL}/security/policies/platform/default`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(policyData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update platform default security policy');
    }
    return res.json();
  },

  // -------------------------------------------------------------
  // Alerts & Investigation Management
  // -------------------------------------------------------------
  async listAlerts(
    adminToken: string,
    params?: { quiz_id?: string; status?: string; severity?: string; page?: number; limit?: number }
  ): Promise<SecurityAlertListResponse> {
    const query = new URLSearchParams();
    if (params?.quiz_id) query.set('quiz_id', params.quiz_id);
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.page) query.set('page', String(params.page));
    if (params?.limit) query.set('limit', String(params.limit));

    const res = await fetch(`${API_BASE_URL}/security/alerts?${query.toString()}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to list security alerts');
    }
    return res.json();
  },

  async updateAlertStatus(
    adminToken: string,
    alertId: string,
    body: { status: string; resolution_reason?: string }
  ): Promise<SecurityAlert> {
    const res = await fetch(`${API_BASE_URL}/security/alerts/${alertId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update security alert');
    }
    return res.json();
  },

  async getInvestigation(adminToken: string, attemptId: string): Promise<SecurityInvestigationDetail> {
    const res = await fetch(`${API_BASE_URL}/security/investigations/${attemptId}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch investigation timeline');
    }
    return res.json();
  },

  async addInvestigationNote(
    adminToken: string,
    attemptId: string,
    body: { note_text: string; action_taken?: string; alert_id?: string }
  ): Promise<SecurityInvestigationNote> {
    const res = await fetch(`${API_BASE_URL}/security/investigations/${attemptId}/notes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to record administrative note');
    }
    return res.json();
  },

  async getDashboardSummary(adminToken: string, quizId?: string): Promise<SecurityDashboardSummary> {
    const query = quizId ? `?quiz_id=${quizId}` : '';
    const res = await fetch(`${API_BASE_URL}/security/dashboard${query}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load security dashboard metrics');
    }
    return res.json();
  },

  async purgeRetention(adminToken: string, retentionDays: number = 90): Promise<{ success: boolean; purged_count: number; message: string }> {
    const res = await fetch(`${API_BASE_URL}/security/retention/purge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify({ retention_days: retentionDays }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to purge security telemetry records');
    }
    return res.json();
  },

  // -------------------------------------------------------------
  // Candidate Pre-Exam Transparency & Telemetry
  // -------------------------------------------------------------
  async getStudentSecurityNotice(token: string): Promise<SecurityNotice> {
    const res = await fetch(`${API_BASE_URL}/student/exams/${token}/security-notice`, {
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch candidate security notice');
    }
    return res.json();
  },

  async acknowledgeMonitoring(
    attemptId: string,
    sessionToken: string
  ): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/acknowledge-monitoring`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ acknowledged: true }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to acknowledge examination monitoring');
    }
    return res.json();
  },

  async submitSecurityEvents(
    attemptId: string,
    sessionToken: string,
    events: SecurityEventPayload[]
  ): Promise<SecurityEventSubmitResponse> {
    const res = await fetch(`${API_BASE_URL}/student/attempts/${attemptId}/security-events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ events }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to post security telemetry events');
    }
    return res.json();
  },
};
