'use client';

import React from 'react';
import { Settings, Shield, KeyRound, Database, Server, RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ThemeSelectorCard } from '@/components/ui/ThemeSelectorCard';

export default function SuperAdminSettingsPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Super Admin', href: '/super-admin/dashboard' }, { label: 'Settings' }]} />

      <PageHeader
        title="Platform &amp; System Settings"
        description="Manage global appearance theme, security parameters, database connections, and platform infrastructure."
      />

      {/* Global Theme Selector */}
      <ThemeSelectorCard />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DashboardCard glow="brand" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Global Security &amp; RBAC</h3>
              <p className="text-xs text-muted-foreground">Access controls and audit logs</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Multi-Tenant RLS:</span>
              <span className="text-emerald-500 font-semibold">Enabled</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Authentication Token:</span>
              <span className="text-foreground">HS256 Cryptographic JWT</span>
            </div>
            <div className="flex justify-between py-2">
              <span>Session Invalidation:</span>
              <span className="text-cyber-cyan font-semibold">Real-time Redis / DB</span>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard glow="purple" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Database &amp; Storage Architecture</h3>
              <p className="text-xs text-muted-foreground">Supabase PostgreSQL &amp; Bucket Storage</p>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Engine:</span>
              <span className="text-foreground">PostgreSQL 15</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span>Tables Governed:</span>
              <span className="text-foreground font-semibold">92 Tables</span>
            </div>
            <div className="flex justify-between py-2">
              <span>Service Role Policies:</span>
              <span className="text-emerald-500 font-semibold">Active</span>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}
