'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Layers, ShieldCheck, ArrowLeft, Cpu, Database, Eye } from 'lucide-react';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

export default function AboutPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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

      <main className="flex-1 relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        <Breadcrumb items={[{ label: 'About' }]} />

        <PageHeader
          title="About QUIZVERSE"
          description="Architecture overview and roadmap for the next-generation 3D spatial assessment platform."
          badge={
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-brand-500/15 border border-brand-500/30 text-brand-300">
              System Specification
            </span>
          }
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <DashboardCard glow="cyan">
            <Layers className="w-6 h-6 text-cyber-cyan mb-3" />
            <h3 className="text-base font-semibold text-white">Spatial 3D Engine</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Leverages WebGPU and Three.js with React Three Fiber to render interactive, 3D
              assessment scenes, spatial graphs, and scientific models directly in candidate
              browsers.
            </p>
          </DashboardCard>

          <DashboardCard glow="brand">
            <Cpu className="w-6 h-6 text-brand-400 mb-3" />
            <h3 className="text-base font-semibold text-white">High-Speed API</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Engineered with FastAPI on Python 3.13, offering sub-millisecond route dispatch,
              Pydantic v2 input validation, and horizontal scaling on free-tier containers.
            </p>
          </DashboardCard>

          <DashboardCard glow="purple">
            <Database className="w-6 h-6 text-purple-400 mb-3" />
            <h3 className="text-base font-semibold text-white">PostgreSQL Foundation</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Powered by Supabase PostgreSQL 15, Row Level Security (RLS), and Alembic migration
              versioning for deterministic deployment across all 20 phases.
            </p>
          </DashboardCard>
        </div>

        <DashboardCard className="p-6 md:p-8 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">20-Phase Development Roadmap</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            QUIZVERSE is executed in sequential development phases. Phase 1 establishes the monorepo,
            design tokens, FastAPI foundation, Next.js App Router, and database integration
            readiness. Phase 2 introduces full Supabase Authentication and Role-Based Access Control
            (RBAC).
          </p>

          <div className="pt-2">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-cyber-cyan hover:underline"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Platform Overview
            </Link>
          </div>
        </DashboardCard>
      </main>
    </div>
  );
}
