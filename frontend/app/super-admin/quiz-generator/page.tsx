'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { QuizGeneratorWizard } from '@/components/quiz-generator/QuizGeneratorWizard';
import { Clock } from 'lucide-react';

export default function SuperAdminQuizGeneratorPage() {
  const { token, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !token)) {
      router.push('/login?redirect=/super-admin/quiz-generator');
    }
  }, [isLoading, isAuthenticated, token, router]);

  if (isLoading || !isAuthenticated || !token) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-primary-400" />
        <span>Authenticating admin console...</span>
      </div>
    );
  }

  return <QuizGeneratorWizard basePath="/super-admin" token={token} />;
}
