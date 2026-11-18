'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  GenerationSession,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import { GeneratedPaperEditor } from '@/components/quiz-generator/GeneratedPaperEditor';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function AdminGeneratedPaperPage() {
  const params = useParams();
  const router = useRouter();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;

  const [session, setSession] = useState<GenerationSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSession = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await quizGeneratorService.getSession(id);
      setSession(data);
    } catch (err: any) {
      console.error('Failed to load generation session', err);
      setError(err.message || 'Failed to load generated paper session.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSession();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 py-6">
        <LoadingSkeleton />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 py-6">
        <ErrorState
          message={error || 'Generation session not found or you are not authorized to view it.'}
          onRetry={fetchSession}
        />
        <div className="text-center">
          <Link
            href="/admin/quiz-generator"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-slate-200 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Quiz Generator</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <GeneratedPaperEditor
      session={session}
      onSessionUpdated={(updated) => setSession(updated)}
      basePath="/admin"
    />
  );
}
