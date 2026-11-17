import { Link } from 'react-router-dom';
import {
  Users,
  BookOpen,
  HelpCircle,
  Activity,
  Layers,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useSystemStatus } from '../../hooks/useStatus';

export function AdminDashboardPage() {
  const { data: status } = useSystemStatus();

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-surface-border">
        <div>
          <div className="inline-flex items-center gap-2 mb-2">
            <Badge variant="brand" dot>
              Admin Workspace
            </Badge>
            <Badge variant="cyan">Phase 1 Foundation</Badge>
          </div>
          <h1 className="text-2xl font-display font-bold text-white">
            Platform Command Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Realtime metrics, question banks, quiz generation, and candidate sessions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/admin/question-bank">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <HelpCircle className="w-3.5 h-3.5" />
              Manage Questions
            </Button>
          </Link>
          <Link to="/admin/quizzes">
            <Button variant="primary" size="sm" className="gap-1.5">
              <BookOpen className="w-3.5 h-3.5" />
              Manage Quizzes
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <GlassCard glow="brand">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Total Exams</span>
            <div className="p-2 rounded-lg bg-brand-500/10 text-brand-400">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-3">0</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Phase 3 module ready</span>
        </GlassCard>

        <GlassCard glow="cyan">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Question Pool</span>
            <div className="p-2 rounded-lg bg-cyber-cyan/10 text-cyber-cyan">
              <HelpCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-3">0</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Zod schema validated</span>
        </GlassCard>

        <GlassCard glow="purple">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Active Candidates</span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-3">0</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Realtime channel standby</span>
        </GlassCard>

        <GlassCard>
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">System State</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400 mt-3">
            {status?.database === 'connected' ? 'Operational' : 'Online'}
          </p>
          <span className="text-[11px] text-slate-400 mt-1 block">Hono API v1 active</span>
        </GlassCard>
      </div>

      {/* Module Overview & Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Module Readiness Matrix</h2>
            <Badge variant="purple">Architecture</Badge>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
              <div className="flex items-center gap-3">
                <Layers className="w-4 h-4 text-cyber-cyan" />
                <span className="text-sm text-slate-200">Phase 1: Foundation &amp; Environment</span>
              </div>
              <Badge variant="emerald">Completed</Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
              <div className="flex items-center gap-3">
                <ShieldCheck className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-400">Phase 2: Authentication &amp; RBAC</span>
              </div>
              <Badge variant="neutral">Pending Approval</Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
              <div className="flex items-center gap-3">
                <BookOpen className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-400">Phase 3: Database &amp; Quiz Engine</span>
              </div>
              <Badge variant="neutral">Upcoming</Badge>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Quick Administration Links</h2>
            <ArrowUpRight className="w-4 h-4 text-slate-400" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Link
              to="/admin/question-bank"
              className="p-4 rounded-xl bg-surface-base border border-surface-border hover:border-brand-500/40 transition-colors block"
            >
              <HelpCircle className="w-5 h-5 text-cyber-cyan mb-2" />
              <h3 className="text-sm font-medium text-white">Question Bank</h3>
              <p className="text-xs text-slate-400 mt-1">Configure questions, tags, and types.</p>
            </Link>

            <Link
              to="/admin/quizzes"
              className="p-4 rounded-xl bg-surface-base border border-surface-border hover:border-brand-500/40 transition-colors block"
            >
              <BookOpen className="w-5 h-5 text-brand-400 mb-2" />
              <h3 className="text-sm font-medium text-white">Quizzes Manager</h3>
              <p className="text-xs text-slate-400 mt-1">Publish 3D-enabled assessments.</p>
            </Link>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
