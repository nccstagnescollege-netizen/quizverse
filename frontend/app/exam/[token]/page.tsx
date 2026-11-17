'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { KeyRound, CheckCircle2, ArrowRight, ShieldCheck, Timer } from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function ExamSessionPage() {
  const params = useParams();
  const token = (params?.token as string) || 'DEMO-EXAM-TOKEN';

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 bg-grid-pattern p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
      <div className="max-w-3xl mx-auto w-full space-y-6">
        <Breadcrumb items={[{ label: 'Exam Portal' }, { label: token }]} />

        <div className="text-center space-y-2 py-4">
          <span className="px-3 py-1 rounded-full text-xs font-mono uppercase tracking-wider bg-cyber-cyan/15 border border-cyber-cyan/30 text-cyber-cyan">
            Candidate Gateway
          </span>
          <h1 className="text-2xl sm:text-4xl font-display font-bold text-white">
            Examination Session Portal
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Secure browser session verified for candidate evaluation.
          </p>
        </div>

        <DashboardCard glow="cyan" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-surface-border">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-cyber-cyan/10 border border-cyber-cyan/30 text-cyber-cyan shrink-0">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400 block">
                  Access Token Verified
                </span>
                <span className="text-sm sm:text-base font-bold font-mono text-white tracking-wider">
                  {token}
                </span>
              </div>
            </div>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 w-fit">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Candidate
            </span>
          </div>

          <div className="space-y-3">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-300">
              Session Verification Checkpoints
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <span className="text-white block font-medium">WebGL 2.0 3D Acceleration</span>
                  <span className="text-[10px] text-slate-400">Hardware accelerated graphics</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2.5">
                <Timer className="w-4 h-4 text-brand-400 shrink-0" />
                <div>
                  <span className="text-white block font-medium">Precision Server Sync</span>
                  <span className="text-[10px] text-slate-400">Low-latency Fastify / FastAPI ping</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Proctored telemetry enabled
            </span>

            <Link href={`/exam/${token}/instructions`} className="w-full sm:w-auto">
              <button className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple">
                Proceed to Instructions
                <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </DashboardCard>
      </div>

      <div className="text-center py-6 text-xs text-slate-500">
        QUIZVERSE Spatial Examination &bull; Phase 1 Architecture
      </div>
    </div>
  );
}
