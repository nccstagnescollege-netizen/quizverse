'use client';

import React, { useState } from 'react';
import {
  Layers,
  Plus,
  Trash2,
  Edit2,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  HelpCircle,
  Settings2,
  ListOrdered,
  X,
} from 'lucide-react';
import { QuizSectionItem, manualQuizService } from '@/services/manualQuizService';

interface SectionManagerProps {
  quizId: string;
  sections: QuizSectionItem[];
  token: string;
  onRefresh: () => void;
  activeSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
}

export function SectionManager({
  quizId,
  sections,
  token,
  onRefresh,
  activeSectionId,
  onSelectSection,
}: SectionManagerProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<QuizSectionItem | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [selectionRule, setSelectionRule] = useState<'all_compulsory' | 'all_optional' | 'answer_n_of_m'>('all_compulsory');
  const [requiredCount, setRequiredCount] = useState<number>(1);
  const [defaultMarks, setDefaultMarks] = useState<number>(1.0);
  const [defaultNegativeMarks, setDefaultNegativeMarks] = useState<number>(0.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const openCreateModal = () => {
    setEditingSection(null);
    setTitle(`PART ${String.fromCharCode(65 + sections.length)}`);
    setDescription('');
    setInstructions('');
    setSelectionRule('all_compulsory');
    setRequiredCount(1);
    setDefaultMarks(1.0);
    setDefaultNegativeMarks(0.0);
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const openEditModal = (sec: QuizSectionItem) => {
    setEditingSection(sec);
    setTitle(sec.title);
    setDescription(sec.description || '');
    setInstructions(sec.instructions || '');
    setSelectionRule(sec.selection_rule);
    setRequiredCount(sec.required_question_count || 1);
    setDefaultMarks(sec.default_marks_per_question);
    setDefaultNegativeMarks(sec.default_negative_marks_per_question);
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      if (editingSection) {
        await manualQuizService.updateSection(
          quizId,
          editingSection.id,
          {
            title: title.trim(),
            description: description.trim() || undefined,
            instructions: instructions.trim() || undefined,
            selection_rule: selectionRule,
            required_question_count: selectionRule === 'answer_n_of_m' ? requiredCount : 0,
            default_marks_per_question: defaultMarks,
            default_negative_marks_per_question: defaultNegativeMarks,
          },
          token
        );
      } else {
        await manualQuizService.createSection(
          quizId,
          {
            title: title.trim(),
            description: description.trim() || undefined,
            instructions: instructions.trim() || undefined,
            selection_rule: selectionRule,
            required_question_count: selectionRule === 'answer_n_of_m' ? requiredCount : 0,
            default_marks_per_question: defaultMarks,
            default_negative_marks_per_question: defaultNegativeMarks,
          },
          token
        );
      }
      setIsModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save section.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (secId: string) => {
    if (!confirm('Are you sure you want to delete this section? Questions inside will become unsectioned.')) return;
    try {
      await manualQuizService.deleteSection(quizId, secId, token);
      if (activeSectionId === secId) onSelectSection(null);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to delete section: ${err.message}`);
    }
  };

  const handleMove = async (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= sections.length) return;

    const newSections = [...sections];
    const [moved] = newSections.splice(index, 1);
    newSections.splice(targetIndex, 0, moved);

    const items = newSections.map((s, idx) => ({ id: s.id, section_order: idx + 1 }));
    try {
      await manualQuizService.reorderSections(quizId, items, token);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to reorder sections: ${err.message}`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-3 border-b border-surface-border">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-primary-400" />
            <span>Sections & Parts ({sections.length})</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Organize examination into distinct parts with independent selection rules (e.g. Answer any 4 of 6).
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add Section</span>
        </button>
      </div>

      {/* Sections List */}
      {sections.length === 0 ? (
        <div className="p-8 rounded-2xl border border-dashed border-surface-border text-center space-y-3 bg-surface-elevated/30">
          <Layers className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Sections Configured</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            You can create sections (e.g., PART A - Objective, PART B - Long Essay) to configure selection rules and marks.
          </p>
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium border border-slate-700"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create First Section</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {sections.map((sec, idx) => {
            const isSelected = activeSectionId === sec.id;
            return (
              <div
                key={sec.id}
                className={`p-4 rounded-2xl border transition-all ${
                  isSelected
                    ? 'bg-primary-950/20 border-primary-500/50 shadow-md ring-1 ring-primary-500/30'
                    : 'bg-surface-elevated border-surface-border hover:border-slate-600'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-[11px] font-bold flex items-center justify-center shrink-0">
                        {idx + 1}
                      </span>
                      <h3 className="text-sm font-bold text-white truncate">{sec.title}</h3>

                      {/* Rule Badge */}
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                          sec.selection_rule === 'all_compulsory'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : sec.selection_rule === 'answer_n_of_m'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                        }`}
                      >
                        {sec.selection_rule === 'all_compulsory'
                          ? 'ALL COMPULSORY'
                          : sec.selection_rule === 'answer_n_of_m'
                          ? `ANSWER ANY ${sec.required_question_count} OF ${sec.total_questions_count}`
                          : 'ALL OPTIONAL'}
                      </span>
                    </div>

                    {sec.description && (
                      <p className="text-xs text-slate-300 line-clamp-1">{sec.description}</p>
                    )}

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1">
                      <span>
                        <strong className="text-slate-200">{sec.total_questions_count}</strong> questions
                      </span>
                      <span>•</span>
                      <span>
                        <strong className="text-slate-200">+{sec.default_marks_per_question}m</strong> per question
                      </span>
                      {sec.default_negative_marks_per_question > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-rose-400">-{sec.default_negative_marks_per_question} negative</span>
                        </>
                      )}
                      <span>•</span>
                      <span>
                        Total Marks: <strong className="text-emerald-400">{sec.section_total_marks}m</strong>
                      </span>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleMove(idx, 'up')}
                      disabled={idx === 0}
                      title="Move Up"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                    >
                      <ChevronUp className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleMove(idx, 'down')}
                      disabled={idx === sections.length - 1}
                      title="Move Down"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                    >
                      <ChevronDown className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => openEditModal(sec)}
                      title="Edit Section"
                      className="p-1.5 rounded-lg text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(sec.id)}
                      title="Delete Section"
                      className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Create or Edit Section */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-elevated border border-surface-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between p-4 border-b border-surface-border bg-slate-900/60">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary-400" />
                <span>{editingSection ? 'Edit Section' : 'Create New Section'}</span>
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              {errorMsg && (
                <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs">
                  {errorMsg}
                </div>
              )}

              {/* Title */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">
                  Section Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. PART A: Multiple Choice Questions"
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
                  required
                />
              </div>

              {/* Selection Rule */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Candidate Selection Rule</label>
                <select
                  value={selectionRule}
                  onChange={(e) => setSelectionRule(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="all_compulsory">All Compulsory (Candidate must answer all questions)</option>
                  <option value="answer_n_of_m">Answer N of M (e.g. Answer any 4 of 6 questions)</option>
                  <option value="all_optional">All Optional (Candidate chooses zero or more)</option>
                </select>
              </div>

              {/* Required Count for Answer N of M */}
              {selectionRule === 'answer_n_of_m' && (
                <div className="space-y-1 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
                  <label className="text-xs font-semibold text-amber-300">
                    Required Question Count (N)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={requiredCount}
                    onChange={(e) => setRequiredCount(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-amber-500/30 text-xs text-white focus:outline-none"
                    required
                  />
                  <p className="text-[10px] text-amber-200/80">
                    Candidates must answer this many questions to obtain full obtainable section marks.
                  </p>
                </div>
              )}

              {/* Default Marks & Negative Marks */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Marks per Question</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    value={defaultMarks}
                    onChange={(e) => setDefaultMarks(Number(e.target.value))}
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
                    value={defaultNegativeMarks}
                    onChange={(e) => setDefaultNegativeMarks(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>

              {/* Instructions */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Specific Section Instructions</label>
                <textarea
                  rows={2}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Answer any four questions. All questions carry equal marks."
                  className="w-full p-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : editingSection ? 'Update Section' : 'Create Section'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
