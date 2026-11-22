'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { QuizDetailsOverview } from '@/components/quiz-publishing/QuizDetailsOverview';
import { Clock } from 'lucide-react';

export default function SuperAdminQuizDetailsPage() {
  const params = useParams();
  const quizId = (params?.id || params?.quizId) as string;
  const { token, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-2 text-slate-400 text-sm">
        <Clock className="w-6 h-6 animate-spin text-primary-400" />
        <span>Authenticating super admin console...</span>
      </div>
    );
  }

  if (!isAuthenticated || !token) {
    router.push(`/login?redirect=/super-admin/quiz/${quizId}`);
    return null;
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <QuizDetailsOverview quizId={quizId} basePath="/super-admin" token={token} />
    </div>
  );
}
