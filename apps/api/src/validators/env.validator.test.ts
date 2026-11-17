import { describe, it, expect } from 'vitest';
import { getValidatedEnv } from '../config/env';

describe('Environment Validator', () => {
  it('should accept valid development environment with defaults', () => {
    const config = getValidatedEnv({
      PORT: '8787',
      ENVIRONMENT: 'development',
    });
    expect(config.PORT).toBe(8787);
    expect(config.ENVIRONMENT).toBe('development');
    expect(config.FRONTEND_ORIGIN).toBe('http://localhost:5173');
  });

  it('should reject invalid PORT type', () => {
    expect(() => {
      getValidatedEnv({
        PORT: 'not-a-port-number',
      });
    }).toThrow('[QUIZVERSE] Invalid environment configuration');
  });

  it('should reject invalid ENVIRONMENT enum', () => {
    expect(() => {
      getValidatedEnv({
        ENVIRONMENT: 'invalid-environment-value',
      });
    }).toThrow('[QUIZVERSE] Invalid environment configuration');
  });
});
