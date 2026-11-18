'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  FileText,
  Layers,
  HelpCircle,
  Plus,
  BookOpen,
  Award,
  Eye,
  Save,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Edit,
  ChevronUp,
  ChevronDown,
  ArrowRight,
  Sparkles,
  ChevronRight,
  ArrowLeft,
  SlidersHorizontal,
  MoveVertical,
  X,
  FileCheck,
} from 'lucide-react';

import {
  QuizEditorResponse,
  QuizQuestionItem,
  QuizSectionItem,
  manualQuizService,
} from '@/services/manualQuizService';

import { QuizDetailsForm } from './QuizDetailsForm';
import { SectionManager } from './SectionManager';
import { QuestionEditorModal } from './QuestionEditorModal';
import { QuestionBankPickerModal } from './QuestionBankPickerModal';
import { MarksScoringPanel } from './MarksScoringPanel';
import { LivePaperPreviewModal } from './LivePaperPreviewModal';
import { AutosaveIndicator } from './AutosaveIndicator';

interface ManualQuizWorkspaceProps {
  quizId: string;
  token: string;
  basePath: string; // e.g. '/admin/quiz' or '/super-admin/quiz'
  canViewAnswerKey?: boolean;
}

export function ManualQuizWorkspace({
  quizId,
  token,
  basePath,
  canViewAnswerKey = true,
}: ManualQuizWorkspaceProps) {
  const router = useRouter();

  // Navigation tab states
  const [activeTab, setActiveTab] = useState<
    'details' | 'sections' | 'questions' | 'scoring' | 'preview'
  >('questions');

  // Core Data
  const [data, setData] = useState<QuizEditorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSavingDetails, setIsSavingDetails] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Autosave Status
  const [autosaveStatus, setAutosaveStatus] = useState<
    'idle' | 'saving' | 'saved' | 'error'
  >('idle');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Modals
  const [isQuestionEditorOpen, setIsQuestionEditorOpen] = useState(false);
  const [questionToEdit, setQuestionToEdit] = useState<QuizQuestionItem | null>(null);
  const [isQuestionBankPickerOpen, setIsQuestionBankPickerOpen] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Active section filter for Question View
  const [selectedSectionFilter, setSelectedSectionFilter] = useState<string>('all');

  // Fetch full editor state
  const loadEditorData = useCallback(async () => {
    try {
      setErrorMsg(null);
      const res = await manualQuizService.getEditorState(quizId, token);
      setData(res);
      setLoading(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load quiz editor.');
      setLoading(false);
    }
  }, [quizId, token]);

  useEffect(() => {
    loadEditorData();
  }, [loadEditorData]);

  // Handle Quiz Details Save
  const handleSaveDetails = async (updatedFields: Record<string, unknown>) => {
    setIsSavingDetails(true);
    setAutosaveStatus('saving');
    try {
      await manualQuizService.updateQuizDetails(quizId, updatedFields, token);
      await loadEditorData();
      setAutosaveStatus('saved');
      setHasUnsavedChanges(false);
    } catch (err: any) {
      setAutosaveStatus('error');
      alert(`Failed to save quiz details: ${err.message}`);
    } finally {
      setIsSavingDetails(false);
    }
  };

  // Manual Draft Snapshot Action
  const handleManualSaveDraft = async (changeNote?: string) => {
    setAutosaveStatus('saving');
    try {
      await manualQuizService.saveDraft(quizId, changeNote, token);
      await loadEditorData();
      setAutosaveStatus('saved');
      setHasUnsavedChanges(false);
    } catch (err: any) {
      setAutosaveStatus('error');
      alert(`Failed to save draft snapshot: ${err.message}`);
    }
  };

  // Question CRUD Handlers
  const handleDeleteQuestion = async (qId: string) => {
    if (!confirm('Remove this question from the quiz?')) return;
    try {
      await manualQuizService.deleteQuizQuestion(quizId, qId, token);
      await loadEditorData();
    } catch (err: any) {
      alert(`Failed to delete question: ${err.message}`);
    }
  };

  const handleMoveQuestion = async (index: number, direction: 'up' | 'down') => {
    if (!data) return;
    const questions = [...data.questions];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= questions.length) return;

    const [moved] = questions.splice(index, 1);
    questions.splice(targetIdx, 0, moved);

    const items = questions.map((q, idx) => ({
      id: q.id,
      question_order: idx + 1,
      section_id: q.section_id,
    }));

    try {
      await manualQuizService.reorderQuestions(quizId, items, token);
      await loadEditorData();
    } catch (err: any) {
      alert(`Failed to reorder: ${err.message}`);
    }
  };

  const handleChangeSection = async (questionId: string, newSectionId: string) => {
    try {
      await manualQuizService.updateQuizQuestion(
        quizId,
        questionId,
        { section_id: newSectionId || null },
        token
      );
      await loadEditorData();
    } catch (err: any) {
      alert(`Failed to move question: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading Manual Quiz Authoring Workspace...</p>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-6 rounded-2xl bg-surface-elevated border border-surface-border text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Failed to Open Quiz Creator</h3>
        <p className="text-xs text-slate-300">{errorMsg || 'Quiz not found.'}</p>
        <Link
          href={basePath}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white hover:bg-slate-700 font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Quizzes</span>
        </Link>
      </div>
    );
  }

  const filteredQuestions =
    selectedSectionFilter === 'all'
      ? data.questions
      : selectedSectionFilter === 'none'
      ? data.questions.filter((q) => !q.section_id)
      : data.questions.filter((q) => q.section_id === selectedSectionFilter);

  return (
    <div className="space-y-5 max-w-7xl mx-auto w-full pb-16">
      {/* Top Breadcrumb & Autosave Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-surface-border">
        <div className="flex items-center gap-2.5">
          <Link
            href={basePath}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
            title="Back to Quizzes"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-primary-500/10 text-primary-400 border border-primary-500/20">
                Manual Quiz Creator
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {data.quiz.reference_code || 'Draft'}
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-black text-white tracking-tight mt-0.5">
              {data.quiz.title}
            </h1>
          </div>
        </div>

        {/* Autosave and Preview Buttons */}
        <div className="flex items-center gap-3">
          <AutosaveIndicator
            status={autosaveStatus}
            draftVersion={data.quiz.draft_version}
            onManualSave={handleManualSaveDraft}
            hasUnsavedChanges={hasUnsavedChanges}
          />

          <button
            onClick={() => setIsPreviewOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 shadow-sm transition-colors"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Live Preview</span>
          </button>
        </div>
      </div>

      {/* 3-Panel Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Navigation Panel (Tabs) */}
        <div className="lg:col-span-3 space-y-2 bg-surface-elevated/40 border border-surface-border p-3 rounded-2xl">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 block mb-1">
            Authoring Workspace
          </span>

          {/* Tab 1: Quiz Details */}
          <button
            onClick={() => setActiveTab('details')}
            className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'details'
                ? 'bg-primary-600 text-white shadow-md'
                : 'text-slate-300 hover:bg-surface-elevated hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <FileText className="w-4 h-4" />
              <span>Quiz Details</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
          </button>

          {/* Tab 2: Sections */}
          <button
            onClick={() => setActiveTab('sections')}
            className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'sections'
                ? 'bg-primary-600 text-white shadow-md'
                : 'text-slate-300 hover:bg-surface-elevated hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Layers className="w-4 h-4" />
              <span>Sections ({data.sections.length})</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
          </button>

          {/* Tab 3: Questions List */}
          <button
            onClick={() => setActiveTab('questions')}
            className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'questions'
                ? 'bg-primary-600 text-white shadow-md'
                : 'text-slate-300 hover:bg-surface-elevated hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <HelpCircle className="w-4 h-4" />
              <span>Questions ({data.questions.length})</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
          </button>

          {/* Tab 4: Scoring & Rules */}
          <button
            onClick={() => setActiveTab('scoring')}
            className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'scoring'
                ? 'bg-primary-600 text-white shadow-md'
                : 'text-slate-300 hover:bg-surface-elevated hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Award className="w-4 h-4" />
              <span>Marks & Scoring</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
          </button>

          {/* Two Fast Addition Buttons */}
          <div className="pt-3 border-t border-surface-border/60 space-y-2">
            <button
              onClick={() => {
                setQuestionToEdit(null);
                setIsQuestionEditorOpen(true);
              }}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 border border-primary-500/30 text-xs font-semibold transition-colors shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Write Question (Method A)</span>
            </button>

            <button
              onClick={() => setIsQuestionBankPickerOpen(true)}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-colors shadow-sm"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Add From Bank (Method B)</span>
            </button>
          </div>
        </div>

        {/* Center Main Workspace */}
        <div className="lg:col-span-6 bg-surface-elevated rounded-2xl border border-surface-border p-5 min-h-[600px]">
          {activeTab === 'details' && (
            <QuizDetailsForm
              quiz={data.quiz}
              token={token}
              onSave={handleSaveDetails}
              isSaving={isSavingDetails}
            />
          )}

          {activeTab === 'sections' && (
            <SectionManager
              quizId={quizId}
              sections={data.sections}
              token={token}
              onRefresh={loadEditorData}
              activeSectionId={selectedSectionFilter === 'all' ? null : selectedSectionFilter}
              onSelectSection={(secId) => {
                setSelectedSectionFilter(secId || 'all');
                setActiveTab('questions');
              }}
            />
          )}

          {activeTab === 'questions' && (
            <div className="space-y-4">
              {/* Header with Section Filter & Add buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-white">Questions</h2>
                  {/* Filter by Section dropdown */}
                  {data.sections.length > 0 && (
                    <select
                      value={selectedSectionFilter}
                      onChange={(e) => setSelectedSectionFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-slate-900 border border-surface-border text-xs text-slate-300 focus:outline-none"
                    >
                      <option value="all">All Sections ({data.questions.length})</option>
                      {data.sections.map((sec) => (
                        <option key={sec.id} value={sec.id}>
                          {sec.title} (
                          {data.questions.filter((q) => q.section_id === sec.id).length})
                        </option>
                      ))}
                      <option value="none">
                        Unsectioned (
                        {data.questions.filter((q) => !q.section_id).length})
                      </option>
                    </select>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setQuestionToEdit(null);
                      setIsQuestionEditorOpen(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-sm transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>New Question</span>
                  </button>

                  <button
                    onClick={() => setIsQuestionBankPickerOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold shadow-sm transition-colors"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>From Bank</span>
                  </button>
                </div>
              </div>

              {/* Questions List */}
              {filteredQuestions.length === 0 ? (
                <div className="p-10 rounded-2xl border border-dashed border-surface-border text-center space-y-3 bg-slate-900/20">
                  <HelpCircle className="w-10 h-10 text-slate-600 mx-auto" />
                  <h3 className="text-sm font-semibold text-slate-300">
                    No Questions in this Section
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Write a question directly inside the quiz or add existing questions from the
                    shared Question Bank.
                  </p>
                  <div className="flex items-center justify-center gap-2 pt-2">
                    <button
                      onClick={() => {
                        setQuestionToEdit(null);
                        setIsQuestionEditorOpen(true);
                      }}
                      className="px-3.5 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
                    >
                      Write Question
                    </button>
                    <button
                      onClick={() => setIsQuestionBankPickerOpen(true)}
                      className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium border border-slate-700"
                    >
                      Add from Bank
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredQuestions.map((q, idx) => {
                    const snap = q.question_snapshot || ({} as any);
                    const sectionName = data.sections.find((s) => s.id === q.section_id)?.title;

                    return (
                      <div
                        key={q.id}
                        className="p-4 rounded-2xl bg-surface-elevated/70 border border-surface-border hover:border-slate-600 transition-all space-y-2.5"
                      >
                        {/* Header Badges */}
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-bold flex items-center justify-center shrink-0">
                              {idx + 1}
                            </span>

                            {/* Source Type Badge */}
                            <span
                              className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                                q.source_type === 'bank'
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                  : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                              }`}
                            >
                              {q.source_type === 'bank' ? 'Question Bank' : 'Manually Created'}
                            </span>

                            {/* Question Type */}
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                              {(snap.question_type || 'MCQ').replace('_', ' ')}
                            </span>

                            {/* Compulsory Badge */}
                            {q.is_compulsory ? (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                Compulsory
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                Optional
                              </span>
                            )}

                            {/* Marks */}
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-300 border border-slate-800">
                              +{q.marks}m{q.negative_marks > 0 ? ` (-${q.negative_marks})` : ''}
                            </span>
                          </div>

                          {/* Reordering & Actions */}
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => handleMoveQuestion(idx, 'up')}
                              disabled={idx === 0}
                              title="Move Up"
                              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                            >
                              <ChevronUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleMoveQuestion(idx, 'down')}
                              disabled={idx === filteredQuestions.length - 1}
                              title="Move Down"
                              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                            >
                              <ChevronDown className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                setQuestionToEdit(q);
                                setIsQuestionEditorOpen(true);
                              }}
                              title="Edit Question"
                              className="p-1 rounded text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteQuestion(q.id)}
                              title="Remove Question"
                              className="p-1 rounded text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        {/* Statement */}
                        <p className="text-xs text-white leading-relaxed line-clamp-3">
                          {snap.question_text}
                        </p>

                        {/* Section Assignment & Options Count */}
                        <div className="flex items-center justify-between pt-1 border-t border-surface-border/40 text-[11px] text-slate-400">
                          <div className="flex items-center gap-2">
                            <span>Section:</span>
                            <select
                              value={q.section_id || ''}
                              onChange={(e) => handleChangeSection(q.id, e.target.value)}
                              className="px-2 py-0.5 rounded bg-slate-900 border border-surface-border text-[11px] text-slate-200 focus:outline-none"
                            >
                              <option value="">None (Unsectioned)</option>
                              {data.sections.map((s) => (
                                <option key={s.id} value={s.id}>
                                  {s.title}
                                </option>
                              ))}
                            </select>
                          </div>

                          {snap.options && (
                            <span className="text-[10px] text-slate-500">
                              {snap.options.length} options
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'scoring' && (
            <MarksScoringPanel
              scoring={data.scoring_summary}
              passingMarks={data.quiz.passing_marks}
              durationMinutes={data.quiz.duration_minutes}
              onRunValidation={loadEditorData}
            />
          )}
        </div>

        {/* Right Inspector Panel */}
        <div className="lg:col-span-3 space-y-4">
          <MarksScoringPanel
            scoring={data.scoring_summary}
            passingMarks={data.quiz.passing_marks}
            durationMinutes={data.quiz.duration_minutes}
            onRunValidation={loadEditorData}
          />
        </div>
      </div>

      {/* Modals */}
      <QuestionEditorModal
        quizId={quizId}
        token={token}
        sections={data.sections}
        questionToEdit={questionToEdit}
        defaultSectionId={selectedSectionFilter === 'all' ? null : selectedSectionFilter}
        isOpen={isQuestionEditorOpen}
        onClose={() => {
          setIsQuestionEditorOpen(false);
          setQuestionToEdit(null);
        }}
        onSaved={loadEditorData}
      />

      <QuestionBankPickerModal
        quizId={quizId}
        token={token}
        sections={data.sections}
        existingQuizQuestions={data.questions}
        isOpen={isQuestionBankPickerOpen}
        onClose={() => setIsQuestionBankPickerOpen(false)}
        onAdded={loadEditorData}
      />

      <LivePaperPreviewModal
        quizId={quizId}
        token={token}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        canViewAnswerKey={canViewAnswerKey}
      />
    </div>
  );
}
