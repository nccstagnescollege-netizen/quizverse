'use client';

import React, { useState, useEffect } from 'react';
import {
  ReplacementCandidateItem,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import {
  X,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertCircle,
  FileQuestion,
  Filter,
} from 'lucide-react';

interface QuestionReplacementModalProps {
  generationId: string;
  targetQuestionId: string;
  targetQuestionText: string;
  isOpen: boolean;
  onClose: () => void;
  onQuestionReplaced: () => void;
}

export function QuestionReplacementModal({
  generationId,
  targetQuestionId,
  targetQuestionText,
  isOpen,
  onClose,
  onQuestionReplaced,
}: QuestionReplacementModalProps) {
  const [candidates, setCandidates] = useState<ReplacementCandidateItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [replacing, setReplacing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [matchDifficulty, setMatchDifficulty] = useState<boolean>(true);
  const [matchType, setMatchType] = useState<boolean>(true);
  const [matchTopic, setMatchTopic] = useState<boolean>(false);

  const loadCandidates = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await quizGeneratorService.getReplacementCandidates(generationId, targetQuestionId, {
        matchDifficulty,
        matchType,
        matchTopic,
      });
      setCandidates(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load replacement candidates.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadCandidates();
    }
  }, [isOpen, matchDifficulty, matchType, matchTopic]);

  const handleSelectReplacement = async (candidateId: string) => {
    setReplacing(true);
    setErrorMsg(null);
    try {
      await quizGeneratorService.replaceQuestion(generationId, targetQuestionId, candidateId);
      onQuestionReplaced();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to replace question.');
    } finally {
      setReplacing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-surface-elevated border border-surface-border rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-surface-border flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-primary-400" />
              <span>Replace Question with Alternative</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-md">
              Replacing: &quot;{targetQuestionText}&quot;
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter Toolbar */}
        <div className="p-3 bg-slate-900/60 border-b border-surface-border/60 flex items-center gap-4 flex-wrap text-xs text-slate-300">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Constraints:</span>
          </span>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={matchDifficulty}
              onChange={(e) => setMatchDifficulty(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-primary-500 bg-slate-950 border-surface-border"
            />
            <span>Match Difficulty</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={matchType}
              onChange={(e) => setMatchType(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-primary-500 bg-slate-950 border-surface-border"
            />
            <span>Match Question Type</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={matchTopic}
              onChange={(e) => setMatchTopic(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-primary-500 bg-slate-950 border-surface-border"
            />
            <span>Same Topic</span>
          </label>
        </div>

        {/* Candidate List Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="p-8 text-center space-y-2">
              <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-400">Searching Question Bank for alternatives...</p>
            </div>
          ) : candidates.length === 0 ? (
            <div className="p-8 text-center space-y-2">
              <FileQuestion className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400 font-medium">No eligible replacement questions found matching constraints.</p>
              <p className="text-[11px] text-slate-500">Try unchecking &quot;Same Topic&quot; to expand candidate search.</p>
            </div>
          ) : (
            candidates.map((c) => (
              <div
                key={c.id}
                className="p-3.5 rounded-xl border border-surface-border bg-slate-900/40 hover:border-primary-500/60 hover:bg-slate-900/80 transition-all flex items-start justify-between gap-3"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                      {c.question_type.replace('_', ' ')}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                        c.difficulty === 'easy'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : c.difficulty === 'medium'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      }`}
                    >
                      {c.difficulty}
                    </span>
                    {c.unit_name && (
                      <span className="text-[10px] text-slate-400 truncate max-w-[150px]">
                        {c.unit_name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 line-clamp-2 leading-relaxed">
                    {c.question_text}
                  </p>
                </div>

                <button
                  onClick={() => handleSelectReplacement(c.id)}
                  disabled={replacing}
                  className="px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shrink-0 transition-colors"
                >
                  {replacing ? 'Replacing...' : 'Use This Question'}
                </button>
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-surface-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-surface-border text-xs text-slate-300 font-semibold"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
