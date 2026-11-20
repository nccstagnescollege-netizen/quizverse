'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { QuizAnalyticsWorkspace } from '@/components/quiz-analytics/QuizAnalyticsWorkspace';

export default function AdminQuizAnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const quizId = (params?.id || params?.quizId) as string;
  const { token, isLoading } = useAuth();

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Authenticating administrator session...
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <QuizAnalyticsWorkspace
        quizId={quizId}
        token={token}
        userRole="admin"
        onBack={() => router.push('/admin/quiz/manage')}
      />
    </div>
  );
}
