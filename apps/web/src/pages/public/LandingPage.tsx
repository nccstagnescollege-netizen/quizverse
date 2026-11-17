import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  Database,
  CheckCircle2,
} from 'lucide-react';
import { SceneCanvas } from '../../components/3d/SceneCanvas';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useApiHealth, useSystemStatus } from '../../hooks/useStatus';

export function LandingPage() {
  const { data: health, isLoading: isHealthLoading, isError: isHealthError } = useApiHealth();
  const { data: systemStatus } = useSystemStatus();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* Hero Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center min-h-[600px]">
        {/* Left Column: Headline and Call-to-actions */}
        <motion.div
          className="lg:col-span-7 space-y-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2">
            <Badge variant="cyan" dot>
              Phase 1 &bull; Architecture Ready
            </Badge>
            <Badge variant="purple">Three.js + R3F Powered</Badge>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold font-display tracking-tight leading-tight">
            The Next Dimension of <br />
            <span className="text-gradient">3D Examination</span> &amp; Assessment.
          </h1>

          <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
            QUIZVERSE transforms modern assessment with immersive 3D spatial environments,
            sub-millisecond latency powered by Cloudflare Workers, and enterprise-grade security on
            Supabase PostgreSQL.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-4">
            <Link to="/exam/demo-2024">
              <Button variant="cyber" size="lg" className="gap-2 group">
                Enter Exam Portal
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>

            <Link to="/admin/dashboard">
              <Button variant="outline" size="lg" className="gap-2">
                <ShieldCheck className="w-4 h-4 text-brand-400" />
                Admin Console
              </Button>
            </Link>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-3 gap-4 pt-8 border-t border-surface-border">
            <div>
              <p className="text-2xl font-bold font-mono text-white">0 ms</p>
              <p className="text-xs text-slate-400">Cold-start Edge</p>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-cyber-cyan">60 FPS</p>
              <p className="text-xs text-slate-400">WebGPU/WebGL 3D</p>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-cyber-purple">100%</p>
              <p className="text-xs text-slate-400">Open-Source Stack</p>
            </div>
          </div>
        </motion.div>

        {/* Right Column: Interactive 3D Canvas */}
        <motion.div
          className="lg:col-span-5 h-[420px] lg:h-[520px] relative rounded-3xl overflow-hidden glass-card border border-brand-500/20 shadow-glass-lg flex items-center justify-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
        >
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyber-cyan animate-ping" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-300">
              Interactive 3D Core
            </span>
          </div>

          {/* 3D Scene Viewport */}
          <SceneCanvas className="w-full h-full cursor-grab active:cursor-grabbing" />

          <div className="absolute bottom-4 right-4 z-10 text-[10px] text-slate-400 font-mono">
            Drag to inspect &bull; R3F + Drei
          </div>
        </motion.div>
      </div>

      {/* Project Foundation Status Section */}
      <section className="mt-24 space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <Badge variant="brand" className="mb-2">
              Phase 1 Verification
            </Badge>
            <h2 className="text-3xl font-display font-bold text-white">
              System Foundation &amp; Status
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Live health check of all monorepo pillars, backend services, and database readiness.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-slate-300">Continuous Monitoring</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Frontend Card */}
          <GlassCard glow="cyan">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-cyber-cyan/10 border border-cyber-cyan/30 text-cyber-cyan">
                <Layers className="w-5 h-5" />
              </div>
              <Badge variant="cyan" dot>
                Running
              </Badge>
            </div>
            <h3 className="text-base font-semibold text-white">Frontend Web App</h3>
            <p className="text-xs text-slate-400 mt-1">
              React 18 + Vite + TypeScript + Tailwind CSS + Framer Motion.
            </p>
            <div className="mt-4 pt-4 border-t border-surface-border text-xs text-slate-400 font-mono">
              Port: 5173 &bull; SPA Router
            </div>
          </GlassCard>

          {/* Backend API Card */}
          <GlassCard glow="brand">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-400">
                <Cpu className="w-5 h-5" />
              </div>
              {isHealthLoading ? (
                <Badge variant="neutral" dot>
                  Checking...
                </Badge>
              ) : health?.status === 'healthy' ? (
                <Badge variant="emerald" dot>
                  Healthy
                </Badge>
              ) : isHealthError ? (
                <Badge variant="rose" dot>
                  Offline
                </Badge>
              ) : (
                <Badge variant="amber" dot>
                  Pending
                </Badge>
              )}
            </div>
            <h3 className="text-base font-semibold text-white">Backend Hono API</h3>
            <p className="text-xs text-slate-400 mt-1">
              Cloudflare Worker / Node runtime with Zod validation and structured logging.
            </p>
            <div className="mt-4 pt-4 border-t border-surface-border text-xs text-slate-400 font-mono">
              Endpoint: /api/v1/health
            </div>
          </GlassCard>

          {/* Supabase PostgreSQL Card */}
          <GlassCard glow="purple">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
                <Database className="w-5 h-5" />
              </div>
              <Badge
                variant={systemStatus?.database === 'connected' ? 'emerald' : 'amber'}
                dot
              >
                {systemStatus?.database === 'connected' ? 'Connected' : 'Prepared'}
              </Badge>
            </div>
            <h3 className="text-base font-semibold text-white">Supabase PostgreSQL</h3>
            <p className="text-xs text-slate-400 mt-1">
              Database connection utilities, migrations directory, and RLS schema documentation.
            </p>
            <div className="mt-4 pt-4 border-t border-surface-border text-xs text-slate-400 font-mono">
              Phase 3 Schema Ready
            </div>
          </GlassCard>

          {/* Shared Package Card */}
          <GlassCard glow="brand">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-brand-600/10 border border-brand-500/30 text-brand-300">
                <Sparkles className="w-5 h-5" />
              </div>
              <Badge variant="brand" dot>
                Linked
              </Badge>
            </div>
            <h3 className="text-base font-semibold text-white">@quizverse/shared</h3>
            <p className="text-xs text-slate-400 mt-1">
              Shared TypeScript contracts, roles, status constants, and Zod schemas.
            </p>
            <div className="mt-4 pt-4 border-t border-surface-border text-xs text-slate-400 font-mono">
              pnpm workspace module
            </div>
          </GlassCard>
        </div>

        {/* Live Diagnostics Card */}
        <GlassCard className="border border-brand-500/20 bg-surface-elevated/60">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h4 className="text-sm font-semibold text-white">Environment &amp; Security Baseline</h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-surface-base border border-surface-border">
              <span className="text-slate-400 block mb-1">Architecture</span>
              <span className="text-slate-200">Monorepo (pnpm workspaces)</span>
            </div>
            <div className="p-3 rounded-lg bg-surface-base border border-surface-border">
              <span className="text-slate-400 block mb-1">Deployment Targets</span>
              <span className="text-cyber-cyan">Cloudflare Pages &amp; Workers</span>
            </div>
            <div className="p-3 rounded-lg bg-surface-base border border-surface-border">
              <span className="text-slate-400 block mb-1">Security Isolation</span>
              <span className="text-emerald-400">Zero Client Secrets Leaked</span>
            </div>
          </div>
        </GlassCard>
      </section>
    </div>
  );
}
