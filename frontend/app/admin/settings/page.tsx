'use client';

import { Settings, Server, Database, Shield, Globe } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ThemeSelectorCard } from '@/components/ui/ThemeSelectorCard';

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Settings' }]} />

      <PageHeader
        title="Settings &amp; Preferences"
        description="Configure theme appearance, FastAPI backend parameters, Supabase database connections, and operational options."
      />

      {/* Theme & Visual Appearance Preference */}
      <ThemeSelectorCard />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DashboardCard glow="brand" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">FastAPI Backend Configuration</h3>
              <p className="text-xs text-muted-foreground">Render / Cloud Python Application</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Endpoint:</span>
              <span className="text-foreground font-semibold">https://quizverse-ymsg.onrender.com</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>API Prefix:</span>
              <span className="text-foreground">/api/v1</span>
            </div>
            <div className="flex justify-between py-2">
              <span>Deployment Mode:</span>
              <span className="text-cyber-cyan font-semibold">Render Free Tier (Zero Cost)</span>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard glow="purple" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Supabase Infrastructure</h3>
              <p className="text-xs text-muted-foreground">PostgreSQL 15 &amp; Connection Pooling</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Database Engine:</span>
              <span className="text-foreground">PostgreSQL 15 (Supabase)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Migrations:</span>
              <span className="text-foreground">Alembic 1.14 (Schema 0010)</span>
            </div>
            <div className="flex justify-between py-2">
              <span>Row Level Security (RLS):</span>
              <span className="text-emerald-500 font-semibold">100% Enforced (92 Tables)</span>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}
