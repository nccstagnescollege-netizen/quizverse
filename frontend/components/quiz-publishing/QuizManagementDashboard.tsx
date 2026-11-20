'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Settings,
  Send,
  Calendar,
  Archive,
  RotateCcw,
  History,
  AlertTriangle,
  Sparkles,
  Edit,
  ExternalLink,
  BookOpen,
  Eye,
  RefreshCw,
  Plus,
  Sliders,
} from 'lucide-react';
import {
  quizPublishingService,
  QuizManagementItem,
  QuizValidationReport,
  QuizPublishingHistoryItem,
} from '@/services/quizPublishingService';
import {
  ValidationReportModal,
  PublishModal,
  ScheduleModal,
  PublishingHistoryModal,
} from './PublishingModals';

interface QuizManagementDashboardProps {
  basePath: string; // '/admin' or '/super-admin'
  token: string;
}

export function QuizManagementDashboard({ basePath, token }: QuizManagementDashboardProps) {
  const [quizzes, setQuizzes] = useState<QuizManagementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedMode, setSelectedMode] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [activeQuiz, setActiveQuiz] = useState<QuizManagementItem | null>(null);
  const [validationReport, setValidationReport] = useState<QuizValidationReport | null>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [historyItems, setHistoryItems] = useState<QuizPublishingHistoryItem[]>([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchQuizzes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await quizPublishingService.getQuizzesForManagement(token, {
        status: selectedStatus,
        creation_mode: selectedMode,
        search: searchQuery || undefined,
      });
      const list = Array.isArray(data) ? data : (data as any)?.items || [];
      setQuizzes(list);
    } catch (err: any) {
      setError(err.message || 'Failed to load quizzes.');
    } finally {
      setLoading(false);
    }
  }, [token, selectedStatus, selectedMode, searchQuery]);

  useEffect(() => {
    fetchQuizzes();
  }, [fetchQuizzes]);

  // Handle Validate
  const handleValidate = async (quiz: QuizManagementItem) => {
    setActionLoadingId(quiz.id);
    try {
      const report = await quizPublishingService.validateQuiz(token, quiz.id);
      setActiveQuiz(quiz);
      setValidationReport(report);
      setShowValidationModal(true);
      fetchQuizzes();
    } catch (err: any) {
      alert(`Validation error: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle Publish Submit
  const handlePublishSubmit = async (changeLog: string, forceImmediate: boolean) => {
    if (!activeQuiz) return;
    await quizPublishingService.publishQuiz(token, activeQuiz.id, {
      change_log: changeLog || undefined,
      force_immediate: forceImmediate,
    });
    fetchQuizzes();
  };

  // Handle Schedule Submit
  const handleScheduleSubmit = async (payload: { start_time: string; end_time: string; timezone: string; change_log?: string }) => {
    if (!activeQuiz) return;
    await quizPublishingService.scheduleQuiz(token, activeQuiz.id, payload);
    fetchQuizzes();
  };

  // Handle Unpublish
  const handleUnpublish = async (quiz: QuizManagementItem) => {
    const reason = prompt(`Enter reason to unpublish "${quiz.title}" and revert to draft:`);
    if (reason === null) return;
    setActionLoadingId(quiz.id);
    try {
      await quizPublishingService.unpublishQuiz(token, quiz.id, { reason: reason || undefined });
      fetchQuizzes();
    } catch (err: any) {
      alert(`Unpublish failed: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle Archive
  const handleArchive = async (quiz: QuizManagementItem) => {
    if (!confirm(`Are you sure you want to archive "${quiz.title}"?`)) return;
    setActionLoadingId(quiz.id);
    try {
      await quizPublishingService.archiveQuiz(token, quiz.id);
      fetchQuizzes();
    } catch (err: any) {
      alert(`Archive failed: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle View History
  const handleViewHistory = async (quiz: QuizManagementItem) => {
    setActionLoadingId(quiz.id);
    try {
      const items = await quizPublishingService.getPublishingHistory(token, quiz.id);
      setActiveQuiz(quiz);
      setHistoryItems(items);
      setShowHistoryModal(true);
    } catch (err: any) {
      alert(`Failed to load history: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const statusFilters = [
    { label: 'All', value: 'all' },
    { label: 'Draft', value: 'draft' },
    { label: 'Ready for Review', value: 'ready_to_publish' },
    { label: 'Scheduled', value: 'scheduled' },
    { label: 'Published', value: 'published' },
    { label: 'Active', value: 'active' },
    { label: 'Completed', value: 'completed' },
    { label: 'Archived', value: 'archived' },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'scheduled':
        return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30';
      case 'ready_to_publish':
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'active':
        return 'bg-green-500/20 text-green-300 border-green-500/40 animate-pulse';
      case 'completed':
        return 'bg-slate-700/50 text-slate-300 border-slate-600';
      case 'archived':
        return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      default:
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Sliders className="w-6 h-6 text-primary-400" />
            <span>Quiz Management &amp; Publishing</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Configure examination rules, execute pre-publish audits, and manage lifecycles.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Link
            href={`${basePath}/quiz/create/manual`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs font-semibold text-slate-200 transition-colors"
          >
            <Plus className="w-4 h-4 text-primary-400" />
            <span>Create Manual Quiz</span>
          </Link>
          <Link
            href={`${basePath}/quiz-generator`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold shadow-lg shadow-primary-600/20 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Auto Generator</span>
          </Link>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-card p-4 rounded-2xl border border-surface-border space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by title, subject, code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value)}
              aria-label="Filter by creation method"
              className="px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-300 focus:outline-none"
            >
              <option value="all">All Modes (Manual &amp; Auto)</option>
              <option value="manual">Manual Authoring</option>
              <option value="generator">Automatic Generator</option>
            </select>

            <button
              onClick={fetchQuizzes}
              title="Refresh list"
              className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => setSelectedStatus(f.value)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors border ${
                selectedStatus === f.value
                  ? 'bg-primary-600 text-white border-primary-500 shadow-sm'
                  : 'bg-surface-elevated text-slate-400 border-surface-border hover:text-white hover:border-slate-600'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Quizzes List / Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
          <RefreshCw className="w-6 h-6 animate-spin text-primary-400" />
          <span>Loading examinations...</span>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          {error}
        </div>
      ) : quizzes.length === 0 ? (
        <div className="py-16 text-center text-slate-400 glass-card rounded-2xl border border-surface-border p-8">
          <BookOpen className="w-10 h-10 mx-auto text-slate-600 mb-2" />
          <p className="text-sm font-semibold text-slate-300">No examinations found matching your filter criteria.</p>
          <p className="text-xs text-slate-500 mt-1">Create a quiz manually or run the automatic question paper generator.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {quizzes.map((quiz) => (
            <div
              key={quiz.id}
              className="glass-card rounded-2xl border border-surface-border hover:border-slate-600 transition-all p-5 flex flex-col justify-between gap-4 relative overflow-hidden"
            >
              {/* Card Header */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusBadge(
                      quiz.status
                    )}`}
                  >
                    {quiz.status.replace('_', ' ')}
                  </span>

                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                    <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 uppercase font-mono">
                      {quiz.creation_mode}
                    </span>
                    {quiz.published_version > 0 && (
                      <span className="px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-300 border border-primary-500/20 font-bold">
                        v{quiz.published_version}
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="text-sm font-bold text-white hover:text-primary-300 transition-colors line-clamp-1">
                  {quiz.title}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {quiz.description || 'No examination description provided.'}
                </p>

                {quiz.subject_name && (
                  <div className="text-[11px] text-primary-400 font-medium truncate">
                    {quiz.subject_name} {quiz.programme_name ? `• ${quiz.programme_name}` : ''}
                  </div>
                )}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-2 py-2.5 px-3 rounded-xl bg-slate-950/50 border border-surface-border/40 text-center text-xs">
                <div>
                  <div className="text-[10px] text-slate-500">Questions</div>
                  <div className="font-bold text-white mt-0.5">{quiz.total_questions}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Max Marks</div>
                  <div className="font-bold text-white mt-0.5">{quiz.maximum_marks ?? quiz.total_marks ?? 0}m</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Duration</div>
                  <div className="font-bold text-white mt-0.5">{quiz.duration_minutes}m</div>
                </div>
              </div>

              {/* Timing info if scheduled */}
              {quiz.start_time && (
                <div className="text-[11px] text-cyan-300/90 flex items-center gap-1.5 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1.5 rounded-lg">
                  <Calendar className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">
                    {new Date(quiz.start_time).toLocaleDateString()} {new Date(quiz.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              )}

              {/* Actions Footer */}
              <div className="pt-3 border-t border-surface-border/60 flex items-center justify-between gap-1 flex-wrap">
                {/* Configuration Wizard Link */}
                <Link
                  href={`${basePath}/quiz/${quiz.id}/configure`}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-elevated hover:bg-surface-border text-slate-200 text-xs font-semibold border border-surface-border"
                >
                  <Settings className="w-3.5 h-3.5 text-primary-400" />
                  <span>Configure</span>
                </Link>

                <div className="flex items-center gap-1">
                  {/* Validate / Preflight Audit */}
                  <button
                    onClick={() => handleValidate(quiz)}
                    disabled={actionLoadingId === quiz.id}
                    title="Run preflight validation"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  </button>

                  {/* Publish */}
                  {quiz.status !== 'published' && quiz.status !== 'archived' && (
                    <button
                      onClick={() => {
                        setActiveQuiz(quiz);
                        setShowPublishModal(true);
                      }}
                      title="Publish examination"
                      className="p-1.5 rounded-lg text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  )}

                  {/* Schedule */}
                  {quiz.status !== 'archived' && (
                    <button
                      onClick={() => {
                        setActiveQuiz(quiz);
                        setShowScheduleModal(true);
                      }}
                      title="Schedule examination"
                      className="p-1.5 rounded-lg text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors"
                    >
                      <Clock className="w-4 h-4" />
                    </button>
                  )}

                  {/* Unpublish */}
                  {(quiz.status === 'published' || quiz.status === 'scheduled') && (
                    <button
                      onClick={() => handleUnpublish(quiz)}
                      title="Revert to draft"
                      className="p-1.5 rounded-lg text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  )}

                  {/* History */}
                  <button
                    onClick={() => handleViewHistory(quiz)}
                    title="Audit trail and version history"
                    className="p-1.5 rounded-lg text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 transition-colors"
                  >
                    <History className="w-4 h-4" />
                  </button>

                  {/* Archive */}
                  {quiz.status !== 'archived' && (
                    <button
                      onClick={() => handleArchive(quiz)}
                      title="Archive examination"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                    >
                      <Archive className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Validation Report Modal */}
      <ValidationReportModal
        report={validationReport}
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        onProceedToPublish={() => {
          setShowPublishModal(true);
        }}
      />

      {/* Publish Modal */}
      <PublishModal
        quizTitle={activeQuiz?.title || 'Examination'}
        isOpen={showPublishModal}
        onClose={() => setShowPublishModal(false)}
        onConfirm={handlePublishSubmit}
      />

      {/* Schedule Modal */}
      <ScheduleModal
        quizTitle={activeQuiz?.title || 'Examination'}
        isOpen={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        onConfirm={handleScheduleSubmit}
      />

      {/* Publishing History Modal */}
      <PublishingHistoryModal
        quizTitle={activeQuiz?.title || 'Examination'}
        history={historyItems}
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
      />
    </div>
  );
}
