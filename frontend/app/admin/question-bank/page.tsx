'use client';

import { useState } from 'react';
import { Plus, Search, Filter, HelpCircle } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { EmptyState } from '@/components/ui/EmptyState';

export default function AdminQuestionBankPage() {
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Question Bank' }]} />

      <PageHeader
        title="Question Bank Management"
        description="Author, organize, and categorize multi-format questions with 3D spatial models and LaTeX math."
        actions={
          <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple">
            <Plus className="w-3.5 h-3.5" />
            Add Question
          </button>
        }
      />

      {/* Filter Toolbar */}
      <DashboardCard className="p-3.5 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search questions by keyword, topic, or tag..."
            className="w-full bg-surface-base border border-surface-border rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <button className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-300 hover:text-white">
          <Filter className="w-3.5 h-3.5" />
          Filters
        </button>
      </DashboardCard>

      {/* Empty State */}
      <EmptyState
        title="Question Bank is Empty"
        description="No examination questions have been authored yet. Question authoring, media attachments, and 3D coordinate tags will be populated in Phase 3."
        icon={HelpCircle}
        action={
          <span className="px-3 py-1 rounded-full text-[11px] font-mono uppercase tracking-wider bg-surface-elevated border border-surface-border text-slate-400">
            Phase 1 Placeholder
          </span>
        }
      />
    </div>
  );
}
