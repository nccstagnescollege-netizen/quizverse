const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ProctoringPolicy {
  quiz_id: string;
  webcam_monitoring_enabled: boolean;
  microphone_monitoring_enabled: boolean;
  face_presence_detection: boolean;
  multiple_person_detection: boolean;
  head_position_detection: boolean;
  audio_anomaly_detection: boolean;
  browser_activity_integration: boolean;
  mobile_interruption_integration: boolean;
  seb_security_integration: boolean;
  proctoring_mandatory: boolean;
  webcam_permission_required: boolean;
  microphone_permission_required: boolean;
  monitoring_interval_seconds: number;
  risk_warning_threshold: number;
  risk_critical_threshold: number;
  human_review_required: boolean;
  recording_enabled: boolean;
  recording_retention_days: number;
  privacy_disclosure: string;
}

export interface ProctoringSessionData {
  id: string;
  attempt_id: string;
  quiz_id: string;
  student_id: string;
  student_name?: string;
  register_number?: string;
  status: string;
  camera_status: string;
  microphone_status: string;
  lighting_condition: string;
  is_accommodated_exempt: boolean;
  face_presence_state: string;
  head_position_state: string;
  multiple_faces_detected: boolean;
  audio_level_state: string;
  total_face_absent_count: number;
  total_multiple_face_count: number;
  total_head_movement_count: number;
  total_audio_anomaly_count: number;
  total_proctoring_events: number;
  ai_risk_score: number;
  ai_risk_level: string;
  ai_classification: string;
  ai_confidence: number;
  risk_factors?: Array<{ factor: string; impact: number; note: string; count?: number }>;
  review_status: string;
  reviewer_decision?: string;
  reviewer_notes?: string;
  reviewed_at?: string;
  recording_consent_given: boolean;
  started_at: string;
  last_heartbeat_at: string;
}

export interface ProctoringSignal {
  event_type: string;
  severity?: string;
  confidence_score?: number;
  duration_seconds?: number;
  details?: Record<string, any>;
  occurred_at?: string;
}

export interface ProctoringDashboardCandidate {
  session_id: string;
  attempt_id: string;
  student_id: string;
  student_name: string;
  register_number?: string;
  email: string;
  attempt_status: string;
  camera_status: string;
  microphone_status: string;
  lighting_condition: string;
  face_presence_state: string;
  head_position_state: string;
  multiple_faces_detected: boolean;
  audio_level_state: string;
  ai_risk_score: number;
  ai_risk_level: string;
  ai_classification: string;
  review_status: string;
  reviewer_decision?: string;
  total_events: number;
  last_heartbeat_at: string;
  is_accommodated: boolean;
}

export interface ProctoringDashboardOverview {
  quiz_id: string;
  total_proctored_candidates: number;
  active_now: number;
  nominal_count: number;
  requires_attention_count: number;
  critical_review_count: number;
  unresolved_alerts_count: number;
  candidates: ProctoringDashboardCandidate[];
}

export interface ProctoringAlert {
  id: string;
  session_id: string;
  quiz_id: string;
  student_id: string;
  student_name: string;
  alert_type: string;
  severity: string;
  message: string;
  details?: Record<string, any>;
  occurred_at: string;
  acknowledged: boolean;
}

export interface FrameAnalysisResult {
  faceDetected: boolean;
  faceCount: number;
  lightingQuality: 'good' | 'fair' | 'poor';
  headPosition: 'facing_screen' | 'turned_away' | 'looking_down' | 'looking_up';
  confidence: number;
}

export interface AudioAnalysisResult {
  rmsLevel: number;
  isElevated: boolean;
  speechDetected: boolean;
}

class AIProctoringService {
  private getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  // 1. Policy & Config
  async getProctoringPolicy(quizId: string): Promise<ProctoringPolicy> {
    const res = await fetch(`${API_BASE_URL}/proctoring/quizzes/${quizId}/config`, {
      method: 'GET',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch proctoring policy');
    }
    return res.json();
  }

  async updateProctoringPolicy(token: string, quizId: string, policy: Partial<ProctoringPolicy>): Promise<ProctoringPolicy> {
    const res = await fetch(`${API_BASE_URL}/proctoring/quizzes/${quizId}/config`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify(policy),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update proctoring policy');
    }
    return res.json();
  }

  // 2. Candidate Session Lifecycle
  async initializeSession(
    attemptId: string,
    capabilities: {
      camera_status: string;
      microphone_status: string;
      camera_label?: string;
      microphone_label?: string;
      lighting_condition?: string;
      is_accommodated_exempt?: boolean;
      recording_consent_given?: boolean;
      client_metadata?: Record<string, any>;
    },
  ): Promise<ProctoringSessionData> {
    const res = await fetch(`${API_BASE_URL}/proctoring/attempts/${attemptId}/session`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(capabilities),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to initialize proctoring session');
    }
    return res.json();
  }

  async submitSignals(
    sessionId: string,
    payload: {
      face_presence_state?: string;
      head_position_state?: string;
      multiple_faces_detected?: boolean;
      audio_level_state?: string;
      lighting_condition?: string;
      signals: ProctoringSignal[];
    },
  ): Promise<ProctoringSessionData> {
    const res = await fetch(`${API_BASE_URL}/proctoring/sessions/${sessionId}/signals`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to dispatch proctoring telemetry');
    }
    return res.json();
  }

  // 3. Invigilator Dashboard & Reviews
  async getDashboard(token: string, quizId: string): Promise<ProctoringDashboardOverview> {
    const res = await fetch(`${API_BASE_URL}/proctoring/quizzes/${quizId}/dashboard`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch proctoring dashboard');
    }
    return res.json();
  }

  async getSessionDetails(token: string, sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/proctoring/sessions/${sessionId}/details`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch session telemetry details');
    }
    return res.json();
  }

  async submitReview(
    token: string,
    sessionId: string,
    review: { decision: string; justification: string; action_taken?: string },
  ): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/proctoring/sessions/${sessionId}/review`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(review),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to record proctor review');
    }
    return res.json();
  }

  async getAlerts(token: string, quizId: string): Promise<ProctoringAlert[]> {
    const res = await fetch(`${API_BASE_URL}/proctoring/quizzes/${quizId}/alerts`, {
      method: 'GET',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch proctoring alerts');
    }
    return res.json();
  }

  async acknowledgeAlert(token: string, alertId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/proctoring/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to acknowledge alert');
    }
    return res.json();
  }

  // -------------------------------------------------------------------------
  // 4. On-Device Lightweight Vision & Audio Processing Helpers
  // -------------------------------------------------------------------------
  async checkMediaPermissions(): Promise<{
    hasCamera: boolean;
    hasMic: boolean;
    cameraGranted: boolean;
    micGranted: boolean;
    cameraLabel?: string;
    micLabel?: string;
  }> {
    if (typeof window === 'undefined' || !navigator?.mediaDevices) {
      return { hasCamera: false, hasMic: false, cameraGranted: false, micGranted: false };
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const hasCamera = devices.some((d) => d.kind === 'videoinput');
      const hasMic = devices.some((d) => d.kind === 'audioinput');

      let cameraGranted = false;
      let micGranted = false;
      let cameraLabel: string | undefined;
      let micLabel: string | undefined;

      // Check permissions API if available
      if (navigator.permissions && navigator.permissions.query) {
        try {
          const camQuery = await navigator.permissions.query({ name: 'camera' as any });
          cameraGranted = camQuery.state === 'granted';
        } catch (_) {}
        try {
          const micQuery = await navigator.permissions.query({ name: 'microphone' as any });
          micGranted = micQuery.state === 'granted';
        } catch (_) {}
      }

      const activeCam = devices.find((d) => d.kind === 'videoinput' && d.label);
      if (activeCam) {
        cameraGranted = true;
        cameraLabel = activeCam.label;
      }
      const activeMic = devices.find((d) => d.kind === 'audioinput' && d.label);
      if (activeMic) {
        micGranted = true;
        micLabel = activeMic.label;
      }

      return { hasCamera, hasMic, cameraGranted, micGranted, cameraLabel, micLabel };
    } catch (e) {
      return { hasCamera: false, hasMic: false, cameraGranted: false, micGranted: false };
    }
  }

  /**
   * On-device canvas analysis. Evaluates ambient lighting, detects skin-color gradient
   * centroids to count face clusters, and determines center-of-gravity offset for head orientation.
   * Completely local, private, zero external network API calls.
   */
  analyzeVideoFrame(video: HTMLVideoElement, canvas: HTMLCanvasElement): FrameAnalysisResult {
    const width = 160;
    const height = 120;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) {
      return { faceDetected: false, faceCount: 0, lightingQuality: 'good', headPosition: 'facing_screen', confidence: 0.8 };
    }

    ctx.drawImage(video, 0, 0, width, height);
    const imgData = ctx.getImageData(0, 0, width, height);
    const data = imgData.data;

    let totalLuminance = 0;
    let skinPixels = 0;
    let skinSumX = 0;
    let skinSumY = 0;

    // Disjoint quadrant pixel bins to detect secondary person
    let leftHalfSkin = 0;
    let rightHalfSkin = 0;

    const totalPixels = width * height;

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];

      // Luminance (standard Rec. 709)
      const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      totalLuminance += lum;

      // Normalized skin-tone detection in RGB space
      // Rule: r > 95, g > 40, b > 20, max - min > 15, |r - g| > 15, r > g, r > b
      const maxC = Math.max(r, g, b);
      const minC = Math.min(r, g, b);
      if (r > 80 && g > 35 && b > 20 && maxC - minC > 12 && r > g && r > b) {
        skinPixels++;
        const pixelIdx = i / 4;
        const x = pixelIdx % width;
        const y = Math.floor(pixelIdx / width);
        skinSumX += x;
        skinSumY += y;

        if (x < width * 0.4) leftHalfSkin++;
        if (x > width * 0.6) rightHalfSkin++;
      }
    }

    const avgLuminance = totalLuminance / totalPixels;
    let lightingQuality: 'good' | 'fair' | 'poor' = 'good';
    if (avgLuminance < 35 || avgLuminance > 225) {
      lightingQuality = 'poor';
    } else if (avgLuminance < 60 || avgLuminance > 200) {
      lightingQuality = 'fair';
    }

    // Min skin ratio for face detection (~3% of 160x120 frame)
    const skinRatio = skinPixels / totalPixels;
    const faceDetected = skinRatio >= 0.035;

    // Secondary face cluster detection: both left and right extremes contain substantial separated clusters
    let faceCount = faceDetected ? 1 : 0;
    if (faceDetected && leftHalfSkin > totalPixels * 0.025 && rightHalfSkin > totalPixels * 0.025) {
      faceCount = 2;
    }

    // Centroid calculation for head orientation approximation
    let headPosition: 'facing_screen' | 'turned_away' | 'looking_down' | 'looking_up' = 'facing_screen';
    if (faceDetected && skinPixels > 0) {
      const centroidX = skinSumX / skinPixels;
      const centroidY = skinSumY / skinPixels;

      const normX = centroidX / width; // 0.0 (left) to 1.0 (right)
      const normY = centroidY / height; // 0.0 (top) to 1.0 (bottom)

      if (normX < 0.32 || normX > 0.68) {
        headPosition = 'turned_away';
      } else if (normY > 0.72) {
        headPosition = 'looking_down';
      } else if (normY < 0.25) {
        headPosition = 'looking_up';
      }
    }

    return {
      faceDetected,
      faceCount,
      lightingQuality,
      headPosition,
      confidence: faceDetected ? 0.88 : 0.92,
    };
  }

  /**
   * On-device audio frequency analysis via Web Audio API.
   * Calculates RMS volume and speech-band energy.
   */
  analyzeAudioLevel(analyser: AnalyserNode): AudioAnalysisResult {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    let sum = 0;
    let speechBandSum = 0;
    // Speech frequencies roughly correspond to bins 300Hz - 3400Hz
    const minBin = Math.floor(bufferLength * 0.06);
    const maxBin = Math.floor(bufferLength * 0.45);

    for (let i = 0; i < bufferLength; i++) {
      const val = dataArray[i];
      sum += val * val;
      if (i >= minBin && i <= maxBin) {
        speechBandSum += val;
      }
    }

    const rms = Math.sqrt(sum / bufferLength);
    const speechAvg = speechBandSum / (maxBin - minBin + 1);

    const isElevated = rms > 42; // Above quiet ambient noise
    const speechDetected = speechAvg > 35 && isElevated;

    return {
      rmsLevel: Math.round(rms),
      isElevated,
      speechDetected,
    };
  }
}

export const aiProctoringService = new AIProctoringService();
