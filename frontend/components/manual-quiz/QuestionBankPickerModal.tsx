'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Filter,
  Plus,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BookOpen,
  Sparkles,
  Eye,
  Check,
} from 'lucide-react';
import {
  QuestionListItem,
  questionBankService,
} from '@/services/questionBankService';
import {
  QuizSectionItem,
  QuizQuestionItem,
  manualQuizService,
} from '@/services/manualQuizService';

interface QuestionBankPickerModalProps {
  quizId: string;
  token: string;
  sections: QuizSectionItem[];
  existingQuizQuestions: QuizQuestionItem[];
  isOpen: boolean;
  onClose: () => void;
  onAdded: () => void;
}

export function QuestionBankPickerModal({
  quizId,
  token,
  sections,
  existingQuizQuestions,
  isOpen,
  onClose,
  onAdded,
}: QuestionBankPickerModalProps) {
  if (!isOpen) return null;

  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [difficulty, setDifficulty] = useState('all');
  const [questionType, setQuestionType] = useState('all');

  // Selected for import
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [targetSectionId, setTargetSectionId] = useState<string>('');
  const [overrideMarks, setOverrideMarks] = useState<string>('');
  const [overrideNegativeMarks, setOverrideNegativeMarks] = useState<string>('');
  const [isCompulsory, setIsCompulsory] = useState<boolean>(true);
  const [isImporting, setIsImporting] = useState<boolean>(false);

  // Preview single item
  const [previewItem, setPreviewItem] = useState<QuestionListItem | null>(null);

  // Existing Question IDs in this quiz to prevent duplicates
  const existingBankIds = new Set(
    existingQuizQuestions
      .map((q) => q.question_id)
      .filter((id): id is string => Boolean(id))
  );

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    const filterParams: Record<string, string> = { status: 'approved' };
    if (search.trim()) filterParams.search = search.trim();
    if (difficulty !== 'all') filterParams.difficulty = difficulty;
    if (questionType !== 'all') filterParams.question_type = questionType;

    questionBankService
      .getQuestions(filterParams as any, token)
      .then((data) => {
        if (isMounted) {
          setQuestions(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to load Question Bank.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [token, search, difficulty, questionType]);

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleSelectAll = () => {
    const available = questions.filter((q) => !existingBankIds.has(q.id));
    if (selectedIds.size === available.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(available.map((q) => q.id)));
    }
  };

  const handleImport = async () => {
    if (selectedIds.size === 0) return;
    setIsImporting(true);
    setErrorMsg(null);

    try {
      await manualQuizService.addFromQuestionBank(
        quizId,
        {
          question_ids: Array.from(selectedIds),
          section_id: targetSectionId || null,
          default_marks: overrideMarks ? Number(overrideMarks) : undefined,
          default_negative_marks: overrideNegativeMarks ? Number(overrideNegativeMarks) : undefined,
          is_compulsory: isCompulsory,
        },
        token
      );
      onAdded();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to add questions from Question Bank.');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-surface-elevated border border-surface-border rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-auto animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center">
              <BookOpen className="w-3.5 h-3.5" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-white">Select from Question Bank (Method B)</h3>
              <p className="text-[11px] text-slate-400">
                Choose approved questions from your institution’s central question repository.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter Toolbar */}
        <div className="p-3 border-b border-surface-border/60 bg-slate-900/40 grid grid-cols-1 sm:grid-cols-4 gap-2.5 shrink-0">
          {/* Search */}
          <div className="sm:col-span-2 relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search question statement or title..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          {/* Type Filter */}
          <select
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value)}
            className="px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
          >
            <option value="all">All Question Types</option>
            <option value="single_choice">Single Choice</option>
            <option value="multiple_choice">Multiple Choice</option>
            <option value="true_false">True / False</option>
            <option value="short_answer">Short Answer</option>
          </select>

          {/* Difficulty Filter */}
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
          >
            <option value="all">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        {/* Question List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="text-center py-12 text-xs text-slate-400 space-y-2">
              <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Searching eligible Question Bank records...</p>
            </div>
          ) : questions.length === 0 ? (
            <div className="text-center py-12 text-xs text-slate-400">
              No approved questions found matching current criteria.
            </div>
          ) : (
            questions.map((q) => {
              const isAlreadyAdded = existingBankIds.has(q.id);
              const isSelected = selectedIds.has(q.id);

              return (
                <div
                  key={q.id}
                  onClick={() => {
                    if (!isAlreadyAdded) toggleSelect(q.id);
                  }}
                  className={`p-3.5 rounded-xl border transition-all flex items-start gap-3 ${
                    isAlreadyAdded
                      ? 'bg-slate-950/40 border-slate-800 opacity-60 cursor-not-allowed'
                      : isSelected
                      ? 'bg-primary-950/20 border-primary-500/50 cursor-pointer shadow-sm'
                      : 'bg-surface-elevated/80 border-surface-border hover:border-slate-600 cursor-pointer'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isAlreadyAdded}
                    onChange={() => {}}
                    className="mt-0.5 rounded text-primary-600 border-slate-700 bg-slate-800"
                  />

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-200 border border-slate-700 uppercase">
                        {q.question_type.replace('_', ' ')}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                          q.difficulty === 'easy'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : q.difficulty === 'medium'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}
                      >
                        {q.difficulty.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        +{q.default_marks}m
                      </span>

                      {isAlreadyAdded && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-amber-400 border border-amber-500/30">
                          Already in quiz
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-200 line-clamp-2">{q.question_text}</p>

                    {q.subject_name && (
                      <p className="text-[10px] text-slate-400 truncate">
                        {q.subject_name} {q.unit_name ? `› ${q.unit_name}` : ''}
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewItem(q);
                    }}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 shrink-0"
                    title="Preview Question"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Import Configuration & Submit Footer */}
        <div className="p-4 border-t border-surface-border bg-slate-900/80 shrink-0 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
            {/* Target Section */}
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                Assign to Section
              </label>
              <select
                value={targetSectionId}
                onChange={(e) => setTargetSectionId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none"
              >
                <option value="">-- General (No section) --</option>
                {sections.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Override Marks */}
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                Marks (Override)
              </label>
              <input
                type="number"
                step="0.5"
                placeholder="Default"
                value={overrideMarks}
                onChange={(e) => setOverrideMarks(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none"
              />
            </div>

            {/* Override Negative Marks */}
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                Negative Marks
              </label>
              <input
                type="number"
                step="0.25"
                placeholder="Default"
                value={overrideNegativeMarks}
                onChange={(e) => setOverrideNegativeMarks(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none"
              />
            </div>

            {/* Compulsory Toggle */}
            <div className="flex items-center pt-4">
              <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isCompulsory}
                  onChange={(e) => setIsCompulsory(e.target.checked)}
                  className="rounded text-primary-600 border-slate-700 bg-slate-800"
                />
                <span>Compulsory</span>
              </label>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-surface-border/40">
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              Select / Deselect Available
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleImport}
                disabled={selectedIds.size === 0 || isImporting}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md disabled:opacity-40"
              >
                <Plus className="w-4 h-4" />
                <span>
                  {isImporting
                    ? 'Adding Questions...'
                    : `Add Selected (${selectedIds.size}) to Quiz`}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
