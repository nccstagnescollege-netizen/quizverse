import { Hono } from 'hono';
import { jsonSuccess } from '../utils/response.js';
import { getSupabaseStatus } from '../services/supabase.service.js';
import type { SystemStatusData } from '@quizverse/shared';

const statusRouter = new Hono();

statusRouter.get('/', (c) => {
  const environment = process.env.ENVIRONMENT || 'development';
  const supabaseInfo = getSupabaseStatus();

  const statusData: SystemStatusData = {
    service: 'quizverse-backend',
    version: '1.0.0',
    environment,
    database: supabaseInfo.status,
    timestamp: new Date().toISOString(),
    features: {
      realtime: supabaseInfo.configured,
      storage: supabaseInfo.configured,
      auth: supabaseInfo.configured,
    },
  };

  return jsonSuccess(c, statusData);
});

export { statusRouter };
