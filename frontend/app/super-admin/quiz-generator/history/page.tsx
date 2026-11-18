'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  History,
  Sparkles,
  Plus,
  RefreshCw,
  Clock,
  BookOpen,
  FileCheck2,
  ArrowRight,
  ExternalLink,
  HelpCircle,
} from 'lucide-react';
import {
  GenerationHistorySummary,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';

export default function SuperAdminGenerationHistoryPage() {
  const [history, setHistory] = useState<GenerationHistorySummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await quizGeneratorService.listHistory();
      setHistory(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Failed to load generation history', err);
      setError(err.message || 'Failed to load generation history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const columns: TableColumn<GenerationHistorySummary>[] = [
    {
      key: 'title',
      header: 'Exam Paper / Session',
      render: (row) => (
        <div className="space-y-0.5">
          <Link
            href={`/super-admin/quiz-generator/${row.id}`}
            className="text-xs font-semibold text-white hover:text-primary-400 transition-colors"
          >
            {row.session_title || 'Untitled Session'}
          </Link>
          <div className="text-[10px] text-slate-500 font-mono">
            ID: {row.id.substring(0, 8)}...
          </div>
        </div>
      ),
    },
    {
      key: 'subject',
      header: 'Subject',
      render: (row) => (
        <span className="text-xs text-slate-300 font-medium">
          {row.subject_name || 'General / Multi-Subject'}
        </span>
      ),
    },
    {
      key: 'questions',
      header: 'Questions',
      render: (row) => (
        <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-800 text-slate-200 border border-slate-700">
          {row.questions_selected_count} Questions
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
            row.status === 'saved_as_quiz'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
          }`}
        >
          {row.status.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Generated At',
      render: (row) => (
        <div className="text-xs text-slate-400">
          {row.created_at ? new Date(row.created_at).toLocaleString() : 'N/A'}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <Link
            href={`/super-admin/quiz-generator/${row.id}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-surface-border text-[11px] font-medium text-slate-300 hover:text-white transition-colors"
            title="Open generated paper editor"
          >
            <span>Review</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          {row.saved_quiz_id && (
            <Link
              href={`/super-admin/quizzes/${row.saved_quiz_id}`}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[11px] font-medium transition-colors"
              title="View authoritative Quiz draft"
            >
              <span>Quiz Draft</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-primary-600/20 text-primary-400 border border-primary-500/30">
              <History className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Paper Generation History
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Audit logs and generated examination papers across the platform.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchHistory}
            className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-400 hover:text-white transition-colors"
            title="Refresh History"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/super-admin/quiz-generator"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Generate New Quiz</span>
          </Link>
        </div>
      </div>

      {/* Main Content */}
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchHistory} />
      ) : history.length === 0 ? (
        <div className="text-center py-16 p-8 rounded-2xl bg-surface-elevated border border-surface-border space-y-3">
          <Sparkles className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">
            No Generation Sessions Yet
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Generate your first examination paper using our constraint-aware automatic generator.
          </p>
          <Link
            href="/super-admin/quiz-generator"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
          >
            <Plus className="w-4 h-4" />
            <span>Launch Generator</span>
          </Link>
        </div>
      ) : (
        <ResponsiveTable
          columns={columns}
          data={history}
          keyExtractor={(item) => item.id}
          emptyMessage="No generation history found."
        />
      )}
    </div>
  );
}
