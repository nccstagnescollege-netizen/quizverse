'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { QuestionEditor } from '@/components/question-bank/QuestionEditor';
import { QuestionDetail, questionBankService } from '@/services/questionBankService';

export default function UserAdminEditQuestionPage() {
  const { token, isAuthenticated, hasPermission, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const questionId = params?.id as string;

  const [question, setQuestion] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (!token || !questionId) return;

    async function loadQuestion() {
      setLoading(true);
      setError(null);
      try {
        const data = await questionBankService.getQuestion(questionId, token);
        setQuestion(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load question details.');
      } finally {
        setLoading(false);
      }
    }

    loadQuestion();
  }, [authLoading, isAuthenticated, token, questionId, router]);

  if (authLoading || loading) {
    return <LoadingSkeleton />;
  }

  if (!hasPermission('question.edit')) {
    return (
      <div className="p-8 text-center text-slate-400">
        <h2 className="text-lg font-bold text-white mb-2">Access Denied</h2>
        <p className="text-xs">You do not have the required `question.edit` permission to modify questions.</p>
      </div>
    );
  }

  if (error || !question) {
    return (
      <div className="max-w-5xl mx-auto w-full pt-8">
        <ErrorState
          message={error || 'Question not found'}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full pb-16">
      <div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/30">
          User Admin Revision
        </span>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Edit Question & Create Version Snapshot
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Modifying this question will automatically snapshot changes into immutable version history.
        </p>
      </div>

      <QuestionEditor
        initialQuestion={question}
        isEditMode={true}
        baseRedirectPath="/admin/question-bank"
        token={token || ''}
      />
    </div>
  );
}
