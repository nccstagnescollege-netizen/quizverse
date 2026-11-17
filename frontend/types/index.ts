export type UserRole = 'super_admin' | 'admin' | 'instructor' | 'student';

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  avatarUrl?: string;
  createdAt: string;
}

export type QuizStatus = 'draft' | 'published' | 'archived';

export interface QuizItem {
  id: string;
  title: string;
  slug: string;
  durationMinutes: number;
  totalQuestions: number;
  passingScore: number;
  status: QuizStatus;
  is3dEnabled: boolean;
}

export interface BackendHealthResponse {
  success: boolean;
  data: {
    status: 'healthy' | 'degraded';
    service: string;
    version: string;
    environment: string;
    uptime_seconds: number;
    database_status: 'connected' | 'unconfigured' | 'disconnected';
    features: {
      auth: boolean;
      storage: boolean;
      realtime: boolean;
      database_configured: boolean;
    };
  };
  meta: {
    request_id?: string;
    timestamp: string;
    version: string;
  };
}
