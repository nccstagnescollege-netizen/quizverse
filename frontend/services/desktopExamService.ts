/**
 * Phase 25: Secure Desktop Examination Mode & Safe Exam Browser (SEB) Service
 * Client API bindings for SEB configurations, pre-examination compatibility verification,
 * desktop heartbeat monitoring, computer lab management, and lab readiness audits.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SEBConfiguration {
  id: string;
  quiz_id: string;
  version_number: number;
  config_name: string;
  config_key: string;
  browser_exam_key?: string | null;
  is_mandatory: boolean;
  allow_quit: boolean;
  min_seb_version: string;
  allow_reload: boolean;
  enable_url_filter: boolean;
  browser_view_mode: number;
  status: 'draft' | 'published' | 'revoked';
  has_config_password: boolean;
  has_quit_password: boolean;
  created_at: string;
  updated_at: string;
  revoked_at?: string | null;
  revocation_reason?: string | null;
}

export interface SEBConfigPayload {
  config_name?: string;
  start_url?: string;
  quit_url?: string;
  is_mandatory?: boolean;
  allow_quit?: boolean;
  min_seb_version?: string;
  config_password?: string;
  quit_password?: string;
  allow_reload?: boolean;
  enable_url_filter?: boolean;
  browser_view_mode?: number;
  custom_settings?: Record<string, any>;
}

export interface DesktopSessionVerifyPayload {
  quiz_id: string;
  attempt_id?: string;
  student_id?: string;
  reg_code?: string;
  lab_device_reference?: string;
  request_url?: string;
  seb_version?: string;
  os_platform?: string;
  config_key_hash?: string;
  request_hash?: string;
  user_agent?: string;
}

export interface DesktopSessionVerifyResponse {
  verified: boolean;
  session_mode: 'seb_enforced' | 'seb_voluntary' | 'standard_browser';
  is_seb: boolean;
  seb_version?: string | null;
  os_platform?: string | null;
  is_mandatory: boolean;
  can_proceed: boolean;
  config_status: 'valid' | 'revoked' | 'not_required' | 'hash_mismatch' | 'version_unsupported';
  message: string;
  lab_device?: {
    id: string;
    device_reference: string;
    compatibility_status: string;
    os_platform: string;
  } | null;
  session_id?: string | null;
  config_details?: {
    config_name?: string;
    version_number?: number;
    allow_quit?: boolean;
    min_seb_version?: string;
  } | null;
}

export interface ComputerLab {
  id: string;
  institution_id?: string | null;
  campus_name: string;
  lab_name: string;
  room_number?: string | null;
  total_workstations: number;
  network_subnet?: string | null;
  status: 'active' | 'maintenance' | 'inactive';
  contact_person?: string | null;
  notes?: string | null;
  device_count: number;
  ready_devices_count: number;
  created_at: string;
  updated_at: string;
}

export interface LabDevice {
  id: string;
  lab_id: string;
  device_reference: string;
  os_platform: 'windows' | 'macos' | 'linux';
  os_version?: string | null;
  seb_version?: string | null;
  ip_address?: string | null;
  mac_address_masked?: string | null;
  compatibility_status: 'ready' | 'update_required' | 'incompatible' | 'unverified';
  is_active: boolean;
  last_verified_at?: string | null;
  metadata_info?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface LabReadinessAudit {
  lab_id: string;
  lab_name: string;
  total_devices: number;
  ready_devices: number;
  update_required_devices: number;
  incompatible_devices: number;
  unverified_devices: number;
  readiness_percentage: number;
  is_ready_for_examination: boolean;
  audit_timestamp: string;
  recommendations: string[];
}

export const desktopExamService = {
  // -------------------------------------------------------------
  // SEB Configurations
  // -------------------------------------------------------------
  async getSEBConfig(quizId: string): Promise<SEBConfiguration | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/desktop-exam/quizzes/${quizId}/seb-config`, {
        cache: 'no-store',
      });
      if (res.status === 404) return null;
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },

  async createSEBConfig(
    quizId: string,
    payload: SEBConfigPayload,
    adminToken: string
  ): Promise<SEBConfiguration> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/quizzes/${quizId}/seb-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create Safe Exam Browser configuration');
    }
    return res.json();
  },

  async revokeSEBConfig(
    quizId: string,
    reason: string,
    adminToken: string
  ): Promise<SEBConfiguration> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/quizzes/${quizId}/seb-config/revoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify({ revocation_reason: reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to revoke SEB configuration');
    }
    return res.json();
  },

  getSEBDownloadUrl(quizId: string, version?: number): string {
    const url = new URL(`${API_BASE_URL}/desktop-exam/quizzes/${quizId}/seb-config/download`);
    if (version) {
      url.searchParams.set('version', String(version));
    }
    return url.toString();
  },

  // -------------------------------------------------------------
  // Desktop Session Verification & Telemetry
  // -------------------------------------------------------------
  async verifySession(payload: DesktopSessionVerifyPayload): Promise<DesktopSessionVerifyResponse> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/verify-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Desktop session verification failed');
    }
    return res.json();
  },

  async sendHeartbeat(
    sessionId: string,
    attemptId: string,
    inFullscreen: boolean = true,
    hasFocus: boolean = true
  ): Promise<{ status: string; recorded_at: string; interruption_count: number }> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/heartbeat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        attempt_id: attemptId,
        in_fullscreen: inFullscreen,
        has_focus: hasFocus,
        client_timestamp: new Date().toISOString(),
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Desktop heartbeat ping failed');
    }
    return res.json();
  },

  async sendInterruption(
    sessionId: string,
    attemptId: string,
    interruptionType: string,
    details?: any,
    severity: string = 'MEDIUM'
  ): Promise<{ logged: boolean; action: string; message: string; new_interruption_count: number }> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/interruption`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        attempt_id: attemptId,
        interruption_type: interruptionType,
        details,
        severity,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to record desktop interruption');
    }
    return res.json();
  },

  // -------------------------------------------------------------
  // Computer Lab Management
  // -------------------------------------------------------------
  async listLabs(adminToken: string, institutionId?: string, status?: string): Promise<ComputerLab[]> {
    const query = new URLSearchParams();
    if (institutionId) query.set('institution_id', institutionId);
    if (status) query.set('status', status);

    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs?${query.toString()}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load computer laboratories');
    }
    return res.json();
  },

  async createLab(payload: Partial<ComputerLab>, adminToken: string): Promise<ComputerLab> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create computer lab');
    }
    return res.json();
  },

  async updateLab(labId: string, payload: Partial<ComputerLab>, adminToken: string): Promise<ComputerLab> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update computer lab');
    }
    return res.json();
  },

  async deleteLab(labId: string, adminToken: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to delete computer lab');
    }
    return res.json();
  },

  // -------------------------------------------------------------
  // Lab Devices & Readiness Audit
  // -------------------------------------------------------------
  async listLabDevices(labId: string, adminToken: string): Promise<LabDevice[]> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}/devices`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to list lab devices');
    }
    return res.json();
  },

  async registerLabDevice(
    labId: string,
    payload: Partial<LabDevice>,
    adminToken: string
  ): Promise<LabDevice> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}/devices`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to register workstation in lab');
    }
    return res.json();
  },

  async updateLabDevice(
    labId: string,
    deviceId: string,
    payload: Partial<LabDevice>,
    adminToken: string
  ): Promise<LabDevice> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}/devices/${deviceId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update lab workstation');
    }
    return res.json();
  },

  async deleteLabDevice(
    labId: string,
    deviceId: string,
    adminToken: string
  ): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}/devices/${deviceId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to delete workstation');
    }
    return res.json();
  },

  async auditLabReadiness(labId: string, adminToken: string): Promise<LabReadinessAudit> {
    const res = await fetch(`${API_BASE_URL}/desktop-exam/labs/${labId}/readiness`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to audit lab readiness');
    }
    return res.json();
  },
};
