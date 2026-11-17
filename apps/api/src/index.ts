import { serve } from '@hono/node-server';
import { app } from './app.js';
import { getValidatedEnv } from './config/env.js';
import { logger } from './utils/logger.js';

// Validate environment variables on startup
const env = getValidatedEnv(process.env);

const port = env.PORT;

logger.info(`Starting QUIZVERSE API server on port ${port}...`, {
  data: {
    port,
    environment: env.ENVIRONMENT,
    frontendOrigin: env.FRONTEND_ORIGIN,
  },
});

serve(
  {
    fetch: app.fetch,
    port,
  },
  (info) => {
    logger.info(`🚀 QUIZVERSE API listening on http://localhost:${info.port}`);
    logger.info(`👉 Health check: http://localhost:${info.port}/api/v1/health`);
    logger.info(`👉 System status: http://localhost:${info.port}/api/v1/status`);
  }
);
