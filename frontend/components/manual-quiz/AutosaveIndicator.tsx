'use client';

import React, { useState } from 'react';
import {
  Save,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  History,
  FileCheck,
} from 'lucide-react';

interface AutosaveIndicatorProps {
  status: 'idle' | 'saving' | 'saved' | 'error';
  draftVersion: number;
  lastSavedAt?: string | null;
  onManualSave: (changeNote?: string) => Promise<void>;
  hasUnsavedChanges?: boolean;
}

export function AutosaveIndicator({
  status,
  draftVersion,
  lastSavedAt,
  onManualSave,
  hasUnsavedChanges,
}: AutosaveIndicatorProps) {
  const [isPromptOpen, setIsPromptOpen] = useState(false);
  const [changeNote, setChangeNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onManualSave(changeNote.trim() || undefined);
      setIsPromptOpen(false);
      setChangeNote('');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* Live Status Pill */}
      {status === 'saving' ? (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span>Saving draft...</span>
        </span>
      ) : status === 'error' ? (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 font-medium">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>Draft save failed</span>
        </span>
      ) : hasUnsavedChanges ? (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span>Unsaved changes</span>
        </span>
      ) : (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Draft v{draftVersion} saved</span>
        </span>
      )}

      {/* Manual Save Draft Snapshot Button */}
      <button
        onClick={() => setIsPromptOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors"
        title="Create an immutable draft version snapshot with change notes"
      >
        <Save className="w-3.5 h-3.5" />
        <span>Save Draft</span>
      </button>

      {/* Save Draft Version Modal */}
      {isPromptOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-elevated border border-surface-border rounded-2xl w-full max-w-sm p-4 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-primary-400" />
              <div>
                <h4 className="text-sm font-bold text-white">Create Draft Snapshot</h4>
                <p className="text-[11px] text-slate-400">
                  Save snapshot as Version {draftVersion + 1} with an audit log note.
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300">
                Change Summary (Optional)
              </label>
              <input
                type="text"
                value={changeNote}
                onChange={(e) => setChangeNote(e.target.value)}
                placeholder="e.g. Added 5 question bank items to PART B"
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={() => setIsPromptOpen(false)}
                className="px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md disabled:opacity-50"
              >
                {isSaving ? 'Creating...' : 'Snapshot Draft'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
