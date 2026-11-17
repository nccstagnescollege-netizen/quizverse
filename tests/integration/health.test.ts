import { describe, it, expect } from 'vitest';
import { app } from '../../apps/api/src/app';

describe('Monorepo System Integration Tests', () => {
  it('should verify backend API responds to health check with requestId', async () => {
    const res = await app.request('/api/v1/health');
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data.status).toBe('healthy');
    expect(body.data.service).toBe('quizverse-api');
    expect(body.meta.requestId).toBeDefined();
    expect(body.meta.version).toBe('v1');
  });

  it('should verify status endpoint returns database status without credential leakage', async () => {
    const res = await app.request('/api/v1/status');
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data.service).toBe('quizverse-backend');
    expect(body.data.database).toBeDefined();

    // Verify secrets are NOT exposed
    const stringified = JSON.stringify(body);
    expect(stringified).not.toContain('SUPABASE_SERVICE_ROLE_KEY');
    expect(stringified).not.toContain('postgresql://');
  });
});
