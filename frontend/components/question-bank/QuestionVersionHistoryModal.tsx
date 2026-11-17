'use client';

import React, { useState, useEffect } from 'react';
import { X, History, Clock, User, ChevronDown, ChevronRight, FileCheck, Layers } from 'lucide-react';
import { QuestionVersion, questionBankService } from '@/services/questionBankService';

interface QuestionVersionHistoryModalProps {
  questionId: string;
  isOpen: boolean;
  onClose: () => void;
  token: string;
}

export function QuestionVersionHistoryModal({
  questionId,
  isOpen,
  onClose,
  token,
}: QuestionVersionHistoryModalProps) {
  const [versions, setVersions] = useState<QuestionVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null);

  useEffect(() => {
    if (!isOpen || !questionId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    async function loadHistory() {
      try {
        const res = await questionBankService.getVersionHistory(questionId, token);
        if (isMounted) {
          setVersions(res.data || []);
          if (res.data && res.data.length > 0) {
            setExpandedVersion(res.data[0].version_number);
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load version history.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, [isOpen, questionId, token]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-surface-base border border-surface-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary-500/10 text-primary-400">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Immutable Version History</h2>
              <p className="text-xs text-slate-400">Snapshot trail ensuring zero side-effects on past examinations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-2">
              <div className="w-7 h-7 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-400">Loading version snapshots...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {error}
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              No historical edits recorded yet. Current state is original Version 1.
            </div>
          ) : (
            <div className="space-y-3">
              {versions.map((ver) => {
                const isExpanded = expandedVersion === ver.version_number;
                return (
                  <div
                    key={ver.id}
                    className="border border-surface-border rounded-xl bg-surface-elevated overflow-hidden transition-all"
                  >
                    <button
                      onClick={() => setExpandedVersion(isExpanded ? null : ver.version_number)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-border/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-500/10 text-primary-400 font-bold text-xs border border-primary-500/20">
                          v{ver.version_number}
                        </span>
                        <div>
                          <p className="text-xs font-semibold text-slate-100">
                            {ver.change_summary || `Version ${ver.version_number} Snapshot`}
                          </p>
                          <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                            <span className="flex items-center gap-1">
                              <User className="w-3 h-3" />
                              {ver.changed_by_name || 'System / Administrator'}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(ver.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-slate-400">
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="p-4 border-t border-surface-border bg-slate-900/60 space-y-3 text-xs">
                        <div>
                          <span className="font-semibold text-slate-400 block mb-1">Question Text at this Version:</span>
                          <p className="p-3 rounded-lg bg-surface-elevated border border-surface-border text-slate-200">
                            {ver.question_snapshot?.question_text || 'No prompt stored'}
                          </p>
                        </div>
                        {ver.question_snapshot?.options && (
                          <div>
                            <span className="font-semibold text-slate-400 block mb-1">
                              Options ({ver.question_snapshot.options.length}):
                            </span>
                            <div className="space-y-1">
                              {ver.question_snapshot.options.map((opt: any, idx: number) => (
                                <div
                                  key={idx}
                                  className={`p-2 rounded-lg border text-xs flex items-center justify-between ${
                                    opt.is_correct
                                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                                      : 'bg-surface-elevated border-surface-border text-slate-300'
                                  }`}
                                >
                                  <span>{String.fromCharCode(65 + idx)}. {opt.option_text}</span>
                                  {opt.is_correct && <span className="font-bold text-[10px]">CORRECT</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                          <span>Marks: {ver.question_snapshot?.default_marks ?? 1.0}</span>
                          <span>Negative Marks: {ver.question_snapshot?.default_negative_marks ?? 0.0}</span>
                          <span>Difficulty: {ver.question_snapshot?.difficulty ?? 'medium'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-surface-border bg-surface-elevated">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
