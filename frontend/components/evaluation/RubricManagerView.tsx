'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Search,
  BookOpen,
  Award,
  Layers,
  X,
  Check,
} from 'lucide-react';
import {
  evaluationService,
  GradingRubric,
  GradingCriterion,
} from '@/services/evaluationService';

export default function RubricManagerView() {
  const [token, setToken] = useState<string | null>(null);
  const [rubrics, setRubrics] = useState<GradingRubric[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Create / Edit Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [totalMaxMarks, setTotalMaxMarks] = useState<number>(10);
  const [gradingInstructions, setGradingInstructions] = useState('');
  const [criteria, setCriteria] = useState<GradingCriterion[]>([
    { title: 'Criterion 1: Core Concept', description: 'Accurate definition and identification', max_marks: 5 },
    { title: 'Criterion 2: Technical Rigor', description: 'Logical steps and clear calculation', max_marks: 5 },
  ]);

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  useEffect(() => {
    const stored =
      localStorage.getItem('token') ||
      localStorage.getItem('admin_token') ||
      localStorage.getItem('access_token');
    setToken(stored);
  }, []);

  const loadRubrics = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await evaluationService.listRubrics(token, undefined, search || undefined);
      setRubrics(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch rubrics');
    } finally {
      setLoading(false);
    }
  }, [token, search]);

  useEffect(() => {
    if (token) loadRubrics();
  }, [token, loadRubrics]);

  const handleAddCriterion = () => {
    setCriteria((prev) => [
      ...prev,
      { title: `Criterion ${prev.length + 1}`, description: '', max_marks: 2 },
    ]);
  };

  const handleRemoveCriterion = (idx: number) => {
    setCriteria((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpdateCriterion = (idx: number, field: keyof GradingCriterion, value: any) => {
    setCriteria((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c))
    );
  };

  const criteriaSum = criteria.reduce((acc, c) => acc + (Number(c.max_marks) || 0), 0);

  const handleCreateRubric = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (Math.abs(criteriaSum - totalMaxMarks) > 0.001) {
      alert(`The sum of criterion max marks (${criteriaSum}) must equal the rubric total max marks (${totalMaxMarks}).`);
      return;
    }

    try {
      setSaving(true);
      await evaluationService.createRubric(token, {
        title,
        description,
        total_max_marks: totalMaxMarks,
        applicable_question_types: ['descriptive', 'short_answer'],
        status: 'active',
        grading_instructions: gradingInstructions || undefined,
        criteria: criteria.map((c, idx) => ({
          title: c.title,
          description: c.description,
          max_marks: Number(c.max_marks),
          criterion_order: idx + 1,
        })),
      });

      setIsModalOpen(false);
      setSaveSuccess('Grading rubric published successfully!');
      setTimeout(() => setSaveSuccess(null), 3000);
      await loadRubrics();
    } catch (err: any) {
      alert(err.message || 'Failed to create rubric');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl border border-surface-border p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-primary-500" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Grading Rubric Designer</h1>
              <p className="text-xs text-slate-400 mt-1">
                Author standardized multi-criterion evaluation rubrics with version history and partial-credit tiers.
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-primary-900/30"
          >
            <Plus className="w-4 h-4" />
            <span>Create Rubric</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{saveSuccess}</span>
        </div>
      )}

      {/* Search Toolbar */}
      <div className="glass-card rounded-2xl border border-surface-border p-4 shadow-lg flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rubrics by title or subject..."
            className="w-full bg-slate-900 border border-surface-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>

      {/* Rubrics Grid */}
      {loading ? (
        <div className="glass-card rounded-2xl border border-surface-border p-12 text-center text-slate-400 space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-primary-500/20 border-t-primary-500 animate-spin mx-auto" />
          <p className="text-xs">Loading rubric catalog...</p>
        </div>
      ) : rubrics.length === 0 ? (
        <div className="glass-card rounded-2xl border border-surface-border p-12 text-center text-slate-500 space-y-2">
          <BookOpen className="w-10 h-10 mx-auto opacity-30 text-slate-400" />
          <p className="text-sm font-semibold text-slate-400">No Rubrics Defined</p>
          <p className="text-xs text-slate-500">Create your first rubric to standardize manual evaluation.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rubrics.map((r) => (
            <div
              key={r.id}
              className="glass-card rounded-2xl border border-surface-border p-5 shadow-xl space-y-4 hover:border-surface-border/80 transition-all flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-[10px] text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                    Version {r.version}
                  </span>
                  <span className="font-mono font-bold text-white text-xs">
                    {r.total_max_marks} Total Marks
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">{r.title}</h3>
                {r.description && <p className="text-xs text-slate-400 line-clamp-2">{r.description}</p>}
              </div>

              {/* Criteria Pills */}
              <div className="space-y-1.5 pt-2 border-t border-surface-border">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Criteria Breakdown ({r.criteria.length})
                </span>
                <div className="space-y-1">
                  {r.criteria.map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-[11px] text-slate-300">
                      <span className="truncate pr-2">• {c.title}</span>
                      <span className="font-mono text-cyan-400 shrink-0">{c.max_marks} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Rubric Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <form
            onSubmit={handleCreateRubric}
            className="max-w-2xl w-full glass-card rounded-2xl border border-surface-border shadow-2xl p-6 space-y-4 my-8 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h2 className="text-base font-bold text-white">Design New Grading Rubric</h2>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2 space-y-1">
                <label className="text-xs font-semibold text-slate-300">Rubric Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Master Theorem Analytical Rubric"
                  className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Total Max Marks</label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  required
                  value={totalMaxMarks}
                  onChange={(e) => setTotalMaxMarks(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-white font-mono font-bold focus:outline-none focus:border-primary-500"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Scope and purpose of this rubric..."
                className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Grading Instructions for Evaluator</label>
              <textarea
                rows={2}
                value={gradingInstructions}
                onChange={(e) => setGradingInstructions(e.target.value)}
                placeholder="Instructions on key points, penalties, or partial credit rules..."
                className="w-full bg-slate-900 border border-surface-border rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            {/* Criteria Builder */}
            <div className="space-y-3 pt-2 border-t border-surface-border">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white uppercase tracking-wider">Evaluation Criteria</span>
                  <span
                    className={`ml-2 text-xs font-mono font-semibold ${
                      Math.abs(criteriaSum - totalMaxMarks) < 0.001 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    Sum: {criteriaSum} / {totalMaxMarks} pts
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleAddCriterion}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Criterion</span>
                </button>
              </div>

              <div className="space-y-2">
                {criteria.map((crit, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-900/80 border border-surface-border space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        required
                        value={crit.title}
                        onChange={(e) => handleUpdateCriterion(idx, 'title', e.target.value)}
                        placeholder="Criterion title..."
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                      />
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        required
                        value={crit.max_marks}
                        onChange={(e) => handleUpdateCriterion(idx, 'max_marks', parseFloat(e.target.value) || 0)}
                        className="w-20 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-white font-mono text-center"
                      />
                      {criteria.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveCriterion(idx)}
                          className="p-1.5 text-slate-500 hover:text-rose-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      value={crit.description || ''}
                      onChange={(e) => handleUpdateCriterion(idx, 'description', e.target.value)}
                      placeholder="Expected answer characteristics for full marks..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-[11px] text-slate-400"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-surface-border flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || Math.abs(criteriaSum - totalMaxMarks) > 0.001}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white font-bold disabled:opacity-40"
              >
                Save Rubric
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
