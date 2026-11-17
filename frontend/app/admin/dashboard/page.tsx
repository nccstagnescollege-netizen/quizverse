'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Users,
  BookOpen,
  HelpCircle,
  Activity,
  Layers,
  ArrowUpRight,
  Plus,
  ShieldAlert,
  Download,
  Filter,
  CheckCircle2,
  Clock,
  Sparkles,
  BarChart2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ChartContainer } from '@/components/ui/ChartContainer';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';
import { useAuth } from '@/contexts/AuthContext';

const MOCK_ACTIVITY_DATA = [
  { name: '08:00', candidates: 14, submissions: 10 },
  { name: '10:00', candidates: 38, submissions: 25 },
  { name: '12:00', candidates: 92, submissions: 80 },
  { name: '14:00', candidates: 145, submissions: 130 },
  { name: '16:00', candidates: 110, submissions: 98 },
  { name: '18:00', candidates: 65, submissions: 58 },
  { name: '20:00', candidates: 30, submissions: 28 },
];

const MOCK_TOPIC_DATA = [
  { topic: 'Relational DB', avgScore: 84, passingRate: 91 },
  { topic: 'Cryptography', avgScore: 72, passingRate: 78 },
  { topic: 'Academic Hier.', avgScore: 89, passingRate: 95 },
  { topic: 'Proctoring', avgScore: 68, passingRate: 74 },
  { topic: 'Alembic DDL', avgScore: 76, passingRate: 82 },
];

interface RecentQuiz {
  id: string;
  title: string;
  slug: string;
  duration: string;
  totalAttempts: number;
  averageScore: string;
  status: 'published' | 'scheduled' | 'draft';
}

const MOCK_RECENT_QUIZZES: RecentQuiz[] = [
  {
    id: 'qz-101',
    title: 'Advanced Database Architecture & RLS',
    slug: 'adv-database-rls-2026',
    duration: '45 mins',
    totalAttempts: 142,
    averageScore: '82.4%',
    status: 'published',
  },
  {
    id: 'qz-102',
    title: 'Distributed Systems & Vector Projections',
    slug: 'dist-systems-vector',
    duration: '60 mins',
    totalAttempts: 88,
    averageScore: '74.1%',
    status: 'published',
  },
  {
    id: 'qz-103',
    title: 'Cryptographic Hashing & Token Verification',
    slug: 'crypto-tokens-sha256',
    duration: '30 mins',
    totalAttempts: 0,
    averageScore: '--',
    status: 'scheduled',
  },
  {
    id: 'qz-104',
    title: 'Quantum Computing Fundamentals (3D Lab)',
    slug: 'quantum-computing-3d',
    duration: '90 mins',
    totalAttempts: 0,
    averageScore: '--',
    status: 'draft',
  },
];

export default function AdminDashboardPage() {
  const [activeChartTab, setActiveChartTab] = useState<'concurrency' | 'proficiency'>('concurrency');
  const { user, isSuperAdmin, hasPermission } = useAuth();

  const columns: TableColumn<RecentQuiz>[] = [
    {
      key: 'title',
      header: 'Examination Title',
      render: (row) => (
        <div className="space-y-0.5">
          <span className="font-semibold text-white block">{row.title}</span>
          <span className="text-[10px] font-mono text-slate-400 block">{row.slug}</span>
        </div>
      ),
    },
    {
      key: 'duration',
      header: 'Duration',
      hideOnMobile: true,
      render: (row) => (
        <span className="inline-flex items-center gap-1 font-mono text-xs text-slate-300">
          <Clock className="w-3 h-3 text-slate-400" />
          {row.duration}
        </span>
      ),
    },
    {
      key: 'totalAttempts',
      header: 'Submissions',
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-cyber-cyan">{row.totalAttempts}</span>
      ),
    },
    {
      key: 'averageScore',
      header: 'Avg Score',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-brand-300">{row.averageScore}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => {
        const colors = {
          published: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
          scheduled: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
          draft: 'bg-slate-800 border-slate-700 text-slate-400',
        }[row.status];
        return (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border font-medium ${colors}`}>
            {row.status}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Action',
      className: 'text-right',
      render: (row) => (
        <div className="flex justify-end gap-1.5">
          <Link href={`/exam/${row.slug}`} target="_blank">
            <button className="px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-brand-600/30 border border-surface-border text-[11px] text-slate-200 transition-colors">
              Preview
            </button>
          </Link>
          <Link href="/admin/quiz">
            <button className="px-2.5 py-1 rounded-lg bg-brand-600/20 hover:bg-brand-600 text-brand-300 hover:text-white border border-brand-500/30 text-[11px] font-medium transition-colors">
              Edit
            </button>
          </Link>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin' }, { label: 'Dashboard' }]} />

      <PageHeader
        title="Platform Command Center"
        description="Monitor real-time candidate concurrency, psychometric difficulty curves, and live examination sessions."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-300 hover:text-white transition-colors">
              <Download className="w-3.5 h-3.5" />
              Export Telemetry
            </button>
            <Link href="/admin/quiz">
              <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple min-h-[36px]">
                <Plus className="w-3.5 h-3.5" />
                Create Quiz
              </button>
            </Link>
          </div>
        }
      />

      {/* Role & Access Scope Indicator */}
      {isSuperAdmin ? (
        <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-lg bg-purple-500/20 text-purple-300">
              <ShieldAlert className="w-4 h-4" />
            </span>
            <div>
              <div className="font-semibold text-white">Super Administrator Session Active</div>
              <p className="text-slate-400">You have unrestricted global platform authority across all operational domains.</p>
            </div>
          </div>
          <Link
            href="/super-admin/dashboard"
            className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs self-start sm:self-auto transition-colors"
          >
            Super Admin Command Hub &rarr;
          </Link>
        </div>
      ) : (
        <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span className="text-slate-300">
              Operational Scope: <strong>{user?.full_name || 'Assigned User Administrator'}</strong> ({user?.roles?.join(', ') || 'user_admin'})
            </span>
          </div>
          <span className="font-mono text-[11px] text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded-full">
            {user ? `${user.permissions.length} granular permissions` : 'Default-deny RBAC active'}
          </span>
        </div>
      )}

      {/* 1. KPI Stats Grid (Adaptive 1 col on phone, 2 on tablet, 4 on desktop) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard
          label="Total Examinations"
          value="4 Active"
          subtitle="All 34 schema tables online"
          icon={BookOpen}
          variant="brand"
          trend="+2 This Week"
        />

        <StatCard
          label="Question Bank Pool"
          value="150 Items"
          subtitle="Categorized across 5 topics"
          icon={HelpCircle}
          variant="cyan"
          trend="100% Validated"
        />

        <StatCard
          label="Live Concurrent Students"
          value="145 Online"
          subtitle="Real-time proctoring telemetry"
          icon={Users}
          variant="purple"
          trend="Zero Cheating Flags"
        />

        <StatCard
          label="Infrastructure & RLS"
          value="Optimal"
          subtitle="FastAPI + Supabase PostgreSQL"
          icon={Activity}
          variant="emerald"
          trend="99.99% Uptime"
        />
      </div>

      {/* 2. Responsive Multi-Chart Deck (Side-by-Side on Desktop, Stacked on Mobile) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Chart 1: Candidate Concurrency & Submissions */}
        <div className="lg:col-span-7">
          <ChartContainer
            title="Real-Time Concurrency Telemetry"
            subtitle="Live concurrent examinees vs completed submissions over 24 hours"
            height={260}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_ACTIVITY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="candidateGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4668fa" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#4668fa" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="subGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f5d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00f5d4" stopOpacity={0.0} />
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
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Area type="monotone" name="Active Examinees" dataKey="candidates" stroke="#4668fa" strokeWidth={2} fill="url(#candidateGrad)" />
                <Area type="monotone" name="Submissions" dataKey="submissions" stroke="#00f5d4" strokeWidth={2} fill="url(#subGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        {/* Chart 2: Topic Proficiency & Passing Ratios */}
        <div className="lg:col-span-5">
          <ChartContainer
            title="Topic Proficiency & Pass Rates"
            subtitle="Average candidate scores aggregated by academic topic"
            height={260}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MOCK_TOPIC_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="topic" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f1422',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="avgScore" name="Avg Score %" fill="#9d4edd" radius={[4, 4, 0, 0]} />
                <Bar dataKey="passingRate" name="Pass Rate %" fill="#00f5d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </div>

      {/* 3. Comprehensive Examination Registry Table (Responsive Cards on Mobile) */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-white">Active Examination Portals</h2>
            <p className="text-xs text-slate-400">Manage candidate access, review token invitations, and inspect real-time attempts.</p>
          </div>
          <Link href="/admin/quiz" className="text-xs text-cyber-cyan hover:underline flex items-center gap-1 font-mono">
            View All Examinations <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <ResponsiveTable
          columns={columns}
          data={MOCK_RECENT_QUIZZES}
          keyExtractor={(row) => row.id}
          mobileCardRender={(row) => (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-white text-xs leading-snug">{row.title}</h3>
                  <span className="font-mono text-[10px] text-slate-400">{row.slug}</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider border shrink-0 ${
                  row.status === 'published' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                }`}>
                  {row.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono py-2 border-y border-surface-border/50">
                <div>
                  <span className="text-slate-500 block text-[10px]">SUBMISSIONS</span>
                  <span className="text-cyber-cyan font-bold">{row.totalAttempts}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">AVERAGE SCORE</span>
                  <span className="text-brand-300 font-bold">{row.averageScore}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {row.duration}
                </span>
                <div className="flex gap-2">
                  <Link href={`/exam/${row.slug}`} target="_blank">
                    <button className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-slate-200">
                      Preview
                    </button>
                  </Link>
                  <Link href="/admin/quiz">
                    <button className="px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-medium">
                      Configure
                    </button>
                  </Link>
                </div>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  );
}
