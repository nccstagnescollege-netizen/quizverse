'use client';

import React from 'react';
import Link from 'next/link';
import {
  Users,
  BookOpen,
  HelpCircle,
  Activity,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  Plus,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ChartContainer } from '@/components/ui/ChartContainer';

const MOCK_ACTIVITY_DATA = [
  { name: '08:00', candidates: 0 },
  { name: '10:00', candidates: 12 },
  { name: '12:00', candidates: 45 },
  { name: '14:00', candidates: 78 },
  { name: '16:00', candidates: 62 },
  { name: '18:00', candidates: 20 },
];

export default function AdminDashboardPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin' }, { label: 'Dashboard' }]} />

      <PageHeader
        title="Platform Command Center"
        description="Monitor examination telemetry, candidate volume, and question pool configurations."
        actions={
          <div className="flex items-center gap-2">
            <Link href="/admin/quiz">
              <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple">
                <Plus className="w-3.5 h-3.5" />
                Create Quiz
              </button>
            </Link>
          </div>
        }
      />

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard
          label="Total Quizzes"
          value="0"
          subtitle="Phase 2 schema readiness"
          icon={BookOpen}
          variant="brand"
          trend="Drafts Ready"
        />

        <StatCard
          label="Question Pool"
          value="0"
          subtitle="Pydantic models prepared"
          icon={HelpCircle}
          variant="cyan"
          trend="Schema Validated"
        />

        <StatCard
          label="Active Candidates"
          value="0"
          subtitle="Realtime channel standby"
          icon={Users}
          variant="purple"
          trend="WebSocket Ready"
        />

        <StatCard
          label="System Health"
          value="Optimal"
          subtitle="FastAPI + Supabase pooling"
          icon={Activity}
          variant="emerald"
          trend="99.99% Uptime"
        />
      </div>

      {/* Chart & Readiness Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Responsive Chart */}
        <div className="lg:col-span-7">
          <ChartContainer
            title="Candidate Concurrency Telemetry"
            subtitle="Real-time examination session tracking across active portals"
            height={260}
          >
            <AreaChart data={MOCK_ACTIVITY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="candidateGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stop-color="#4668fa" stop-opacity={0.4} />
                  <stop offset="95%" stop-color="#4668fa" stop-opacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f1422',
                  borderColor: 'rgba(255,255,255,0.1)',
                  borderRadius: '12px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="candidates"
                stroke="#4668fa"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#candidateGradient)"
              />
            </AreaChart>
          </ChartContainer>
        </div>

        {/* Right Column: Roadmap Readiness Matrix */}
        <div className="lg:col-span-5">
          <DashboardCard glow="purple" className="h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white">Roadmap Phase Progression</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-brand-500/15 text-brand-300 border border-brand-500/30">
                  Phase 1 of 20
                </span>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
                  <div className="flex items-center gap-2.5">
                    <Layers className="w-4 h-4 text-cyber-cyan" />
                    <span className="text-xs text-white">Phase 1: Foundation &amp; Architecture</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold">
                    Complete
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-slate-400" />
                    <span className="text-xs text-slate-400">Phase 2: Authentication &amp; RBAC</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Pending
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-surface-base border border-surface-border">
                  <div className="flex items-center gap-2.5">
                    <BookOpen className="w-4 h-4 text-slate-400" />
                    <span className="text-xs text-slate-400">Phase 3: Database &amp; Question Engine</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Upcoming
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
              <span>FastAPI + Supabase PostgreSQL</span>
              <Link href="/admin/settings" className="hover:text-white flex items-center gap-1 text-cyber-cyan">
                View Config <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </DashboardCard>
        </div>
      </div>
    </div>
  );
}
