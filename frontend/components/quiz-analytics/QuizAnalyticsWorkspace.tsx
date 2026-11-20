'use client';

import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Users,
  GraduationCap,
  HelpCircle,
  Layers,
  BookOpen,
  PieChart,
  Clock,
  AlertOctagon,
  ShieldAlert,
  GitCompare,
  FileSpreadsheet,
  Download,
  Calendar,
  Award,
  RefreshCw,
  ChevronRight,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Check,
  Flag,
  Info,
} from 'lucide-react';
import {
  quizAnalyticsService,
  QuizOverviewAnalytics,
  QuizParticipantAnalytics,
  StudentPerformanceListResponse,
  StudentPerformanceItem,
  StudentProfileAnalytics,
  QuizQuestionAnalysisResponse,
  QuestionAnalysisItem,
  QuizSectionAnalysisResponse,
  QuizAcademicAnalysisResponse,
  QuizDifficultyAnalysisResponse,
  QuizQuestionTypeAnalysisResponse,
  TimeAnalysisResponse,
  NegativeMarkingAnalysisResponse,
  SecuritySummaryResponse,
  StudentComparisonResponse,
  ReportItem,
} from '@/services/quizAnalyticsService';

interface QuizAnalyticsWorkspaceProps {
  quizId: string;
  token: string;
  userRole?: string;
  onBack?: () => void;
  initialStudentId?: string;
}

export type AnalyticsTab =
  | 'overview'
  | 'participants'
  | 'students'
  | 'student_profile'
  | 'questions'
  | 'sections_academic'
  | 'difficulty_types'
  | 'time_negative'
  | 'security'
  | 'compare'
  | 'reports';

export function QuizAnalyticsWorkspace({
  quizId,
  token,
  userRole = 'admin',
  onBack,
  initialStudentId,
}: QuizAnalyticsWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>(initialStudentId ? 'student_profile' : 'overview');
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(initialStudentId || null);

  // Data states
  const [overview, setOverview] = useState<QuizOverviewAnalytics | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = async () => {
    try {
      setLoadingOverview(true);
      setError(null);
      const data = await quizAnalyticsService.getOverview(token, quizId);
      setOverview(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load quiz analytics');
    } finally {
      setLoadingOverview(false);
    }
  };

  useEffect(() => {
    if (quizId && token) {
      loadOverview();
    }
  }, [quizId, token]);

  const viewStudent = (studentId: string) => {
    setSelectedStudentId(studentId);
    setActiveTab('student_profile');
  };

  const navItems = [
    { key: 'overview', label: 'Overview', icon: BarChart3 },
    { key: 'participants', label: 'Participants', icon: Users },
    { key: 'students', label: 'Student Performance', icon: GraduationCap },
    { key: 'questions', label: 'Question Analysis', icon: HelpCircle },
    { key: 'sections_academic', label: 'Sections & Academic', icon: Layers },
    { key: 'difficulty_types', label: 'Difficulty & Types', icon: PieChart },
    { key: 'time_negative', label: 'Time & Penalties', icon: Clock },
    { key: 'security', label: 'Security & Integrity', icon: ShieldAlert },
    { key: 'compare', label: 'Student Comparison', icon: GitCompare },
    { key: 'reports', label: 'Exports & Reports', icon: FileSpreadsheet },
  ];

  const meta = overview?.quiz_info;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-3">
              {onBack && (
                <button
                  onClick={onBack}
                  className="p-1.5 rounded-xl border border-surface-border hover:bg-surface-elevated text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
              )}
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                {meta?.title || 'Examination Analytics'}
              </h1>
              {meta?.published_version && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  Version {meta.published_version}
                </span>
              )}
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                {meta?.status || 'Active'}
              </span>
            </div>
            <p className="text-xs text-slate-400 flex flex-wrap items-center gap-x-4 gap-y-1">
              {meta?.subject_name && (
                <span className="flex items-center gap-1.5 text-slate-300">
                  <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                  {meta.subject_name}
                </span>
              )}
              {meta?.programme_name && <span>Programme: {meta.programme_name}</span>}
              {meta?.semester_name && <span>Semester: {meta.semester_name}</span>}
              {meta?.creation_mode && <span className="capitalize">Mode: {meta.creation_mode}</span>}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadOverview}
              disabled={loadingOverview}
              className="px-3 py-2 rounded-xl text-xs font-medium border border-surface-border hover:bg-surface-elevated text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingOverview ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setActiveTab('reports')}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white flex items-center gap-1.5 shadow-md shadow-primary-900/30 transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              Download Report
            </button>
          </div>
        </div>

        {/* Quick Parameters Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mt-5 pt-4 border-t border-surface-border/60 text-xs text-slate-300">
          <div>
            <span className="text-slate-500 block text-[11px]">Maximum Marks</span>
            <span className="font-semibold text-white font-mono">{meta?.max_marks || 0} pts</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Exam Duration</span>
            <span className="font-semibold text-white font-mono">{meta?.duration_minutes || 0} mins</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Questions</span>
            <span className="font-semibold text-white font-mono">{meta?.total_questions || 0}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Eligible Students</span>
            <span className="font-semibold text-white font-mono">{overview?.total_eligible || 0}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Finalized Attempts</span>
            <span className="font-semibold text-emerald-400 font-mono">{overview?.completed_evaluations || 0}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Completion Rate</span>
            <span className="font-semibold text-cyan-400 font-mono">{overview?.completion_rate?.toFixed(1) || 0}%</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-surface-border scrollbar-none">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.key;
          return (
            <button
              key={item.key}
              onClick={() => {
                setActiveTab(item.key as AnalyticsTab);
                if (item.key !== 'student_profile') setSelectedStudentId(null);
              }}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-primary-600 text-white shadow-md shadow-primary-900/40'
                  : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {item.label}
            </button>
          );
        })}
        {selectedStudentId && activeTab === 'student_profile' && (
          <button
            onClick={() => setActiveTab('student_profile')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap bg-cyan-600 text-white shadow-md"
          >
            <GraduationCap className="w-3.5 h-3.5" />
            Student Profile Card
          </button>
        )}
      </div>

      {/* Tab View Container */}
      {error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      ) : activeTab === 'overview' ? (
        <OverviewTabView overview={overview} loading={loadingOverview} onViewStudent={viewStudent} />
      ) : activeTab === 'participants' ? (
        <ParticipantsTabView quizId={quizId} token={token} onViewStudent={viewStudent} />
      ) : activeTab === 'students' ? (
        <StudentsTabView quizId={quizId} token={token} onViewStudent={viewStudent} />
      ) : activeTab === 'student_profile' && selectedStudentId ? (
        <StudentProfileTabView
          quizId={quizId}
          studentId={selectedStudentId}
          token={token}
          onBack={() => setActiveTab('students')}
        />
      ) : activeTab === 'questions' ? (
        <QuestionsTabView quizId={quizId} token={token} />
      ) : activeTab === 'sections_academic' ? (
        <SectionsAcademicTabView quizId={quizId} token={token} />
      ) : activeTab === 'difficulty_types' ? (
        <DifficultyTypesTabView quizId={quizId} token={token} />
      ) : activeTab === 'time_negative' ? (
        <TimeNegativeTabView quizId={quizId} token={token} />
      ) : activeTab === 'security' ? (
        <SecurityTabView quizId={quizId} token={token} />
      ) : activeTab === 'compare' ? (
        <CompareTabView quizId={quizId} token={token} />
      ) : activeTab === 'reports' ? (
        <ReportsTabView quizId={quizId} token={token} />
      ) : null}
    </div>
  );
}

// =========================================================================
// 1. Overview Tab
// =========================================================================
function OverviewTabView({
  overview,
  loading,
  onViewStudent,
}: {
  overview: QuizOverviewAnalytics | null;
  loading: boolean;
  onViewStudent: (id: string) => void;
}) {
  if (loading) {
    return <div className="p-12 text-center text-slate-400">Loading comprehensive quiz analytics...</div>;
  }
  if (!overview) return null;

  const kpis = [
    { label: 'Registered', val: overview.total_registered, color: 'text-slate-200' },
    { label: 'Started', val: overview.started_attempts, color: 'text-cyan-400' },
    { label: 'Submitted', val: overview.submitted_attempts, color: 'text-blue-400' },
    { label: 'Evaluated', val: overview.completed_evaluations, color: 'text-emerald-400' },
    { label: 'Passed', val: overview.pass_count, color: 'text-emerald-400' },
    { label: 'Failed', val: overview.fail_count, color: 'text-rose-400' },
    { label: 'Pass Rate', val: `${overview.pass_percentage.toFixed(1)}%`, color: 'text-emerald-400' },
    { label: 'Average', val: `${overview.average_percentage.toFixed(1)}%`, color: 'text-cyan-400' },
    { label: 'Median', val: `${overview.median_percentage.toFixed(1)}%`, color: 'text-indigo-400' },
    { label: 'Highest', val: `${overview.highest_percentage.toFixed(1)}%`, color: 'text-emerald-300' },
    { label: 'Lowest', val: `${overview.lowest_percentage.toFixed(1)}%`, color: 'text-amber-400' },
    { label: 'Completion', val: `${overview.completion_rate.toFixed(1)}%`, color: 'text-cyan-300' },
  ];

  return (
    <div className="space-y-6">
      {/* 12 KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {kpis.map((k, idx) => (
          <div key={idx} className="p-4 rounded-xl bg-surface-card border border-surface-border">
            <span className="text-[11px] font-medium text-slate-400 block">{k.label}</span>
            <span className={`text-xl font-bold font-mono mt-1 block ${k.color}`}>{k.val}</span>
          </div>
        ))}
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pass vs Fail & Funnel */}
        <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Award className="w-4 h-4 text-emerald-400" />
            Outcome & Participation Funnel
          </h3>

          <div className="flex items-center gap-6 py-2">
            <div className="flex-1 bg-surface-elevated p-4 rounded-xl border border-surface-border text-center">
              <span className="text-xs text-slate-400 block">Passed Candidates</span>
              <span className="text-2xl font-bold text-emerald-400 font-mono mt-1 block">
                {overview.pass_count}
              </span>
              <span className="text-[11px] text-emerald-500/80 font-medium">
                {overview.pass_percentage.toFixed(1)}% of evaluated
              </span>
            </div>
            <div className="flex-1 bg-surface-elevated p-4 rounded-xl border border-surface-border text-center">
              <span className="text-xs text-slate-400 block">Failed Candidates</span>
              <span className="text-2xl font-bold text-rose-400 font-mono mt-1 block">
                {overview.fail_count}
              </span>
              <span className="text-[11px] text-rose-500/80 font-medium">
                {(100 - overview.pass_percentage).toFixed(1)}% of evaluated
              </span>
            </div>
          </div>

          {/* Funnel Progress */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold text-slate-300">Participation Funnel</span>
            {overview.participation_funnel.map((f, i) => (
              <div key={i} className="space-y-1">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>{f.stage}</span>
                  <span className="font-mono text-white font-semibold">
                    {f.count} ({f.percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all"
                    style={{ width: `${Math.min(100, f.percentage)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Score Distribution Histogram */}
        <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            Marks & Percentage Distribution (10% Bins)
          </h3>

          <div className="space-y-2 pt-2">
            {overview.score_distribution.map((b, idx) => {
              const maxCount = Math.max(...overview.score_distribution.map((x) => x.count), 1);
              const barWidth = (b.count / maxCount) * 100;
              return (
                <div key={idx} className="flex items-center gap-3 text-xs">
                  <span className="w-20 font-mono text-slate-400 text-right shrink-0">{b.band}</span>
                  <div className="flex-1 bg-slate-800 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-3 rounded-full transition-all"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className="w-8 font-mono text-white font-semibold shrink-0 text-right">{b.count}</span>
                </div>
              );
            })}
          </div>

          {/* Difficulty Accuracy Overview */}
          <div className="pt-4 border-t border-surface-border grid grid-cols-3 gap-2 text-center">
            {Object.entries(overview.difficulty_accuracy).map(([diff, acc]) => (
              <div key={diff} className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">{diff}</span>
                <span className="text-sm font-bold font-mono text-white mt-0.5 block">{acc.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 2. Participants Tab
// =========================================================================
function ParticipantsTabView({
  quizId,
  token,
  onViewStudent,
}: {
  quizId: string;
  token: string;
  onViewStudent: (id: string) => void;
}) {
  const [data, setData] = useState<QuizParticipantAnalytics | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await quizAnalyticsService.getParticipants(token, quizId, {
          status: statusFilter,
          page,
          limit: 20,
        });
        setData(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, token, statusFilter, page]);

  if (loading && !data) return <div className="p-12 text-center text-slate-400">Loading participants...</div>;

  return (
    <div className="space-y-6">
      {/* Funnel & Conversion Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
          <span className="text-xs text-slate-400 block">Unique Candidates</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">{data?.unique_students_count || 0}</span>
        </div>
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
          <span className="text-xs text-slate-400 block">Total Attempts</span>
          <span className="text-xl font-bold font-mono text-cyan-400 mt-1 block">{data?.total_attempts_count || 0}</span>
        </div>
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
          <span className="text-xs text-slate-400 block">Submitted Exams</span>
          <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">{data?.submitted_count || 0}</span>
        </div>
        <div className="p-4 rounded-xl bg-surface-card border border-surface-border">
          <span className="text-xs text-slate-400 block">Expired / Unfinished</span>
          <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">{data?.expired_count || 0}</span>
        </div>
      </div>

      {/* Filter and Table */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-white">Enrolled & Participating Candidates</h3>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200"
          >
            <option value="all">All Registration Statuses</option>
            <option value="approved">Approved Only</option>
            <option value="pending">Pending Approval</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/80 text-slate-400 border-b border-surface-border uppercase font-mono text-[11px]">
              <tr>
                <th className="p-3">Student Name</th>
                <th className="p-3">Register #</th>
                <th className="p-3">Registration</th>
                <th className="p-3">Attempt Status</th>
                <th className="p-3">Score</th>
                <th className="p-3">Result</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border text-slate-300">
              {data?.participants.map((p) => (
                <tr key={p.student_id} className="hover:bg-surface-elevated/40 transition-colors">
                  <td className="p-3 font-semibold text-white">{p.student_name}</td>
                  <td className="p-3 font-mono text-slate-400">{p.register_number || '—'}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-slate-800 text-slate-300">
                      {p.registration_status}
                    </span>
                  </td>
                  <td className="p-3 capitalize font-mono text-[11px]">
                    {p.attempt_status || 'Not Started'}
                  </td>
                  <td className="p-3 font-mono font-semibold">
                    {p.obtained_score !== null && p.obtained_score !== undefined
                      ? `${p.obtained_score} pts`
                      : '—'}
                  </td>
                  <td className="p-3">
                    {p.is_passed === true ? (
                      <span className="text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                      </span>
                    ) : p.is_passed === false ? (
                      <span className="text-rose-400 font-semibold flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> Failed
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onViewStudent(p.student_id)}
                      className="px-2.5 py-1 rounded-lg bg-surface-elevated border border-surface-border hover:bg-primary-600 hover:text-white text-slate-300 transition-colors"
                    >
                      View Report
                    </button>
                  </td>
                </tr>
              ))}
              {data?.participants.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500">
                    No participants found matching selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 3. Students Performance Tab
// =========================================================================
function StudentsTabView({
  quizId,
  token,
  onViewStudent,
}: {
  quizId: string;
  token: string;
  onViewStudent: (id: string) => void;
}) {
  const [data, setData] = useState<StudentPerformanceListResponse | null>(null);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('percentage');
  const [sortDir, setSortDir] = useState('desc');
  const [resultStatus, setResultStatus] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  const loadStudents = async () => {
    try {
      setLoading(true);
      const res = await quizAnalyticsService.getStudentPerformance(token, quizId, {
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        result_status: resultStatus !== 'all' ? resultStatus : undefined,
      });
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudents();
  }, [quizId, token, sortBy, sortDir, resultStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadStudents();
  };

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by student name or register number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-3">
          <select
            value={resultStatus}
            onChange={(e) => setResultStatus(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200"
          >
            <option value="all">All Results</option>
            <option value="passed">Passed Only</option>
            <option value="failed">Failed Only</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200"
          >
            <option value="percentage">Sort by Percentage</option>
            <option value="marks">Sort by Marks</option>
            <option value="student_name">Sort by Name</option>
            <option value="submission_time">Sort by Submission Time</option>
          </select>
        </div>
      </div>

      {/* Student Performance Table */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/80 text-slate-400 border-b border-surface-border uppercase font-mono text-[11px]">
              <tr>
                <th className="p-3">Rank</th>
                <th className="p-3">Student Name</th>
                <th className="p-3">Register Number</th>
                <th className="p-3">Obtained Marks</th>
                <th className="p-3">Percentage</th>
                <th className="p-3">Result</th>
                <th className="p-3">Evaluation Status</th>
                <th className="p-3 text-right">Profile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border text-slate-300">
              {data?.items.map((row) => (
                <tr key={row.student_id} className="hover:bg-surface-elevated/40 transition-colors">
                  <td className="p-3 font-mono font-bold text-cyan-400">
                    {row.rank ? `#${row.rank}` : '—'}
                  </td>
                  <td className="p-3 font-semibold text-white">{row.student_name}</td>
                  <td className="p-3 font-mono text-slate-400">{row.register_number || '—'}</td>
                  <td className="p-3 font-mono font-semibold text-white">
                    {row.obtained_marks} / {row.max_marks}
                  </td>
                  <td className="p-3 font-mono font-bold text-cyan-300">
                    {row.percentage.toFixed(1)}%
                  </td>
                  <td className="p-3">
                    {row.is_passed === true ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Passed
                      </span>
                    ) : row.is_passed === false ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        Failed
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="p-3 capitalize font-mono text-[10px] text-slate-400">
                    {row.evaluation_status.replace(/_/g, ' ')}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onViewStudent(row.student_id)}
                      className="px-2.5 py-1 rounded-lg bg-surface-elevated border border-surface-border hover:bg-cyan-600 hover:text-white text-slate-300 transition-colors font-medium"
                    >
                      Detailed Profile
                    </button>
                  </td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500">
                    No student performance records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 4. Student Individual Profile Tab
// =========================================================================
function StudentProfileTabView({
  quizId,
  studentId,
  token,
  onBack,
}: {
  quizId: string;
  studentId: string;
  token: string;
  onBack: () => void;
}) {
  const [profile, setProfile] = useState<StudentProfileAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await quizAnalyticsService.getStudentProfile(token, quizId, studentId);
        setProfile(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, studentId, token]);

  if (loading) return <div className="p-12 text-center text-slate-400">Loading student profile report card...</div>;
  if (!profile) return <div className="p-12 text-center text-rose-400">Student profile record not found.</div>;

  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="text-xs text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Students Table
      </button>

      {/* Candidate Scorecard Banner */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white">{profile.student_name}</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Matriculation ID: <span className="font-mono text-slate-200">{profile.register_number || '—'}</span> &bull;{' '}
              {profile.email}
            </p>
          </div>
          <div className="flex items-center gap-4 text-center">
            <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
              <span className="text-[11px] text-slate-400 block">Class Rank</span>
              <span className="text-xl font-bold text-cyan-400 font-mono">
                {profile.rank ? `#${profile.rank}` : '—'}
              </span>
            </div>
            <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
              <span className="text-[11px] text-slate-400 block">Marks Obtained</span>
              <span className="text-xl font-bold text-white font-mono">
                {profile.obtained_marks} / {profile.max_marks}
              </span>
            </div>
            <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
              <span className="text-[11px] text-slate-400 block">Score Percentage</span>
              <span className="text-xl font-bold text-emerald-400 font-mono">
                {profile.percentage.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Section-Wise Breakdown Table */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Section-Wise Performance</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {profile.section_breakdown.map((sec, i) => (
            <div key={i} className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-white">{sec.section_name}</span>
                <span className="font-mono text-cyan-400 font-bold">{sec.percentage.toFixed(1)}%</span>
              </div>
              <div className="text-[11px] text-slate-400 flex justify-between">
                <span>Score: {sec.obtained_marks} / {sec.max_marks} pts</span>
                <span>Ans: {sec.answered_count} | Unans: {sec.unanswered_count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Question Breakdown List */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Question-by-Question Attempt Breakdown</h3>
        <div className="space-y-3">
          {profile.question_breakdown.map((q) => (
            <div
              key={q.question_order}
              className={`p-4 rounded-xl border text-xs space-y-2 ${
                q.is_correct
                  ? 'bg-emerald-950/20 border-emerald-500/30'
                  : q.is_partially_correct
                  ? 'bg-amber-950/20 border-amber-500/30'
                  : 'bg-rose-950/20 border-rose-500/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">
                  Q{q.question_order}. {q.question_text}
                </span>
                <span className="font-mono font-bold text-white">
                  {q.obtained_marks} / {q.max_marks} pts
                </span>
              </div>

              <div className="flex flex-wrap gap-4 text-[11px] text-slate-400">
                <span>Type: <strong className="text-slate-200 capitalize">{q.question_type}</strong></span>
                {q.assigned_difficulty && (
                  <span>Difficulty: <strong className="text-slate-200 capitalize">{q.assigned_difficulty}</strong></span>
                )}
                {q.negative_deduction > 0 && (
                  <span className="text-rose-400 font-semibold">
                    Negative Penalty: -{q.negative_deduction} pts
                  </span>
                )}
                <span>Time Spent: {q.time_spent_seconds}s</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 5. Question Analysis & Psychometric Tab
// =========================================================================
function QuestionsTabView({ quizId, token }: { quizId: string; token: string }) {
  const [data, setData] = useState<QuizQuestionAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [flaggingQuestion, setFlaggingQuestion] = useState<QuestionAnalysisItem | null>(null);
  const [flagNotes, setFlagNotes] = useState('');

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const res = await quizAnalyticsService.getQuestionAnalysis(token, quizId);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuestions();
  }, [quizId, token]);

  const handleFlagSubmit = async () => {
    if (!flaggingQuestion) return;
    try {
      await quizAnalyticsService.flagQuestionReview(token, quizId, {
        quiz_question_id: flaggingQuestion.quiz_question_id,
        flag_type: 'review_needed',
        status: 'pending',
        internal_notes: flagNotes,
      });
      setFlaggingQuestion(null);
      setFlagNotes('');
      await loadQuestions();
    } catch (err: any) {
      alert(err.message || 'Failed to submit flag');
    }
  };

  if (loading && !data) return <div className="p-12 text-center text-slate-400">Loading psychometric item analysis...</div>;

  return (
    <div className="space-y-6">
      {/* Insight Banner */}
      <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-300 flex items-center gap-2.5">
        <Info className="w-4 h-4 shrink-0" />
        <span>
          Psychometric Item Analysis calculates Difficulty Index ($P$) and Discrimination Index ($D$) between upper 27% and lower 27% cohorts.
        </span>
      </div>

      {/* Questions Cards */}
      <div className="space-y-4">
        {data?.items.map((q) => (
          <div key={q.quiz_question_id} className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-surface-elevated border border-surface-border flex items-center justify-center font-mono font-bold text-xs text-white">
                  Q{q.question_order}
                </span>
                <span className="font-semibold text-white text-sm">{q.question_text}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setFlaggingQuestion(q)}
                  className="px-2.5 py-1 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-xs flex items-center gap-1 font-semibold transition-colors"
                >
                  <Flag className="w-3 h-3" /> Flag for Review
                </button>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3 text-xs">
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Difficulty (P)</span>
                <span className="font-mono font-bold text-white text-sm">
                  {q.difficulty_index.toFixed(2)}
                </span>
                <span className="text-[10px] text-cyan-400 capitalize block">{q.assigned_difficulty}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Discrimination (D)</span>
                <span className="font-mono font-bold text-white text-sm">
                  {q.discrimination_index !== null && q.discrimination_index !== undefined
                    ? q.discrimination_index.toFixed(2)
                    : 'N/A'}
                </span>
                <span className="text-[10px] text-slate-400 capitalize block">{q.discrimination_status}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Accuracy</span>
                <span className="font-mono font-bold text-emerald-400 text-sm">{q.correct_percentage.toFixed(1)}%</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Incorrect Rate</span>
                <span className="font-mono font-bold text-rose-400 text-sm">{q.incorrect_percentage.toFixed(1)}%</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Unanswered</span>
                <span className="font-mono font-bold text-amber-400 text-sm">{q.unanswered_percentage.toFixed(1)}%</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-400 block uppercase">Avg Marks</span>
                <span className="font-mono font-bold text-white text-sm">{q.average_awarded_marks.toFixed(1)} / {q.max_marks}</span>
              </div>
            </div>

            {/* Distractor Analysis Bar */}
            {q.distractors && q.distractors.length > 0 && (
              <div className="pt-2 border-t border-surface-border/60 space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-300">Option Selection Breakdown:</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                  {q.distractors.map((d) => (
                    <div
                      key={d.option_id}
                      className={`p-2 rounded-lg border text-[11px] ${
                        d.is_correct
                          ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                          : 'bg-surface-elevated border-surface-border text-slate-300'
                      }`}
                    >
                      <div className="flex justify-between items-center font-semibold">
                        <span className="truncate">{d.option_text}</span>
                        <span className="font-mono">{d.selection_percentage.toFixed(1)}%</span>
                      </div>
                      <span className="text-[10px] text-slate-400">{d.selection_count} selected</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Flag Modal */}
      {flaggingQuestion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Flag className="w-4 h-4 text-amber-400" />
              Flag Question #{flaggingQuestion.question_order} for Review
            </h3>
            <textarea
              rows={3}
              value={flagNotes}
              onChange={(e) => setFlagNotes(e.target.value)}
              placeholder="Provide administrative notes (e.g., negative discrimination index, ambiguous question stem)..."
              className="w-full p-3 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setFlaggingQuestion(null)}
                className="px-3 py-1.5 rounded-xl border border-surface-border text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleFlagSubmit}
                className="px-4 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold"
              >
                Save Review Flag
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// 6. Sections & Academic Breakdown Tab
// =========================================================================
function SectionsAcademicTabView({ quizId, token }: { quizId: string; token: string }) {
  const [sections, setSections] = useState<QuizSectionAnalysisResponse | null>(null);
  const [academic, setAcademic] = useState<QuizAcademicAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [s, a] = await Promise.all([
          quizAnalyticsService.getSectionAnalysis(token, quizId),
          quizAnalyticsService.getAcademicAnalysis(token, quizId),
        ]);
        setSections(s);
        setAcademic(a);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, token]);

  if (loading) return <div className="p-12 text-center text-slate-400">Loading section and academic analysis...</div>;

  return (
    <div className="space-y-6">
      {/* Sections Table */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Section-Wise Performance Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/80 text-slate-400 border-b border-surface-border uppercase font-mono text-[11px]">
              <tr>
                <th className="p-3">Section Title</th>
                <th className="p-3">Total Questions</th>
                <th className="p-3">Max Marks</th>
                <th className="p-3">Avg Marks</th>
                <th className="p-3">Avg %</th>
                <th className="p-3">Attempted Rate</th>
                <th className="p-3">Grading Complete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border text-slate-300">
              {sections?.sections.map((s, i) => (
                <tr key={i} className="hover:bg-surface-elevated/40">
                  <td className="p-3 font-semibold text-white">{s.section_title}</td>
                  <td className="p-3 font-mono">{s.total_questions}</td>
                  <td className="p-3 font-mono">{s.max_marks} pts</td>
                  <td className="p-3 font-mono font-semibold text-cyan-400">{s.average_marks.toFixed(1)}</td>
                  <td className="p-3 font-mono font-bold text-white">{s.average_percentage.toFixed(1)}%</td>
                  <td className="p-3 font-mono">{s.questions_attempted_avg.toFixed(1)} / {s.total_questions}</td>
                  <td className="p-3">
                    {s.manual_grading_complete ? (
                      <span className="text-emerald-400 font-semibold flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" /> 100% Complete
                      </span>
                    ) : (
                      <span className="text-amber-400 font-semibold">Pending Grading</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Units Breakdown */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Curriculum Units Breakdown</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {academic?.units.map((u, i) => (
            <div key={i} className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1.5">
              <span className="font-semibold text-white text-xs block">{u.name}</span>
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Accuracy: <strong className="text-cyan-400 font-mono">{u.average_accuracy_percentage.toFixed(1)}%</strong></span>
                <span>{u.questions_count} Questions</span>
              </div>
            </div>
          ))}
          {academic?.units.length === 0 && (
            <div className="p-4 text-slate-500 text-xs">No unit metadata tagged on examination questions.</div>
          )}
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 7. Difficulty & Question Types Tab
// =========================================================================
function DifficultyTypesTabView({ quizId, token }: { quizId: string; token: string }) {
  const [difficulty, setDifficulty] = useState<QuizDifficultyAnalysisResponse | null>(null);
  const [types, setTypes] = useState<QuizQuestionTypeAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [d, t] = await Promise.all([
          quizAnalyticsService.getDifficultyAnalysis(token, quizId),
          quizAnalyticsService.getQuestionTypeAnalysis(token, quizId),
        ]);
        setDifficulty(d);
        setTypes(t);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, token]);

  if (loading) return <div className="p-12 text-center text-slate-400">Loading difficulty and format analytics...</div>;

  return (
    <div className="space-y-6">
      {/* Difficulty Breakdown */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Difficulty Level Breakdown (Easy, Medium, Hard)</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {difficulty?.levels.map((lvl) => (
            <div key={lvl.difficulty_level} className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-2 text-center">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                {lvl.difficulty_level} Level
              </span>
              <span className="text-2xl font-bold font-mono text-cyan-400 block">
                {lvl.average_accuracy.toFixed(1)}%
              </span>
              <span className="text-[11px] text-slate-400 block">
                {lvl.questions_count} Questions &bull; {lvl.max_marks} Total Marks
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Question Type Breakdown */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Question Type & Format Performance</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {types?.types.map((t) => (
            <div key={t.question_type} className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-white capitalize">{t.question_type.replace(/_/g, ' ')}</span>
                <span className="font-mono text-cyan-400 font-bold">{t.accuracy_or_score_percentage.toFixed(1)}%</span>
              </div>
              <div className="text-[11px] text-slate-400 flex justify-between">
                <span>{t.questions_count} Questions ({t.max_marks} pts)</span>
                <span>{t.is_subjective ? 'Subjective' : 'Objective'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 8. Time & Negative Marking Tab
// =========================================================================
function TimeNegativeTabView({ quizId, token }: { quizId: string; token: string }) {
  const [time, setTime] = useState<TimeAnalysisResponse | null>(null);
  const [penalty, setPenalty] = useState<NegativeMarkingAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [t, p] = await Promise.all([
          quizAnalyticsService.getTimeAnalysis(token, quizId),
          quizAnalyticsService.getNegativeMarkingAnalysis(token, quizId),
        ]);
        setTime(t);
        setPenalty(p);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, token]);

  if (loading) return <div className="p-12 text-center text-slate-400">Loading timing and penalty analytics...</div>;

  return (
    <div className="space-y-6">
      {/* Time Telemetry */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            Time Usage & Duration Telemetry
          </h3>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            {time?.data_reliability_label || 'Telemetry Recorded'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Configured Time</span>
            <span className="text-lg font-bold font-mono text-white mt-0.5 block">
              {time?.configured_duration_minutes}m
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Average Time Spent</span>
            <span className="text-lg font-bold font-mono text-cyan-400 mt-0.5 block">
              {((time?.average_time_spent_seconds || 0) / 60).toFixed(1)}m
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Median Duration</span>
            <span className="text-lg font-bold font-mono text-indigo-400 mt-0.5 block">
              {((time?.median_time_spent_seconds || 0) / 60).toFixed(1)}m
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Avg Time Remaining</span>
            <span className="text-lg font-bold font-mono text-emerald-400 mt-0.5 block">
              {((time?.average_time_remaining_seconds || 0) / 60).toFixed(1)}m
            </span>
          </div>
        </div>
      </div>

      {/* Negative Marking Impact */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-rose-400" />
          Negative Marking Penalty Impact
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Total Penalty Deductions</span>
            <span className="text-lg font-bold font-mono text-rose-400 mt-0.5 block">
              -{penalty?.total_negative_marks_deducted || 0} pts
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Average Penalty per Attempt</span>
            <span className="text-lg font-bold font-mono text-amber-400 mt-0.5 block">
              -{penalty?.average_negative_marks_per_attempt.toFixed(2)} pts
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Candidates Affected</span>
            <span className="text-lg font-bold font-mono text-white mt-0.5 block">
              {penalty?.students_affected_count || 0}
            </span>
          </div>
          <div className="p-3 bg-surface-elevated rounded-xl border border-surface-border">
            <span className="text-[11px] text-slate-400 block">Marks Lost to Penalties</span>
            <span className="text-lg font-bold font-mono text-rose-400 mt-0.5 block">
              {penalty?.percentage_of_marks_lost.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 9. Security & Integrity Tab
// =========================================================================
function SecurityTabView({ quizId, token }: { quizId: string; token: string }) {
  const [data, setData] = useState<SecuritySummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await quizAnalyticsService.getSecuritySummary(token, quizId);
        setData(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [quizId, token]);

  if (loading) return <div className="p-12 text-center text-slate-400">Loading security integrity summary...</div>;

  return (
    <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-cyan-400" />
          Proctoring & Integrity Summary
        </h3>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border ${
            data?.integrity_status === 'clean'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : data?.integrity_status === 'minor_flags'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
          }`}
        >
          Integrity Status: {data?.integrity_status?.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div className="p-4 bg-surface-elevated rounded-xl border border-surface-border">
          <span className="text-xs text-slate-400 block">Total Security Events</span>
          <span className="text-2xl font-bold font-mono text-white mt-1 block">
            {data?.total_security_events || 0}
          </span>
        </div>
        <div className="p-4 bg-surface-elevated rounded-xl border border-surface-border">
          <span className="text-xs text-slate-400 block">High Severity Incidents</span>
          <span className="text-2xl font-bold font-mono text-rose-400 mt-1 block">
            {data?.high_severity_events || 0}
          </span>
        </div>
        <div className="p-4 bg-surface-elevated rounded-xl border border-surface-border">
          <span className="text-xs text-slate-400 block">Unreviewed Alerts</span>
          <span className="text-2xl font-bold font-mono text-amber-400 mt-1 block">
            {data?.unreviewed_alerts || 0}
          </span>
        </div>
        <div className="p-4 bg-surface-elevated rounded-xl border border-surface-border">
          <span className="text-xs text-slate-400 block">Flagged Candidate Attempts</span>
          <span className="text-2xl font-bold font-mono text-indigo-400 mt-1 block">
            {data?.attempts_with_security_flags || 0}
          </span>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// 10. Student Comparison Tab
// =========================================================================
function CompareTabView({ quizId, token }: { quizId: string; token: string }) {
  const [students, setStudents] = useState<StudentPerformanceItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<StudentComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadCandidates() {
      try {
        const res = await quizAnalyticsService.getStudentPerformance(token, quizId, { limit: 50 });
        setStudents(res.items);
      } catch (err) {
        console.error(err);
      }
    }
    loadCandidates();
  }, [quizId, token]);

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((x) => x !== id));
    } else {
      if (selectedIds.length >= 5) {
        alert('You can select up to 5 students to compare simultaneously.');
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) {
      alert('Please select at least 2 students to compare.');
      return;
    }
    try {
      setLoading(true);
      const res = await quizAnalyticsService.compareStudents(token, quizId, selectedIds);
      setComparison(res);
    } catch (err: any) {
      alert(err.message || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Selection Box */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Select Students to Benchmark & Compare (2 to 5)</h3>
          <button
            onClick={handleCompare}
            disabled={selectedIds.length < 2 || loading}
            className="px-4 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-md"
          >
            {loading ? 'Comparing...' : `Compare ${selectedIds.length} Students`}
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-56 overflow-y-auto p-1">
          {students.map((s) => {
            const isSelected = selectedIds.includes(s.student_id);
            return (
              <button
                key={s.student_id}
                onClick={() => toggleSelect(s.student_id)}
                className={`p-2.5 rounded-xl border text-left text-xs flex items-center justify-between transition-colors ${
                  isSelected
                    ? 'bg-cyan-500/20 border-cyan-500 text-white font-semibold'
                    : 'bg-surface-elevated border-surface-border text-slate-300 hover:text-white'
                }`}
              >
                <div className="truncate">
                  <span>{s.student_name}</span>
                  <span className="text-[10px] text-slate-400 block font-mono">
                    Score: {s.percentage.toFixed(1)}% &bull; #{s.rank || '—'}
                  </span>
                </div>
                <div
                  className={`w-4 h-4 rounded flex items-center justify-center border ${
                    isSelected ? 'bg-cyan-500 border-cyan-400 text-slate-950' : 'border-slate-600'
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3" />}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Comparison Grid Results */}
      {comparison && (
        <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
          <h3 className="text-sm font-semibold text-white">Side-by-Side Benchmark Matrix</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {comparison.compared_students.map((c) => (
              <div key={c.student_id} className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-3">
                <div>
                  <span className="text-xs font-bold text-white block truncate">{c.student_name}</span>
                  <span className="text-[10px] font-mono text-cyan-400">Class Rank: #{c.rank || '—'}</span>
                </div>
                <div className="text-center py-2 bg-slate-900/60 rounded-lg">
                  <span className="text-xl font-bold font-mono text-emerald-400 block">{c.percentage.toFixed(1)}%</span>
                  <span className="text-[10px] text-slate-400 font-mono">{c.total_score} pts</span>
                </div>
                {/* Section Scores */}
                <div className="space-y-1 text-[11px] pt-2 border-t border-surface-border">
                  <span className="text-[10px] text-slate-500 font-semibold block uppercase">Sections:</span>
                  {Object.entries(c.section_scores).map(([sec, sc]) => (
                    <div key={sec} className="flex justify-between text-slate-300 font-mono">
                      <span className="truncate">{sec}</span>
                      <span>{sc.toFixed(1)} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// 11. Reports & Exports Tab
// =========================================================================
function ReportsTabView({ quizId, token }: { quizId: string; token: string }) {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedType, setSelectedType] = useState<any>('quiz_performance');
  const [selectedFormat, setSelectedFormat] = useState<'csv' | 'xlsx' | 'pdf'>('csv');

  const loadReports = async () => {
    try {
      setLoading(true);
      const res = await quizAnalyticsService.listReports(token, quizId);
      setReports(res.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [quizId, token]);

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await quizAnalyticsService.generateReport(token, quizId, {
        report_type: selectedType,
        export_format: selectedFormat,
      });
      await loadReports();
    } catch (err: any) {
      alert(err.message || 'Report generation failed');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Generate Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Generate Examination Report</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
          >
            <option value="quiz_performance">Quiz Performance Summary</option>
            <option value="detailed_student">Detailed Student Performance</option>
            <option value="question_analysis">Question & Item Analysis</option>
            <option value="academic_performance">Curriculum Academic Performance</option>
            <option value="time_analysis">Time Usage Telemetry Report</option>
            <option value="security_summary">Security & Integrity Audit</option>
          </select>

          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value as any)}
            className="px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
          >
            <option value="csv">CSV (Comma-Separated Values)</option>
            <option value="xlsx">Excel Spreadsheet (.xlsx)</option>
            <option value="pdf">PDF Document (.pdf)</option>
          </select>

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            {generating ? 'Generating Report...' : 'Generate and Export'}
          </button>
        </div>
      </div>

      {/* Reports List */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white">Available Generated Reports</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/80 text-slate-400 border-b border-surface-border uppercase font-mono text-[11px]">
              <tr>
                <th className="p-3">File Name</th>
                <th className="p-3">Type</th>
                <th className="p-3">Format</th>
                <th className="p-3">Created</th>
                <th className="p-3 text-right">Download</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border text-slate-300">
              {reports.map((r) => (
                <tr key={r.id} className="hover:bg-surface-elevated/40">
                  <td className="p-3 font-semibold text-white font-mono">{r.file_name}</td>
                  <td className="p-3 capitalize">{r.report_type.replace(/_/g, ' ')}</td>
                  <td className="p-3 uppercase font-mono font-bold text-cyan-400">{r.export_format}</td>
                  <td className="p-3 text-slate-400">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="p-3 text-right">
                    <a
                      href={quizAnalyticsService.getDownloadUrl(r.id, token)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 rounded-lg bg-surface-elevated border border-surface-border hover:bg-primary-600 hover:text-white text-cyan-400 text-xs font-semibold transition-colors inline-flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" /> Download
                    </a>
                  </td>
                </tr>
              ))}
              {reports.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">
                    No exported reports generated for this quiz yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
