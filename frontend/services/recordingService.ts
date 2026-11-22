const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://quizverse-ymsg.onrender.com/api/v1';

export interface QuizRecordingSettingsResponse {
  quiz_id: string;
  recording_storage_enabled: boolean;
  webcam_recording_enabled: boolean;
  microphone_recording_enabled: boolean;
  recording_quality: 'standard' | 'high' | 'bandwidth_optimized';
  recording_retention_days: number;
  allow_invigilator_recording_access: boolean;
  allow_admin_recording_download: boolean;
  estimated_storage_mb_per_hour: number;
}

export interface QuizRecordingSettingsUpdateRequest {
  recording_storage_enabled?: boolean;
  webcam_recording_enabled?: boolean;
  microphone_recording_enabled?: boolean;
  recording_quality?: 'standard' | 'high' | 'bandwidth_optimized';
  recording_retention_days?: number;
  allow_invigilator_recording_access?: boolean;
  allow_admin_recording_download?: boolean;
}

export interface StorageEstimateRequest {
  duration_minutes: number;
  student_count: number;
  recording_quality?: 'standard' | 'high' | 'bandwidth_optimized';
}

export interface StorageEstimateResponse {
  student_count: number;
  duration_minutes: number;
  recording_quality: string;
  estimated_mb_total: number;
  estimated_gb_total: number;
  storage_warning?: string | null;
}

export interface StartRecordingRequest {
  session_id?: string;
  webcam_recorded?: boolean;
  microphone_recorded?: boolean;
  recording_quality?: string;
}

export interface StopRecordingRequest {
  reason?: string;
}

export interface ExamRecordingItem {
  id: string;
  institution_id?: string | null;
  quiz_id: string;
  quiz_title?: string | null;
  student_id: string;
  student_name?: string | null;
  student_email?: string | null;
  attempt_id: string;
  session_id?: string | null;
  bucket_name: string;
  storage_object_path?: string | null;
  file_name?: string | null;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds: number;
  recording_status: 'NOT_STARTED' | 'RECORDING' | 'UPLOADING' | 'COMPLETED' | 'FAILED' | 'DELETED' | 'EXPIRED';
  webcam_recorded: boolean;
  microphone_recorded: boolean;
  recording_quality: string;
  started_at?: string | null;
  completed_at?: string | null;
  uploaded_at?: string | null;
  checksum?: string | null;
  retention_expires_at?: string | null;
  created_at: string;
}

export interface ExamRecordingListResponse {
  total: number;
  items: ExamRecordingItem[];
}

export interface SignedPlaybackUrlResponse {
  recording_id: string;
  playback_url: string;
  expires_in_seconds: number;
  file_name: string;
  mime_type: string;
  duration_seconds: number;
  student_name?: string | null;
  quiz_title?: string | null;
}

export interface SignedDownloadUrlResponse {
  recording_id: string;
  download_url: string;
  expires_in_seconds: number;
  file_name: string;
  file_size_bytes: number;
}

export interface SuperAdminStorageStatsResponse {
  total_recordings: number;
  total_storage_bytes: number;
  total_storage_mb: number;
  total_storage_gb: number;
  completed_count: number;
  recording_count: number;
  failed_count: number;
  expired_count: number;
  storage_by_quiz: Array<{
    quiz_id: string;
    title: string;
    recordings_count: number;
    bytes: number;
    mb: number;
  }>;
  storage_by_institution: Array<{
    institution_id: string;
    recordings_count: number;
    bytes: number;
    mb: number;
  }>;
}

export interface RecordingCleanupResponse {
  deleted_count: number;
  freed_bytes: number;
  freed_mb: number;
  recordings_cleared: string[];
}

class RecordingService {
  private getHeaders(token: string): HeadersInit {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  // 1. Get Quiz Recording Settings
  async getQuizRecordingSettings(quizId: string, token: string): Promise<QuizRecordingSettingsResponse> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/recording-settings`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch recording settings');
    }
    return res.json();
  }

  // 2. Update Quiz Recording Settings
  async updateQuizRecordingSettings(
    quizId: string,
    payload: QuizRecordingSettingsUpdateRequest,
    token: string
  ): Promise<QuizRecordingSettingsResponse> {
    const res = await fetch(`${API_BASE_URL}/quizzes/${quizId}/recording-settings`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update recording settings');
    }
    return res.json();
  }

  // 3. Estimate Storage Usage
  async estimateStorage(payload: StorageEstimateRequest, token: string): Promise<StorageEstimateResponse> {
    const res = await fetch(`${API_BASE_URL}/recordings/estimate-storage`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to calculate storage estimate');
    }
    return res.json();
  }

  // 4. Candidate: Start Recording
  async startRecording(
    attemptToken: string,
    payload: StartRecordingRequest = {}
  ): Promise<ExamRecordingItem> {
    const res = await fetch(`${API_BASE_URL}/recordings/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Exam-Token': attemptToken,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to start recording');
    }
    return res.json();
  }

  // 5. Candidate: Stop Recording
  async stopRecording(
    attemptToken: string,
    payload: StopRecordingRequest = {}
  ): Promise<ExamRecordingItem> {
    const res = await fetch(`${API_BASE_URL}/recordings/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Exam-Token': attemptToken,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to stop recording');
    }
    return res.json();
  }

  // 6. Candidate: Upload Recording Chunk/File
  async uploadRecording(
    attemptToken: string,
    recordingId: string,
    fileBlob: Blob,
    durationSeconds: number,
    segmentIndex: number = 0,
    isFinal: boolean = true
  ): Promise<ExamRecordingItem> {
    const formData = new FormData();
    formData.append('file', fileBlob, `recording_${recordingId}.webm`);
    formData.append('duration_seconds', durationSeconds.toString());
    formData.append('segment_index', segmentIndex.toString());
    formData.append('is_final', isFinal.toString());

    const res = await fetch(`${API_BASE_URL}/recordings/${recordingId}/upload`, {
      method: 'POST',
      headers: {
        'X-Exam-Token': attemptToken,
      },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload examination recording');
    }
    return res.json();
  }

  // 7. List Recordings for a Quiz (Admin / Invigilator)
  async listQuizRecordings(
    quizId: string,
    token: string,
    params?: { status?: string; student_id?: string; limit?: number; offset?: number }
  ): Promise<ExamRecordingListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.student_id) query.set('student_id', params.student_id);
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());

    const url = `${API_BASE_URL}/quizzes/${quizId}/recordings${query.toString() ? `?${query.toString()}` : ''}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to list quiz recordings');
    }
    return res.json();
  }

  // 8. Get Playback Signed URL
  async getPlaybackUrl(recordingId: string, token: string): Promise<SignedPlaybackUrlResponse> {
    const res = await fetch(`${API_BASE_URL}/recordings/${recordingId}/playback-url`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to obtain playback URL');
    }
    return res.json();
  }

  // 9. Get Download Signed URL
  async getDownloadUrl(recordingId: string, token: string): Promise<SignedDownloadUrlResponse> {
    const res = await fetch(`${API_BASE_URL}/recordings/${recordingId}/download-url`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to obtain download URL');
    }
    return res.json();
  }

  // 10. Delete Recording
  async deleteRecording(recordingId: string, token: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/recordings/${recordingId}`, {
      method: 'DELETE',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to delete recording');
    }
    return res.json();
  }

  // 11. Super Admin: Platform Storage Stats
  async getSuperAdminStorageStats(token: string): Promise<SuperAdminStorageStatsResponse> {
    const res = await fetch(`${API_BASE_URL}/super-admin/recordings/storage-stats`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch platform storage stats');
    }
    return res.json();
  }

  // 12. Super Admin: Trigger Retention Cleanup
  async triggerRetentionCleanup(token: string): Promise<RecordingCleanupResponse> {
    const res = await fetch(`${API_BASE_URL}/super-admin/recordings/cleanup`, {
      method: 'POST',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to trigger retention cleanup');
    }
    return res.json();
  }
}

export const recordingService = new RecordingService();
