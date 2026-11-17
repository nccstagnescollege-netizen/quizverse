'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Mail, Lock, ArrowRight, ShieldCheck, Info } from 'lucide-react';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { FormField } from '@/components/ui/FormField';

export default function LoginPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
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
              Access Gateway
            </span>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-white">
              Sign In to QUIZVERSE
            </h1>
            <p className="text-xs text-slate-400">
              Enter your administrator or institutional credentials.
            </p>
          </div>

          <DashboardCard glow="brand" className="border border-brand-500/20">
            <form onSubmit={handleSignIn} className="space-y-4">
              <FormField
                label="Email Address"
                type="email"
                placeholder="administrator@quizverse.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<Mail className="w-4 h-4" />}
                required
              />

              <FormField
                label="Password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock className="w-4 h-4" />}
                required
              />

              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
                  <input type="checkbox" className="rounded bg-surface-base border-surface-border text-brand-500" />
                  Remember session
                </label>
                <Link href="#" className="text-brand-400 hover:text-brand-300">
                  Reset password
                </Link>
              </div>

              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-semibold shadow-glow-purple transition-all"
              >
                Sign In to Platform
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-start gap-2.5 text-xs text-slate-400">
                <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <span className="text-[11px]">
                  <strong>Phase 1 Notice:</strong> Full Supabase Authentication &amp; JWT verification
                  flows activate in Phase 2.
                </span>
              </div>
            </form>
          </DashboardCard>

          <div className="text-center">
            <Link
              href="/admin/dashboard"
              className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
              Preview Admin Dashboard Directly &rarr;
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
