'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { QuizConfigurationWizard } from '@/components/quiz-publishing/QuizConfigurationWizard';
import { Clock } from 'lucide-react';

export default function AdminQuizzesConfigureAliasPage() {
  const params = useParams();
  const quizId = (params?.id || params?.quizId) as string;
  const { token, isAuthenticated, isLoading } = useAuth();

  if (isLoading || !isAuthenticated || !token) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-primary-400" />
        <span>Authenticating admin console...</span>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
      <QuizConfigurationWizard quizId={quizId} basePath="/admin" token={token} />
    </div>
  );
}
