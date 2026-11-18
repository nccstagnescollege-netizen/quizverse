'use client';

import React from 'react';
import { QuizGeneratorWizard } from '@/components/quiz-generator/QuizGeneratorWizard';

export default function AdminQuizGeneratorPage() {
  return <QuizGeneratorWizard basePath="/admin" />;
}
