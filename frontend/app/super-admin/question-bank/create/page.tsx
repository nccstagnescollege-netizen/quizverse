'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { QuestionEditor } from '@/components/question-bank/QuestionEditor';

export default function SuperAdminCreateQuestionPage() {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  if (authLoading) {
    return <LoadingSkeleton />;
  }

  if (!isAuthenticated || !token) {
    router.push('/login');
    return null;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full pb-16">
      <div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30">
          Super Admin Authoring
        </span>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Create New Question
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Author a new academic examination item with full hierarchy mapping, LaTeX math, code syntax, and answer verification.
        </p>
      </div>

      <QuestionEditor
        isEditMode={false}
        baseRedirectPath="/super-admin/question-bank"
        token={token}
      />
    </div>
  );
}
