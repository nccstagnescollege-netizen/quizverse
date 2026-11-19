/**
 * Phase 11: Invitation Links, QR Codes & Student Registration Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface RegistrationFormFieldConfig {
  field_name: string;
  field_label: string;
  field_type: 'text' | 'textarea' | 'email' | 'phone' | 'number' | 'select' | 'radio' | 'checkbox' | 'date';
  placeholder?: string;
  help_text?: string;
  is_required: boolean;
  is_built_in?: boolean;
  default_value?: any;
  min_length?: number;
  max_length?: number;
  validation_regex?: string;
  options?: string[];
  is_unique?: boolean;
  display_order?: number;
}

export interface RegistrationFormResponse {
  id: string;
  quiz_id: string;
  version_number: number;
  title: string;
  description?: string;
  fields_config: RegistrationFormFieldConfig[];
  unique_fields: string[];
  require_manual_approval: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvitationCreatePayload {
  quiz_id: string;
  name: string;
  description?: string;
  invitation_type?: 'general' | 'single_use' | 'individual' | 'group' | 'restricted';
  category?: string;
  max_uses?: number;
  max_attempts_per_student?: number;
  target_email?: string;
  starts_at?: string | null;
  expires_at?: string | null;
  timezone?: string;
  allowed_student_groups?: string[];
  is_reusable?: boolean;
  require_account?: boolean;
  require_approval?: boolean;
  internal_notes?: string;
}

export interface InvitationUpdatePayload {
  name?: string;
  description?: string;
  category?: string;
  max_uses?: number;
  max_attempts_per_student?: number;
  target_email?: string;
  starts_at?: string | null;
  expires_at?: string | null;
  timezone?: string;
  allowed_student_groups?: string[];
  is_reusable?: boolean;
  require_account?: boolean;
  require_approval?: boolean;
  internal_notes?: string;
}

export interface InvitationItem {
  id: string;
  quiz_id: string;
  quiz_title?: string;
  subject_name?: string;
  name: string;
  description?: string;
  invitation_type: 'general' | 'single_use' | 'individual' | 'group' | 'restricted';
  category: string;
  status: 'active' | 'scheduled' | 'expired' | 'revoked' | 'exhausted' | 'draft';
  target_email?: string;
  max_uses: number;
  used_count: number;
  remaining_uses: number;
  max_attempts_per_student: number;
  starts_at?: string | null;
  expires_at?: string | null;
  timezone: string;
  allowed_student_groups?: string[];
  is_reusable: boolean;
  require_account: boolean;
  require_approval: boolean;
  internal_notes?: string;
  is_revoked: boolean;
  created_by_name?: string;
  created_at: string;
  updated_at: string;

  // Present on initial generation
  access_url?: string;
  qr_svg?: string;
  qr_png_base64?: string;
  raw_token?: string;
}

export interface InvitationListResponse {
  items: InvitationItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface InvitationUsageItem {
  id: string;
  invitation_id: string;
  student_id: string;
  student_name?: string;
  student_email?: string;
  student_identifier?: string;
  status: string;
  failure_reason?: string;
  device_type?: string;
  ip_address?: string;
  user_agent?: string;
  used_at: string;
}

export interface InvitationUsageResponse {
  total_redemptions: number;
  successful_count: number;
  failed_count: number;
  remaining_capacity: number;
  usages: InvitationUsageItem[];
}

export interface ParticipantItem {
  id: string;
  quiz_id: string;
  invitation_id?: string;
  student_id: string;
  full_name: string;
  email: string;
  phone?: string;
  student_identifier?: string;
  institution?: string;
  registration_data: Record<string, any>;
  status: 'approved' | 'pending_approval' | 'rejected' | 'revoked';
  attempt_count: number;
  registered_at: string;
  approved_at?: string;
  approved_by_name?: string;
  rejection_reason?: string;
  internal_notes?: string;
}

export interface ParticipantListResponse {
  items: ParticipantItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  stats: {
    total: number;
    approved: number;
    pending_approval: number;
    rejected: number;
    revoked: number;
  };
}

export interface EligibleQuizItem {
  id: string;
  title: string;
  subject_name?: string;
  status: string;
  total_questions: number;
  total_marks: number;
  duration_minutes: number;
  schedule_start?: string;
  schedule_end?: string;
  requires_invitation: boolean;
  active_invitations_count: number;
}

export interface PublicInvitationValidation {
  is_valid: boolean;
  error_code?: string;
  error_message?: string;
  quiz_id?: string;
  quiz_title?: string;
  subject_name?: string;
  duration_minutes?: number;
  total_marks?: number;
  instructions?: string;
  schedule_start?: string;
  schedule_end?: string;
  timezone?: string;
  invitation_name?: string;
  invitation_type?: string;
  require_approval: boolean;
  registration_form?: RegistrationFormFieldConfig[];
}

export interface PublicRegistrationReceipt {
  success: boolean;
  participant_id: string;
  registration_code: string;
  status: string;
  message: string;
  quiz_title: string;
  subject_name?: string;
  student_name: string;
  student_identifier?: string;
  scheduled_start?: string;
  examination_duration_minutes?: number;
}

export const invitationService = {
  async getEligibleQuizzes(token: string): Promise<EligibleQuizItem[]> {
    const res = await fetch(`${API_BASE_URL}/invitations/eligible-quizzes`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load eligible quizzes');
    }
    return res.json();
  },

  async createInvitation(token: string, payload: InvitationCreatePayload): Promise<InvitationItem> {
    const res = await fetch(`${API_BASE_URL}/invitations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to generate invitation link');
    }
    return res.json();
  },

  async listInvitations(
    token: string,
    params?: {
      quiz_id?: string;
      status?: string;
      type?: string;
      search?: string;
      page?: number;
      limit?: number;
    }
  ): Promise<InvitationListResponse> {
    const url = new URL(`${API_BASE_URL}/invitations`);
    if (params?.quiz_id) url.searchParams.set('quiz_id', params.quiz_id);
    if (params?.status && params.status !== 'all') url.searchParams.set('status', params.status);
    if (params?.type && params.type !== 'all') url.searchParams.set('type', params.type);
    if (params?.search) url.searchParams.set('search', params.search);
    if (params?.page) url.searchParams.set('page', String(params.page));
    if (params?.limit) url.searchParams.set('limit', String(params.limit));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load invitations');
    }
    return res.json();
  },

  async getInvitation(token: string, invitationId: string): Promise<InvitationItem> {
    const res = await fetch(`${API_BASE_URL}/invitations/${invitationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load invitation detail');
    }
    return res.json();
  },

  async updateInvitation(token: string, invitationId: string, payload: InvitationUpdatePayload): Promise<InvitationItem> {
    const res = await fetch(`${API_BASE_URL}/invitations/${invitationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to update invitation');
    }
    return res.json();
  },

  async revokeInvitation(token: string, invitationId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/invitations/${invitationId}/revoke`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to revoke invitation');
    }
    return res.json();
  },

  async getInvitationUsage(token: string, invitationId: string): Promise<InvitationUsageResponse> {
    const res = await fetch(`${API_BASE_URL}/invitations/${invitationId}/usage`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load usage history');
    }
    return res.json();
  },

  async getInvitationParticipants(
    token: string,
    invitationId: string,
    params?: { status?: string; search?: string; page?: number; limit?: number }
  ): Promise<ParticipantListResponse> {
    const url = new URL(`${API_BASE_URL}/invitations/${invitationId}/participants`);
    if (params?.status && params.status !== 'all') url.searchParams.set('status', params.status);
    if (params?.search) url.searchParams.set('search', params.search);
    if (params?.page) url.searchParams.set('page', String(params.page));
    if (params?.limit) url.searchParams.set('limit', String(params.limit));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load participants');
    }
    return res.json();
  },

  async exportInvitationParticipantsCSV(token: string, invitationId: string): Promise<Blob> {
    const res = await fetch(`${API_BASE_URL}/invitations/${invitationId}/export`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      throw new Error('Failed to download CSV');
    }
    return res.blob();
  },

  async getQuizRegistrationForm(token: string, quizId: string): Promise<RegistrationFormResponse> {
    const res = await fetch(`${API_BASE_URL}/invitations/quizzes/${quizId}/registration-form`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load registration form');
    }
    return res.json();
  },

  async saveQuizRegistrationForm(
    token: string,
    quizId: string,
    payload: {
      title: string;
      description?: string;
      fields_config: RegistrationFormFieldConfig[];
      unique_fields: string[];
      require_manual_approval: boolean;
    }
  ): Promise<RegistrationFormResponse> {
    const res = await fetch(`${API_BASE_URL}/invitations/quizzes/${quizId}/registration-form`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to save registration form');
    }
    return res.json();
  },

  async listAllParticipants(
    token: string,
    params?: { quiz_id?: string; status?: string; search?: string; page?: number; limit?: number }
  ): Promise<ParticipantListResponse> {
    const url = new URL(`${API_BASE_URL}/invitations/participants`);
    if (params?.quiz_id) url.searchParams.set('quiz_id', params.quiz_id);
    if (params?.status && params.status !== 'all') url.searchParams.set('status', params.status);
    if (params?.search) url.searchParams.set('search', params.search);
    if (params?.page) url.searchParams.set('page', String(params.page));
    if (params?.limit) url.searchParams.set('limit', String(params.limit));

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load participants');
    }
    return res.json();
  },

  async updateParticipantStatus(
    token: string,
    participantId: string,
    payload: { status: string; rejection_reason?: string; internal_notes?: string }
  ): Promise<ParticipantItem> {
    const res = await fetch(`${API_BASE_URL}/invitations/participants/${participantId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to update participant status');
    }
    return res.json();
  },

  async batchUpdateParticipantStatus(
    token: string,
    payload: { participant_ids: string[]; status: string; rejection_reason?: string }
  ): Promise<{ success: boolean; updated_count: number }> {
    const res = await fetch(`${API_BASE_URL}/invitations/participants/batch-status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to batch update participant status');
    }
    return res.json();
  },

  // -------------------------------------------------------------
  // Public Candidate Endpoints
  // -------------------------------------------------------------

  async validatePublicToken(token: string): Promise<PublicInvitationValidation> {
    const res = await fetch(`${API_BASE_URL}/public/invitations/${token}/validate`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return {
        is_valid: false,
        error_code: 'SERVER_ERROR',
        error_message: err.error?.message || err.detail || 'Failed to validate invitation link',
        require_approval: false,
      };
    }
    return res.json();
  },

  async registerCandidate(token: string, formData: Record<string, any>): Promise<PublicRegistrationReceipt> {
    const res = await fetch(`${API_BASE_URL}/public/invitations/${token}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_data: formData }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to submit registration');
    }
    return res.json();
  },
};
