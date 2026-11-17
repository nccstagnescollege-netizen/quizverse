'use client';

import { useState, useMemo } from 'react';
import {
  Plus,
  Search,
  Filter,
  HelpCircle,
  Tag,
  CheckCircle2,
  Clock,
  Layers,
  Edit3,
  Trash2,
  Eye,
  SlidersHorizontal,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';

interface QuestionBankItem {
  id: string;
  questionText: string;
  topic: string;
  type: string;
  difficulty: 'easy' | 'medium' | 'hard';
  marks: number;
  negativeMarks: number;
  version: number;
  status: 'published' | 'draft' | 'archived';
  optionsCount: number;
}

const SAMPLE_QUESTION_BANK: QuestionBankItem[] = [
  {
    id: 'qb-001',
    questionText: 'Which PostgreSQL feature enforces zero-trust data isolation using auth.uid() at the database level?',
    topic: 'Relational DB',
    type: 'single_choice',
    difficulty: 'easy',
    marks: 2.0,
    negativeMarks: 0.5,
    version: 3,
    status: 'published',
    optionsCount: 4,
  },
  {
    id: 'qb-002',
    questionText: 'Explain the cascading delete constraints between Units, Chapters, and Topics in the QUIZVERSE schema.',
    topic: 'Academic Structure',
    type: 'short_answer',
    difficulty: 'medium',
    marks: 5.0,
    negativeMarks: 0.0,
    version: 1,
    status: 'published',
    optionsCount: 0,
  },
  {
    id: 'qb-003',
    questionText: 'Calculate the total number of questions selected when easy=30%, medium=50%, and hard=20% from a target pool of 50.',
    topic: 'Automatic Generation',
    type: 'numerical',
    difficulty: 'hard',
    marks: 4.0,
    negativeMarks: 1.0,
    version: 2,
    status: 'published',
    optionsCount: 0,
  },
  {
    id: 'qb-004',
    questionText: 'Which cryptographic algorithm hashes invitation tokens prior to storage in invitation_links?',
    topic: 'Cryptographic Security',
    type: 'single_choice',
    difficulty: 'easy',
    marks: 2.0,
    negativeMarks: 0.0,
    version: 1,
    status: 'published',
    optionsCount: 4,
  },
  {
    id: 'qb-005',
    questionText: 'Identify all security events tracked by attempt_events during candidate proctoring.',
    topic: 'Proctoring Telemetry',
    type: 'multiple_choice',
    difficulty: 'medium',
    marks: 3.5,
    negativeMarks: 0.5,
    version: 1,
    status: 'draft',
    optionsCount: 4,
  },
];

export default function AdminQuestionBankPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('all');
  const [topicFilter, setTopicFilter] = useState<string>('all');
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);

  const filteredQuestions = useMemo(() => {
    return SAMPLE_QUESTION_BANK.filter((q) => {
      const matchesSearch =
        q.questionText.toLowerCase().includes(searchTerm.toLowerCase()) ||
        q.topic.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesDiff = difficultyFilter === 'all' || q.difficulty === difficultyFilter;
      const matchesTopic = topicFilter === 'all' || q.topic === topicFilter;
      return matchesSearch && matchesDiff && matchesTopic;
    });
  }, [searchTerm, difficultyFilter, topicFilter]);

  const columns: TableColumn<QuestionBankItem>[] = [
    {
      key: 'questionText',
      header: 'Question Text',
      render: (row) => (
        <div className="space-y-1 max-w-md">
          <p className="font-medium text-white line-clamp-2 leading-relaxed">{row.questionText}</p>
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <span className="text-cyber-cyan">{row.topic}</span>
            <span>&bull;</span>
            <span className="text-slate-500">v{row.version}.0 snapshot</span>
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs text-slate-300 capitalize">{row.type.replace('_', ' ')}</span>
      ),
    },
    {
      key: 'difficulty',
      header: 'Difficulty',
      render: (row) => {
        const colors = {
          easy: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
          medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          hard: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
        }[row.difficulty];
        return (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border font-medium ${colors}`}>
            {row.difficulty}
          </span>
        );
      },
    },
    {
      key: 'marks',
      header: 'Marks',
      hideOnMobile: true,
      render: (row) => (
        <span className="font-mono text-xs">
          <span className="text-emerald-400 font-semibold">+{row.marks}</span>
          {row.negativeMarks > 0 && <span className="text-rose-400 ml-1">(-{row.negativeMarks})</span>}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      hideOnMobile: true,
      render: (row) => (
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase border ${
          row.status === 'published' ? 'bg-brand-500/15 text-brand-300 border-brand-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
        }`}>
          {row.status}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      render: () => (
        <div className="flex items-center justify-end gap-1.5">
          <button className="p-1.5 rounded-lg bg-surface-elevated text-slate-300 hover:text-white hover:bg-brand-600/30 transition-colors" title="Edit Question">
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button className="p-1.5 rounded-lg bg-surface-elevated text-slate-400 hover:text-rose-400 transition-colors" title="Delete Question">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Question Bank' }]} />

      <PageHeader
        title="Question Bank Repository"
        description="Author, categorize, and snapshot multi-format academic questions with LaTeX math and 3D coordinate metadata."
        actions={
          <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple min-h-[36px]">
            <Plus className="w-3.5 h-3.5" />
            Add Question
          </button>
        }
      />

      {/* Filter & Search Toolbar */}
      <DashboardCard className="p-3.5 space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search questions by text, topic, or keyword..."
              className="w-full bg-surface-base border border-surface-border rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Desktop Filter Pills */}
          <div className="hidden md:flex items-center gap-2">
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="bg-surface-base border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>

            <select
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
              className="bg-surface-base border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none"
            >
              <option value="all">All Topics</option>
              <option value="Relational DB">Relational DB</option>
              <option value="Academic Structure">Academic Structure</option>
              <option value="Automatic Generation">Automatic Generation</option>
              <option value="Cryptographic Security">Cryptographic Security</option>
              <option value="Proctoring Telemetry">Proctoring Telemetry</option>
            </select>
          </div>

          {/* Mobile Filter Toggle */}
          <button
            onClick={() => setIsMobileFilterOpen(!isMobileFilterOpen)}
            className="md:hidden flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Filters ({difficultyFilter !== 'all' || topicFilter !== 'all' ? 'Active' : 'All'})</span>
          </button>
        </div>

        {/* Mobile Filter Collapsible Sheet */}
        {isMobileFilterOpen && (
          <div className="md:hidden pt-3 border-t border-surface-border grid grid-cols-2 gap-2 animate-in slide-in-from-top-1">
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="bg-surface-base border border-surface-border rounded-xl px-2.5 py-2 text-xs text-slate-200 focus:outline-none"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>

            <select
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
              className="bg-surface-base border border-surface-border rounded-xl px-2.5 py-2 text-xs text-slate-200 focus:outline-none truncate"
            >
              <option value="all">All Topics</option>
              <option value="Relational DB">Relational DB</option>
              <option value="Academic Structure">Academic Structure</option>
              <option value="Automatic Generation">Automatic Gen</option>
              <option value="Cryptographic Security">Crypto Security</option>
              <option value="Proctoring Telemetry">Proctoring</option>
            </select>
          </div>
        )}
      </DashboardCard>

      {/* Responsive Table / Mobile Card Stack */}
      <ResponsiveTable
        columns={columns}
        data={filteredQuestions}
        keyExtractor={(row) => row.id}
        mobileCardRender={(row) => (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider border ${
                row.difficulty === 'easy' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                row.difficulty === 'medium' ? 'bg-amber-500/15 border-amber-500/30 text-amber-300' :
                'bg-rose-500/15 border-rose-500/30 text-rose-400'
              }`}>
                {row.difficulty}
              </span>
              <span className="font-mono text-xs text-emerald-400 font-semibold">+{row.marks} pts</span>
            </div>

            <p className="text-xs text-white font-medium leading-relaxed">{row.questionText}</p>

            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-surface-border/50">
              <span className="text-cyber-cyan">{row.topic}</span>
              <span>v{row.version}.0</span>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <button className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-slate-200">
                Edit
              </button>
              <button className="px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs">
                Delete
              </button>
            </div>
          </div>
        )}
      />
    </div>
  );
}
