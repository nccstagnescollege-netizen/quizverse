'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  Plus,
  Search,
  Clock,
  CheckCircle2,
  Users,
  KeyRound,
  ExternalLink,
  Edit,
  Trash2,
  Calendar,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';

interface QuizItem {
  id: string;
  title: string;
  slug: string;
  durationMinutes: number;
  totalMarks: number;
  passingPercentage: number;
  maxAttempts: number;
  status: 'published' | 'scheduled' | 'draft';
  totalAttempts: number;
}

const SAMPLE_QUIZZES: QuizItem[] = [
  {
    id: 'qz-1',
    title: 'PostgreSQL Relational Schema & RLS Examination',
    slug: 'postgres-rls-schema-2026',
    durationMinutes: 45,
    totalMarks: 50,
    passingPercentage: 60,
    maxAttempts: 1,
    status: 'published',
    totalAttempts: 142,
  },
  {
    id: 'qz-2',
    title: 'Distributed Systems & Vector Coordinate Space',
    slug: 'distributed-systems-vector',
    durationMinutes: 60,
    totalMarks: 75,
    passingPercentage: 50,
    maxAttempts: 2,
    status: 'published',
    totalAttempts: 88,
  },
  {
    id: 'qz-3',
    title: 'Cryptographic Security & Token Hashing Verification',
    slug: 'crypto-token-hashing',
    durationMinutes: 30,
    totalMarks: 40,
    passingPercentage: 70,
    maxAttempts: 1,
    status: 'scheduled',
    totalAttempts: 0,
  },
  {
    id: 'qz-4',
    title: '3D Spatial Geometry & Polyhedron Transformations',
    slug: '3d-spatial-geometry',
    durationMinutes: 90,
    totalMarks: 100,
    passingPercentage: 40,
    maxAttempts: 3,
    status: 'draft',
    totalAttempts: 0,
  },
];

export default function AdminQuizPage() {
  const { token } = useAuth();
  const [quizzes, setQuizzes] = useState<QuizItem[]>(SAMPLE_QUIZZES);
  const [isSyncing, setIsSyncing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchQuizzes = useCallback(async () => {
    if (!token) return;
    setIsSyncing(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/admin/dashboard/quiz-performance`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const mapped: QuizItem[] = data.map((d: any, idx: number) => ({
            id: d.quiz_id || `qz-${idx}`,
            title: d.title || 'Untitled Exam',
            slug: d.slug || d.title?.toLowerCase().replace(/[^a-z0-9]+/g, '-') || `exam-${idx}`,
            durationMinutes: d.duration_minutes || 60,
            totalMarks: d.total_marks || 100,
            passingPercentage: d.passing_percentage || 50,
            maxAttempts: d.max_attempts || 1,
            status: d.status || 'published',
            totalAttempts: d.attempts_count || 0,
          }));
          setQuizzes(mapped);
        }
      }
    } catch {
      // Clean fallback to initial mock items
    } finally {
      setIsSyncing(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) fetchQuizzes();
  }, [token, fetchQuizzes]);

  const filteredQuizzes = quizzes.filter(
    (q) =>
      q.title.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      q.slug.toLowerCase().includes(debouncedSearch.toLowerCase())
  );

  const columns: TableColumn<QuizItem>[] = [
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
        <span className="font-mono text-xs text-slate-300 flex items-center gap-1">
          <Clock className="w-3 h-3 text-slate-400" />
          {row.durationMinutes} mins
        </span>
      ),
    },
    {
      key: 'totalMarks',
      header: 'Marks',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs text-slate-200">
          {row.totalMarks} pts (Pass: {row.passingPercentage}%)
        </span>
      ),
    },
    {
      key: 'totalAttempts',
      header: 'Submissions',
      render: (row) => (
        <span className="font-mono text-xs text-cyber-cyan font-bold">{row.totalAttempts}</span>
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
      header: 'Actions',
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-1.5">
          <Link href={`/exam/${row.slug}`} target="_blank">
            <button className="p-1.5 rounded-lg bg-surface-elevated text-slate-300 hover:text-white" title="Launch Exam">
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </Link>
          <button className="p-1.5 rounded-lg bg-surface-elevated text-slate-300 hover:text-white" title="Edit Quiz Configuration">
            <Edit className="w-3.5 h-3.5" />
          </button>
          <button className="p-1.5 rounded-lg bg-surface-elevated text-slate-400 hover:text-rose-400" title="Delete">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Quiz Management' }]} />

      <PageHeader
        title="Quiz &amp; Examination Engine"
        description="Configure timed examination sessions, question shuffling policies, pass marks, and student invitation links."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchQuizzes}
              disabled={isSyncing}
              className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors disabled:opacity-60"
              title="Refresh Quizzes Asynchronously"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin text-brand-400' : ''}`} />
            </button>
            <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple min-h-[36px]">
              <Plus className="w-3.5 h-3.5" />
              Create Examination
            </button>
          </div>
        }
      />

      {/* Search Toolbar */}
      <DashboardCard className="p-3.5">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search examinations by title or slug..."
            className="w-full bg-surface-base border border-surface-border rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
      </DashboardCard>

      {/* Responsive Table / Card Stack */}
      <ResponsiveTable
        columns={columns}
        data={filteredQuizzes}
        keyExtractor={(row) => row.id}
        mobileCardRender={(row) => (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-white text-xs leading-snug">{row.title}</h3>
                <span className="font-mono text-[10px] text-slate-400">{row.slug}</span>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider border shrink-0 ${
                row.status === 'published' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                row.status === 'scheduled' ? 'bg-amber-500/15 border-amber-500/30 text-amber-300' :
                'bg-slate-800 border-slate-700 text-slate-400'
              }`}>
                {row.status}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs font-mono py-2 border-y border-surface-border/50 text-center">
              <div>
                <span className="text-slate-500 block text-[9px]">DURATION</span>
                <span className="text-slate-200 font-semibold">{row.durationMinutes}m</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[9px]">TOTAL MARKS</span>
                <span className="text-emerald-400 font-semibold">{row.totalMarks}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[9px]">SUBMISSIONS</span>
                <span className="text-cyber-cyan font-semibold">{row.totalAttempts}</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <Link href={`/exam/${row.slug}`} target="_blank">
                <button className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-slate-200">
                  Launch
                </button>
              </Link>
              <button className="px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-medium">
                Configure
              </button>
            </div>
          </div>
        )}
      />
    </div>
  );
}
