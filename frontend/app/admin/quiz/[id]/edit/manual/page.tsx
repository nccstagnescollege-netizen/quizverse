'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { ManualQuizWorkspace } from '@/components/manual-quiz/ManualQuizWorkspace';

export default function AdminManualQuizEditorPage() {
  const params = useParams();
  const quizId = params?.id as string;
  const { token, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !token) {
    router.push('/login');
    return null;
  }

  return (
    <ManualQuizWorkspace
      quizId={quizId}
      token={token}
      basePath="/admin/quiz"
      canViewAnswerKey={true}
    />
  );
}
