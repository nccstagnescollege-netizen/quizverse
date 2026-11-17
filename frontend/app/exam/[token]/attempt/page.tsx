'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Timer, ArrowRight, ArrowLeft, Shield, AlertCircle } from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';

export default function ExamAttemptPage() {
  const params = useParams();
  const token = (params?.token as string) || 'DEMO-EXAM-TOKEN';
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 flex flex-col justify-between">
      {/* Exam Header */}
      <header className="h-16 border-b border-surface-border px-4 sm:px-8 flex items-center justify-between bg-surface-elevated/70 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <span className="font-display font-bold text-sm text-white">QUIZVERSE</span>
          <span className="text-slate-600">/</span>
          <span className="text-xs font-mono text-cyber-cyan truncate max-w-[120px] sm:max-w-none">
            {token}
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-base border border-surface-border text-xs font-mono text-brand-300">
            <Timer className="w-3.5 h-3.5 text-brand-400" />
            <span>44:38</span>
          </div>

          <button
            onClick={() => setShowSubmitModal(true)}
            className="px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-glow-primary transition-all"
          >
            Submit Exam
          </button>
        </div>
      </header>

      {/* Main Attempt Workspace */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-4 sm:p-6 lg:p-8 space-y-6">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 pb-2 border-b border-surface-border">
          <span>Question 1 of 30</span>
          <span>Single Choice &bull; 2 Points</span>
        </div>

        <DashboardCard glow="brand" className="space-y-6">
          <h2 className="text-base sm:text-lg font-semibold text-white leading-relaxed">
            Which architectural component in QUIZVERSE is responsible for providing zero-trust
            database access with Row Level Security?
          </h2>

          <div className="space-y-2.5">
            {[
              'Supabase PostgreSQL with RLS policies and server-side service role key',
              'Next.js public environment variables exposed directly in client bundle',
              'Unvalidated client-side localStorage access tokens',
              'Plaintext credential storage in frontend repository commits',
            ].map((option, idx) => {
              const isSelected = selectedOption === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setSelectedOption(idx)}
                  className={`w-full text-left p-4 rounded-xl border text-xs sm:text-sm transition-all flex items-center justify-between ${
                    isSelected
                      ? 'bg-brand-600/15 border-brand-500 text-white shadow-glow-primary'
                      : 'bg-surface-base border-surface-border text-slate-300 hover:border-slate-500 hover:bg-white/[0.02]'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <span
                      className={`w-6 h-6 rounded-lg font-mono text-xs flex items-center justify-center shrink-0 border ${
                        isSelected
                          ? 'bg-brand-600 text-white border-brand-400'
                          : 'bg-surface-elevated text-slate-400 border-surface-border'
                      }`}
                    >
                      {String.fromCharCode(65 + idx)}
                    </span>
                    {option}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2 text-xs text-slate-400">
            <Shield className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Phase 1 Demonstration Item &bull; Full dynamic exam engine loads in Phase 4.</span>
          </div>

          <div className="pt-4 border-t border-surface-border flex items-center justify-between">
            <button
              disabled
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-500 cursor-not-allowed"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Previous
            </button>

            <Link href={`/exam/${token}/result`}>
              <button className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple">
                Next Question
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </Link>
          </div>
        </DashboardCard>
      </main>

      <footer className="h-12 border-t border-surface-border px-4 sm:px-8 flex items-center justify-between text-[11px] text-slate-500">
        <span>Session Protected by QUIZVERSE Anti-Cheat Engine</span>
        <span>Auto-sync Active</span>
      </footer>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showSubmitModal}
        title="Submit Examination Attempt?"
        message="Are you sure you want to conclude this examination? Once submitted, answers cannot be edited."
        confirmLabel="Finalize & Submit"
        cancelLabel="Continue Exam"
        variant="danger"
        onConfirm={() => {
          setShowSubmitModal(false);
          window.location.href = `/exam/${token}/result`;
        }}
        onCancel={() => setShowSubmitModal(false)}
      />
    </div>
  );
}
