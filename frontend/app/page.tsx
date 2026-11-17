'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import {
  Sparkles,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  Database,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { StatCard } from '@/components/ui/StatCard';
import { fetchBackendHealth } from '@/services/api';
import type { BackendHealthResponse } from '@/types';

// Lazy-load heavy 3D scene to prevent blocking main thread
const HeroScene = dynamic(() => import('@/components/3d/HeroScene'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-24 h-24 rounded-full border-2 border-brand-500/30 border-t-cyber-cyan animate-spin" />
    </div>
  ),
});

export default function LandingPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [healthData, setHealthData] = useState<BackendHealthResponse | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);

  useEffect(() => {
    fetchBackendHealth()
      .then((data) => setHealthData(data))
      .finally(() => setIsCheckingHealth(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100 bg-grid-pattern relative">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      {/* Top Navigation */}
      <TopNavbar
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        isMobileMenuOpen={isMobileMenuOpen}
      />

      {/* Mobile Drawer */}
      <MobileNavigation
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content */}
      <main className="flex-1 relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-16">
        {/* Hero Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 md:gap-12 items-center min-h-[520px]">
          {/* Left Column */}
          <div className="lg:col-span-7 space-y-5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium border border-cyber-cyan/30 bg-cyber-cyan/10 text-cyber-cyan tracking-wide uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-cyber-cyan animate-ping" />
              Phase 1 &bull; System Architecture
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-display tracking-tight leading-tight">
              The Next Dimension of <br />
              <span className="text-gradient">3D Examination</span> &amp; Assessment.
            </h1>

            <p className="text-sm sm:text-base text-slate-300 max-w-xl leading-relaxed">
              QUIZVERSE is an enterprise spatial assessment ecosystem combining real-time
              Three.js visualization, high-concurrency FastAPI edge endpoints, and Supabase PostgreSQL.
            </p>

            <div className="flex flex-wrap items-center gap-3.5 pt-2">
              <Link href="/exam/demo-test" className="w-full sm:w-auto">
                <button className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs sm:text-sm font-semibold shadow-glow-purple border border-purple-400/30 hover:scale-105 active:scale-95 transition-all">
                  Candidate Exam Portal
                  <ArrowRight className="w-4 h-4" />
                </button>
              </Link>

              <Link href="/admin/dashboard" className="w-full sm:w-auto">
                <button className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-surface-elevated border border-surface-border text-slate-200 text-xs sm:text-sm font-medium hover:text-white hover:border-brand-500/40 transition-colors">
                  <ShieldCheck className="w-4 h-4 text-brand-400" />
                  Administrator Suite
                </button>
              </Link>
            </div>
          </div>

          {/* Right Column: 3D Canvas */}
          <div className="lg:col-span-5 h-[360px] sm:h-[420px] lg:h-[480px] relative rounded-3xl overflow-hidden glass-card border border-brand-500/20 shadow-glass-lg flex items-center justify-center">
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-300">
                Interactive 3D Core
              </span>
            </div>

            <HeroScene />

            <div className="absolute bottom-4 right-4 z-10 text-[9px] text-slate-400 font-mono">
              WebGL 2.0 &bull; Reduced Motion Supported
            </div>
          </div>
        </div>

        {/* Foundation Telemetry Stats */}
        <section className="mt-16 md:mt-24 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
            <div>
              <span className="text-xs font-mono uppercase text-brand-400 font-semibold tracking-wider">
                Telemetry
              </span>
              <h2 className="text-2xl sm:text-3xl font-display font-bold text-white mt-1">
                Platform Architecture Matrix
              </h2>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Phase 1 Verification Active
            </div>
          </div>

          {/* Responsive Cards: 1 column on mobile, 2 on tablet, 4 on desktop */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            <StatCard
              label="Frontend Engine"
              value="Next.js 14"
              subtitle="App Router + TypeScript + Tailwind"
              icon={Layers}
              variant="cyan"
              trend="Vercel Ready"
            />

            <StatCard
              label="Backend API"
              value="FastAPI"
              subtitle={
                isCheckingHealth
                  ? 'Connecting to :8000...'
                  : healthData?.data.status === 'healthy'
                  ? 'FastAPI Online (:8000)'
                  : 'FastAPI Standby'
              }
              icon={Cpu}
              variant="brand"
              trend={healthData?.data.version ? `v${healthData.data.version}` : 'Python 3.13'}
            />

            <StatCard
              label="Database"
              value="Supabase"
              subtitle="PostgreSQL 15 + Alembic Migrations"
              icon={Database}
              variant="purple"
              trend="Free Tier"
            />

            <StatCard
              label="Security & Auth"
              value="Zero-Trust"
              subtitle="Strict RLS + Sanitized HTTP Boundaries"
              icon={Lock}
              variant="emerald"
              trend="OWASP Top 10"
            />
          </div>

          {/* Diagnostics Box */}
          <DashboardCard glow="brand" className="mt-6 border border-brand-500/20">
            <div className="flex items-center gap-2.5 mb-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">System Verification Checklist</h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
                <span className="text-slate-400 block mb-0.5">Deployment Ready</span>
                <span className="text-slate-200">Vercel (FE) + Render (BE)</span>
              </div>
              <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
                <span className="text-slate-400 block mb-0.5">Health API Probe</span>
                <span className="text-cyber-cyan">GET /api/v1/health</span>
              </div>
              <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
                <span className="text-slate-400 block mb-0.5">Secret Isolation</span>
                <span className="text-emerald-400">Zero Client Secrets Leaked</span>
              </div>
            </div>
          </DashboardCard>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border bg-surface-base/90 py-8 relative z-10 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white">QUIZVERSE</span>
            <span>&bull;</span>
            <span>Phase 1 Foundation</span>
          </div>
          <div className="flex items-center gap-4 font-mono">
            <span>Next.js App Router</span>
            <span>FastAPI</span>
            <span>Supabase</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
