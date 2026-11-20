'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  Flag,
  User,
  Shield,
  Save,
  ChevronRight,
  ChevronLeft,
  BookOpen,
  Award,
  ListOrdered,
  Sparkles,
  Check,
} from 'lucide-react';
import {
  evaluationService,
  EvaluationTaskItem,
  ManualGradingWorkspace,
  ManualGradingQuestionItem,
} from '@/services/evaluationService';

export default function ManualGradingWorkspaceView() {
  const [token, setToken] = useState<string | null>(null);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [tasks, setTasks] = useState<EvaluationTaskItem[]>([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);

  const [workspace, setWorkspace] = useState<ManualGradingWorkspace | null>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Grading form state for active question
  const [marksInput, setMarksInput] = useState<number>(0);
  const [feedbackInput, setFeedbackInput] = useState('');
  const [notesInput, setNotesInput] = useState('');
  const [flagModeration, setFlagModeration] = useState(false);
  const [criterionScores, setCriterionScores] = useState<Record<string, number>>({});

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    const stored =
      localStorage.getItem('token') ||
      localStorage.getItem('admin_token') ||
      localStorage.getItem('access_token');
    setToken(stored);
  }, []);

  const loadTasks = useCallback(async () => {
    if (!token) return;
    try {
      setLoadingTasks(true);
      const res = await evaluationService.listManualTasks(token);
      setTasks(res);
      if (res.length > 0 && !selectedAttemptId) {
        setSelectedAttemptId(res[0].attempt_id);
      }
    } catch (err: any) {
      console.error('Failed to load tasks', err);
    } finally {
      setLoadingTasks(false);
    }
  }, [token, selectedAttemptId]);

  useEffect(() => {
    if (token) loadTasks();
  }, [token, loadTasks]);

  const loadWorkspace = useCallback(async (attemptId: string) => {
    if (!token) return;
    try {
      setLoadingWorkspace(true);
      const ws = await evaluationService.getGradingWorkspace(token, attemptId);
      setWorkspace(ws);
      setCurrentQuestionIndex(0);
    } catch (err: any) {
      alert(err.message || 'Failed to load grading workspace');
    } finally {
      setLoadingWorkspace(false);
    }
  }, [token]);

  useEffect(() => {
    if (selectedAttemptId) {
      loadWorkspace(selectedAttemptId);
    }
  }, [selectedAttemptId, loadWorkspace]);

  // Sync active question state
  const activeQuestion: ManualGradingQuestionItem | undefined =
    workspace?.questions[currentQuestionIndex];

  useEffect(() => {
    if (activeQuestion) {
      setMarksInput(Number(activeQuestion.marks_awarded || 0));
      setFeedbackInput(activeQuestion.feedback || '');
      setNotesInput(activeQuestion.private_notes || '');
      setFlagModeration(activeQuestion.is_flagged_for_moderation || false);

      const critMap: Record<string, number> = {};
      if (activeQuestion.criterion_scores) {
        activeQuestion.criterion_scores.forEach((c) => {
          critMap[c.criterion_title] = Number(c.awarded_marks || 0);
        });
      }
      setCriterionScores(critMap);
    }
  }, [activeQuestion]);

  const handleCriterionClick = (title: string, marks: number) => {
    setCriterionScores((prev) => {
      const next = { ...prev, [title]: marks };
      // Sum criterion scores into total marks
      const total = Object.values(next).reduce((a, b) => a + b, 0);
      setMarksInput(Math.min(activeQuestion?.max_marks || 0, total));
      return next;
    });
  };

  const handleSaveMarks = async () => {
    if (!token || !workspace || !activeQuestion) return;

    if (marksInput < 0 || marksInput > activeQuestion.max_marks) {
      alert(`Marks awarded must be between 0 and maximum marks (${activeQuestion.max_marks}).`);
      return;
    }

    try {
      setSaving(true);
      const critScoresArray = Object.entries(criterionScores).map(([title, awarded]) => ({
        criterion_title: title,
        awarded_marks: awarded,
        max_marks: activeQuestion.rubric?.criteria.find((c) => c.title === title)?.max_marks || awarded,
      }));

      await evaluationService.saveManualEvaluation(token, {
        attempt_id: workspace.attempt_id,
        quiz_question_id: activeQuestion.quiz_question_id,
        marks_awarded: marksInput,
        feedback: feedbackInput,
        private_notes: notesInput,
        rubric_id: activeQuestion.rubric?.id,
        criterion_scores: critScoresArray.length > 0 ? critScoresArray : undefined,
        flag_for_moderation: flagModeration,
      });

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);

      // Refresh workspace and tasks
      await loadWorkspace(workspace.attempt_id);
      await loadTasks();

      // Automatically advance to next question if available
      if (currentQuestionIndex < workspace.questions.length - 1) {
        setCurrentQuestionIndex((i) => i + 1);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to save marks');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl border border-surface-border p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-primary-500 to-cyan-500" />
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Manual Grading Workspace</h1>
            <p className="text-xs text-slate-400 mt-1">
              Standardized rubric-driven manual evaluation for descriptive answers with anonymous candidate masking.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar: Tasks Queue */}
        <div className="lg:col-span-1 glass-card rounded-2xl border border-surface-border p-4 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Grading Queue ({tasks.length})
            </span>
            <span className="text-[10px] font-mono text-cyan-400">Pending</span>
          </div>

          {loadingTasks ? (
            <div className="p-6 text-center text-slate-500 text-xs">Loading queue...</div>
          ) : tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 space-y-2">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400/50" />
              <p className="text-xs font-semibold text-slate-400">Queue Clear!</p>
              <p className="text-[11px] text-slate-500">All descriptive answers have been graded.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {tasks.map((t) => (
                <button
                  key={t.attempt_id}
                  onClick={() => setSelectedAttemptId(t.attempt_id)}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedAttemptId === t.attempt_id
                      ? 'bg-primary-600/15 border-primary-500/40 text-white'
                      : 'bg-slate-900/50 border-surface-border text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <div className="text-xs font-semibold truncate">{t.student_identifier}</div>
                  <div className="text-[11px] text-slate-500 truncate mt-0.5">{t.quiz_title}</div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 mt-2">
                    <span>{t.pending_questions_count} pending</span>
                    <span>{new Date(t.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Main Area: Grading Canvas */}
        <div className="lg:col-span-3 space-y-6">
          {loadingWorkspace ? (
            <div className="glass-card rounded-2xl border border-surface-border p-16 text-center text-slate-400 space-y-3">
              <div className="w-8 h-8 rounded-full border-2 border-primary-500/20 border-t-primary-500 animate-spin mx-auto" />
              <p className="text-xs">Loading candidate submission and rubric criteria...</p>
            </div>
          ) : !workspace || !activeQuestion ? (
            <div className="glass-card rounded-2xl border border-surface-border p-16 text-center text-slate-500">
              <p className="text-sm font-semibold text-slate-400">Select an examination attempt from the queue.</p>
            </div>
          ) : (
            <div className="glass-card rounded-2xl border border-surface-border p-6 shadow-xl space-y-6">
              {/* Candidate Info Header */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-500/15 border border-cyan-500/30">
                      {workspace.student_identifier}
                    </span>
                    {workspace.student_roll_no && (
                      <span className="text-xs text-slate-400 font-mono">ID: {workspace.student_roll_no}</span>
                    )}
                  </div>
                  <h2 className="text-base font-bold text-white mt-1">{workspace.quiz_title}</h2>
                </div>

                {/* Question Navigator */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-mono">
                    Question {currentQuestionIndex + 1} of {workspace.questions.length}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      disabled={currentQuestionIndex === 0}
                      onClick={() => setCurrentQuestionIndex((i) => Math.max(0, i - 1))}
                      className="p-1.5 rounded-lg bg-slate-900 border border-surface-border text-slate-300 disabled:opacity-30"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      disabled={currentQuestionIndex >= workspace.questions.length - 1}
                      onClick={() => setCurrentQuestionIndex((i) => Math.min(workspace.questions.length - 1, i + 1))}
                      className="p-1.5 rounded-lg bg-slate-900 border border-surface-border text-slate-300 disabled:opacity-30"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Question Statement */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-surface-border space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300 uppercase tracking-wider">
                    {activeQuestion.section_title || 'General Section'}
                  </span>
                  <span className="font-mono text-cyan-300 font-bold">
                    Max Marks: {Number(activeQuestion.max_marks).toFixed(2)}
                  </span>
                </div>
                <p className="text-sm text-white leading-relaxed font-medium">
                  {activeQuestion.question_text}
                </p>
              </div>

              {/* Candidate Answer Response */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                  Candidate Submitted Answer:
                </span>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap font-mono leading-relaxed min-h-[140px] select-text">
                  {activeQuestion.student_answer_text || (
                    <span className="text-slate-500 italic">No text answer submitted by candidate.</span>
                  )}
                </div>
              </div>

              {/* Rubric Criteria Clickers (if attached) */}
              {activeQuestion.rubric && (
                <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-purple-300 flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      <span>{activeQuestion.rubric.title} (v{activeQuestion.rubric.version})</span>
                    </span>
                    <span className="text-[11px] text-purple-400 font-mono">
                      Rubric Max: {activeQuestion.rubric.total_max_marks} marks
                    </span>
                  </div>

                  {activeQuestion.rubric.grading_instructions && (
                    <p className="text-[11px] text-slate-400 italic">
                      "{activeQuestion.rubric.grading_instructions}"
                    </p>
                  )}

                  <div className="space-y-3 pt-2">
                    {activeQuestion.rubric.criteria.map((crit, cIdx) => (
                      <div key={cIdx} className="p-3 rounded-lg bg-slate-900/80 border border-surface-border text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{crit.title}</span>
                          <span className="text-[11px] font-mono text-cyan-400">Max: {crit.max_marks}</span>
                        </div>
                        {crit.description && (
                          <p className="text-[11px] text-slate-400">{crit.description}</p>
                        )}

                        {/* Partial Credit Quick Tiers */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {[0, Number(crit.max_marks) * 0.5, Number(crit.max_marks)].map((tierVal, tIdx) => (
                            <button
                              key={tIdx}
                              type="button"
                              onClick={() => handleCriterionClick(crit.title, tierVal)}
                              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                                criterionScores[crit.title] === tierVal
                                  ? 'bg-purple-600 text-white font-bold'
                                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                              }`}
                            >
                              +{tierVal.toFixed(1)} pts
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Awarded Marks & Feedback Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Awarded Marks <span className="text-cyan-400">(/ {activeQuestion.max_marks})</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max={activeQuestion.max_marks}
                    value={marksInput}
                    onChange={(e) => setMarksInput(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-primary-500 font-bold"
                  />
                </div>

                <div className="sm:col-span-2 space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Candidate Feedback</label>
                  <input
                    type="text"
                    value={feedbackInput}
                    onChange={(e) => setFeedbackInput(e.target.value)}
                    placeholder="Feedback visible to student upon results publication..."
                    className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>

              {/* Private Notes & Flag for Moderation */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-xs font-semibold text-slate-400">
                    Internal Evaluator Notes (Private)
                  </label>
                  <input
                    type="text"
                    value={notesInput}
                    onChange={(e) => setNotesInput(e.target.value)}
                    placeholder="Notes for head examiner or moderation review..."
                    className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-primary-500"
                  />
                </div>

                <div className="flex items-end">
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-amber-300 cursor-pointer w-full">
                    <input
                      type="checkbox"
                      checked={flagModeration}
                      onChange={(e) => setFlagModeration(e.target.checked)}
                      className="rounded border-slate-700 text-amber-500 focus:ring-0"
                    />
                    <Flag className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Flag for Moderation</span>
                  </label>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-surface-border flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  {saveSuccess && (
                    <span className="text-emerald-400 font-medium flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" />
                      Marks saved & provisional score recalculated!
                    </span>
                  )}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveMarks}
                    disabled={saving}
                    className="px-5 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-primary-900/30"
                  >
                    <Save className="w-4 h-4" />
                    <span>{saving ? 'Saving...' : 'Save & Continue'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
