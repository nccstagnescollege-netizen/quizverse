'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, ArrowRight, CheckSquare, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function ExamInstructionsPage() {
  const params = useParams();
  const token = (params?.token as string) || 'DEMO-EXAM-TOKEN';

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 bg-grid-pattern p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
      <div className="max-w-3xl mx-auto w-full space-y-6">
        <Breadcrumb
          items={[
            { label: 'Exam Portal', href: `/exam/${token}` },
            { label: 'Instructions' },
          ]}
        />

        <div className="space-y-1">
          <span className="text-xs font-mono uppercase text-brand-400">Pre-Flight Briefing</span>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-white">
            Examination Rules &amp; Protocols
          </h1>
        </div>

        <DashboardCard glow="brand" className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border">
              <Clock className="w-4 h-4 text-brand-400 mb-1" />
              <span className="text-[11px] text-slate-400 block">Total Duration</span>
              <span className="text-sm font-bold text-white">45 Minutes</span>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border">
              <CheckSquare className="w-4 h-4 text-cyber-cyan mb-1" />
              <span className="text-[11px] text-slate-400 block">Question Items</span>
              <span className="text-sm font-bold text-white">30 Questions</span>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border">
              <ShieldCheck className="w-4 h-4 text-purple-400 mb-1" />
              <span className="text-[11px] text-slate-400 block">Proctor Tolerance</span>
              <span className="text-sm font-bold text-white">Strict Fullscreen</span>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <h2 className="font-semibold text-white tracking-wide uppercase font-mono text-[11px]">
              Candidate Guidelines
            </h2>
            <ul className="space-y-2 list-disc list-inside text-slate-300 leading-relaxed">
              <li>Ensure uninterrupted network access before launching the examination.</li>
              <li>Do not leave or blur the browser tab once the assessment starts.</li>
              <li>3D spatial inspection tools can be rotated via touch or cursor drag.</li>
              <li>Answers are automatically synchronized with the FastAPI backend.</li>
            </ul>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3 text-xs text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>
              Closing the window during an active attempt records an early submission event.
            </span>
          </div>

          <div className="pt-4 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link
              href={`/exam/${token}`}
              className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Token Screen
            </Link>

            <Link href={`/exam/${token}/attempt`} className="w-full sm:w-auto">
              <button className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple">
                Start Examination
                <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </DashboardCard>
      </div>

      <div className="text-center py-6 text-xs text-slate-500">
        Candidate Session &bull; QUIZVERSE Phase 1
      </div>
    </div>
  );
}
