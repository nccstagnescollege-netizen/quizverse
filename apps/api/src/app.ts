import { Hono } from 'hono';
import { requestIdMiddleware } from './middleware/requestId.middleware.js';
import { securityHeadersMiddleware } from './middleware/securityHeaders.middleware.js';
import { createCorsMiddleware } from './middleware/cors.middleware.js';
import { loggerMiddleware } from './middleware/logger.middleware.js';
import { centralizedErrorHandler, notFoundHandler } from './middleware/error.middleware.js';
import { registerV1Routes } from './routes/index.js';

export function createApp() {
  const app = new Hono();

  // Global Middleware Chain
  app.use('*', requestIdMiddleware);
  app.use('*', securityHeadersMiddleware);
  app.use('*', createCorsMiddleware(process.env.FRONTEND_ORIGIN));
  app.use('*', loggerMiddleware);

  // Modular Route Registration
  registerV1Routes(app);

  // Root Welcome Endpoint
  app.get('/', (c) => {
    return c.json({
      name: 'QUIZVERSE API',
      version: '1.0.0',
      description: 'Advanced 3D Interactive Online Quiz & Examination Platform API',
      docs: '/api/v1/health',
    });
  });

  // Centralized Error and 404 Handlers
  app.onError(centralizedErrorHandler);
  app.notFound(notFoundHandler);

  return app;
}

export const app = createApp();
