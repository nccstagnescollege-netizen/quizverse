import { Cloud, Database } from 'lucide-react';
import { GlassCard } from '../../components/common/GlassCard';
import { Badge } from '../../components/common/Badge';

export function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="pb-6 border-b border-surface-border">
        <div className="inline-flex items-center gap-2 mb-2">
          <Badge variant="brand">Configuration</Badge>
        </div>
        <h1 className="text-2xl font-display font-bold text-white">System Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage platform parameters, Cloudflare Workers connectivity, and Supabase keys.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Edge API Deployment</h2>
              <p className="text-xs text-slate-400">Cloudflare Workers runtime settings</p>
            </div>
          </div>
          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">Target:</span>
              <span>Cloudflare Workers / Pages</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">API Gateway:</span>
              <span>/api/v1</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">Cost Profile:</span>
              <span className="text-emerald-400">Free Tier Compatible</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Supabase Infrastructure</h2>
              <p className="text-xs text-slate-400">PostgreSQL and Storage connections</p>
            </div>
          </div>
          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">Database Engine:</span>
              <span>PostgreSQL 15 (Supabase)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-border">
              <span className="text-slate-400">RLS Enforcement:</span>
              <span className="text-brand-300">Enabled</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">Storage Buckets:</span>
              <span>exam-assets (prepared)</span>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
