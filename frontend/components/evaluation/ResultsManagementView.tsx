'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Award,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Eye,
  Send,
  Edit3,
  Clock,
  Layers,
  FileCheck,
  AlertTriangle,
  RotateCcw,
  Check,
  X,
  ChevronRight,
  User,
  BookOpen,
  History,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  evaluationService,
  ResultListItem,
  ResultDetail,
  ResultListResponse,
} from '@/services/evaluationService';

interface ResultsManagementViewProps {
  isSuperAdmin?: boolean;
}

export default function ResultsManagementView({ isSuperAdmin = false }: ResultsManagementViewProps) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [resultsData, setResultsData] = useState<ResultListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [quizIdFilter, setQuizIdFilter] = useState('');
  const [isApprovedFilter, setIsApprovedFilter] = useState<string>('all');
  const [isPublishedFilter, setIsPublishedFilter] = useState<string>('all');
  const [isPassedFilter, setIsPassedFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  // Detail Modal & Override Modal states
  const [selectedResult, setSelectedResult] = useState<ResultDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [overrideModalResult, setOverrideModalResult] = useState<ResultListItem | null>(null);
  const [newScoreInput, setNewScoreInput] = useState('');
  const [overrideReasonInput, setOverrideReasonInput] = useState('');
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  // Read Auth Token
  useEffect(() => {
    const storedToken =
      localStorage.getItem('token') ||
      localStorage.getItem('admin_token') ||
      localStorage.getItem('access_token');
    setToken(storedToken);
  }, []);

  const loadResults = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await evaluationService.listResults(token, {
        quiz_id: quizIdFilter || undefined,
        search: search || undefined,
        is_approved: isApprovedFilter === 'all' ? undefined : isApprovedFilter === 'true',
        is_published: isPublishedFilter === 'all' ? undefined : isPublishedFilter === 'true',
        is_passed: isPassedFilter === 'all' ? undefined : isPassedFilter === 'true',
        page,
        limit: 15,
      });
      setResultsData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  }, [token, quizIdFilter, search, isApprovedFilter, isPublishedFilter, isPassedFilter, page]);

  useEffect(() => {
    if (token) {
      loadResults();
    }
  }, [token, loadResults]);

  const handleOpenDetail = async (resultId: string) => {
    if (!token) return;
    try {
      setLoadingDetail(true);
      const detail = await evaluationService.getResultDetail(token, resultId);
      setSelectedResult(detail);
    } catch (err: any) {
      alert(err.message || 'Failed to load result detail');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleApprove = async (resultId: string) => {
    if (!token) return;
    try {
      setActionSubmitting(true);
      await evaluationService.approveResult(token, resultId, 'Standard administrative approval.');
      setActionFeedback('Result approved successfully!');
      setTimeout(() => setActionFeedback(null), 3000);
      await loadResults();
      if (selectedResult && selectedResult.id === resultId) {
        handleOpenDetail(resultId);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to approve result');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handlePublish = async (resultId: string) => {
    if (!token) return;
    try {
      setActionSubmitting(true);
      await evaluationService.publishResult(token, resultId, true);
      setActionFeedback('Result officially published to candidate!');
      setTimeout(() => setActionFeedback(null), 3000);
      await loadResults();
      if (selectedResult && selectedResult.id === resultId) {
        handleOpenDetail(resultId);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to publish result');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleBatchApprove = async () => {
    if (!token || !quizIdFilter) {
      alert('Please specify a Quiz filter to execute batch operations.');
      return;
    }
    if (!confirm('Are you sure you want to approve all completed evaluations for this quiz?')) return;
    try {
      setActionSubmitting(true);
      const res = await evaluationService.batchApproveResults(token, quizIdFilter, 'Batch approved by administrator.');
      alert(`Successfully approved ${res.approved_count} results.`);
      await loadResults();
    } catch (err: any) {
      alert(err.message || 'Batch approval failed');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleBatchPublish = async () => {
    if (!token || !quizIdFilter) {
      alert('Please specify a Quiz filter to execute batch operations.');
      return;
    }
    if (!confirm('Are you sure you want to publish all approved results to students?')) return;
    try {
      setActionSubmitting(true);
      const res = await evaluationService.batchPublishResults(token, quizIdFilter, true);
      alert(`Successfully published ${res.published_count} results.`);
      await loadResults();
    } catch (err: any) {
      alert(err.message || 'Batch publication failed');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleOpenOverrideModal = (item: ResultListItem) => {
    setOverrideModalResult(item);
    setNewScoreInput(String(item.score));
    setOverrideReasonInput('');
  };

  const handleSubmitOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !overrideModalResult) return;
    const scoreVal = parseFloat(newScoreInput);
    if (isNaN(scoreVal) || scoreVal < 0) {
      alert('Please enter a valid non-negative score.');
      return;
    }
    if (!overrideReasonInput.trim()) {
      alert('A documented justification reason is mandatory for administrative score adjustments.');
      return;
    }

    try {
      setActionSubmitting(true);
      await evaluationService.overrideResult(token, overrideModalResult.id, scoreVal, overrideReasonInput);
      setOverrideModalResult(null);
      setActionFeedback('Administrative mark override recorded with audit history.');
      setTimeout(() => setActionFeedback(null), 3000);
      await loadResults();
      if (selectedResult && selectedResult.id === overrideModalResult.id) {
        handleOpenDetail(overrideModalResult.id);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to override score');
    } finally {
      setActionSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl border border-surface-border p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-primary-500 to-emerald-500" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-primary-500/15 border border-primary-500/30 flex items-center justify-center text-primary-400 shrink-0">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white">Results Management & Verification</h1>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                  {isSuperAdmin ? 'Platform-Wide' : 'Scoped'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Authoritative evaluation results, score moderation, multi-tier approvals, and immutable publication audit trail.
              </p>
            </div>
          </div>

          {/* Batch Actions */}
          <div className="flex items-center gap-2 self-stretch sm:self-auto">
            <button
              onClick={handleBatchApprove}
              disabled={actionSubmitting || !quizIdFilter}
              title={!quizIdFilter ? 'Select a specific quiz first' : 'Batch approve completed attempts'}
              className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Batch Approve</span>
            </button>
            <button
              onClick={handleBatchPublish}
              disabled={actionSubmitting || !quizIdFilter}
              title={!quizIdFilter ? 'Select a specific quiz first' : 'Batch publish approved results'}
              className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shadow-lg shadow-primary-900/20"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Batch Publish</span>
            </button>
          </div>
        </div>
      </div>

      {/* Action Toast Feedback */}
      {actionFeedback && (
        <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionFeedback}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="glass-card rounded-2xl border border-surface-border p-4 shadow-lg space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Candidate name or email..."
              className="w-full bg-slate-900 border border-surface-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          {/* Quiz UUID Filter */}
          <div>
            <input
              type="text"
              value={quizIdFilter}
              onChange={(e) => setQuizIdFilter(e.target.value)}
              placeholder="Filter by Quiz ID..."
              className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 font-mono"
            />
          </div>

          {/* Approval Filter */}
          <div>
            <select
              value={isApprovedFilter}
              onChange={(e) => setIsApprovedFilter(e.target.value)}
              className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">Approval: All</option>
              <option value="true">Approved</option>
              <option value="false">Pending Approval</option>
            </select>
          </div>

          {/* Publication Filter */}
          <div>
            <select
              value={isPublishedFilter}
              onChange={(e) => setIsPublishedFilter(e.target.value)}
              className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">Publication: All</option>
              <option value="true">Published</option>
              <option value="false">Unpublished</option>
            </select>
          </div>

          {/* Pass/Fail Filter */}
          <div>
            <select
              value={isPassedFilter}
              onChange={(e) => setIsPassedFilter(e.target.value)}
              className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary-500"
            >
              <option value="all">Outcome: All</option>
              <option value="true">Passed</option>
              <option value="false">Needs Improvement</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="glass-card rounded-2xl border border-surface-border shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-primary-500/20 border-t-primary-500 animate-spin mx-auto" />
            <p className="text-xs">Loading examination results from authoritative records...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 space-y-2">
            <AlertTriangle className="w-8 h-8 mx-auto" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        ) : !resultsData?.items || resultsData.items.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <FileCheck className="w-10 h-10 mx-auto opacity-30 text-slate-400" />
            <p className="text-sm font-semibold text-slate-400">No results found matching your filters.</p>
            <p className="text-xs text-slate-500">Ensure examination attempts have been submitted and evaluated.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-surface-border bg-slate-900/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Candidate</th>
                  <th className="py-3.5 px-4">Examination</th>
                  <th className="py-3.5 px-4 text-center">Score / Max</th>
                  <th className="py-3.5 px-4 text-center">Percentage</th>
                  <th className="py-3.5 px-4 text-center">Outcome</th>
                  <th className="py-3.5 px-4 text-center">Approval</th>
                  <th className="py-3.5 px-4 text-center">Publication</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50 text-xs">
                {resultsData.items.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-900/30 transition-colors">
                    {/* Candidate */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{r.student_name}</div>
                      <div className="text-[11px] text-slate-400">{r.student_email}</div>
                      {r.student_roll_no && (
                        <span className="text-[10px] font-mono text-cyan-400">ID: {r.student_roll_no}</span>
                      )}
                    </td>

                    {/* Examination */}
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-200">{r.quiz_title}</div>
                      {r.subject_name && (
                        <div className="text-[11px] text-slate-400">{r.subject_name}</div>
                      )}
                    </td>

                    {/* Score */}
                    <td className="py-3 px-4 text-center">
                      <span className="text-sm font-bold font-mono text-white">{Number(r.score).toFixed(2)}</span>
                      <span className="text-[11px] font-mono text-slate-500"> / {Number(r.maximum_marks).toFixed(2)}</span>
                    </td>

                    {/* Percentage */}
                    <td className="py-3 px-4 text-center">
                      <span className="font-mono font-semibold text-slate-200">
                        {Number(r.percentage).toFixed(1)}%
                      </span>
                    </td>

                    {/* Outcome */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold ${
                          r.is_passed
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {r.is_passed ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        <span>{r.is_passed ? 'PASSED' : 'NEEDS IMP.'}</span>
                      </span>
                    </td>

                    {/* Approval */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          r.is_approved
                            ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        }`}
                      >
                        {r.is_approved ? 'Approved' : 'Pending'}
                      </span>
                    </td>

                    {/* Publication */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          r.is_published
                            ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                            : 'bg-slate-700/40 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {r.is_published ? 'Published' : 'Hidden'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenDetail(r.id)}
                          title="View complete breakdown"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {!r.is_approved && (
                          <button
                            onClick={() => handleApprove(r.id)}
                            title="Approve result"
                            className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/15 transition-colors"
                          >
                            <ShieldCheck className="w-4 h-4" />
                          </button>
                        )}
                        {!r.is_published && (
                          <button
                            onClick={() => handlePublish(r.id)}
                            title="Publish result to student"
                            className="p-1.5 rounded-lg text-cyan-400 hover:bg-cyan-500/15 transition-colors"
                          >
                            <Send className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleOpenOverrideModal(r)}
                          title="Administrative mark override"
                          className="p-1.5 rounded-lg text-amber-400 hover:bg-amber-500/15 transition-colors"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {resultsData && resultsData.pages > 1 && (
          <div className="p-4 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing Page {resultsData.page} of {resultsData.pages} ({resultsData.total} Total Records)
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded-lg bg-slate-900 border border-surface-border text-slate-300 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page >= resultsData.pages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 rounded-lg bg-slate-900 border border-surface-border text-slate-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Result Detail Modal */}
      {selectedResult && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="max-w-3xl w-full glass-card rounded-2xl border border-surface-border shadow-2xl p-6 space-y-6 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-surface-border">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-primary-400">
                  Authoritative Record
                </span>
                <h2 className="text-lg font-bold text-white mt-0.5">{selectedResult.student_name}</h2>
                <p className="text-xs text-slate-400">{selectedResult.quiz_title}</p>
              </div>
              <button
                onClick={() => setSelectedResult(null)}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Overall Score Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-900 border border-surface-border text-center">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Final Score</span>
                <span className="text-xl font-bold font-mono text-cyan-300">
                  {Number(selectedResult.score).toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500 block">/ {Number(selectedResult.maximum_marks).toFixed(2)}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-surface-border text-center">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Percentage</span>
                <span className="text-xl font-bold font-mono text-white">
                  {Number(selectedResult.percentage).toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-500 block">Passing: {selectedResult.passing_marks || 40}%</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-surface-border text-center">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Objective Pts</span>
                <span className="text-xl font-bold font-mono text-emerald-400">
                  +{Number(selectedResult.objective_marks).toFixed(2)}
                </span>
                <span className="text-[10px] text-rose-400 block">
                  -{Number(selectedResult.negative_marks).toFixed(2)} Penalty
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-surface-border text-center">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Manual Marks</span>
                <span className="text-xl font-bold font-mono text-primary-400">
                  +{Number(selectedResult.manual_marks).toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500 block">Evaluated</span>
              </div>
            </div>

            {/* Section Breakdown Accordion */}
            {(selectedResult.section_scores || selectedResult.section_breakdown) && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-primary-400" />
                  <span>Section Breakdown</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(selectedResult.section_scores || selectedResult.section_breakdown || []).map((sec, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900/60 border border-surface-border space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-white">{sec.title}</span>
                        <span className="font-mono text-cyan-300 font-bold">
                          {Number(sec.obtained_marks).toFixed(2)} / {Number(sec.max_marks).toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 flex justify-between">
                        <span>Attempted: {sec.attempted_count} / {sec.questions_count}</span>
                        {sec.compulsory_count && <span>Required: {sec.compulsory_count}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Question Evaluations List */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                <span>Question Evaluations ({selectedResult.evaluations?.length || 0})</span>
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {selectedResult.evaluations.map((ev, i) => (
                  <div key={i} className="p-2.5 rounded-xl bg-slate-900/40 border border-surface-border text-xs flex items-center justify-between">
                    <div>
                      <span className="font-mono font-semibold text-slate-300">Q{i + 1} ({ev.question_type})</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">{ev.scoring_reason || ev.feedback || 'Evaluated'}</p>
                    </div>
                    <div className="text-right">
                      <span className={`font-mono font-bold ${ev.marks_awarded > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {Number(ev.marks_awarded).toFixed(2)}
                      </span>
                      <span className="text-slate-500 font-mono"> / {Number(ev.max_marks).toFixed(2)}</span>
                      {ev.negative_deduction > 0 && (
                        <div className="text-[10px] text-rose-400 font-mono">-{Number(ev.negative_deduction).toFixed(2)}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Correction Audit History */}
            {(selectedResult.corrections || selectedResult.correction_history) &&
              (selectedResult.corrections || selectedResult.correction_history || []).length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-amber-400" />
                    <span>Correction Audit History</span>
                  </h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {(selectedResult.corrections || selectedResult.correction_history || []).map((c, i) => (
                      <div key={i} className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-1">
                        <div className="flex items-center justify-between text-[11px] text-amber-300 font-semibold">
                          <span>
                            Adjusted from {Number(c.previous_score).toFixed(2)} to {Number(c.new_score).toFixed(2)} marks
                          </span>
                          <span>{new Date(c.corrected_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-[11px] text-slate-300 italic">"{c.reason}"</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Modal Actions */}
            <div className="pt-4 border-t border-surface-border flex items-center justify-between">
              <div className="text-[11px] text-slate-500">
                Version {selectedResult.result_version} • Calculated {new Date(selectedResult.calculated_at).toLocaleString()}
              </div>
              <div className="flex items-center gap-2">
                {!selectedResult.is_approved && (
                  <button
                    onClick={() => handleApprove(selectedResult.id)}
                    disabled={actionSubmitting}
                    className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30"
                  >
                    Approve Result
                  </button>
                )}
                {!selectedResult.is_published && (
                  <button
                    onClick={() => handlePublish(selectedResult.id)}
                    disabled={actionSubmitting}
                    className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white"
                  >
                    Publish to Student
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Override Score Dialog */}
      {overrideModalResult && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleSubmitOverride}
            className="max-w-md w-full glass-card rounded-2xl border border-amber-500/30 shadow-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div className="flex items-center gap-2 text-amber-400">
                <Edit3 className="w-5 h-5" />
                <h2 className="text-base font-bold text-white">Administrative Mark Override</h2>
              </div>
              <button
                type="button"
                onClick={() => setOverrideModalResult(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-300 space-y-1">
              <div>Candidate: <strong className="text-white">{overrideModalResult.student_name}</strong></div>
              <div>Current Score: <strong className="text-cyan-300">{Number(overrideModalResult.score).toFixed(2)}</strong> / {overrideModalResult.maximum_marks}</div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">New Overall Score</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max={overrideModalResult.maximum_marks}
                value={newScoreInput}
                onChange={(e) => setNewScoreInput(e.target.value)}
                required
                className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500 font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">
                Documented Justification Reason <span className="text-rose-400">*</span>
              </label>
              <textarea
                rows={3}
                value={overrideReasonInput}
                onChange={(e) => setOverrideReasonInput(e.target.value)}
                required
                placeholder="Reason for mark change (e.g. Head Examiner moderation, ambiguity in question statement)..."
                className="w-full bg-slate-900 border border-surface-border rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
              />
              <span className="text-[10px] text-slate-500">
                This reason will be permanently archived in the official institutional audit history.
              </span>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setOverrideModalResult(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={actionSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold disabled:opacity-40"
              >
                Confirm Override
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
