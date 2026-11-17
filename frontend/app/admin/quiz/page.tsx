'use client';

import { BookOpen, Plus } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { EmptyState } from '@/components/ui/EmptyState';

export default function AdminQuizPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Quiz Management' }]} />

      <PageHeader
        title="Quiz &amp; Examination Engine"
        description="Configure timed exams, randomize question permutations, and set 3D spatial environments."
        actions={
          <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple">
            <Plus className="w-3.5 h-3.5" />
            Create Examination
          </button>
        }
      />

      <EmptyState
        title="No Active Quizzes"
        description="Quiz creation wizards, token generators, and student attempt monitoring will be integrated in Phase 3."
        icon={BookOpen}
        action={
          <span className="px-3 py-1 rounded-full text-[11px] font-mono uppercase tracking-wider bg-surface-elevated border border-surface-border text-slate-400">
            Phase 1 Module Placeholder
          </span>
        }
      />
    </div>
  );
}
