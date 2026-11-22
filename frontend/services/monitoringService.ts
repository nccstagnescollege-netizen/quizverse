const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://quizverse-ymsg.onrender.com/api/v1';

export interface MonitoringAlertItem {
  id: string;
  quiz_id: string;
  quiz_title?: string;
  student_id?: string;
  student_name?: string;
  attempt_id?: string;
  alert_type: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  title: string;
  details?: Record<string, any>;
  is_acknowledged: boolean;
  is_resolved: boolean;
  created_at: string;
}

export interface LiveExaminationItem {
  id: string;
  title: string;
  subject_name?: string;
  status: string;
  start_time?: string;
  end_time?: string;
  duration_minutes: number;
  total_marks: number;
  total_questions: number;
  enrolled_count: number;
  active_count: number;
  submitted_count: number;
  disconnected_count: number;
  sync_issue_count: number;
  security_alert_count: number;
  lead_invigilator_name?: string;
  invigilators_count: number;
  created_at?: string;
}

export interface LiveMonitoringOverviewResponse {
  active_examinations_count: number;
  total_eligible_participants: number;
  active_participants: number;
  disconnected_participants: number;
  sync_issue_participants: number;
  submitted_participants: number;
  pending_participants: number;
  critical_security_alerts: number;
  examinations_nearing_deadline: number;
  completed_examinations_today: number;
  recent_alerts: MonitoringAlertItem[];
  active_examinations: LiveExaminationItem[];
}

export interface InvigilatorSummary {
  id: string;
  invigilator_id: string;
  name: string;
  email: string;
  is_lead: boolean;
  permissions: string[];
  status: string;
  assigned_at: string;
}

export interface ExaminationMonitoringRoomResponse {
  id: string;
  title: string;
  subject_name?: string;
  programme_name?: string;
  semester_name?: string;
  status: string;
  start_time?: string;
  end_time?: string;
  duration_minutes: number;
  total_marks: number;
  total_questions: number;
  enrolled_participants: number;
  active_now: number;
  completed_submissions: number;
  disconnected_count: number;
  sync_pending_count: number;
  unresolved_incidents_count: number;
  critical_alerts_count: number;
  invigilators: InvigilatorSummary[];
  timeline_summary: Record<string, any>;
}

export interface ParticipantMonitoringItem {
  student_id: string;
  attempt_id?: string;
  full_name: string;
  register_number?: string;
  email: string;
  student_group?: string;
  attempt_status: string;
  connection_status: 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED' | 'COMPLETED' | 'NOT_STARTED';
  last_heartbeat_at?: string;
  sync_status: 'SYNCHRONIZED' | 'SYNC_PENDING' | 'SYNC_FAILED' | 'NOT_STARTED';
  last_sync_at?: string;
  current_question_index?: number;
  current_section_name?: string;
  answered_count: number;
  marked_for_review_count: number;
  unanswered_count: number;
  progress_percentage: number;
  time_spent_seconds: number;
  remaining_seconds: number;
  deadline_at?: string;
  security_alerts_count: number;
  latest_security_event?: string;
  has_active_incident: boolean;
  ip_address?: string;
  browser?: string;
  browser_compatibility_status?: string;
  fullscreen_status?: string;
  focus_loss_count?: number;
  fullscreen_exit_count?: number;
  incident_count?: number;
  review_status?: string;
  latest_incident?: string;
  // Phase 23 Watermark & Capture Telemetry
  watermark_status?: string;
  watermark_code?: string;
  capture_capability?: string;
  capture_signals_count?: number;
  latest_capture_signal?: string;
  // Phase 24 Mobile Security Telemetry
  device_platform?: 'android' | 'ios' | 'web';
  device_model?: string;
  native_app_version?: string;
  flag_secure_active?: boolean;
  kiosk_mode_active?: boolean;
  mobile_interruptions_count?: number;
  root_detected?: boolean;
  // Phase 25 Desktop Security & Safe Exam Browser Telemetry
  desktop_mode?: 'seb_enforced' | 'seb_voluntary' | 'standard_browser';
  is_seb_verified?: boolean;
  seb_version?: string;
  os_platform?: string;
  lab_device_reference?: string;
  desktop_interruption_count?: number;
  // Phase 26 Advanced AI-Assisted Live Proctoring Telemetry
  proctoring_session_id?: string;
  camera_status?: string;
  microphone_status?: string;
  face_presence_state?: string;
  head_position_state?: string;
  lighting_condition?: string;
  multiple_faces_detected?: boolean;
  audio_level_state?: string;
  ai_risk_score?: number;
  ai_risk_level?: string;
  ai_classification?: string;
  is_accommodated?: boolean;
  last_active_at?: string;
}

export interface AttemptEventItem {
  id: string;
  event_type: string;
  severity: string;
  details?: Record<string, any>;
  client_timestamp?: string;
  created_at: string;
}

export interface QuestionProgressSummary {
  question_index: number;
  question_type: string;
  is_answered: boolean;
  is_marked_for_review: boolean;
  answered_at?: string;
}

export interface IncidentSummaryItem {
  id: string;
  incident_code: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  created_at: string;
}

export interface ExtensionHistoryItem {
  id: string;
  extension_minutes: number;
  previous_deadline: string;
  new_deadline: string;
  reason: string;
  extended_by_name?: string;
  created_at: string;
}

export interface ParticipantDetailMonitoringResponse {
  participant: ParticipantMonitoringItem;
  event_timeline: AttemptEventItem[];
  question_progress: QuestionProgressSummary[];
  incidents: IncidentSummaryItem[];
  extension_history: ExtensionHistoryItem[];
}

export interface ExaminationAnnouncementResponse {
  id: string;
  quiz_id: string;
  sender_id?: string;
  sender_name?: string;
  title: string;
  message: string;
  announcement_type: string;
  target_scope: string;
  target_participant_ids?: string[];
  requires_acknowledgement: boolean;
  acknowledgement_count: number;
  created_at: string;
}

export interface IncidentNoteResponse {
  id: string;
  incident_id: string;
  author_id?: string;
  author_name?: string;
  note: string;
  created_at: string;
}

export interface ExaminationIncidentResponse {
  id: string;
  incident_code: string;
  quiz_id: string;
  student_id?: string;
  student_name?: string;
  attempt_id?: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  reported_by?: string;
  reported_by_name?: string;
  assigned_to?: string;
  assigned_to_name?: string;
  resolution_notes?: string;
  resolved_at?: string;
  notes: IncidentNoteResponse[];
  created_at: string;
  updated_at: string;
}

export interface MonitoringInterventionResponse {
  id: string;
  quiz_id: string;
  action_type: string;
  performed_by_id?: string;
  performed_by_name?: string;
  target_type: string;
  target_id?: string;
  reason: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  created_at: string;
}

class MonitoringService {
  private getHeaders(token: string): HeadersInit {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  // 1. Live Overview
  async getLiveOverview(token: string): Promise<LiveMonitoringOverviewResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/overview`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch live monitoring overview');
    }
    return res.json();
  }

  // 2. Active Examinations List
  async listActiveExaminations(token: string, status?: string, search?: string): Promise<{ total: number; items: LiveExaminationItem[] }> {
    const query = new URLSearchParams();
    if (status && status !== 'all') query.append('status', status);
    if (search) query.append('search', search);

    const res = await fetch(`${API_BASE_URL}/monitoring/examinations?${query.toString()}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch active examinations');
    }
    return res.json();
  }

  // 3. Examination Monitoring Room
  async getExaminationRoom(token: string, quizId: string): Promise<ExaminationMonitoringRoomResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch examination room data');
    }
    return res.json();
  }

  // 4. Live Participants Table
  async listRoomParticipants(
    token: string,
    quizId: string,
    search?: string,
    status?: string,
    connection?: string,
  ): Promise<{ total: number; items: ParticipantMonitoringItem[] }> {
    const query = new URLSearchParams();
    if (search) query.append('search', search);
    if (status && status !== 'ALL') query.append('status', status);
    if (connection && connection !== 'ALL') query.append('connection', connection);

    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/participants?${query.toString()}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch participant monitoring data');
    }
    return res.json();
  }

  // 5. Individual Participant Telemetry
  async getParticipantDetail(token: string, quizId: string, participantId: string): Promise<ParticipantDetailMonitoringResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/participants/${participantId}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch participant telemetry');
    }
    return res.json();
  }

  // 6. Invigilator Management
  async listInvigilators(token: string, quizId: string): Promise<{ total: number; items: any[] }> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/invigilators`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch invigilator list');
    }
    return res.json();
  }

  async assignInvigilator(
    token: string,
    quizId: string,
    payload: { invigilator_id: string; is_lead?: boolean; permissions?: string[] },
  ): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/invigilators`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to assign invigilator');
    }
    return res.json();
  }

  async revokeInvigilator(token: string, quizId: string, assignmentId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/invigilators/${assignmentId}`, {
      method: 'DELETE',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to revoke invigilator');
    }
    return res.json();
  }

  // 7. Announcements
  async listAnnouncements(token: string, quizId: string): Promise<{ total: number; items: ExaminationAnnouncementResponse[] }> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/announcements`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch announcements');
    }
    return res.json();
  }

  async createAnnouncement(
    token: string,
    quizId: string,
    payload: {
      title: string;
      message: string;
      announcement_type?: string;
      target_scope?: string;
      target_participant_ids?: string[];
      requires_acknowledgement?: boolean;
    },
  ): Promise<ExaminationAnnouncementResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/announcements`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to send announcement');
    }
    return res.json();
  }

  // 8. Incidents
  async listIncidents(token: string, quizId: string, status?: string, severity?: string): Promise<{ total: number; items: ExaminationIncidentResponse[] }> {
    const query = new URLSearchParams();
    if (status && status !== 'ALL') query.append('status', status);
    if (severity && severity !== 'ALL') query.append('severity', severity);

    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/incidents?${query.toString()}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch incidents');
    }
    return res.json();
  }

  async createIncident(
    token: string,
    quizId: string,
    payload: {
      category: string;
      severity?: string;
      title: string;
      description?: string;
      student_id?: string;
      attempt_id?: string;
      assigned_to?: string;
    },
  ): Promise<ExaminationIncidentResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/incidents`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({
        quiz_id: quizId,
        ...payload,
        description: payload.description || payload.title || 'Incident reported',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to report incident');
    }
    return res.json();
  }

  async updateIncident(
    token: string,
    quizId: string,
    incidentId: string,
    payload: { status?: string; assigned_to?: string; resolution_notes?: string },
  ): Promise<ExaminationIncidentResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/incidents/${incidentId}`, {
      method: 'PATCH',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update incident');
    }
    return res.json();
  }

  async addIncidentNote(token: string, quizId: string, incidentId: string, note: string): Promise<IncidentNoteResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/incidents/${incidentId}/notes`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ note }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to add incident note');
    }
    return res.json();
  }

  // 9. Alerts
  async listAlerts(token: string, quizId?: string, priority?: string, isResolved?: boolean): Promise<MonitoringAlertItem[]> {
    const query = new URLSearchParams();
    if (quizId) query.append('quiz_id', quizId);
    if (priority && priority !== 'ALL') query.append('priority', priority);
    if (isResolved !== undefined) query.append('is_resolved', String(isResolved));

    const res = await fetch(`${API_BASE_URL}/monitoring/alerts?${query.toString()}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch monitoring alerts');
    }
    return res.json();
  }

  async acknowledgeAlert(token: string, alertId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/monitoring/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to acknowledge alert');
    }
    return res.json();
  }

  async resolveAlert(token: string, alertId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/monitoring/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to resolve alert');
    }
    return res.json();
  }

  // 10. Emergency Interventions
  async extendTime(
    token: string,
    quizId: string,
    payload: { minutes: number; target_type?: string; student_id?: string; reason: string },
  ): Promise<MonitoringInterventionResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/extend-time`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to extend examination time');
    }
    return res.json();
  }

  async terminateAttempt(
    token: string,
    quizId: string,
    payload: { attempt_id?: string; student_id?: string; reason?: string },
  ): Promise<MonitoringInterventionResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/terminate-attempt`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({
        ...payload,
        reason: payload.reason?.trim() || 'Terminated by examination proctor',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to terminate attempt');
    }
    return res.json();
  }

  async cancelExamination(token: string, quizId: string, reason: string): Promise<MonitoringInterventionResponse> {
    const res = await fetch(`${API_BASE_URL}/monitoring/examinations/${quizId}/cancel`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to cancel examination');
    }
    return res.json();
  }
}

export const monitoringService = new MonitoringService();
