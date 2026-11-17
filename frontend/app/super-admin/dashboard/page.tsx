'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Users,
  ShieldCheck,
  ShieldAlert,
  Layers,
  HelpCircle,
  BookOpen,
  ClipboardList,
  GraduationCap,
  Award,
  BarChart3,
  Activity,
  FileText,
  PlusCircle,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
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
import { SuperAdminSidebar } from '@/components/layout/SuperAdminSidebar';
import { DashboardTopNavbar } from '@/components/layout/DashboardTopNavbar';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ChartContainer } from '@/components/ui/ChartContainer';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const CHART_COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#3b82f6'];

interface OverviewStats {
  total_user_admins: number;
  active_user_admins: number;
  disabled_user_admins: number;
  total_students: number;
  total_questions: number;
  total_quizzes: number;
  draft_quizzes: number;
  published_quizzes: number;
  scheduled_quizzes: number;
  active_examinations: number;
  completed_examinations: number;
  total_examination_attempts: number;
}

export default function SuperAdminDashboardPage() {
  const { user, token, isSuperAdmin, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Filters for trends
  const [quizPeriod, setQuizPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [studentPeriod, setStudentPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [examPeriod, setExamPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  // Chart datasets
  const [quizTrends, setQuizTrends] = useState<any[]>([]);
  const [studentTrends, setStudentTrends] = useState<any[]>([]);
  const [examTrends, setExamTrends] = useState<any[]>([]);
  const [completionData, setCompletionData] = useState<any[]>([]);
  const [scoreData, setScoreData] = useState<any[]>([]);
  const [questionData, setQuestionData] = useState<any[]>([]);
  const [quizStatusData, setQuizStatusData] = useState<any[]>([]);
  const [adminActivity, setAdminActivity] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  // Guard access: Reject non-super admins
  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else if (!isSuperAdmin) {
        router.push('/admin/dashboard');
      }
    }
  }, [user, isSuperAdmin, authLoading, router]);

  const authHeaders = useCallback(() => {
    return {
      Authorization: `Bearer ${token || localStorage.getItem('quizverse_admin_token')}`,
    };
  }, [token]);

  // Fetch Statistics
  const fetchOverviewStats = useCallback(async () => {
    setLoadingStats(true);
    setStatsError(null);
    try {
      const res = await fetch(`${API_BASE}/super-admin/dashboard/overview`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error('Failed to retrieve overview statistics');
      const data = await res.json();
      setStats(data);
    } catch (err: any) {
      setStatsError(err.message || 'Unable to connect to database');
    } finally {
      setLoadingStats(false);
    }
  }, [authHeaders]);

  // Fetch Charts
  const fetchChartData = useCallback(async () => {
    try {
      const headers = authHeaders();

      // 1. Quiz Trends
      const resQuiz = await fetch(
        `${API_BASE}/super-admin/dashboard/quiz-trends?period=${quizPeriod}`,
        { headers }
      );
      if (resQuiz.ok) setQuizTrends(await resQuiz.json());

      // 2. Student Trends
      const resStudent = await fetch(
        `${API_BASE}/super-admin/dashboard/student-trends?period=${studentPeriod}`,
        { headers }
      );
      if (resStudent.ok) setStudentTrends(await resStudent.json());

      // 3. Exam Participation
      const resExam = await fetch(
        `${API_BASE}/super-admin/dashboard/examination-statistics?period=${examPeriod}`,
        { headers }
      );
      if (resExam.ok) setExamTrends(await resExam.json());

      // 4. Completion breakdown
      const resComp = await fetch(
        `${API_BASE}/super-admin/dashboard/examination-completion`,
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

      // 5. Score Distribution
      const resScores = await fetch(
        `${API_BASE}/super-admin/dashboard/score-distribution`,
        { headers }
      );
      if (resScores.ok) setScoreData(await resScores.json());

      // 6. Question Distribution
      const resQ = await fetch(
        `${API_BASE}/super-admin/dashboard/question-distribution`,
        { headers }
      );
      if (resQ.ok) setQuestionData(await resQ.json());

      // 7. Quiz Status
      const resStatus = await fetch(
        `${API_BASE}/super-admin/dashboard/quiz-status-distribution`,
        { headers }
      );
      if (resStatus.ok) {
        const s = await resStatus.json();
        setQuizStatusData([
          { name: 'Published', count: s.published, color: '#10b981' },
          { name: 'Draft', count: s.draft, color: '#8b5cf6' },
          { name: 'Scheduled', count: s.scheduled, color: '#06b6d4' },
          { name: 'Archived', count: s.archived, color: '#6b7280' },
        ]);
      }

      // 8. Admin Activity
      const resAct = await fetch(
        `${API_BASE}/super-admin/dashboard/admin-activity`,
        { headers }
      );
      if (resAct.ok) setAdminActivity(await resAct.json());

      // Recent Activity
      const resRecent = await fetch(
        `${API_BASE}/super-admin/dashboard/recent-activity`,
        { headers }
      );
      if (resRecent.ok) setRecentActivity(await resRecent.json());
    } catch {
      // Handled gracefully in individual chart states
    }
  }, [authHeaders, quizPeriod, studentPeriod, examPeriod]);

  useEffect(() => {
    if (isSuperAdmin) {
      fetchOverviewStats();
      fetchChartData();
    }
  }, [isSuperAdmin, fetchOverviewStats, fetchChartData]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <LoadingSkeleton className="w-64 h-8" />
      </div>
    );
  }

  if (!isSuperAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen flex bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      {/* Desktop Sidebar (14 Sections) */}
      <SuperAdminSidebar />

      {/* Mobile Drawer */}
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsMobileDrawerOpen(false)}
          />
          <div className="relative z-10">
            <SuperAdminSidebar
              isMobileDrawer
              onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        <DashboardTopNavbar
          title="Super Admin Command Hub"
          breadcrumbs={[
            { label: 'Platform Console', href: '/super-admin/dashboard' },
            { label: 'Overview' },
          ]}
          onToggleSidebar={() => setIsMobileDrawerOpen(!isMobileDrawerOpen)}
          isSidebarOpen={isMobileDrawerOpen}
        />

        <main className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto w-full">
          {/* Header Banner & Quick Actions */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-purple-950/40 via-surface-elevated/80 to-surface-base border border-purple-500/20 shadow-xl backdrop-blur-xl">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] px-2.5 py-0.5 rounded-full font-mono uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Global System Owner
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {user?.email}
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-display font-bold text-white tracking-tight">
                Platform-Wide Real-Time Intelligence
              </h1>
              <p className="text-xs text-slate-400">
                Live metrics aggregated across all User Administrators, academic units, and examination sessions.
              </p>
            </div>

            {/* Quick Actions (Functional, not decorative) */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Link href="/super-admin/admins">
                <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-purple-600 hover:bg-purple-500 text-white shadow-glow-purple transition-all">
                  <Users className="w-3.5 h-3.5" />
                  Manage Admins
                </button>
              </Link>

              <Link href="/super-admin/admins?tab=roles">
                <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 text-slate-200 border border-surface-border transition-all">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  Permissions
                </button>
              </Link>

              <Link href="/admin/quiz">
                <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 text-slate-200 border border-surface-border transition-all">
                  <BookOpen className="w-3.5 h-3.5 text-brand-400" />
                  All Quizzes
                </button>
              </Link>

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

          {/* 12 Real Database Statistics Cards */}
          {statsError ? (
            <ErrorState
              title="Database Aggregation Error"
              message={statsError}
              onRetry={fetchOverviewStats}
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
              <StatCard
                label="Total User Admins"
                value={loadingStats ? '...' : (stats?.total_user_admins ?? 0)}
                subtitle={`${stats?.active_user_admins ?? 0} active, ${stats?.disabled_user_admins ?? 0} disabled`}
                icon={Users}
                variant="purple"
              />
              <StatCard
                label="Total Candidates"
                value={loadingStats ? '...' : (stats?.total_students ?? 0)}
                subtitle="Enrolled student accounts"
                icon={GraduationCap}
                variant="cyan"
              />
              <StatCard
                label="Total Questions"
                value={loadingStats ? '...' : (stats?.total_questions ?? 0)}
                subtitle="Authoring repository"
                icon={HelpCircle}
                variant="brand"
              />
              <StatCard
                label="Total Quizzes"
                value={loadingStats ? '...' : (stats?.total_quizzes ?? 0)}
                subtitle={`${stats?.published_quizzes ?? 0} published, ${stats?.draft_quizzes ?? 0} draft`}
                icon={BookOpen}
                variant="purple"
              />

              <StatCard
                label="Published Quizzes"
                value={loadingStats ? '...' : (stats?.published_quizzes ?? 0)}
                subtitle="Active examination papers"
                icon={CheckCircle2}
              />
              <StatCard
                label="Draft Quizzes"
                value={loadingStats ? '...' : (stats?.draft_quizzes ?? 0)}
                subtitle="In composition state"
                icon={FileText}
              />
              <StatCard
                label="Scheduled Quizzes"
                value={loadingStats ? '...' : (stats?.scheduled_quizzes ?? 0)}
                subtitle="Pending start window"
                icon={Clock}
              />
              <StatCard
                label="Active Exams"
                value={loadingStats ? '...' : (stats?.active_examinations ?? 0)}
                subtitle="Real-time live attempts"
                icon={Activity}
                variant="brand"
              />

              <StatCard
                label="Completed Exams"
                value={loadingStats ? '...' : (stats?.completed_examinations ?? 0)}
                subtitle="Submitted attempts"
                icon={Award}
              />
              <StatCard
                label="Total Attempts"
                value={loadingStats ? '...' : (stats?.total_examination_attempts ?? 0)}
                subtitle="All attempt records"
                icon={ClipboardList}
              />
              <StatCard
                label="Active User Admins"
                value={loadingStats ? '...' : (stats?.active_user_admins ?? 0)}
                subtitle="Authorized operators"
                icon={ShieldCheck}
              />
              <StatCard
                label="Disabled Admins"
                value={loadingStats ? '...' : (stats?.disabled_user_admins ?? 0)}
                subtitle="Sessions terminated"
                icon={ShieldAlert}
              />
            </div>
          )}

          {/* Section: 8 Interactive Visualizations */}
          <div className="space-y-6 pt-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-display font-bold text-white tracking-tight flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                Platform Visualizations &amp; Psychometrics
              </h2>
              <span className="text-xs text-slate-400 font-mono hidden sm:inline">
                Zero fake data • Real SQL Aggregations
              </span>
            </div>

            {/* Row 1: Quiz Trends & Student Trends */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 1: Quiz Creation Trends */}
              <ChartContainer
                title="Chart 1: Quiz Creation Trends"
                subtitle="Volume of quizzes created across periods"
                actions={
                  <div className="flex items-center bg-surface-base p-1 rounded-lg border border-surface-border text-[11px]">
                    {(['daily', 'weekly', 'monthly'] as const).map((p) => (
                      <button
                        key={p}
                        onClick={() => setQuizPeriod(p)}
                        className={`px-2 py-0.5 rounded capitalize transition-colors ${
                          quizPeriod === p
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
                {quizTrends.length === 0 ? (
                  <EmptyState title="No Quiz Trends" message="No quizzes created in this time window." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={quizTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="purpleGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.6} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
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
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#purpleGrad)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartContainer>

              {/* Chart 2: Student Registration Trends */}
              <ChartContainer
                title="Chart 2: Student Registration Trends"
                subtitle="Candidate intake and onboarding over time"
                actions={
                  <div className="flex items-center bg-surface-base p-1 rounded-lg border border-surface-border text-[11px]">
                    {(['daily', 'weekly', 'monthly'] as const).map((p) => (
                      <button
                        key={p}
                        onClick={() => setStudentPeriod(p)}
                        className={`px-2 py-0.5 rounded capitalize transition-colors ${
                          studentPeriod === p
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
                {studentTrends.length === 0 ? (
                  <EmptyState title="No Student Records" message="No candidates registered in this time period." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={studentTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
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
                          name="Students Registered"
                          stroke="#06b6d4"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#cyanGrad)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartContainer>
            </div>

            {/* Row 2: Examination Participation & Completion Status */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 3: Examination Participation */}
              <ChartContainer
                title="Chart 3: Examination Participation Trends"
                subtitle="Total attempts vs unique student candidates"
                actions={
                  <div className="flex items-center bg-surface-base p-1 rounded-lg border border-surface-border text-[11px]">
                    {(['daily', 'weekly', 'monthly'] as const).map((p) => (
                      <button
                        key={p}
                        onClick={() => setExamPeriod(p)}
                        className={`px-2 py-0.5 rounded capitalize transition-colors ${
                          examPeriod === p
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
                {examTrends.length === 0 ? (
                  <EmptyState title="No Examination Attempts" message="No examinations conducted in this range." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={examTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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

              {/* Chart 4: Examination Completion Breakdown */}
              <ChartContainer
                title="Chart 4: Examination Completion Comparison"
                subtitle="Status breakdown: submitted, timed out, abandoned, in progress"
              >
                {completionData.length === 0 ? (
                  <EmptyState title="No Attempts Recorded" message="Zero examination attempts have been logged." />
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
            </div>

            {/* Row 3: Score Distribution & Question Bank Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 5: Score Distribution */}
              <ChartContainer
                title="Chart 5: Examination Score Distribution"
                subtitle="Cohort performance across 20% score intervals"
              >
                {scoreData.every((s) => s.count === 0) ? (
                  <EmptyState title="No Graded Examinations" message="Evaluation results will populate this histogram." />
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
                        <Bar dataKey="count" fill="#06b6d4" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartContainer>

              {/* Chart 6: Question Bank Academic Distribution */}
              <ChartContainer
                title="Chart 6: Question Bank by Academic Unit"
                subtitle="Authoring distribution across curriculum units"
              >
                {questionData.length === 0 ? (
                  <EmptyState title="No Academic Units" message="Configure units and topics in Academic Structure." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={questionData} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                        <XAxis type="number" stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                        <YAxis
                          type="category"
                          dataKey="unit_code"
                          stroke="#94a3b8"
                          fontSize={10}
                          tickLine={false}
                          width={60}
                        />
                        <Tooltip
                          formatter={(val: any, name: any, item: any) => [
                            `${val} questions (${item.payload.unit_name})`,
                            'Questions',
                          ]}
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            borderColor: '#334155',
                            borderRadius: '0.75rem',
                            fontSize: '12px',
                          }}
                        />
                        <Bar dataKey="question_count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartContainer>
            </div>

            {/* Row 4: Quiz Status Distribution & User Admin Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 7: Quiz Status Distribution */}
              <ChartContainer
                title="Chart 7: Quiz Status Distribution"
                subtitle="Draft, published, scheduled, and archived configurations"
              >
                {quizStatusData.every((s) => s.count === 0) ? (
                  <EmptyState title="No Quizzes Configured" message="Quizzes created across the system appear here." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={quizStatusData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                        <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} tickLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} allowDecimals={false} />
                        <Tooltip
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

              {/* Chart 8: User Admin Activity */}
              <ChartContainer
                title="Chart 8: User Admin Operational Activity"
                subtitle="Quizzes authored and question bank contributions by admin"
              >
                {adminActivity.length === 0 ? (
                  <EmptyState title="No User Admins" message="Provision User Admins in Administrator Management." />
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={adminActivity} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                        <XAxis dataKey="full_name" stroke="#94a3b8" fontSize={10} tickLine={false} />
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
                        <Bar dataKey="quizzes_created" name="Quizzes Created" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="questions_created" name="Questions Authored" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartContainer>
            </div>
          </div>

          {/* Real Live Recent Activity Feed */}
          <div className="space-y-4 pt-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-display font-bold text-white tracking-tight flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                Live Administrative Audit Stream
              </h2>
              <Link href="/super-admin/admins?tab=audit">
                <span className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 cursor-pointer">
                  View Full Audit Logs <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </Link>
            </div>

            <DashboardCard className="p-0 overflow-hidden">
              {recentActivity.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  Zero administrative security events or audit entries recorded.
                </div>
              ) : (
                <div className="divide-y divide-surface-border">
                  {recentActivity.map((act) => (
                    <div key={act.id} className="p-3.5 sm:px-5 flex items-center justify-between text-xs hover:bg-surface-elevated/40 transition-colors">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-surface-elevated flex items-center justify-center shrink-0 border border-surface-border">
                          <Activity className="w-4 h-4 text-purple-400" />
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
        </main>
      </div>
    </div>
  );
}
