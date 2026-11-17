import type { ApiResponse } from '@quizverse/shared';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8787';

export class ApiError extends Error {
  code: string;
  details?: unknown[];
  status: number;

  constructor(message: string, code: string, status: number, details?: unknown[]) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL.replace(/\/$/, '')}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok || !data?.success) {
    const error = data?.error || {
      code: 'HTTP_ERROR',
      message: response.statusText || 'Network request failed',
    };
    throw new ApiError(error.message, error.code, response.status, error.details);
  }

  return data as ApiResponse<T>;
}
