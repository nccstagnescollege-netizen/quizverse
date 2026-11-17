import { cors } from 'hono/cors';

export function createCorsMiddleware(frontendOrigin?: string) {
  const allowedOrigins = frontendOrigin
    ? [frontendOrigin, 'http://localhost:5173', 'http://127.0.0.1:5173']
    : ['http://localhost:5173', 'http://127.0.0.1:5173'];

  return cors({
    origin: (origin) => {
      // In development or if no origin provided (e.g., server-to-server or curl)
      if (!origin) return allowedOrigins[0];
      if (allowedOrigins.includes(origin)) return origin;
      // Allow Cloudflare Pages preview URLs for quizverse
      if (/^https:\/\/[a-z0-9-]+\.quizverse\.pages\.dev$/.test(origin)) {
        return origin;
      }
      return null;
    },
    allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
    allowHeaders: ['Content-Type', 'Authorization', 'x-request-id'],
    exposeHeaders: ['x-request-id', 'Content-Length'],
    maxAge: 86400,
    credentials: true,
  });
}
