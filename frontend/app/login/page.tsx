'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Mail, Lock, ArrowRight, ShieldCheck, AlertCircle, Shield, KeyRound, CheckCircle2 } from 'lucide-react';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { FormField } from '@/components/ui/FormField';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const res = await login(email, password);
    if (!res.success) {
      setErrorMessage(res.error || 'Authentication failed. Please verify credentials.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      <TopNavbar
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        isMobileMenuOpen={isMobileMenuOpen}
      />

      <MobileNavigation
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      <main className="flex-1 relative z-10 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center space-y-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-cyber-purple/15 border border-cyber-purple/30 text-purple-300">
              Administrative Gateway
            </span>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-white tracking-tight">
              Sign In to QUIZVERSE
            </h1>
            <p className="text-xs text-slate-400">
              Access the Super Admin Control Hub or Scoped User Admin Dashboard.
            </p>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <DashboardCard glow="brand" className="border border-brand-500/20 backdrop-blur-xl">
            <form onSubmit={handleSignIn} className="space-y-4">
              <FormField
                label="Administrator Email"
                type="email"
                placeholder="admin@quizverse.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<Mail className="w-4 h-4 text-slate-400" />}
                required
              />

              <FormField
                label="Security Password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock className="w-4 h-4 text-slate-400" />}
                required
              />

              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 text-slate-400 cursor-pointer text-[11px]">
                  <input
                    type="checkbox"
                    defaultChecked
                    className="rounded bg-surface-base border-surface-border text-brand-500 focus:ring-0"
                  />
                  Maintain persistent session
                </label>
                <span className="text-[11px] text-slate-500">
                  Protected by PyJWT &amp; RLS
                </span>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? 'Authenticating...' : 'Sign In to Platform'}
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="p-2.5 rounded-lg bg-surface-highlight/30 border border-surface-border/50 text-[11px]">
                  <div className="flex items-center gap-1.5 font-semibold text-purple-300">
                    <Shield className="w-3.5 h-3.5" />
                    Super Admin
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Full platform governance &amp; User Admin control
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-surface-highlight/30 border border-surface-border/50 text-[11px]">
                  <div className="flex items-center gap-1.5 font-semibold text-cyan-300">
                    <KeyRound className="w-3.5 h-3.5" />
                    User Admin
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Scoped quiz authoring &amp; examination monitor
                  </p>
                </div>
              </div>
            </form>
          </DashboardCard>

          <div className="p-3 rounded-xl bg-surface-card/60 border border-surface-border flex items-center justify-between text-xs text-slate-400">
            <span>Are you a student or candidate?</span>
            <Link
              href="/exam/demo-token"
              className="text-brand-400 hover:text-brand-300 font-semibold inline-flex items-center gap-1"
            >
              Candidate Portal &rarr;
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
