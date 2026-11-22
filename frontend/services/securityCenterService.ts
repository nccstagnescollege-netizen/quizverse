/**
 * Phase 28 - Centralized Anti-Cheating Control Center Service
 * Interfaces with FastAPI endpoints at /api/v1/security-center/*
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SecurityOverviewStats {
  active_examinations_count: number;
  active_attempts_count: number;
  connected_students_count: number;
  interrupted_attempts_count: number;
  open_incidents_count: number;
  critical_incidents_count: number;
  active_proctoring_sessions_count: number;
  high_risk_proctoring_count: number;
  pending_recovery_count: number;
  seb_enforced_exams_count: number;
  android_native_exams_count: number;
  security_events_last_hour_count: number;
  subsystem_health_summary: Record<string, string>;
  quick_action_items: Array<{
    type: string;
    label: string;
    count: number;
    severity: 'critical' | 'high' | 'medium' | 'low';
    target_url: string;
  }>;
}

export interface SubsystemHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'offline';
  latency_ms: number;
  message: string;
  last_checked_at: string;
  details?: Record<string, any>;
}

export interface SecurityHealthResponse {
  overall_status: 'healthy' | 'degraded' | 'offline';
  timestamp: string;
  subsystems: SubsystemHealth[];
}

export interface SecurityPolicyTemplate {
  id: string;
  name: string;
  code: string;
  description: string;
  is_system: boolean;
  category: string;
  config: Record<string, any>;
  supported_platforms: string[];
  restricted_platforms: string[];
  created_at: string;
  updated_at: string;
}

export interface PolicyValidationConflict {
  field_name: string;
  conflict_rule: string;
  description: string;
  suggested_resolution: string;
}

export interface PolicyValidationResult {
  is_valid: boolean;
  severity: 'valid' | 'warning' | 'conflict_error';
  conflicts: PolicyValidationConflict[];
  recommendations: string[];
  compatible_platforms: string[];
  incompatible_platforms: string[];
}

export interface PlatformCapability {
  platform: string;
  display_name: string;
  tier: string;
  supported_modes: string[];
  browser_lockdown_supported: boolean;
  fullscreen_lock_supported: boolean;
  tab_switch_detection_supported: boolean;
  clipboard_restriction_supported: boolean;
  watermark_supported: boolean;
  ai_proctoring_supported: boolean;
  os_screenshot_blocking_supported: boolean;
  phone_call_suppression_supported: boolean;
  notification_shade_blocking_supported: boolean;
  boundary_notes: string;
}

export interface DeviceCompatibilityCheckResponse {
  detected_platform: string;
  is_compatible: boolean;
  unmet_requirements: string[];
  warnings: string[];
  suggested_mode: string;
  platform_boundary_explanation: string;
}

export interface LiveExamSessionItem {
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  student_id: string;
  student_name: string;
  student_identifier: string;
  status: string;
  client_platform: string;
  connection_status: 'connected' | 'reconnecting' | 'disconnected';
  remaining_seconds: number;
  open_incidents_count: number;
  highest_incident_severity?: string;
  ai_proctoring_score?: number;
  ai_proctoring_level?: string;
  is_interrupted: boolean;
  pending_recovery: boolean;
  last_heartbeat_at?: string;
  started_at: string;
}

export interface SecurityActionRequest {
  action: 'SEND_WARNING' | 'FLAG_ATTEMPT' | 'PAUSE_EXAM' | 'PERMIT_RECOVERY' | 'REVOKE_SESSION' | 'TERMINATE_ATTEMPT';
  attempt_id: string;
  reason: string;
  confirmation_code: string; // Must be "CONFIRM"
  custom_message?: string;
}

export interface SecurityReportsData {
  timeframe_days: number;
  total_incidents: number;
  incidents_by_category: Record<string, number>;
  incidents_by_severity: Record<string, number>;
  incident_resolution_rate: number;
  average_recovery_time_seconds: number;
  false_positive_rate_estimate: number;
  policy_compliance_index: number;
  top_flagged_quizzes: Array<{ quiz_id: string; quiz_title: string; incident_count: number }>;
}

export interface PrivacyRetentionPolicy {
  category: string;
  display_name: string;
  retention_days: number;
  anonymization_procedure: string;
  is_immutable_audit: boolean;
  last_updated_at?: string;
}

export interface SecurityAuditEvent {
  id: string;
  actor_id?: string;
  actor_name: string;
  actor_role: string;
  action: string;
  target_type: string;
  target_id?: string;
  reason?: string;
  outcome: string;
  ip_address?: string;
  created_at: string;
  details?: Record<string, any>;
}

class SecurityCenterService {
  private getHeaders(token: string) {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  async getOverview(token: string): Promise<SecurityOverviewStats> {
    const res = await fetch(`${API_BASE_URL}/security-center/overview`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch security overview stats');
    }
    return res.json();
  }

  async getHealth(token: string): Promise<SecurityHealthResponse> {
    const res = await fetch(`${API_BASE_URL}/security-center/health`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch security subsystem health');
    }
    return res.json();
  }

  async listPolicyTemplates(token: string): Promise<SecurityPolicyTemplate[]> {
    const res = await fetch(`${API_BASE_URL}/security-center/policies/templates`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch policy templates');
    }
    return res.json();
  }

  async createCustomTemplate(token: string, payload: {
    name: string;
    code: string;
    description: string;
    category?: string;
    config: Record<string, any>;
    supported_platforms?: string[];
    restricted_platforms?: string[];
  }): Promise<SecurityPolicyTemplate> {
    const res = await fetch(`${API_BASE_URL}/security-center/policies/templates`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create security template');
    }
    return res.json();
  }

  async validatePolicy(token: string, config: Record<string, any>): Promise<PolicyValidationResult> {
    const res = await fetch(`${API_BASE_URL}/security-center/policies/validate`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ config }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to validate security policy');
    }
    return res.json();
  }

  async assignPolicy(token: string, payload: {
    quiz_id: string;
    template_code_or_id: string;
    custom_overrides?: Record<string, any>;
  }): Promise<{ message: string; quiz_id: string; applied_template: string }> {
    const res = await fetch(`${API_BASE_URL}/security-center/policies/assign`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to assign policy to quiz');
    }
    return res.json();
  }

  async getCapabilityMatrix(token: string): Promise<PlatformCapability[]> {
    const res = await fetch(`${API_BASE_URL}/security-center/device/capabilities`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch device capability matrix');
    }
    return res.json();
  }

  async checkDeviceCompatibility(token: string, payload: {
    user_agent?: string;
    platform?: string;
    sec_ch_ua?: string;
    quiz_id?: string;
  }): Promise<DeviceCompatibilityCheckResponse> {
    const res = await fetch(`${API_BASE_URL}/security-center/device/compatibility-check`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to check device compatibility');
    }
    return res.json();
  }

  async getLiveSessions(token: string, params?: { status?: string; search?: string }): Promise<LiveExamSessionItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);

    const qs = searchParams.toString();
    const url = `${API_BASE_URL}/security-center/monitoring/live${qs ? `?${qs}` : ''}`;
    const res = await fetch(url, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch live monitoring sessions');
    }
    return res.json();
  }

  async executeSecurityAction(token: string, payload: SecurityActionRequest): Promise<{
    success: boolean;
    action: string;
    attempt_id: string;
    timestamp: string;
    message: string;
  }> {
    const res = await fetch(`${API_BASE_URL}/security-center/actions/execute`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to execute security action');
    }
    return res.json();
  }

  async getSecurityReports(token: string, days: number = 30): Promise<SecurityReportsData> {
    const res = await fetch(`${API_BASE_URL}/security-center/reports?days=${days}`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch security analytics reports');
    }
    return res.json();
  }

  async getPrivacyPolicies(token: string): Promise<PrivacyRetentionPolicy[]> {
    const res = await fetch(`${API_BASE_URL}/security-center/privacy/policies`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch privacy retention policies');
    }
    return res.json();
  }

  async updatePrivacyRetention(token: string, payload: {
    category: string;
    retention_days: number;
    justification: string;
  }): Promise<{ message: string; category: string; new_retention_days: number }> {
    const res = await fetch(`${API_BASE_URL}/security-center/privacy/policies`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update privacy retention');
    }
    return res.json();
  }

  async getAuditLogs(token: string, limit: number = 50, skip: number = 0): Promise<SecurityAuditEvent[]> {
    const res = await fetch(`${API_BASE_URL}/security-center/audit?limit=${limit}&skip=${skip}`, {
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch security audit logs');
    }
    return res.json();
  }
}

export const securityCenterService = new SecurityCenterService();
