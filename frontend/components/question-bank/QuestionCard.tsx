'use client';

import React from 'react';
import Link from 'next/link';
import {
  Eye,
  Edit,
  Copy,
  Archive,
  RotateCcw,
  Trash2,
  History,
  CheckCircle2,
  Clock,
  Sparkles,
  Code,
  Tag,
  MessageSquare,
  AlertCircle,
  FileQuestion,
} from 'lucide-react';
import { QuestionListItem } from '@/services/questionBankService';

interface QuestionCardProps {
  question: QuestionListItem;
  basePath: string; // e.g. '/super-admin/question-bank' or '/admin/question-bank'
  onPreview: (q: QuestionListItem) => void;
  onReview: (q: QuestionListItem) => void;
  onHistory: (q: QuestionListItem) => void;
  onDuplicate: (q: QuestionListItem) => void;
  onArchive: (q: QuestionListItem) => void;
  onRestore: (q: QuestionListItem) => void;
  onDelete: (q: QuestionListItem) => void;
  canEdit?: boolean;
  canDelete?: boolean;
  canReview?: boolean;
}

export function QuestionCard({
  question: q,
  basePath,
  onPreview,
  onReview,
  onHistory,
  onDuplicate,
  onArchive,
  onRestore,
  onDelete,
  canEdit = true,
  canDelete = true,
  canReview = true,
}: QuestionCardProps) {
  const isArchived = q.status === 'archived';

  return (
    <div
      className={`relative p-5 rounded-2xl border transition-all hover:shadow-lg flex flex-col justify-between gap-4 ${
        isArchived
          ? 'bg-slate-950/40 border-slate-800/80 opacity-75'
          : 'bg-surface-elevated border-surface-border hover:border-slate-600'
      }`}
    >
      {/* Top Header: Types, Difficulty, Marks, Status */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Question Type */}
          <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-800 text-slate-200 border border-slate-700 uppercase tracking-wider">
            {q.question_type.replace('_', ' ')}
          </span>

          {/* Difficulty */}
          <span
            className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${
              q.difficulty === 'easy'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : q.difficulty === 'medium'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}
          >
            {q.difficulty.toUpperCase()}
          </span>

          {/* Marks */}
          <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800/60 text-slate-300 border border-slate-700">
            +{q.default_marks}m {q.default_negative_marks > 0 ? `(-${q.default_negative_marks})` : ''}
          </span>

          {/* Feature tags */}
          {q.is_mathematical && (
            <span
              className="p-1 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20"
              title="LaTeX Mathematical Equation Support"
            >
              <Sparkles className="w-3 h-3" />
            </span>
          )}
          {q.code_language && (
            <span
              className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono"
              title={`Code: ${q.code_language}`}
            >
              {q.code_language}
            </span>
          )}
        </div>

        {/* Status Badge */}
        <span
          className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border ${
            q.status === 'approved'
              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
              : q.status === 'pending_review'
              ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
              : q.status === 'archived'
              ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
              : 'bg-slate-700/40 text-slate-300 border-slate-600'
          }`}
        >
          {q.status.replace('_', ' ')}
        </span>
      </div>

      {/* Main Content: Title & Text */}
      <div className="space-y-1.5 flex-1">
        {q.title && (
          <h3 className="text-sm font-semibold text-white line-clamp-1 hover:text-primary-300 transition-colors">
            {q.title}
          </h3>
        )}
        <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">
          {q.question_text}
        </p>
      </div>

      {/* Academic Hierarchy Breadcrumbs */}
      <div className="text-[11px] text-slate-400 flex flex-wrap items-center gap-1.5 pt-1 border-t border-surface-border/60">
        <span className="text-slate-500 font-medium">Path:</span>
        {q.subject_name && (
          <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 font-medium">
            {q.subject_name}
          </span>
        )}
        {q.unit_name && (
          <>
            <span className="text-slate-600">&rsaquo;</span>
            <span className="text-slate-400">{q.unit_name}</span>
          </>
        )}
        {q.topic_name && (
          <>
            <span className="text-slate-600">&rsaquo;</span>
            <span className="text-primary-400 font-medium">{q.topic_name}</span>
          </>
        )}
      </div>

      {/* Tags row */}
      {Array.isArray(q.tags) && q.tags.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {q.tags.map((t, idx) => (
            <span
              key={idx}
              className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700"
            >
              #{t}
            </span>
          ))}
        </div>
      )}

      {/* Footer Info & Actions */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-surface-border/60">
        <div className="text-[10px] text-slate-400 flex items-center gap-2">
          <span>{q.options_count} options</span>
          <span>•</span>
          <span>{new Date(q.created_at).toLocaleDateString()}</span>
        </div>

        {/* Action Buttons with touch-friendly min targets */}
        <div className="flex items-center gap-1">
          {/* Preview */}
          <button
            onClick={() => onPreview(q)}
            title="Preview Question"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-surface-border transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
          >
            <Eye className="w-4 h-4" />
          </button>

          {/* Review Workflow */}
          {canReview && (
            <button
              onClick={() => onReview(q)}
              title="Review / Approval Workflow"
              className="p-1.5 rounded-lg text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            >
              <MessageSquare className="w-4 h-4" />
            </button>
          )}

          {/* Version History */}
          <button
            onClick={() => onHistory(q)}
            title="Version History & Snapshots"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-surface-border transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
          >
            <History className="w-4 h-4" />
          </button>

          {/* Duplicate */}
          <button
            onClick={() => onDuplicate(q)}
            title="Duplicate Question"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-surface-border transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
          >
            <Copy className="w-4 h-4" />
          </button>

          {/* Edit */}
          {canEdit && !isArchived && (
            <Link
              href={`${basePath}/${q.id}/edit`}
              title="Edit Question"
              className="p-1.5 rounded-lg text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            >
              <Edit className="w-4 h-4" />
            </Link>
          )}

          {/* Archive / Restore */}
          {isArchived ? (
            <button
              onClick={() => onRestore(q)}
              title="Restore from Archive"
              className="p-1.5 rounded-lg text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => onArchive(q)}
              title="Archive Question"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            >
              <Archive className="w-4 h-4" />
            </button>
          )}

          {/* Delete */}
          {canDelete && (
            <button
              onClick={() => onDelete(q)}
              title="Permanently Delete Question"
              className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
