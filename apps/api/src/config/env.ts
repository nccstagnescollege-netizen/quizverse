import { z } from 'zod';

export const envSchema = z.object({
  PORT: z.coerce.number().default(8787),
  ENVIRONMENT: z.enum(['development', 'test', 'production']).default('development'),
  FRONTEND_ORIGIN: z.string().default('http://localhost:5173'),
  SUPABASE_URL: z.string().url().optional().or(z.literal('')),
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional().or(z.literal('')),
  SUPABASE_DB_URL: z.string().optional().or(z.literal('')),
});

export type EnvConfig = z.infer<typeof envSchema>;

export function getValidatedEnv(env: Record<string, unknown> = process.env): EnvConfig {
  const result = envSchema.safeParse(env);
  if (!result.success) {
    const issues = result.error.issues.map((i) => ` - ${i.path.join('.')}: ${i.message}`).join('\n');
    throw new Error(`[QUIZVERSE] Invalid environment configuration:\n${issues}`);
  }
  return result.data;
}
