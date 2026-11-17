import type { MiddlewareHandler } from 'hono';
import { logger } from '../utils/logger.js';

export const loggerMiddleware: MiddlewareHandler = async (c, next) => {
  const start = Date.now();
  const { method, path } = c.req;
  const requestId = c.get('requestId') as string;

  await next();

  const durationMs = Date.now() - start;
  const statusCode = c.res.status;

  logger.info(`HTTP ${method} ${path} ${statusCode}`, {
    requestId,
    method,
    path,
    statusCode,
    durationMs,
  });
};
