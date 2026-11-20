'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  Award,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  Download,
  Filter,
  Calendar,
  Layers,
  GraduationCap,
  FileCheck,
  ShieldAlert,
  ArrowUpRight,
  HelpCircle,
  Activity,
  FileText,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
} from 'recharts';
import { useAuth } from '@/contexts/AuthContext';
import {
  analyticsService,
  AnalyticsFilterParams,
  AnalyticsOverviewResponse,
  ExaminationStatsResponse,
  ParticipationAnalyticsResponse,
  PerformanceAnalyticsResponse,
  PassFailAnalyticsResponse,
  ScoreDistributionResponse,
  AcademicPerformanceResponse,
  ExaminationTrendsResponse,
  EvaluationAnalyticsResponse,
  QuestionBankAnalyticsResponse,
  QuestionEffectivenessResponse,
  FilterOptionsResponse,
} from '@/services/analyticsService';

const PIE_COLORS = ['#10b981', '#f43f5e', '#06b6d4', '#f59e0b', '#8b5cf6', '#ec4899'];
const SCORE_COLORS = ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#10b981', '#06b6d4', '#3b82f6', '#8b5cf6'];

export function AnalyticsDashboardView() {
  const { token, isSuperAdmin } = useAuth();

  // Active Tab
  const [activeTab, setActiveTab] = useState<
    'overview' | 'examinations' | 'participation' | 'performance' | 'pass-fail' | 'distribution' | 'evaluations' | 'question-bank' | 'trends'
  >('overview');

  // Filter States
  const [datePreset, setDatePreset] = useState<'all' | '7d' | '30d' | '90d'>('all');
  const [selectedQuiz, setSelectedQuiz] = useState<string>('all');
  const [selectedProgramme, setSelectedProgramme] = useState<string>('all');
  const [selectedSubject, setSelectedSubject] = useState<string>('all');
  const [selectedYear, setSelectedYear] = useState<string>('all');

  // Filter Options
  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse | null>(null);

  // Data States
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null);
  const [examStats, setExamStats] = useState<ExaminationStatsResponse | null>(null);
  const [participation, setParticipation] = useState<ParticipationAnalyticsResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceAnalyticsResponse | null>(null);
  const [passFail, setPassFail] = useState<PassFailAnalyticsResponse | null>(null);
  const [distribution, setDistribution] = useState<ScoreDistributionResponse | null>(null);
  const [academic, setAcademic] = useState<AcademicPerformanceResponse | null>(null);
  const [trends, setTrends] = useState<ExaminationTrendsResponse | null>(null);
  const [evaluations, setEvaluations] = useState<EvaluationAnalyticsResponse | null>(null);
  const [questionBank, setQuestionBank] = useState<QuestionBankAnalyticsResponse | null>(null);
  const [effectiveness, setEffectiveness] = useState<QuestionEffectivenessResponse | null>(null);

  // Compute active filters
  const currentFilters = useMemo((): AnalyticsFilterParams => {
    const filters: AnalyticsFilterParams = {};
    if (datePreset !== 'all') {
      const now = new Date();
      const past = new Date();
      if (datePreset === '7d') past.setDate(now.getDate() - 7);
      if (datePreset === '30d') past.setDate(now.getDate() - 30);
      if (datePreset === '90d') past.setDate(now.getDate() - 90);
      filters.start_date = past.toISOString();
      filters.end_date = now.toISOString();
    }
    if (selectedQuiz !== 'all') filters.quiz_id = selectedQuiz;
    if (selectedProgramme !== 'all') filters.programme_id = selectedProgramme;
    if (selectedSubject !== 'all') filters.subject_id = selectedSubject;
    if (selectedYear !== 'all') filters.academic_year = selectedYear;
    return filters;
  }, [datePreset, selectedQuiz, selectedProgramme, selectedSubject, selectedYear]);

  // Load filter dropdown options once
  useEffect(() => {
    if (!token) return;
    analyticsService.getFilterOptions(token)
      .then(setFilterOptions)
      .catch((err) => console.error('Failed to load filter options:', err));
  }, [token]);

  // Fetch Tab-Specific Data
  const loadTabContent = useCallback(async (isRefresh = false) => {
    if (!token) return;
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      // Always load Overview for top stats
      const [ovData] = await Promise.all([
        analyticsService.getOverview(token, currentFilters),
      ]);
      setOverview(ovData);

      // Load specific tab dataset
      if (activeTab === 'overview') {
        const [pData, pfData, trData] = await Promise.all([
          analyticsService.getPerformance(token, currentFilters),
          analyticsService.getPassFail(token, currentFilters),
          analyticsService.getExaminationTrends(token, currentFilters, 'day'),
        ]);
        setPerformance(pData);
        setPassFail(pfData);
        setTrends(trData);
      } else if (activeTab === 'examinations') {
        const [eData, trData] = await Promise.all([
          analyticsService.getExaminationStats(token, currentFilters),
          analyticsService.getExaminationTrends(token, currentFilters, 'day'),
        ]);
        setExamStats(eData);
        setTrends(trData);
      } else if (activeTab === 'participation') {
        const pData = await analyticsService.getParticipation(token, currentFilters);
        setParticipation(pData);
      } else if (activeTab === 'performance') {
        const [perfData, acData] = await Promise.all([
          analyticsService.getPerformance(token, currentFilters),
          analyticsService.getAcademicPerformance(token, currentFilters),
        ]);
        setPerformance(perfData);
        setAcademic(acData);
      } else if (activeTab === 'pass-fail') {
        const pfData = await analyticsService.getPassFail(token, currentFilters);
        setPassFail(pfData);
      } else if (activeTab === 'distribution') {
        const dData = await analyticsService.getScoreDistribution(token, currentFilters);
        setDistribution(dData);
      } else if (activeTab === 'evaluations') {
        const evData = await analyticsService.getEvaluations(token, currentFilters);
        setEvaluations(evData);
      } else if (activeTab === 'question-bank') {
        const [qbData, effData] = await Promise.all([
          analyticsService.getQuestionBankAnalytics(token, currentFilters),
          analyticsService.getQuestionEffectiveness(token, currentFilters),
        ]);
        setQuestionBank(qbData);
        setEffectiveness(effData);
      } else if (activeTab === 'trends') {
        const trData = await analyticsService.getExaminationTrends(token, currentFilters, 'day');
        setTrends(trData);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch database analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, activeTab, currentFilters]);

  useEffect(() => {
    loadTabContent();
  }, [loadTabContent]);

  const handleResetFilters = () => {
    setDatePreset('all');
    setSelectedQuiz('all');
    setSelectedProgramme('all');
    setSelectedSubject('all');
    setSelectedYear('all');
  };

  const renderTrendIcon = (trend?: string) => {
    if (trend === 'up') return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
    if (trend === 'down') return <TrendingDown className="w-3.5 h-3.5 text-rose-400" />;
    return <Minus className="w-3.5 h-3.5 text-slate-400" />;
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner / Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/20 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  Academic Analytics & Examination Reports
                </h1>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase border ${
                  isSuperAdmin
                    ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                    : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                }`}>
                  {isSuperAdmin ? 'Global Platform Scope' : 'Authorized Quizzes Scope'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Official institutional analytics derived strictly from production examination database records.
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/admin/analytics/reports"
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-primary-600 hover:from-cyan-400 hover:to-primary-500 text-slate-950 flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Reporting Center</span>
          </Link>
          <button
            onClick={() => loadTabContent(true)}
            disabled={refreshing || loading}
            className="px-3.5 py-2 rounded-xl text-xs font-medium bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 flex items-center gap-2 transition-colors disabled:opacity-50"
            title="Refresh database aggregations"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Freshness Indicator */}
      {overview && (
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Database Aggregation Freshness: {new Date(overview.freshness_timestamp).toLocaleTimeString()} ({overview.period_label})</span>
          </div>
          <span>Strict DB Aggregations (Zero Mock Data)</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            <span>Dynamic Query Filters</span>
          </div>
          <button
            onClick={handleResetFilters}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 underline font-medium"
          >
            Reset Filters
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
          {/* Date Range Preset */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Time Horizon</label>
            <select
              value={datePreset}
              onChange={(e) => setDatePreset(e.target.value as any)}
              className="w-full bg-slate-900 border border-slate-700/70 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All-Time Cumulative</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
          </div>

          {/* Quiz Selector */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Examination Quiz</label>
            <select
              value={selectedQuiz}
              onChange={(e) => setSelectedQuiz(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700/70 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 truncate"
            >
              <option value="all">All Authorized Quizzes</option>
              {filterOptions?.quizzes.map((q) => (
                <option key={q.id} value={q.id}>{q.title}</option>
              ))}
            </select>
          </div>

          {/* Programme Selector */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Academic Programme</label>
            <select
              value={selectedProgramme}
              onChange={(e) => setSelectedProgramme(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700/70 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 truncate"
            >
              <option value="all">All Programmes</option>
              {filterOptions?.programmes.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
              ))}
            </select>
          </div>

          {/* Subject Selector */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Subject</label>
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700/70 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 truncate"
            >
              <option value="all">All Subjects</option>
              {filterOptions?.subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
              ))}
            </select>
          </div>

          {/* Academic Year Selector */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Academic Year</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700/70 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Cohorts / Sessions</option>
              {filterOptions?.academic_years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Primary KPI Cards (Always visible from overview) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Quizzes */}
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Quizzes</span>
            <BookOpen className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {overview ? overview.total_quizzes : '-'}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Published: {overview?.published_quizzes || 0}</span>
            {overview?.comparison?.total_quizzes && (
              <span className="flex items-center gap-1 font-semibold text-emerald-400">
                {renderTrendIcon(overview.comparison.total_quizzes.trend)}
                {overview.comparison.total_quizzes.percentage_change !== null ? `${overview.comparison.total_quizzes.percentage_change}%` : 'New'}
              </span>
            )}
          </div>
        </div>

        {/* Total Candidates Registered */}
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Registered Candidates</span>
            <Users className="w-4 h-4 text-primary-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {overview ? overview.total_registered_participants : '-'}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Attempts: {overview?.total_attempts || 0}</span>
            {overview?.comparison?.total_registered_participants && (
              <span className="flex items-center gap-1 font-semibold text-primary-400">
                {renderTrendIcon(overview.comparison.total_registered_participants.trend)}
                {overview.comparison.total_registered_participants.percentage_change !== null ? `${overview.comparison.total_registered_participants.percentage_change}%` : 'New'}
              </span>
            )}
          </div>
        </div>

        {/* Completed Attempts */}
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Completed Attempts</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {overview ? overview.submitted_attempts : '-'}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Results Published: {overview?.published_results || 0}</span>
            <span className="text-emerald-400 font-semibold">
              {overview && overview.total_attempts > 0 ? `${Math.round((overview.submitted_attempts / overview.total_attempts) * 100)}%` : '0%'}
            </span>
          </div>
        </div>

        {/* Pass Rate */}
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Overall Pass Rate</span>
            <Award className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {overview ? `${overview.overall_pass_percentage}%` : '-'}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Avg Score: {overview?.average_score_percentage || 0}%</span>
            {overview?.comparison?.overall_pass_percentage && (
              <span className="flex items-center gap-1 font-semibold text-amber-400">
                {renderTrendIcon(overview.comparison.overall_pass_percentage.trend)}
                {overview.comparison.overall_pass_percentage.percentage_change !== null ? `${overview.comparison.overall_pass_percentage.percentage_change}%` : '0%'}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2 border-b border-surface-border text-xs scrollbar-thin">
        {[
          { id: 'overview', label: 'Executive Overview', icon: Activity },
          { id: 'examinations', label: 'Examinations', icon: BookOpen },
          { id: 'participation', label: 'Participation Funnel', icon: Users },
          { id: 'performance', label: 'Academic Performance', icon: GraduationCap },
          { id: 'pass-fail', label: 'Pass / Fail Analysis', icon: Award },
          { id: 'distribution', label: 'Score Distribution', icon: BarChart3 },
          { id: 'evaluations', label: 'Evaluations & Grading', icon: FileCheck },
          { id: 'question-bank', label: 'Question Bank & Items', icon: HelpCircle },
          { id: 'trends', label: 'Historical Trends', icon: TrendingUp },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-2 rounded-xl font-semibold flex items-center gap-2 whitespace-nowrap transition-colors ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <div>{error}</div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !overview && (
        <div className="h-64 rounded-2xl bg-surface-card border border-surface-border flex items-center justify-center text-slate-400 text-xs">
          <RefreshCw className="w-5 h-5 animate-spin mr-2 text-cyan-400" />
          Aggregating database analytics...
        </div>
      )}

      {/* TAB CONTENT */}

      {/* 1. EXECUTIVE OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Quick Performance Summary */}
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Award className="w-4 h-4 text-cyan-400" />
                <span>Performance & Score Metrics</span>
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Evaluated Students</span>
                  <span className="text-lg font-bold text-white">{performance?.total_evaluated_students || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Average Marks</span>
                  <span className="text-lg font-bold text-cyan-300">{performance?.average_marks || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Highest Marks</span>
                  <span className="text-lg font-bold text-emerald-400">{performance?.highest_marks || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Lowest Marks</span>
                  <span className="text-lg font-bold text-rose-400">{performance?.lowest_marks || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Median Marks</span>
                  <span className="text-lg font-bold text-white">{performance?.median_marks || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Eval Completion</span>
                  <span className="text-lg font-bold text-amber-400">{performance?.evaluation_completion_rate || 0}%</span>
                </div>
              </div>
            </div>

            {/* Pass vs Fail Donut Chart */}
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span>Pass vs Fail Outcome Proportion</span>
              </h3>
              <div className="h-52 flex items-center justify-center">
                {passFail && (passFail.overall_pass_count > 0 || passFail.overall_fail_count > 0) ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Passed', value: passFail.overall_pass_count },
                          { name: 'Failed', value: passFail.overall_fail_count },
                        ]}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={5}
                      >
                        <Cell fill="#10b981" />
                        <Cell fill="#f43f5e" />
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#1e293b', borderRadius: '12px' }} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-slate-500">No evaluated examination records found.</div>
                )}
              </div>
            </div>
          </div>

          {/* 14-Day Examination Trajectory Chart */}
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span>Examination Activity Trajectory (14 Days)</span>
            </h3>
            <div className="h-64">
              {trends && trends.data_points.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trends.data_points}>
                    <defs>
                      <linearGradient id="colorAttempts" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="label" stroke="#64748b" textAnchor="end" fontSize={10} />
                    <YAxis stroke="#64748b" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#1e293b', borderRadius: '12px' }} />
                    <Legend verticalAlign="top" height={36} />
                    <Area type="monotone" dataKey="attempts" name="Total Attempts" stroke="#06b6d4" fillOpacity={1} fill="url(#colorAttempts)" />
                    <Area type="monotone" dataKey="completed" name="Completed" stroke="#10b981" fillOpacity={1} fill="url(#colorCompleted)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  No activity points recorded in this period.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2. EXAMINATION STATS */}
      {activeTab === 'examinations' && examStats && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Total Configured</span>
              <div className="text-xl font-bold text-white mt-1">{examStats.total_quizzes}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Active Live</span>
              <div className="text-xl font-bold text-cyan-400 mt-1">{examStats.active_examinations}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Completed</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">{examStats.completed_examinations}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Avg Duration</span>
              <div className="text-xl font-bold text-amber-400 mt-1">{examStats.avg_duration_minutes} min</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white">Quizzes by Lifecycle Status</h3>
              <div className="space-y-2 text-xs">
                {Object.entries(examStats.quizzes_by_status).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="capitalize text-slate-300 font-medium">{status}</span>
                    <span className="font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white">Quizzes by Category</h3>
              <div className="space-y-2 text-xs">
                {Object.entries(examStats.quizzes_by_category).map(([cat, count]) => (
                  <div key={cat} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="capitalize text-slate-300 font-medium">{cat}</span>
                    <span className="font-bold text-primary-400 px-2 py-0.5 rounded bg-primary-500/10 border border-primary-500/20">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. PARTICIPATION FUNNEL */}
      {activeTab === 'participation' && participation && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" />
                <span>Candidate Conversion Funnel</span>
              </h3>
              <div className="flex items-center gap-4 text-xs">
                <span>Completion Rate: <strong className="text-emerald-400">{participation.completion_rate}%</strong></span>
                <span>Conversion Rate: <strong className="text-cyan-400">{participation.conversion_rate}%</strong></span>
              </div>
            </div>

            {/* Funnel Progress Bars */}
            <div className="space-y-3">
              {[
                { label: 'Registered Candidates', count: participation.registered_participants, color: 'bg-indigo-500' },
                { label: 'Started Examination Attempts', count: participation.started_attempts, color: 'bg-cyan-500' },
                { label: 'Submitted Examination Attempts', count: participation.submitted_attempts, color: 'bg-emerald-500' },
                { label: 'Completed Students', count: participation.completed_participants, color: 'bg-teal-500' },
                { label: 'Unstarted Candidates', count: participation.unstarted_participants, color: 'bg-slate-600' },
                { label: 'Expired / Timed-out', count: participation.expired_attempts, color: 'bg-rose-500' },
              ].map((step) => {
                const max = Math.max(participation.registered_participants, participation.started_attempts, 1);
                const pct = Math.min(100, Math.round((step.count / max) * 100));
                return (
                  <div key={step.label} className="space-y-1 text-xs">
                    <div className="flex justify-between text-slate-300">
                      <span>{step.label}</span>
                      <span className="font-bold text-white">{step.count} ({pct}%)</span>
                    </div>
                    <div className="h-2.5 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
                      <div className={`h-full rounded-full ${step.color}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Demographic / College Breakdown */}
          {participation.college_distribution.length > 0 && (
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white">Top Participating Institutions / Colleges</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                {participation.college_distribution.map((c, i) => (
                  <div key={i} className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                    <span className="text-slate-300 truncate font-medium">{c.name}</span>
                    <span className="font-bold text-cyan-400 shrink-0 ml-2">{c.count} students</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. ACADEMIC PERFORMANCE */}
      {activeTab === 'performance' && academic && (
        <div className="space-y-6">
          {/* Programme Breakdown Table */}
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-cyan-400" />
              <span>Performance by Academic Programme</span>
            </h3>
            {academic.by_programme.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-surface-border text-[10px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="py-2.5 px-3">Programme</th>
                      <th className="py-2.5 px-3">Evaluated Students</th>
                      <th className="py-2.5 px-3">Average %</th>
                      <th className="py-2.5 px-3">Pass Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {academic.by_programme.map((p) => (
                      <tr key={p.id} className="hover:bg-surface-elevated">
                        <td className="py-2.5 px-3 font-semibold text-white">{p.name}</td>
                        <td className="py-2.5 px-3">{p.students}</td>
                        <td className="py-2.5 px-3 font-mono text-cyan-300">{p.average_percentage}%</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            p.pass_rate >= 50 ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300'
                          }`}>
                            {p.pass_rate}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-slate-500">No programme breakdown records available.</div>
            )}
          </div>

          {/* Subject Breakdown Table */}
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary-400" />
              <span>Performance by Subject</span>
            </h3>
            {academic.by_subject.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-surface-border text-[10px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="py-2.5 px-3">Subject</th>
                      <th className="py-2.5 px-3">Evaluated Students</th>
                      <th className="py-2.5 px-3">Average %</th>
                      <th className="py-2.5 px-3">Pass Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {academic.by_subject.map((s) => (
                      <tr key={s.id} className="hover:bg-surface-elevated">
                        <td className="py-2.5 px-3 font-semibold text-white">{s.name}</td>
                        <td className="py-2.5 px-3">{s.students}</td>
                        <td className="py-2.5 px-3 font-mono text-cyan-300">{s.average_percentage}%</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            s.pass_rate >= 50 ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300'
                          }`}>
                            {s.pass_rate}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-slate-500">No subject breakdown records available.</div>
            )}
          </div>
        </div>
      )}

      {/* 5. PASS / FAIL ANALYSIS */}
      {activeTab === 'pass-fail' && passFail && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white">Subject-wise Pass Rates</h3>
              {passFail.subject_wise.length > 0 ? (
                <div className="space-y-3 text-xs">
                  {passFail.subject_wise.map((sw, i) => (
                    <div key={i} className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                      <div className="flex justify-between items-center text-slate-200">
                        <span className="font-semibold">{sw.name}</span>
                        <span className="text-emerald-400 font-bold">{sw.pass_percentage}% Pass</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400">
                        <span>Passed: <strong className="text-white">{sw.passed}</strong></span>
                        <span>Failed: <strong className="text-white">{sw.failed}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500">No subject records found.</div>
              )}
            </div>

            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-white">Programme-wise Pass Rates</h3>
              {passFail.programme_wise.length > 0 ? (
                <div className="space-y-3 text-xs">
                  {passFail.programme_wise.map((pw, i) => (
                    <div key={i} className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                      <div className="flex justify-between items-center text-slate-200">
                        <span className="font-semibold">{pw.name}</span>
                        <span className="text-emerald-400 font-bold">{pw.pass_percentage}% Pass</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400">
                        <span>Passed: <strong className="text-white">{pw.passed}</strong></span>
                        <span>Failed: <strong className="text-white">{pw.failed}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500">No programme records found.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 6. SCORE DISTRIBUTION HISTOGRAM */}
      {activeTab === 'distribution' && distribution && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                <span>10-Band Percentage Marks Histogram (0% – 100%)</span>
              </h3>
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <span>Total Results: <strong>{distribution.total_results}</strong></span>
                <span>Median: <strong className="text-cyan-400">{distribution.median_percentage}%</strong></span>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distribution.score_bands}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="band" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#090d16', borderColor: '#1e293b', borderRadius: '12px' }}
                    formatter={(val: any, name: any, item: any) => [`${val} students (${item.payload.percentage}%)`, 'Students']}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {distribution.score_bands.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={SCORE_COLORS[index % SCORE_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* 7. EVALUATIONS & GRADING WORKLOAD */}
      {activeTab === 'evaluations' && evaluations && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Auto-Evaluated</span>
              <span className="text-xl font-bold text-white mt-1 block">{evaluations.auto_evaluations_completed}</span>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Manual Pending</span>
              <span className="text-xl font-bold text-amber-400 mt-1 block">{evaluations.manual_evaluations_pending}</span>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Manual Done</span>
              <span className="text-xl font-bold text-emerald-400 mt-1 block">{evaluations.manual_evaluations_completed}</span>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">In Moderation</span>
              <span className="text-xl font-bold text-purple-400 mt-1 block">{evaluations.awaiting_moderation}</span>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Published Results</span>
              <span className="text-xl font-bold text-cyan-400 mt-1 block">{evaluations.published_results}</span>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Corrections Audit</span>
              <span className="text-xl font-bold text-rose-400 mt-1 block">{evaluations.result_corrections_count}</span>
            </div>
          </div>

          {/* Evaluator Workload Table */}
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <h3 className="text-sm font-semibold text-white">Evaluator Grading Distribution</h3>
            {evaluations.evaluator_workload.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-surface-border text-[10px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="py-2.5 px-3">Evaluator</th>
                      <th className="py-2.5 px-3">Completed Evaluations</th>
                      <th className="py-2.5 px-3">Pending Workload</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {evaluations.evaluator_workload.map((ev) => (
                      <tr key={ev.evaluator_id} className="hover:bg-surface-elevated">
                        <td className="py-2.5 px-3 font-semibold text-white">{ev.evaluator_name}</td>
                        <td className="py-2.5 px-3 font-mono text-emerald-400">{ev.evaluated_count}</td>
                        <td className="py-2.5 px-3 font-mono text-amber-400">{ev.pending_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-slate-500">No manual evaluator workloads recorded yet.</div>
            )}
          </div>
        </div>
      )}

      {/* 8. QUESTION BANK & PSYCHOMETRICS */}
      {activeTab === 'question-bank' && questionBank && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Total Items in Pool</span>
              <div className="text-xl font-bold text-white mt-1">{questionBank.total_questions}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Approved Questions</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">{questionBank.approved_questions}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Used in Examinations</span>
              <div className="text-xl font-bold text-cyan-400 mt-1">{questionBank.used_in_examinations_count}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
              <span className="text-[10px] uppercase font-bold text-slate-400">Draft Status</span>
              <div className="text-xl font-bold text-amber-400 mt-1">{questionBank.draft_questions}</div>
            </div>
          </div>

          {/* Psychometric Item Effectiveness Table */}
          {effectiveness && (
            <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>Item Discrimination & Psychometric Effectiveness</span>
                </h3>
                <span className="text-xs text-slate-400">Total Analyzed: <strong>{effectiveness.total_evaluated_questions}</strong></span>
              </div>

              {effectiveness.items.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="border-b border-surface-border text-[10px] uppercase font-bold text-slate-400">
                      <tr>
                        <th className="py-2.5 px-3">Question Statement</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Presented</th>
                        <th className="py-2.5 px-3">Accuracy %</th>
                        <th className="py-2.5 px-3">Assigned Diff</th>
                        <th className="py-2.5 px-3">Observed Diff</th>
                        <th className="py-2.5 px-3">Sample Validity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {effectiveness.items.map((item) => (
                        <tr key={item.question_id} className="hover:bg-surface-elevated">
                          <td className="py-2.5 px-3 max-w-xs truncate text-white font-medium" title={item.question_text}>
                            {item.question_text}
                          </td>
                          <td className="py-2.5 px-3 uppercase text-[10px] text-slate-400">{item.question_type}</td>
                          <td className="py-2.5 px-3 font-mono">{item.times_presented}</td>
                          <td className="py-2.5 px-3 font-mono text-cyan-300">{item.correct_percentage}%</td>
                          <td className="py-2.5 px-3 capitalize">{item.assigned_difficulty}</td>
                          <td className="py-2.5 px-3 capitalize font-semibold text-amber-300">{item.observed_difficulty}</td>
                          <td className="py-2.5 px-3">
                            {item.sample_warning ? (
                              <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20" title={item.warning_message || 'Low sample size'}>
                                <AlertTriangle className="w-3 h-3" />
                                <span>Low Sample (&lt;10)</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Reliable</span>
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-xs text-slate-500">No evaluated question responses available yet.</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 9. HISTORICAL TRENDS */}
      {activeTab === 'trends' && trends && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <h3 className="text-sm font-semibold text-white">Daily Examination Volume & Completions</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends.data_points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="label" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#1e293b', borderRadius: '12px' }} />
                  <Legend verticalAlign="top" height={36} />
                  <Line type="monotone" dataKey="attempts" name="Total Attempts" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="completed" name="Completed" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="average_score" name="Avg Score %" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
