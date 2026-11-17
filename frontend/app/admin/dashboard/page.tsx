'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  PlusCircle,
  HelpCircle,
  Layers,
  GraduationCap,
  Award,
  BarChart3,
  Activity,
  CheckCircle2,
  Clock,
  FileText,
  RefreshCw,
  ArrowRight,
  Filter,
  Sparkles,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

import { useAuth } from '@/contexts/AuthContext';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ChartContainer } from '@/components/ui/ChartContainer';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const CHART_COLORS = ['#06b6d4', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899'];

interface UserAdminOverviewStats {
  my_total_quizzes: number;
  my_draft_quizzes: number;
  my_published_quizzes: number;
  my_scheduled_quizzes: number;
  my_active_examinations: number;
  my_completed_examinations: number;
  my_total_participants: number;
  my_average_examination_score: number;
}

interface QuizPerformanceItem {
  quiz_id: string;
  title: string;
  status: string;
  attempts_count: number;
  average_score: number;
  passing_rate: number;
}

export default function UserAdminDashboardPage() {
  const { user, token, hasPermission, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [stats, setStats] = useState<UserAdminOverviewStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Filters
  const [quizPeriod, setQuizPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [studentPeriod, setStudentPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [selectedQuizId, setSelectedQuizId] = useState<string>('all');

  // Chart datasets
  const [quizTrends, setQuizTrends] = useState<any[]>([]);
  const [studentTrends, setStudentTrends] = useState<any[]>([]);
  const [completionData, setCompletionData] = useState<any[]>([]);
  const [scoreData, setScoreData] = useState<any[]>([]);
  const [performanceData, setPerformanceData] = useState<QuizPerformanceItem[]>([]);
  const [difficultyData, setDifficultyData] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  // Guard access
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const authHeaders = useCallback(() => {
    return {
      Authorization: `Bearer ${token || localStorage.getItem('quizverse_admin_token')}`,
    };
  }, [token]);

  // Fetch Scoped Overview Statistics
  const fetchOverviewStats = useCallback(async () => {
    setLoadingStats(true);
    setStatsError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/dashboard/overview`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error('Failed to retrieve operational statistics');
      const data = await res.json();
      setStats(data);
    } catch (err: any) {
      setStatsError(err.message || 'Unable to load operational statistics');
    } finally {
      setLoadingStats(false);
    }
  }, [authHeaders]);

  // Fetch Visualizations
  const fetchChartData = useCallback(async () => {
    try {
      const headers = authHeaders();
      const quizParam = selectedQuizId !== 'all' ? `&quiz_id=${selectedQuizId}` : '';
      const quizParamOnly = selectedQuizId !== 'all' ? `?quiz_id=${selectedQuizId}` : '';

      // 1. My Quiz Trends
      const resQuiz = await fetch(
        `${API_BASE}/admin/dashboard/quiz-trends?period=${quizPeriod}`,
        { headers }
      );
      if (resQuiz.ok) setQuizTrends(await resQuiz.json());

      // 2. My Student Trends
      const resStudent = await fetch(
        `${API_BASE}/admin/dashboard/student-trends?period=${studentPeriod}${quizParam}`,
        { headers }
      );
      if (resStudent.ok) setStudentTrends(await resStudent.json());

      // 3. Completion Rates
      const resComp = await fetch(
        `${API_BASE}/admin/dashboard/examination-statistics${quizParamOnly}`,
        { headers }
      );
      if (resComp.ok) {
        const d = await resComp.json();
        setCompletionData([
          { name: 'Submitted', value: d.submitted, color: '#10b981' },
          { name: 'Timed Out', value: d.timed_out, color: '#f59e0b' },
          { name: 'Abandoned', value: d.abandoned, color: '#ef4444' },
          { name: 'In Progress', value: d.in_progress, color: '#06b6d4' },
          { name: 'Disqualified', value: d.disqualified, color: '#6b7280' },
        ].filter((x) => x.value > 0));
      }

      // 4. Score Distribution
      const resScores = await fetch(
        `${API_BASE}/admin/dashboard/score-distribution${quizParamOnly}`,
        { headers }
      );
      if (resScores.ok) setScoreData(await resScores.json());

      // 5. Quiz Performance Comparison
      const resPerf = await fetch(
        `${API_BASE}/admin/dashboard/quiz-performance`,
        { headers }
      );
      if (resPerf.ok) setPerformanceData(await resPerf.json());

      // 6. Question Difficulty Distribution
      const resDiff = await fetch(
        `${API_BASE}/admin/dashboard/question-difficulty${quizParamOnly}`,
        { headers }
      );
      if (resDiff.ok) setDifficultyData(await resDiff.json());

      // Recent Activity
      const resRecent = await fetch(
        `${API_BASE}/admin/dashboard/recent-activity`,
        { headers }
      );
      if (resRecent.ok) setRecentActivity(await resRecent.json());
    } catch {
      // Handled gracefully in empty chart UI states
    }
  }, [authHeaders, quizPeriod, studentPeriod, selectedQuizId]);

  useEffect(() => {
    if (user) {
      fetchOverviewStats();
      fetchChartData();
    }
  }, [user, fetchOverviewStats, fetchChartData]);

  if (authLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <LoadingSkeleton className="w-64 h-8" />
      </div>
    );
  }

  const performanceColumns: TableColumn<QuizPerformanceItem>[] = [
    {
      key: 'title',
      header: 'Quiz Title',
      render: (item) => (
        <span className="font-medium text-white truncate block max-w-xs">{item.title}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-mono capitalize ${
            item.status === 'published'
              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
              : item.status === 'scheduled'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
          }`}
        >
          {item.status}
        </span>
      ),
    },
    {
      key: 'attempts_count',
      header: 'Attempts',
      render: (item) => <span className="font-mono text-slate-300">{item.attempts_count}</span>,
    },
    {
      key: 'average_score',
      header: 'Avg. Score',
      render: (item) => (
        <span className="font-mono text-cyan-300 font-semibold">{item.average_score}%</span>
      ),
    },
    {
      key: 'passing_rate',
      header: 'Pass Rate',
      render: (item) => (
        <span className="font-mono text-emerald-300 font-semibold">{item.passing_rate}%</span>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header Banner & Scoped Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-brand-950/40 via-surface-elevated/80 to-surface-base border border-brand-500/20 shadow-xl backdrop-blur-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2.5 py-0.5 rounded-full font-mono uppercase tracking-wider bg-brand-500/20 text-cyan-300 border border-brand-500/30">
              Scoped Administrator
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {user?.email}
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-display font-bold text-white tracking-tight">
            My Examination Command Center
          </h1>
          <p className="text-xs text-slate-400">
            Metrics and candidate responses filtered strictly by quizzes you authored or have been delegated.
          </p>
        </div>

        {/* Quick Actions (Permission-Gated & Functional) */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {hasPermission('quiz.create') && (
            <Link href="/admin/quiz#create">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-brand-600 hover:bg-brand-500 text-white shadow-glow-primary transition-all">
                <PlusCircle className="w-3.5 h-3.5" />
                Create Quiz
              </button>
            </Link>
          )}

          {hasPermission('question.create') && (
            <Link href="/admin/question-bank">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 text-slate-200 border border-surface-border transition-all">
                <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
                Add Questions
              </button>
            </Link>
          )}

          {hasPermission('quiz.view') && (
            <Link href="/admin/quiz">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 text-slate-200 border border-surface-border transition-all">
                <BookOpen className="w-3.5 h-3.5 text-brand-400" />
                My Quizzes
              </button>
            </Link>
          )}

          {hasPermission('analytics.view') && (
            <Link href="/admin/analytics">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 text-slate-200 border border-surface-border transition-all">
                <BarChart3 className="w-3.5 h-3.5 text-purple-400" />
                View Results
              </button>
            </Link>
          )}

          <button
            onClick={() => {
              fetchOverviewStats();
              fetchChartData();
            }}
            className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-400 hover:text-white transition-all"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStats ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Quiz Filter Bar */}
      {performanceData.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-surface-elevated/40 border border-surface-border text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <Filter className="w-4 h-4 text-cyan-400 shrink-0" />
            <span className="font-medium">Filter Charts by Quiz:</span>
          </div>
          <select
            value={selectedQuizId}
            onChange={(e) => setSelectedQuizId(e.target.value)}
            className="w-full sm:w-auto bg-surface-base border border-surface-border text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="all">All Authorized Quizzes ({performanceData.length})</option>
            {performanceData.map((q) => (
              <option key={q.quiz_id} value={q.quiz_id}>
                {q.title}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* 8 Scoped Database Statistics Cards */}
      {statsError ? (
        <ErrorState
          title="Database Aggregation Error"
          message={statsError}
          onRetry={fetchOverviewStats}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
          <StatCard
            label="My Total Quizzes"
            value={loadingStats ? '...' : (stats?.my_total_quizzes ?? 0)}
            subtitle="Authored &amp; assigned"
            icon={BookOpen}
            variant="cyan"
          />
          <StatCard
            label="My Published Quizzes"
            value={loadingStats ? '...' : (stats?.my_published_quizzes ?? 0)}
            subtitle="Accessible to candidates"
            icon={CheckCircle2}
            variant="brand"
          />
          <StatCard
            label="My Draft Quizzes"
            value={loadingStats ? '...' : (stats?.my_draft_quizzes ?? 0)}
            subtitle="In composition state"
            icon={FileText}
          />
          <StatCard
            label="My Scheduled Quizzes"
            value={loadingStats ? '...' : (stats?.my_scheduled_quizzes ?? 0)}
            subtitle="Future start window"
            icon={Clock}
          />

          <StatCard
            label="My Active Examinations"
            value={loadingStats ? '...' : (stats?.my_active_examinations ?? 0)}
            subtitle="Real-time in-progress attempts"
            icon={Activity}
            variant="brand"
          />
          <StatCard
            label="My Completed Exams"
            value={loadingStats ? '...' : (stats?.my_completed_examinations ?? 0)}
            subtitle="Submissions received"
            icon={Award}
          />
          <StatCard
            label="My Total Candidates"
            value={loadingStats ? '...' : (stats?.my_total_participants ?? 0)}
            subtitle="Distinct participants"
            icon={GraduationCap}
            variant="purple"
          />
          <StatCard
            label="Average Score"
            value={loadingStats ? '...' : `${stats?.my_average_examination_score ?? 0.0}%`}
            subtitle="Across authorized papers"
            icon={BarChart3}
            variant="cyan"
          />
        </div>
      )}

      {/* Section: 6 Scoped Visualizations */}
      <div className="space-y-6 pt-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-display font-bold text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            Scoped Visualizations &amp; Candidate Metrics
          </h2>
          <span className="text-xs text-slate-400 font-mono hidden sm:inline">
            Data strictly isolated to your authorized quizzes
          </span>
        </div>

        {/* Row 1: My Quiz Creation Trends & Student Participation Trends */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: My Quiz Creation Trends */}
          <ChartContainer
            title="Chart 1: My Quiz Creation Trends"
            subtitle="Quizzes authored over time"
            actions={
              <div className="flex items-center bg-surface-base p-1 rounded-lg border border-surface-border text-[11px]">
                {(['daily', 'weekly', 'monthly'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setQuizPeriod(p)}
                    className={`px-2 py-0.5 rounded capitalize transition-colors ${
                      quizPeriod === p
                        ? 'bg-cyan-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            }
          >
            {quizTrends.every((t) => t.count === 0) ? (
              <EmptyState title="No Quizzes Authored" message="Author your first quiz to generate trend records." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={quizTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="cyanArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Quizzes Created"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#cyanArea)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartContainer>

          {/* Chart 2: My Student Participation Trends */}
          <ChartContainer
            title="Chart 2: Candidate Participation Trends"
            subtitle="Attempts &amp; unique students in your quizzes"
            actions={
              <div className="flex items-center bg-surface-base p-1 rounded-lg border border-surface-border text-[11px]">
                {(['daily', 'weekly', 'monthly'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setStudentPeriod(p)}
                    className={`px-2 py-0.5 rounded capitalize transition-colors ${
                      studentPeriod === p
                        ? 'bg-purple-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            }
          >
            {studentTrends.every((t) => t.attempts === 0) ? (
              <EmptyState title="No Student Attempts" message="Invite candidates to start generating participation telemetry." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={studentTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Bar dataKey="attempts" name="Total Attempts" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="unique_students" name="Unique Candidates" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartContainer>
        </div>

        {/* Row 2: Completion Rates & Score Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 3: My Quiz Completion Rates */}
          <ChartContainer
            title="Chart 3: My Quiz Completion Rates"
            subtitle="Attempt status across your authorized quizzes"
          >
            {completionData.length === 0 ? (
              <EmptyState title="No Completion Data" message="No examinations have concluded on your quizzes yet." />
            ) : (
              <div className="h-64 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={completionData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      innerRadius={45}
                      paddingAngle={3}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {completionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color || CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartContainer>

          {/* Chart 4: My Score Distribution */}
          <ChartContainer
            title="Chart 4: My Examination Score Ranges"
            subtitle="Candidate score brackets on your papers"
          >
            {scoreData.every((s) => s.count === 0) ? (
              <EmptyState title="No Scores Recorded" message="Scores will populate as students complete attempts." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scoreData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="range" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      formatter={(val: any, name: any, item: any) => [
                        `${val} candidates (${item.payload.percentage}%)`,
                        'Count',
                      ]}
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="count" fill="#10b981" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartContainer>
        </div>

        {/* Row 3: Performance Comparison & Difficulty Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 5: Performance Comparison Table */}
          <DashboardCard
            title="Chart 5: My Quiz Performance Comparison"
            subtitle="Comparative attempts, averages, and pass rates"
            className="overflow-hidden"
          >
            {performanceData.length === 0 ? (
              <EmptyState title="No Quizzes Configured" message="Create a quiz to view comparative performance." />
            ) : (
              <div className="h-64 overflow-y-auto">
                <ResponsiveTable
                  data={performanceData}
                  columns={performanceColumns}
                  keyExtractor={(item) => item.quiz_id}
                />
              </div>
            )}
          </DashboardCard>

          {/* Chart 6: Question Difficulty Distribution */}
          <ChartContainer
            title="Chart 6: Question Difficulty Distribution"
            subtitle="Easy, Medium, and Hard balance across your quizzes"
          >
            {difficultyData.every((d) => d.count === 0) ? (
              <EmptyState title="No Questions Linked" message="Add questions to your quizzes to inspect difficulty ratios." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={difficultyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="difficulty" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      formatter={(val: any, name: any, item: any) => [
                        `${val} questions (${item.payload.percentage}%)`,
                        'Count',
                      ]}
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartContainer>
        </div>
      </div>

      {/* Scoped Recent Activity Stream */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-display font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-400" />
            Recent Operational Activity
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            Scoped to your authored quizzes
          </span>
        </div>

        <DashboardCard className="p-0 overflow-hidden">
          {recentActivity.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              Zero recent operational actions or modifications logged on your quizzes.
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {recentActivity.map((act) => (
                <div key={act.id} className="p-3.5 sm:px-5 flex items-center justify-between text-xs hover:bg-surface-elevated/40 transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-surface-elevated flex items-center justify-center shrink-0 border border-surface-border">
                      <Activity className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-white truncate">{act.description}</p>
                      <p className="text-[11px] text-slate-400 truncate">
                        Actor: <span className="font-mono text-slate-300">{act.actor_email}</span> • Entity: {act.entity_type}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <span className="text-[10px] text-slate-400 font-mono block">
                      {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono block">
                      {new Date(act.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DashboardCard>
      </div>
    </div>
  );
}
