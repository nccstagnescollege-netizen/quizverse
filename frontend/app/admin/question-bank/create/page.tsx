'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { QuestionEditor } from '@/components/question-bank/QuestionEditor';

export default function UserAdminCreateQuestionPage() {
  const { token, isAuthenticated, hasPermission, isLoading: authLoading } = useAuth();
  const router = useRouter();

  if (authLoading) {
    return <LoadingSkeleton />;
  }

  if (!isAuthenticated || !token) {
    router.push('/login');
    return null;
  }

  if (!hasPermission('question.create')) {
    return (
      <div className="p-8 text-center text-slate-400">
        <h2 className="text-lg font-bold text-white mb-2">Access Denied</h2>
        <p className="text-xs">You do not have the required `question.create` permission to author questions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full pb-16">
      <div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/30">
          User Admin Authoring
        </span>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Create Question
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Author an examination question scoped to your authorized academic curriculum assignments.
        </p>
      </div>

      <QuestionEditor
        isEditMode={false}
        baseRedirectPath="/admin/question-bank"
        token={token}
      />
    </div>
  );
}
