'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  HelpCircle,
  Plus,
  RefreshCw,
  Search,
  Filter,
  FileText,
  CheckCircle2,
  Clock,
  Archive,
  Layers,
  LayoutGrid,
  Table as TableIcon,
  Shield,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { StatCard } from '@/components/ui/StatCard';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';

import {
  QuestionListItem,
  QuestionStats,
  QuestionFilterParams,
  questionBankService,
} from '@/services/questionBankService';
import { QuestionCard } from '@/components/question-bank/QuestionCard';
import { QuestionPreviewModal } from '@/components/question-bank/QuestionPreviewModal';
import { QuestionReviewModal } from '@/components/question-bank/QuestionReviewModal';
import { QuestionVersionHistoryModal } from '@/components/question-bank/QuestionVersionHistoryModal';

export default function UserAdminQuestionBankPage() {
  const { user, token, isAuthenticated, hasPermission, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Permissions
  const canCreate = hasPermission('question.create');
  const canEdit = hasPermission('question.edit');
  const canDelete = hasPermission('question.delete');
  const canArchive = hasPermission('question.archive');
  const canReview = hasPermission('question.review') || hasPermission('question.approve');
  const canViewAnswer = hasPermission('question.answer.view');

  // Data States
  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [stats, setStats] = useState<QuestionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Modals State
  const [previewQuestionId, setPreviewQuestionId] = useState<string | null>(null);
  const [reviewQuestion, setReviewQuestion] = useState<QuestionListItem | null>(null);
  const [historyQuestionId, setHistoryQuestionId] = useState<string | null>(null);
  const [questionToDelete, setQuestionToDelete] = useState<QuestionListItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const filterParams: QuestionFilterParams = {};
      if (search.trim()) filterParams.search = search.trim();
      if (selectedStatus !== 'all') filterParams.status = selectedStatus;
      if (selectedDifficulty !== 'all') filterParams.difficulty = selectedDifficulty;
      if (selectedType !== 'all') filterParams.question_type = selectedType;

      const [qList, sData] = await Promise.all([
        questionBankService.getQuestions(filterParams, token),
        questionBankService.getStats(token),
      ]);

      setQuestions(qList);
      setStats(sData);
    } catch (err: any) {
      setError(err.message || 'Failed to load question bank data.');
    } finally {
      setLoading(false);
    }
  }, [token, search, selectedStatus, selectedDifficulty, selectedType]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (token) {
      fetchData();
    }
  }, [authLoading, isAuthenticated, token, fetchData, router]);

  async function handleDuplicate(q: QuestionListItem) {
    if (!token || !canCreate) return;
    try {
      await questionBankService.duplicateQuestion(q.id, token);
      fetchData();
    } catch (err: any) {
      alert(`Duplicate failed: ${err.message}`);
    }
  }

  async function handleArchive(q: QuestionListItem) {
    if (!token || !canArchive) return;
    try {
      await questionBankService.archiveQuestion(q.id, token);
      fetchData();
    } catch (err: any) {
      alert(`Archive failed: ${err.message}`);
    }
  }

  async function handleRestore(q: QuestionListItem) {
    if (!token || !canArchive) return;
    try {
      await questionBankService.restoreQuestion(q.id, token);
      fetchData();
    } catch (err: any) {
      alert(`Restore failed: ${err.message}`);
    }
  }

  async function handleConfirmDelete() {
    if (!token || !questionToDelete || !canDelete) return;
    setDeleteLoading(true);
    try {
      await questionBankService.deleteQuestion(questionToDelete.id, token);
      setQuestionToDelete(null);
      fetchData();
    } catch (err: any) {
      alert(`Delete rejected: ${err.message}`);
    } finally {
      setDeleteLoading(false);
    }
  }

  const tableColumns: TableColumn<QuestionListItem>[] = [
    {
      key: 'title',
      header: 'Question',
      render: (q) => (
        <div className="space-y-1 max-w-md">
          <div className="font-semibold text-slate-100 line-clamp-1">{q.title || 'Untitled'}</div>
          <div className="text-xs text-slate-400 line-clamp-2">{q.question_text}</div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-0.5">
            <span>{q.subject_name || 'Subject'}</span>
            <span>&rsaquo;</span>
            <span className="text-primary-400">{q.topic_name || 'Topic'}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type & Difficulty',
      render: (q) => (
        <div className="space-y-1">
          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-200 border border-slate-700 uppercase">
            {q.question_type.replace('_', ' ')}
          </span>
          <div>
            <span
              className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${
                q.difficulty === 'easy'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : q.difficulty === 'medium'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              {q.difficulty.toUpperCase()}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'marks',
      header: 'Marks',
      render: (q) => (
        <div className="text-xs font-semibold text-slate-200">
          +{q.default_marks} <span className="text-slate-500">(-{q.default_negative_marks})</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (q) => (
        <span
          className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border ${
            q.status === 'approved'
              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
              : q.status === 'pending_review'
              ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
              : q.status === 'archived'
              ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
              : 'bg-slate-700/40 text-slate-300 border-slate-600'
          }`}
        >
          {q.status.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (q) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setPreviewQuestionId(q.id)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 hover:text-white"
          >
            Preview
          </button>
          {canReview && (
            <button
              onClick={() => setReviewQuestion(q)}
              className="p-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-xs text-amber-400"
            >
              Review
            </button>
          )}
          <button
            onClick={() => setHistoryQuestionId(q.id)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 hover:text-white"
          >
            History
          </button>
          {canEdit && q.status !== 'archived' && (
            <Link
              href={`/admin/question-bank/${q.id}/edit`}
              className="p-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-xs text-blue-400"
            >
              Edit
            </Link>
          )}
          {canDelete && (
            <button
              onClick={() => setQuestionToDelete(q)}
              className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-xs text-rose-400"
            >
              Delete
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/30">
              User Admin
            </span>
            <span className="text-xs text-slate-400">Scoped Academic Question Bank</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Question Bank Management
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage examination questions within your authorized academic curriculum and subject assignments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors"
            title="Refresh Questions"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {canCreate && (
            <Link
              href="/admin/question-bank/create"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-all shadow-md shadow-primary-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Create Question</span>
            </Link>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Questions"
          value={stats?.total_questions ?? 0}
          icon={HelpCircle}
          subtitle="In your authorized scope"
        />
        <StatCard
          title="Drafts"
          value={stats?.draft ?? 0}
          icon={FileText}
          subtitle="Authored by you"
        />
        <StatCard
          title="Pending Review"
          value={stats?.pending_review ?? 0}
          icon={Clock}
          subtitle="In review"
        />
        <StatCard
          title="Approved"
          value={stats?.approved ?? 0}
          icon={CheckCircle2}
          subtitle="Ready for inclusion"
        />
        <StatCard
          title="Archived"
          value={stats?.archived ?? 0}
          icon={Archive}
          subtitle="Archived items"
        />
      </div>

      {/* Filter and Control Toolbar */}
      <div className="p-4 rounded-2xl bg-surface-elevated border border-surface-border space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, prompt text, or tag..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="pending_review">Pending Review</option>
              <option value="approved">Approved</option>
              <option value="archived">Archived</option>
            </select>

            <select
              value={selectedDifficulty}
              onChange={(e) => setSelectedDifficulty(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>

            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">All Types</option>
              <option value="single_choice">Single Choice</option>
              <option value="multiple_choice">Multiple Choice</option>
              <option value="true_false">True / False</option>
              <option value="short_answer">Short Answer</option>
            </select>

            <div className="flex items-center rounded-xl bg-slate-900 p-1 border border-surface-border">
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-lg transition-colors ${
                  viewMode === 'grid' ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
                title="Grid Cards"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-lg transition-colors ${
                  viewMode === 'table' ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
                title="Table View"
              >
                <TableIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main List */}
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchData} />
      ) : questions.length === 0 ? (
        <div className="text-center py-16 p-8 rounded-2xl bg-surface-elevated border border-surface-border space-y-3">
          <HelpCircle className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">No Questions Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No questions found in your academic scope matching the current filters.
          </p>
          {canCreate && (
            <Link
              href="/admin/question-bank/create"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
            >
              <Plus className="w-4 h-4" />
              <span>Create Question</span>
            </Link>
          )}
        </div>
      ) : viewMode === 'table' ? (
        <ResponsiveTable
          columns={tableColumns}
          data={questions}
          keyExtractor={(q) => q.id}
          mobileCardRender={(q) => (
            <QuestionCard
              question={q}
              basePath="/admin/question-bank"
              onPreview={(item) => setPreviewQuestionId(item.id)}
              onReview={(item) => setReviewQuestion(item)}
              onHistory={(item) => setHistoryQuestionId(item.id)}
              onDuplicate={handleDuplicate}
              onArchive={handleArchive}
              onRestore={handleRestore}
              onDelete={(item) => setQuestionToDelete(item)}
              canEdit={canEdit}
              canDelete={canDelete}
              canReview={canReview}
            />
          )}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {questions.map((q) => (
            <QuestionCard
              key={q.id}
              question={q}
              basePath="/admin/question-bank"
              onPreview={(item) => setPreviewQuestionId(item.id)}
              onReview={(item) => setReviewQuestion(item)}
              onHistory={(item) => setHistoryQuestionId(item.id)}
              onDuplicate={handleDuplicate}
              onArchive={handleArchive}
              onRestore={handleRestore}
              onDelete={(item) => setQuestionToDelete(item)}
              canEdit={canEdit}
              canDelete={canDelete}
              canReview={canReview}
            />
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {previewQuestionId && (
        <QuestionPreviewModal
          questionId={previewQuestionId}
          isOpen={!!previewQuestionId}
          onClose={() => setPreviewQuestionId(null)}
          token={token}
          canViewAnswerKey={canViewAnswer}
        />
      )}

      {/* Review Modal */}
      {reviewQuestion && (
        <QuestionReviewModal
          question={reviewQuestion}
          isOpen={!!reviewQuestion}
          onClose={() => setReviewQuestion(null)}
          onSuccess={fetchData}
          token={token || ''}
          isSuperAdmin={false}
        />
      )}

      {/* Version History Modal */}
      {historyQuestionId && (
        <QuestionVersionHistoryModal
          questionId={historyQuestionId}
          isOpen={!!historyQuestionId}
          onClose={() => setHistoryQuestionId(null)}
          token={token || ''}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={!!questionToDelete}
        title="Delete Question"
        message={`Are you sure you want to permanently delete "${questionToDelete?.title || 'this question'}"? This action cannot be undone.`}
        confirmLabel={deleteLoading ? 'Deleting...' : 'Delete Permanently'}
        onConfirm={handleConfirmDelete}
        onCancel={() => setQuestionToDelete(null)}
        variant="danger"
      />
    </div>
  );
}
