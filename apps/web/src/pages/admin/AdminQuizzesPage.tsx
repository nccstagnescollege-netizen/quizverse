import { BookOpen, Plus, Sparkles } from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';

export function AdminQuizzesPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-surface-border">
        <div>
          <div className="inline-flex items-center gap-2 mb-2">
            <Badge variant="purple">Assessment Engine</Badge>
          </div>
          <h1 className="text-2xl font-display font-bold text-white">Quizzes &amp; Examinations</h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure examination rules, timing, anti-cheat tolerances, and 3D environment scenes.
          </p>
        </div>

        <Button variant="cyber" size="sm" className="gap-2">
          <Plus className="w-4 h-4" />
          Create New Quiz
        </Button>
      </div>

      <GlassCard className="p-12 text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center mx-auto">
          <BookOpen className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-white">No Quizzes Configured</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
            Quiz creation workflows, access token generators, and student attempt monitoring will
            be integrated in Phase 3.
          </p>
        </div>
        <div className="pt-2">
          <Badge variant="neutral">
            <Sparkles className="w-3 h-3 mr-1 inline" />
            Module Placeholder Ready
          </Badge>
        </div>
      </GlassCard>
    </div>
  );
}
