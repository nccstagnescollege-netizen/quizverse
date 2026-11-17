import { Hono } from 'hono';
import { jsonSuccess } from '../utils/response.js';
import type { HealthCheckData } from '@quizverse/shared';

const healthRouter = new Hono();
const startTime = Date.now();

healthRouter.get('/', (c) => {
  const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
  const environment = process.env.ENVIRONMENT || 'development';

  const healthData: HealthCheckData = {
    status: 'healthy',
    uptimeSeconds,
    service: 'quizverse-api',
    version: '1.0.0',
    environment,
  };

  return jsonSuccess(c, healthData);
});

export { healthRouter };
