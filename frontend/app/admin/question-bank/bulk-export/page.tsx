'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import BulkExportPanel from '@/components/question-bank/BulkExportPanel';

export default function UserAdminBulkExportPage() {
  const { user, token, isSuperAdmin, isLoading } = useAuth();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <span className="animate-spin mr-2">⏳</span> Loading...
      </div>
    );
  }

  // Check if admin has question.answer.view permission
  const canViewAnswers = user?.permissions?.includes('question.answer.view') || isSuperAdmin;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold mb-1">
            <Link href="/admin/question-bank" className="hover:underline">
              Question Bank
            </Link>
            <span>/</span>
            <span className="text-slate-400">Bulk Export</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <span>📤</span> Scoped Question Export
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Export questions within your assigned academic scope. Answer keys are strictly protected based on your granted permissions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/admin/question-bank/bulk-import"
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition"
          >
            📥 Go to Bulk Import
          </Link>
          <Link
            href="/admin/question-bank"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl transition"
          >
            Back to Questions
          </Link>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-950/60 border border-rose-500/40 rounded-xl text-rose-200 text-sm flex items-center justify-between">
          <span>⚠️ {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-200 text-sm flex items-center justify-between">
          <span>✅ {successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      <BulkExportPanel
        token={token || ''}
        isSuperAdmin={false}
        canViewAnswers={canViewAnswers}
        onError={(msg) => setErrorMsg(msg)}
        onSuccess={(msg) => setSuccessMsg(msg)}
      />
    </div>
  );
}
