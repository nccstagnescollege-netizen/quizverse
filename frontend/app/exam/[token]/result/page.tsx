'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Award, CheckCircle2, Clock, RotateCcw, Home, ArrowRight } from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function ExamResultPage() {
  const params = useParams();
  const token = (params?.token as string) || 'DEMO-EXAM-TOKEN';

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 bg-grid-pattern p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
      <div className="max-w-3xl mx-auto w-full space-y-6">
        <Breadcrumb
          items={[
            { label: 'Exam Portal', href: `/exam/${token}` },
            { label: 'Result Summary' },
          ]}
        />

        <div className="text-center space-y-2 py-2">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-glow-primary">
            <Award className="w-7 h-7" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-white">
            Examination Concluded
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Session submitted and archived for automated score verification.
          </p>
        </div>

        <DashboardCard glow="brand" className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border text-center">
              <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                Score Status
              </span>
              <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-400">
                Validated
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border text-center">
              <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                Time Elapsed
              </span>
              <span className="text-xl sm:text-2xl font-bold font-mono text-white">
                12m 45s
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border text-center">
              <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                Proctor Audit
              </span>
              <span className="text-xl sm:text-2xl font-bold font-mono text-cyber-cyan">
                Passed
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-surface-base border border-surface-border flex items-start gap-3 text-xs text-slate-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>
              Your session payload was registered with token{' '}
              <code className="text-cyber-cyan font-mono">{token}</code>. Official psychometric
              breakdown and certificates will be downloadable in Phase 5.
            </span>
          </div>

          <div className="pt-4 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-3">
            <Link href="/" className="w-full sm:w-auto">
              <button className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 hover:text-white transition-colors">
                <Home className="w-3.5 h-3.5" /> Return to Homepage
              </button>
            </Link>

            <Link href="/admin/dashboard" className="w-full sm:w-auto">
              <button className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple">
                View Admin Dashboard <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </Link>
          </div>
        </DashboardCard>
      </div>

      <div className="text-center py-6 text-xs text-slate-500">
        QUIZVERSE Spatial Examination &bull; Phase 1 Foundation
      </div>
    </div>
  );
}
