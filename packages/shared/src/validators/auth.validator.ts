import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters long'),
});

export type LoginInput = z.infer<typeof loginSchema>;

export const examTokenSchema = z.object({
  token: z
    .string()
    .min(6, 'Exam access token must be at least 6 characters')
    .max(64, 'Exam access token is too long')
    .regex(/^[a-zA-Z0-9-_]+$/, 'Token contains invalid characters'),
});

export type ExamTokenInput = z.infer<typeof examTokenSchema>;
