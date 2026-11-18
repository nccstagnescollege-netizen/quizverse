'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  FileText,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { manualQuizService } from '@/services/manualQuizService';

export default function SuperAdminCreateManualQuizPage() {
  const { token, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('examination');
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    if (!title.trim()) {
      setErrorMsg('Please provide a quiz title.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await manualQuizService.createManualQuiz(
        {
          title: title.trim(),
          category,
          duration_minutes: durationMinutes,
        },
        token
      );
      router.push(`/super-admin/quiz/${res.quiz_id}/edit/manual`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to initialize manual quiz draft.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Link href="/super-admin/dashboard" className="hover:text-white transition-colors">
          Super Admin
        </Link>
        <span>/</span>
        <span className="text-slate-200">Manual Quiz Creator</span>
      </div>

      {/* Hero Header */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-950/40 via-surface-elevated to-surface-elevated border border-surface-border space-y-2">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-500/30">
            <ShieldCheck className="w-4 h-4" />
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
            Super Administrator Authority
          </span>
        </div>
        <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
          Create Manual Examination
        </h1>
        <p className="text-xs text-slate-300 leading-relaxed max-w-xl">
          Full platform-wide scope: assemble manual questions and Question Bank items across any
          institution, programme, or subject.
        </p>
      </div>

      {/* Quick Launch Form */}
      <form onSubmit={handleCreate} className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-5">
        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs">
            {errorMsg}
          </div>
        )}

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-200">
            Quiz / Examination Title <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Platform-Wide Standardized Assessment"
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            autoFocus
            required
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-200">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
            >
              <option value="examination">Formal Examination</option>
              <option value="midterm">Midterm Assessment</option>
              <option value="quiz">Weekly Quiz / Test</option>
              <option value="practice">Practice Assessment</option>
              <option value="placement">Placement Assessment</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-200">Duration (Minutes)</label>
            <input
              type="number"
              min="5"
              max="600"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
            />
          </div>
        </div>

        <div className="pt-3 border-t border-surface-border flex items-center justify-between">
          <Link
            href="/super-admin/dashboard"
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting || !title.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md transition-colors disabled:opacity-50"
          >
            <span>{isSubmitting ? 'Initializing Draft...' : 'Open Authoring Workspace'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
