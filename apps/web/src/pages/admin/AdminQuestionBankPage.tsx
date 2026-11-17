import { HelpCircle, Plus, Search, Filter } from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';

export function AdminQuestionBankPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-surface-border">
        <div>
          <div className="inline-flex items-center gap-2 mb-2">
            <Badge variant="cyan">Question Management</Badge>
          </div>
          <h1 className="text-2xl font-display font-bold text-white">Question Bank</h1>
          <p className="text-xs text-slate-400 mt-1">
            Build and organize multi-type question pools with rich media &amp; 3D spatial cues.
          </p>
        </div>

        <Button variant="cyber" size="sm" className="gap-2">
          <Plus className="w-4 h-4" />
          Create Question
        </Button>
      </div>

      {/* Filter / Search Bar */}
      <GlassCard className="p-4 flex flex-col sm:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search questions by title, tag, or topic..."
            className="w-full bg-surface-base border border-surface-border rounded-xl pl-10 pr-4 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
          />
        </div>
        <Button variant="secondary" size="sm" className="gap-2 shrink-0">
          <Filter className="w-3.5 h-3.5" />
          Filters
        </Button>
      </GlassCard>

      {/* Placeholder Table / Empty State */}
      <GlassCard className="p-12 text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-cyber-cyan/10 border border-cyber-cyan/30 text-cyber-cyan flex items-center justify-center mx-auto">
          <HelpCircle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-white">No Questions in Question Bank</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
            This module route is prepared. Full question creation, rich text editing, and 3D asset
            tagging will be fully functional in Phase 3.
          </p>
        </div>
      </GlassCard>
    </div>
  );
}
