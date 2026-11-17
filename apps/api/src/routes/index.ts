import { Hono } from 'hono';
import { healthRouter } from './health.routes.js';
import { statusRouter } from './status.routes.js';

/**
 * API v1 Root Router
 * Modular route registration for current and future QUIZVERSE features.
 */
export function registerV1Routes(app: Hono) {
  const v1 = new Hono();

  // Core system routes
  v1.route('/health', healthRouter);
  v1.route('/status', statusRouter);

  // Modular placeholders for upcoming phases:
  // Phase 2 / Phase 3 modules:
  // v1.route('/auth', authRouter);
  // v1.route('/users', userRouter);
  // v1.route('/quizzes', quizRouter);
  // v1.route('/exams', examRouter);
  // v1.route('/questions', questionRouter);

  app.route('/api/v1', v1);
}
