export type QuizStatus = 'draft' | 'published' | 'archived';

export type QuestionType =
  | 'multiple_choice'
  | 'multiple_select'
  | 'true_false'
  | 'short_answer'
  | 'code_snippet';

export interface QuestionOption {
  id: string;
  text: string;
  isCorrect?: boolean;
}

export interface Question {
  id: string;
  quizId?: string;
  title: string;
  description?: string;
  type: QuestionType;
  points: number;
  options: QuestionOption[];
  explanation?: string;
  orderIndex: number;
  createdAt: string;
  updatedAt: string;
}

export interface Quiz {
  id: string;
  title: string;
  slug: string;
  description?: string;
  durationMinutes: number;
  passingScore: number;
  status: QuizStatus;
  is3dEnabled: boolean;
  totalQuestions: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}
