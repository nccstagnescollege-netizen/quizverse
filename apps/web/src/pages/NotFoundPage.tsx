import { Link } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';
import { GlassCard } from '../components/common/GlassCard';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';

export function NotFoundPage() {
  return (
    <div className="max-w-md mx-auto px-4 py-24 text-center">
      <GlassCard glow="purple" className="space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center mx-auto">
          <Compass className="w-8 h-8 animate-spin" style={{ animationDuration: '10s' }} />
        </div>

        <div>
          <Badge variant="rose" className="mb-2">
            Error 404
          </Badge>
          <h1 className="text-2xl font-display font-bold text-white">Dimension Not Found</h1>
          <p className="text-xs text-slate-400 mt-2">
            The requested QUIZVERSE coordinate does not exist or has moved.
          </p>
        </div>

        <Link to="/">
          <Button variant="cyber" size="md" className="gap-2 w-full">
            <ArrowLeft className="w-4 h-4" />
            Return to Safety
          </Button>
        </Link>
      </GlassCard>
    </div>
  );
}
