import type { MiddlewareHandler } from 'hono';

export const requestIdMiddleware: MiddlewareHandler = async (c, next) => {
  const incomingId = c.req.header('x-request-id');
  const requestId = incomingId && /^[a-zA-Z0-9-_]{8,64}$/.test(incomingId)
    ? incomingId
    : crypto.randomUUID();

  c.set('requestId', requestId);
  c.header('x-request-id', requestId);
  await next();
};
