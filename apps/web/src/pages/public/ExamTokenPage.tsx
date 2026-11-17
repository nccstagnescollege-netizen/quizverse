import { useParams, Link } from 'react-router-dom';
import { KeyRound, ShieldAlert, ArrowLeft, Timer, Cpu, CheckCircle } from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';

export function ExamTokenPage() {
  const { token } = useParams<{ token: string }>();

  return (
    <div className="max-w-3xl mx-auto px-4 py-16">
      <div className="mb-6">
        <Link
          to="/"
          className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1.5 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Platform Overview
        </Link>
      </div>

      <div className="text-center mb-8">
        <Badge variant="cyan" className="mb-3">
          Candidate Examination Portal
        </Badge>
        <h1 className="text-3xl font-display font-bold text-white">3D Examination Session</h1>
        <p className="text-sm text-slate-400 mt-2">
          Secure candidate authentication and proctored environment verification.
        </p>
      </div>

      <GlassCard glow="cyan" className="border border-cyber-cyan/30">
        <div className="flex items-center justify-between pb-6 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-cyber-cyan/10 border border-cyber-cyan/30 text-cyber-cyan">
              <KeyRound className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs text-slate-400 font-mono block">SESSION TOKEN</span>
              <span className="text-base font-bold font-mono text-white tracking-wider">
                {token || 'TEST-EXAM-TOKEN'}
              </span>
            </div>
          </div>
          <Badge variant="emerald" dot>
            Token Validated
          </Badge>
        </div>

        {/* Verification Checkpoints */}
        <div className="py-6 space-y-4">
          <h3 className="text-xs font-mono uppercase text-slate-300 tracking-wider">
            Pre-flight Diagnostic Checkpoints
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <div>
                <span className="text-xs text-white block">WebGL 2.0</span>
                <span className="text-[10px] text-slate-400">Hardware Accelerated</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2.5">
              <Timer className="w-4 h-4 text-brand-400" />
              <div>
                <span className="text-xs text-white block">Clock Sync</span>
                <span className="text-[10px] text-slate-400">NTP Realtime &plusmn;2ms</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center gap-2.5">
              <Cpu className="w-4 h-4 text-purple-400" />
              <div>
                <span className="text-xs text-white block">Worker Engine</span>
                <span className="text-[10px] text-slate-400">Edge Response Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action button */}
        <div className="pt-6 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Phase 1 placeholder: Live 3D examination room activates in Phase 4.</span>
          </div>

          <Button variant="cyber" size="md">
            Launch 3D Exam Room
          </Button>
        </div>
      </GlassCard>
    </div>
  );
}
