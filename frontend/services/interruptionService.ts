const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://quizverse-ymsg.onrender.com/api/v1';

export interface InterruptionEventRequest {
  attempt_id: string;
  quiz_id: string;
  event_type: string;
  severity_level?: number;
  duration_seconds?: number;
  details?: Record<string, any>;
  client_timestamp?: string;
  idempotency_key?: string;
}

export interface InterruptionEventResponse {
  success: boolean;
  event_id: string;
  action_required: 'NONE' | 'WARNING_DISPLAYED' | 'EXAM_PAUSED' | 'REVALIDATION_REQUIRED' | 'PENDING_REVIEW' | 'EXAM_EXPIRED';
  server_remaining_seconds: number;
  message: string;
}

export interface DevicePreparationRequest {
  quiz_id: string;
  attempt_id?: string;
  battery_level?: number;
  is_charging?: boolean;
  network_type?: string;
  dnd_acknowledged: boolean;
  notifications_muted_acknowledged: boolean;
  os_platform: string;
  device_info?: Record<string, any>;
}

export interface DevicePreparationResponse {
  success: boolean;
  can_proceed: boolean;
  policy: Record<string, any>;
  recommendations: string[];
  logged_at: string;
}

export interface SessionRecoveryRequest {
  attempt_id: string;
  quiz_id: string;
  reason: string;
  offline_answers_count?: number;
}

export interface SessionRecoveryResponse {
  success: boolean;
  recovery_status: 'RESUMED' | 'REQUIRES_REVALIDATION' | 'PENDING_REVIEW' | 'EXPIRED' | 'TERMINATED';
  recovery_token: string;
  server_remaining_seconds: number;
  server_deadline: string;
  total_synced_answers: number;
  interruption_policy: string;
  message: string;
}

export interface AnswerSyncItem {
  quiz_question_id: string;
  selected_option_ids?: string[];
  text_response?: string;
  time_spent_seconds?: number;
  client_timestamp?: string;
  idempotency_key?: string;
}

export interface AnswerBatchSyncRequest {
  attempt_id: string;
  quiz_id: string;
  answers: AnswerSyncItem[];
}

export interface AnswerBatchSyncResponse {
  success: boolean;
  total_processed: number;
  synced_count: number;
  ignored_count: number;
  server_time: string;
  results: { quiz_question_id: string; status: string }[];
}

export interface IncidentTimelineItemResponse {
  id: string;
  attempt_id: string;
  event_type: string;
  event_source: 'CLIENT_REPORTED' | 'SERVER_VERIFIED' | 'INVIGILATOR_ACTION';
  severity_level: number;
  duration_seconds: number;
  details?: Record<string, any>;
  client_timestamp?: string;
  server_timestamp: string;
}

export interface IncidentTimelineListResponse {
  attempt_id: string;
  total_events: number;
  events: IncidentTimelineItemResponse[];
}

export interface IncidentActionRequest {
  action: 'ACKNOWLEDGE' | 'ADD_NOTE' | 'ASSIGN' | 'MARK_REVIEWED' | 'ESCALATE' | 'AUTHORIZE_RECOVERY' | 'REQUEST_CLARIFICATION';
  assigned_to?: string;
  note?: string;
  resolution_notes?: string;
  reason?: string;
}

export interface IncidentActionResponse {
  success: boolean;
  incident_id: string;
  new_status: string;
  action_performed: string;
  message: string;
}

export interface InterruptionPolicyResponse {
  quiz_id: string;
  interruption_handling_policy: string;
  allow_call_recovery: boolean;
  max_call_interruptions: number;
  call_grace_seconds: number;
  require_device_prep_acknowledgment: boolean;
  auto_pause_on_disconnect: boolean;
  revalidation_code_required: boolean;
  network_interruption_policy?: string;
  allow_interrupted_session_resume: boolean;
}

class InterruptionService {
  private getHeaders(token?: string): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      headers['x-exam-session-token'] = token;
    }
    return headers;
  }

  async recordInterruptionEvent(
    token: string,
    payload: InterruptionEventRequest
  ): Promise<InterruptionEventResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/events`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to submit interruption event');
    }
    return res.json();
  }

  async recordDevicePreparation(
    token: string,
    payload: DevicePreparationRequest
  ): Promise<DevicePreparationResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/device-preparation`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to submit device preparation acknowledgment');
    }
    return res.json();
  }

  async recoverSession(
    token: string,
    payload: SessionRecoveryRequest
  ): Promise<SessionRecoveryResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/recover-session`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to recover examination session');
    }
    return res.json();
  }

  async syncPendingAnswers(
    token: string,
    payload: AnswerBatchSyncRequest
  ): Promise<AnswerBatchSyncResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/sync-answers`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to synchronize pending answers');
    }
    return res.json();
  }

  async getInterruptionPolicy(quizId: string): Promise<InterruptionPolicyResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/examinations/${quizId}/policy`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch interruption policy');
    }
    return res.json();
  }

  async getIncidentTimeline(
    adminToken: string,
    attemptId: string
  ): Promise<IncidentTimelineListResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/attempts/${attemptId}/timeline`, {
      method: 'GET',
      headers: this.getHeaders(adminToken),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch incident timeline');
    }
    return res.json();
  }

  async performIncidentAction(
    adminToken: string,
    incidentId: string,
    payload: IncidentActionRequest
  ): Promise<IncidentActionResponse> {
    const res = await fetch(`${API_BASE_URL}/interruption/incidents/${incidentId}/action`, {
      method: 'POST',
      headers: this.getHeaders(adminToken),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to perform incident action');
    }
    return res.json();
  }
}

export const interruptionService = new InterruptionService();
