'use client';

import { useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  ShieldAlert,
  Clock,
  Layers,
  ArrowUpRight,
  Download,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
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
import { ChartContainer } from '@/components/ui/ChartContainer';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';

const SCORE_DISTRIBUTION_DATA = [
  { bucket: '0-20%', count: 4 },
  { bucket: '21-40%', count: 12 },
  { bucket: '41-60%', count: 32 },
  { bucket: '61-80%', count: 68 },
  { bucket: '81-100%', count: 26 },
];

interface ItemAnalysisRecord {
  id: string;
  topic: string;
  accuracyRate: string;
  discriminationIndex: number;
  averageDwellSecs: number;
  quality: 'Excellent' | 'Good' | 'Needs Review';
}

const SAMPLE_ITEM_ANALYSIS: ItemAnalysisRecord[] = [
  {
    id: 'Q-01: PostgreSQL RLS',
    topic: 'Relational DB',
    accuracyRate: '88.5%',
    discriminationIndex: 0.48,
    averageDwellSecs: 42,
    quality: 'Excellent',
  },
  {
    id: 'Q-02: Cryptographic Tokens',
    topic: 'Cryptographic Security',
    accuracyRate: '71.2%',
    discriminationIndex: 0.52,
    averageDwellSecs: 58,
    quality: 'Excellent',
  },
  {
    id: 'Q-03: Academic Hierarchy',
    topic: 'Academic Structure',
    accuracyRate: '92.1%',
    discriminationIndex: 0.35,
    averageDwellSecs: 31,
    quality: 'Good',
  },
  {
    id: 'Q-04: Snapshot Isolation',
    topic: 'Quiz Management',
    accuracyRate: '64.0%',
    discriminationIndex: 0.41,
    averageDwellSecs: 64,
    quality: 'Good',
  },
  {
    id: 'Q-05: Proctoring Telemetry',
    topic: 'Proctoring & Audit',
    accuracyRate: '48.2%',
    discriminationIndex: 0.22,
    averageDwellSecs: 85,
    quality: 'Needs Review',
  },
];

export default function AdminAnalyticsPage() {
  const [isSyncing, setIsSyncing] = useState(false);

  const handleRefresh = async () => {
    setIsSyncing(true);
    // Asynchronous revalidation
    setTimeout(() => {
      setIsSyncing(false);
    }, 600);
  };

  const columns: TableColumn<ItemAnalysisRecord>[] = [
    {
      key: 'id',
      header: 'Question / Item',
      render: (row) => (
        <div>
          <span className="font-semibold text-white block">{row.id}</span>
          <span className="text-[10px] font-mono text-cyber-cyan block">{row.topic}</span>
        </div>
      ),
    },
    {
      key: 'accuracyRate',
      header: 'Accuracy Rate',
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-emerald-400">{row.accuracyRate}</span>
      ),
    },
    {
      key: 'discriminationIndex',
      header: 'Discrimination Index',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs text-brand-300 font-medium">
          {row.discriminationIndex.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'averageDwellSecs',
      header: 'Avg Dwell Time',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs text-slate-300">{row.averageDwellSecs}s</span>
      ),
    },
    {
      key: 'quality',
      header: 'Item Quality',
      render: (row) => {
        const color = {
          Excellent: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
          Good: 'bg-cyber-cyan/15 border-cyber-cyan/30 text-cyber-cyan',
          'Needs Review': 'bg-amber-500/15 border-amber-500/30 text-amber-300',
        }[row.quality];
        return (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border font-medium ${color}`}>
            {row.quality}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Analytics' }]} />

      <PageHeader
        title="Psychometric &amp; Exam Analytics"
        description="Deep statistical item discrimination, score distribution curves, and proctoring telemetry audits."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={isSyncing}
              className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors disabled:opacity-60"
              title="Refresh Analytics Asynchronously"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin text-brand-400' : ''}`} />
            </button>
            <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 hover:text-white transition-colors">
              <Download className="w-3.5 h-3.5" />
              Export CSV Report
            </button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard
          label="Cohort Average Score"
          value="76.8%"
          subtitle="Across 230 evaluated attempts"
          icon={TrendingUp}
          variant="brand"
          trend="+4.2% vs baseline"
        />

        <StatCard
          label="Pass Rate"
          value="84.2%"
          subtitle="Threshold set at >= 60%"
          icon={CheckCircle2}
          variant="emerald"
          trend="Target Exceeded"
        />

        <StatCard
          label="Mean Completion Time"
          value="32m 45s"
          subtitle="Out of 45 minutes allotted"
          icon={Clock}
          variant="cyan"
          trend="72% Pace"
        />

        <StatCard
          label="Flagged Telemetry Incidents"
          value="2 Flags"
          subtitle="Tab-switch burst warnings"
          icon={ShieldAlert}
          variant="purple"
          trend="99.1% Integrity"
        />
      </div>

      {/* Score Distribution Chart */}
      <ChartContainer
        title="Cohort Score Distribution Curve"
        subtitle="Histogram of candidate examination percentage bands"
        height={260}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={SCORE_DISTRIBUTION_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} tickLine={false} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f1422',
                borderColor: 'rgba(255,255,255,0.1)',
                borderRadius: '12px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="count" name="Candidates" fill="#4668fa" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartContainer>

      {/* Deep Item Analysis Table */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-white">Item Discrimination &amp; Difficulty Breakdown</h2>
            <p className="text-xs text-slate-400">Psychometric item evaluation to identify poorly performing or ambiguous questions.</p>
          </div>
        </div>

        <ResponsiveTable
          columns={columns}
          data={SAMPLE_ITEM_ANALYSIS}
          keyExtractor={(row) => row.id}
          mobileCardRender={(row) => (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-white text-xs leading-snug">{row.id}</h3>
                  <span className="font-mono text-[10px] text-cyber-cyan">{row.topic}</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider border shrink-0 ${
                  row.quality === 'Excellent' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                  row.quality === 'Good' ? 'bg-cyber-cyan/15 border-cyber-cyan/30 text-cyber-cyan' :
                  'bg-amber-500/15 border-amber-500/30 text-amber-300'
                }`}>
                  {row.quality}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono py-2 border-y border-surface-border/50 text-center">
                <div>
                  <span className="text-slate-500 block text-[9px]">ACCURACY</span>
                  <span className="text-emerald-400 font-bold">{row.accuracyRate}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[9px]">DISCRIM.</span>
                  <span className="text-brand-300 font-bold">{row.discriminationIndex.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[9px]">AVG TIME</span>
                  <span className="text-slate-200 font-bold">{row.averageDwellSecs}s</span>
                </div>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  );
}
