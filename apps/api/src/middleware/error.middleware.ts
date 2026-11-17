import type { ErrorHandler, NotFoundHandler } from 'hono';
import { HTTPException } from 'hono/http-exception';
import { ZodError } from 'zod';
import { logger } from '../utils/logger.js';
import { jsonError } from '../utils/response.js';

export const centralizedErrorHandler: ErrorHandler = (err, c) => {
  const requestId = (c.get('requestId') as string) || crypto.randomUUID();

  // Handle Zod Validation Errors
  if (err instanceof ZodError) {
    const details = err.issues.map((i) => ({
      code: 'VALIDATION_ERROR',
      message: i.message,
      path: i.path,
    }));

    logger.warn('Request validation failure', {
      requestId,
      data: { issues: details },
    });

    return jsonError(c, 'VALIDATION_FAILED', 'Input validation failed', 422, details);
  }

  // Handle Hono HTTP Exceptions
  if (err instanceof HTTPException) {
    logger.warn(`HTTP Exception: ${err.message}`, {
      requestId,
      statusCode: err.status,
    });
    const status = (err.status >= 400 && err.status <= 599 ? err.status : 500) as
      | 400
      | 401
      | 403
      | 404
      | 409
      | 422
      | 500;
    return jsonError(c, 'HTTP_ERROR', err.message, status);
  }

  // Handle Generic Internal Server Errors
  logger.error('Unhandled internal server error', {
    requestId,
    error: {
      name: err.name,
      message: err.message,
    },
  });

  // Never leak internal stack traces or database info to clients
  return jsonError(
    c,
    'INTERNAL_SERVER_ERROR',
    'An unexpected error occurred. Please contact system support.',
    500
  );
};

export const notFoundHandler: NotFoundHandler = (c) => {
  return jsonError(
    c,
    'RESOURCE_NOT_FOUND',
    `Endpoint ${c.req.method} ${c.req.path} not found`,
    404
  );
};
