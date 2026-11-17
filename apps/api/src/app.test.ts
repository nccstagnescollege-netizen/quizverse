import { describe, it, expect } from 'vitest';
import { app } from './app.js';
import type { ApiResponse, HealthCheckData, SystemStatusData, ApiErrorResponse } from '@quizverse/shared';

describe('API Health and Status Endpoints', () => {
  it('GET /api/v1/health should return 200 with healthy status', async () => {
    const res = await app.request('/api/v1/health');
    expect(res.status).toBe(200);

    const json = (await res.json()) as ApiResponse<HealthCheckData>;
    expect(json.success).toBe(true);
    expect(json.data.status).toBe('healthy');
    expect(json.data.service).toBe('quizverse-api');
    expect(json.meta.version).toBe('v1');
    expect(json.meta.requestId).toBeDefined();

    // Verify no secret leak
    expect(JSON.stringify(json)).not.toContain('SUPABASE_SERVICE_ROLE_KEY');
    expect(JSON.stringify(json)).not.toContain('password');
  });

  it('GET /api/v1/status should return 200 with service status', async () => {
    const res = await app.request('/api/v1/status');
    expect(res.status).toBe(200);

    const json = (await res.json()) as ApiResponse<SystemStatusData>;
    expect(json.success).toBe(true);
    expect(json.data.service).toBe('quizverse-backend');
    expect(json.meta.requestId).toBeDefined();
  });

  it('GET /api/v1/non-existent-route should return 404 with structured error', async () => {
    const res = await app.request('/api/v1/non-existent-route');
    expect(res.status).toBe(404);

    const json = (await res.json()) as ApiErrorResponse;
    expect(json.success).toBe(false);
    expect(json.error.code).toBe('RESOURCE_NOT_FOUND');
    expect(json.meta.requestId).toBeDefined();
  });
});
