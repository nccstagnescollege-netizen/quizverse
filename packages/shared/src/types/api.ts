/**
 * Standard API Response Structures for QUIZVERSE
 */

export interface ApiResponseMeta {
  requestId: string;
  timestamp: string;
  version: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  meta: ApiResponseMeta;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  path?: (string | number)[];
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
  };
  meta: ApiResponseMeta;
}

export interface HealthCheckData {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptimeSeconds: number;
  service: string;
  version: string;
  environment: string;
}

export interface SystemStatusData {
  service: string;
  version: string;
  environment: string;
  database: 'connected' | 'disconnected' | 'unconfigured';
  timestamp: string;
  features: {
    realtime: boolean;
    storage: boolean;
    auth: boolean;
  };
}
