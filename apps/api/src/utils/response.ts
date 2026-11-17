import type { Context } from 'hono';
import type { ApiResponse, ApiErrorResponse, ApiErrorDetail } from '@quizverse/shared';

const API_VERSION = 'v1';

export function jsonSuccess<T>(c: Context, data: T, status: 200 | 201 = 200) {
  const requestId = (c.get('requestId') as string) || crypto.randomUUID();
  const response: ApiResponse<T> = {
    success: true,
    data,
    meta: {
      requestId,
      timestamp: new Date().toISOString(),
      version: API_VERSION,
    },
  };
  return c.json(response, status);
}

export function jsonError(
  c: Context,
  code: string,
  message: string,
  status: 400 | 401 | 403 | 404 | 409 | 422 | 500 = 400,
  details?: ApiErrorDetail[]
) {
  const requestId = (c.get('requestId') as string) || crypto.randomUUID();
  const response: ApiErrorResponse = {
    success: false,
    error: {
      code,
      message,
      ...(details ? { details } : {}),
    },
    meta: {
      requestId,
      timestamp: new Date().toISOString(),
      version: API_VERSION,
    },
  };
  return c.json(response, status);
}
