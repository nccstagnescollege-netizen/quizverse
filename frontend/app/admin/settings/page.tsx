'use client';

import { Settings, Server, Database, Shield, Globe } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Admin', href: '/admin/dashboard' }, { label: 'Settings' }]} />

      <PageHeader
        title="System Settings"
        description="Configure FastAPI backend connection, Supabase PostgreSQL poolers, and deployment parameters."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DashboardCard glow="brand" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">FastAPI Backend Configuration</h3>
              <p className="text-xs text-slate-400">Render / Local Python Container</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">Endpoint:</span>
              <span>http://localhost:8000</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">API Prefix:</span>
              <span>/api/v1</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">Deployment Target:</span>
              <span className="text-cyber-cyan">Render Free Tier</span>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard glow="purple" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Supabase Infrastructure</h3>
              <p className="text-xs text-slate-400">PostgreSQL 15 &amp; Connection Pooling</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">Database Engine:</span>
              <span>PostgreSQL 15 (Supabase)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">Migrations:</span>
              <span>Alembic 1.14</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">Row Level Security:</span>
              <span className="text-emerald-400">Enabled</span>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}
