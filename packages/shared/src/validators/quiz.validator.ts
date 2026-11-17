import { z } from 'zod';

export const questionOptionSchema = z.object({
  id: z.string().uuid().optional(),
  text: z.string().min(1, 'Option text cannot be empty'),
  isCorrect: z.boolean().default(false),
});

export const createQuizSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters').max(150),
  description: z.string().max(1000).optional(),
  durationMinutes: z.number().int().min(1).max(300).default(30),
  passingScore: z.number().int().min(0).max(100).default(60),
  is3dEnabled: z.boolean().default(true),
});

export type CreateQuizInput = z.infer<typeof createQuizSchema>;
