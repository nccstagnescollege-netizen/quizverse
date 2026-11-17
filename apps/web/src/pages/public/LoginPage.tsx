import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Lock, Mail, ArrowRight, ShieldCheck, Info } from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <div className="max-w-md mx-auto px-4 py-20">
      <div className="text-center mb-8">
        <Badge variant="purple" className="mb-3">
          Access Gateway
        </Badge>
        <h1 className="text-3xl font-display font-bold text-white">Sign In to QUIZVERSE</h1>
        <p className="text-sm text-slate-400 mt-2">
          Enter your institutional credentials or access token.
        </p>
      </div>

      <GlassCard glow="brand" className="border border-brand-500/20">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="architect@quizverse.io"
                className="w-full bg-surface-base border border-surface-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500 transition-colors"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-surface-base border border-surface-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500 transition-colors"
                required
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Remember credentials</span>
            <Link to="#" className="text-brand-400 hover:text-brand-300">
              Forgot password?
            </Link>
          </div>

          <Button type="submit" variant="cyber" className="w-full gap-2">
            Sign In to Console
            <ArrowRight className="w-4 h-4" />
          </Button>

          {/* Phase 1 Notice */}
          <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border flex items-start gap-2.5 text-xs text-slate-400">
            <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
            <span>
              <strong>Phase 1 Route Placeholder:</strong> Full Supabase Authentication flows will be
              wired in Phase 2.
            </span>
          </div>
        </form>
      </GlassCard>

      <div className="text-center mt-6">
        <Link
          to="/admin/dashboard"
          className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1.5"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
          Preview Admin Portal directly &rarr;
        </Link>
      </div>
    </div>
  );
}
