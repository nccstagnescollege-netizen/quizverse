'use client';

import React, { useState } from 'react';
import {
  X,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Upload,
  BookOpen,
  Save,
  Check,
} from 'lucide-react';
import {
  QuizQuestionItem,
  QuizSectionItem,
  manualQuizService,
} from '@/services/manualQuizService';

interface QuestionEditorModalProps {
  quizId: string;
  token: string;
  sections: QuizSectionItem[];
  questionToEdit: QuizQuestionItem | null;
  defaultSectionId?: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function QuestionEditorModal({
  quizId,
  token,
  sections,
  questionToEdit,
  defaultSectionId,
  isOpen,
  onClose,
  onSaved,
}: QuestionEditorModalProps) {
  if (!isOpen) return null;

  const isEditing = Boolean(questionToEdit);
  const snap = questionToEdit?.question_snapshot || ({} as any);

  // Form States
  const [questionText, setQuestionText] = useState(snap.question_text || '');
  const [title, setTitle] = useState(snap.title || '');
  const [questionType, setQuestionType] = useState<
    'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer'
  >(snap.question_type || 'single_choice');
  const [sectionId, setSectionId] = useState<string>(
    questionToEdit?.section_id || defaultSectionId || ''
  );
  const [marks, setMarks] = useState<number>(questionToEdit?.marks ?? 1.0);
  const [negativeMarks, setNegativeMarks] = useState<number>(
    questionToEdit?.negative_marks ?? 0.0
  );
  const [isCompulsory, setIsCompulsory] = useState<boolean>(
    questionToEdit?.is_compulsory ?? true
  );
  const [difficulty, setDifficulty] = useState<string>(snap.difficulty || 'medium');
  const [explanation, setExplanation] = useState<string>(snap.explanation || '');
  const [isMathematical, setIsMathematical] = useState<boolean>(
    snap.is_mathematical || false
  );

  // MCQ Options
  const [options, setOptions] = useState<
    Array<{ option_text: string; is_correct: boolean; explanation?: string; image_url?: string }>
  >(
    snap.options && snap.options.length > 0
      ? snap.options.map((o: any) => ({
          option_text: o.option_text || '',
          is_correct: Boolean(o.is_correct),
          explanation: o.explanation || '',
          image_url: o.image_url || '',
        }))
      : [
          { option_text: '', is_correct: true },
          { option_text: '', is_correct: false },
          { option_text: '', is_correct: false },
          { option_text: '', is_correct: false },
        ]
  );

  // Short Answer Config
  const [acceptedVariants, setAcceptedVariants] = useState<string[]>(
    snap.short_answer_config?.accepted_variants || ['']
  );
  const [caseSensitive, setCaseSensitive] = useState<boolean>(
    snap.short_answer_config?.case_sensitive || false
  );
  const [manualEvaluation, setManualEvaluation] = useState<boolean>(
    snap.short_answer_config?.manual_evaluation || false
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Option handlers
  const handleOptionChange = (idx: number, text: string) => {
    const next = [...options];
    next[idx].option_text = text;
    setOptions(next);
  };

  const handleCorrectRadio = (idx: number) => {
    const next = options.map((opt, i) => ({
      ...opt,
      is_correct: i === idx,
    }));
    setOptions(next);
  };

  const handleCorrectCheckbox = (idx: number) => {
    const next = [...options];
    next[idx].is_correct = !next[idx].is_correct;
    setOptions(next);
  };

  const addOption = () => {
    setOptions([...options, { option_text: '', is_correct: false }]);
  };

  const removeOption = (idx: number) => {
    if (options.length <= 2) return;
    setOptions(options.filter((_, i) => i !== idx));
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim()) {
      setErrorMsg('Question statement text is required.');
      return;
    }

    // Validation per type
    if (questionType === 'single_choice') {
      const filled = options.filter((o) => o.option_text.trim());
      if (filled.length < 2) {
        setErrorMsg('Single choice questions require at least 2 non-empty options.');
        return;
      }
      const correctCount = filled.filter((o) => o.is_correct).length;
      if (correctCount !== 1) {
        setErrorMsg('Single choice questions must have exactly 1 correct answer selected.');
        return;
      }
    } else if (questionType === 'multiple_choice') {
      const filled = options.filter((o) => o.option_text.trim());
      if (filled.length < 2) {
        setErrorMsg('Multiple choice questions require at least 2 non-empty options.');
        return;
      }
      const correctCount = filled.filter((o) => o.is_correct).length;
      if (correctCount < 1) {
        setErrorMsg('Multiple choice questions must have at least 1 correct answer selected.');
        return;
      }
    } else if (questionType === 'true_false') {
      const hasCorrect = options.some((o) => o.is_correct);
      if (!hasCorrect) {
        setErrorMsg('Please select whether True or False is the correct answer.');
        return;
      }
    } else if (questionType === 'short_answer') {
      const validVariants = acceptedVariants.filter((v) => v.trim());
      if (!manualEvaluation && validVariants.length === 0) {
        setErrorMsg('Please provide at least one accepted answer variant or enable manual evaluation.');
        return;
      }
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      let finalOptions = options;
      if (questionType === 'true_false') {
        finalOptions = [
          { option_text: 'True', is_correct: options[0]?.is_correct ?? true },
          { option_text: 'False', is_correct: options[1]?.is_correct ?? false },
        ];
      }

      if (isEditing && questionToEdit) {
        // Update Quiz Question
        await manualQuizService.updateQuizQuestion(
          quizId,
          questionToEdit.id,
          {
            section_id: sectionId || null,
            marks: Number(marks),
            negative_marks: Number(negativeMarks),
            is_compulsory: isCompulsory,
            question_snapshot: {
              ...snap,
              title: title.trim() || undefined,
              question_text: questionText.trim(),
              question_type: questionType,
              difficulty,
              marks: Number(marks),
              negative_marks: Number(negativeMarks),
              explanation: explanation.trim() || null,
              is_mathematical: isMathematical,
              options: finalOptions,
              short_answer_config:
                questionType === 'short_answer'
                  ? {
                      accepted_variants: acceptedVariants.filter((v) => v.trim()),
                      case_sensitive: caseSensitive,
                      manual_evaluation: manualEvaluation,
                    }
                  : undefined,
            },
          },
          token
        );
      } else {
        // Create new manual question
        await manualQuizService.addManualQuestion(
          quizId,
          {
            question_text: questionText.trim(),
            question_type: questionType,
            section_id: sectionId || null,
            title: title.trim() || undefined,
            difficulty,
            marks: Number(marks),
            negative_marks: Number(negativeMarks),
            is_compulsory: isCompulsory,
            explanation: explanation.trim() || undefined,
            is_mathematical: isMathematical,
            options: finalOptions,
            short_answer_config:
              questionType === 'short_answer'
                ? {
                    accepted_variants: acceptedVariants.filter((v) => v.trim()),
                    case_sensitive: caseSensitive,
                    manual_evaluation: manualEvaluation,
                  }
                : undefined,
          },
          token
        );
      }

      onSaved();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save question.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Promote to Question Bank action
  const handlePromoteToBank = async () => {
    if (!questionToEdit) return;
    if (
      !confirm(
        'Save this question into the platform-wide Question Bank? Authorized administrators will be able to reuse it in future exams.'
      )
    )
      return;

    try {
      const res = await manualQuizService.saveToQuestionBank(quizId, questionToEdit.id, undefined, token);
      alert(res.message || 'Question saved to Question Bank successfully.');
      onSaved();
    } catch (err: any) {
      alert(`Failed to save to Question Bank: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-surface-elevated border border-surface-border rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-auto animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-primary-600/20 text-primary-400 border border-primary-500/30 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5" />
            </span>
            <h3 className="text-sm font-bold text-white">
              {isEditing ? 'Edit Question' : 'Create New Question (Method A)'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-5 overflow-y-auto flex-1">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Section & Type & Difficulty Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Target Section */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300">Assign Section</label>
              <select
                value={sectionId}
                onChange={(e) => setSectionId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
              >
                <option value="">-- No Section (General) --</option>
                {sections.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Question Type */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300">Question Type</label>
              <select
                value={questionType}
                onChange={(e) => setQuestionType(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 font-medium"
              >
                <option value="single_choice">Single Choice (1 Correct)</option>
                <option value="multiple_choice">Multiple Choice (Multiple Correct)</option>
                <option value="true_false">True / False</option>
                <option value="short_answer">Short Answer / Fill-in</option>
              </select>
            </div>

            {/* Difficulty */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          {/* Title (Optional) */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Question Title (Optional)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Asymptotic Time Complexity Analysis"
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          {/* Question Statement */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300">
                Question Statement <span className="text-rose-400">*</span>
              </label>
              <label className="flex items-center gap-1.5 text-[11px] text-purple-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isMathematical}
                  onChange={(e) => setIsMathematical(e.target.checked)}
                  className="rounded text-purple-600 border-slate-700 bg-slate-800"
                />
                <span>LaTeX Math Equation ($...$)</span>
              </label>
            </div>
            <textarea
              rows={3}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="Type your question statement here... Supports markdown and KaTeX equations like $O(N \log N)$ or $\sum_{i=1}^n i$."
              className="w-full p-3 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 font-mono"
              required
            />
          </div>

          {/* Options Section for MCQ & Multiple Choice */}
          {(questionType === 'single_choice' || questionType === 'multiple_choice') && (
            <div className="p-4 rounded-2xl bg-slate-900/40 border border-surface-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Options & Correct Answer
                </span>
                <span className="text-[11px] text-slate-500">
                  {questionType === 'single_choice'
                    ? 'Select the radio button for the single correct answer'
                    : 'Check all answers that are correct'}
                </span>
              </div>

              <div className="space-y-2.5">
                {options.map((opt, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {/* Correct Selector */}
                    {questionType === 'single_choice' ? (
                      <input
                        type="radio"
                        name="correct_option"
                        checked={opt.is_correct}
                        onChange={() => handleCorrectRadio(idx)}
                        className="w-4 h-4 text-emerald-500 border-slate-700 bg-slate-800 cursor-pointer"
                        title="Mark as correct answer"
                      />
                    ) : (
                      <input
                        type="checkbox"
                        checked={opt.is_correct}
                        onChange={() => handleCorrectCheckbox(idx)}
                        className="w-4 h-4 rounded text-emerald-500 border-slate-700 bg-slate-800 cursor-pointer"
                        title="Mark as correct answer"
                      />
                    )}

                    {/* Option Text */}
                    <input
                      type="text"
                      value={opt.option_text}
                      onChange={(e) => handleOptionChange(idx, e.target.value)}
                      placeholder={`Option ${String.fromCharCode(65 + idx)}`}
                      className={`flex-1 px-3 py-2 rounded-xl text-xs text-white border transition-colors ${
                        opt.is_correct
                          ? 'bg-emerald-950/20 border-emerald-500/40 focus:border-emerald-400'
                          : 'bg-slate-900 border-surface-border focus:border-primary-500'
                      }`}
                    />

                    {/* Delete Option */}
                    <button
                      type="button"
                      onClick={() => removeOption(idx)}
                      disabled={options.length <= 2}
                      className="p-1.5 text-slate-500 hover:text-rose-400 disabled:opacity-30 transition-colors"
                      title="Remove option"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {options.length < 8 && (
                <button
                  type="button"
                  onClick={addOption}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-300"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Another Option</span>
                </button>
              )}
            </div>
          )}

          {/* True / False Selector */}
          {questionType === 'true_false' && (
            <div className="p-4 rounded-2xl bg-slate-900/40 border border-surface-border space-y-3">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Select Correct Statement Evaluation
              </span>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setOptions([
                      { option_text: 'True', is_correct: true },
                      { option_text: 'False', is_correct: false },
                    ]);
                  }}
                  className={`p-3 rounded-xl border text-center font-bold text-xs transition-all ${
                    options[0]?.is_correct
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 ring-1 ring-emerald-500/30'
                      : 'bg-slate-900 border-surface-border text-slate-400 hover:text-white'
                  }`}
                >
                  TRUE
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOptions([
                      { option_text: 'True', is_correct: false },
                      { option_text: 'False', is_correct: true },
                    ]);
                  }}
                  className={`p-3 rounded-xl border text-center font-bold text-xs transition-all ${
                    options[1]?.is_correct
                      ? 'bg-rose-500/20 border-rose-500/50 text-rose-300 ring-1 ring-rose-500/30'
                      : 'bg-slate-900 border-surface-border text-slate-400 hover:text-white'
                  }`}
                >
                  FALSE
                </button>
              </div>
            </div>
          )}

          {/* Short Answer Config */}
          {questionType === 'short_answer' && (
            <div className="p-4 rounded-2xl bg-slate-900/40 border border-surface-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Accepted Answer Variants
                </span>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={caseSensitive}
                    onChange={(e) => setCaseSensitive(e.target.checked)}
                    className="rounded text-primary-600 border-slate-700 bg-slate-800"
                  />
                  <span>Case Sensitive</span>
                </label>
              </div>

              <div className="space-y-2">
                {acceptedVariants.map((variant, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={variant}
                      onChange={(e) => {
                        const next = [...acceptedVariants];
                        next[idx] = e.target.value;
                        setAcceptedVariants(next);
                      }}
                      placeholder={`Accepted variant ${idx + 1}`}
                      className="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                    />
                    <button
                      type="button"
                      onClick={() => setAcceptedVariants(acceptedVariants.filter((_, i) => i !== idx))}
                      disabled={acceptedVariants.length <= 1}
                      className="p-1.5 text-slate-500 hover:text-rose-400 disabled:opacity-30"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => setAcceptedVariants([...acceptedVariants, ''])}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-300"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Another Accepted Variant</span>
                </button>

                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={manualEvaluation}
                    onChange={(e) => setManualEvaluation(e.target.checked)}
                    className="rounded text-amber-500 border-slate-700 bg-slate-800"
                  />
                  <span>Requires Manual Human Evaluation</span>
                </label>
              </div>
            </div>
          )}

          {/* Marks, Negative Marks & Compulsory Toggle */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-2xl bg-surface-elevated/40 border border-surface-border">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Marks</label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                value={marks}
                onChange={(e) => setMarks(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Negative Marks</label>
              <input
                type="number"
                step="0.25"
                min="0"
                value={negativeMarks}
                onChange={(e) => setNegativeMarks(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
              />
            </div>
            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isCompulsory}
                  onChange={(e) => setIsCompulsory(e.target.checked)}
                  className="w-4 h-4 rounded text-primary-600 border-slate-700 bg-slate-800"
                />
                <span>Compulsory Question</span>
              </label>
            </div>
          </div>

          {/* Explanation / Rationale */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">
              Explanation & Rationale (Strictly protected in student preview)
            </label>
            <textarea
              rows={2}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Step-by-step mathematical derivation or rationale for the correct answer..."
              className="w-full p-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>
        </form>

        {/* Footer Actions */}
        <div className="flex items-center justify-between p-4 border-t border-surface-border bg-slate-900/60 shrink-0">
          <div>
            {isEditing && questionToEdit?.is_manual && (
              <button
                type="button"
                onClick={handlePromoteToBank}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-semibold transition-colors"
                title="Promote this quiz-specific question to the shared Question Bank"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Save to Question Bank</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : isEditing ? 'Update Question' : 'Add to Quiz'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
