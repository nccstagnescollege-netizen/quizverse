'use client';

import React, { useState, useEffect } from 'react';
import {
  HeartPulse,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Server,
  Database,
  Cpu,
  Lock,
  Smartphone,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  SecurityHealthResponse,
} from '@/services/securityCenterService';

export default function SecurityCenterHealthPage() {
  const { token } = useAuth();
  const [health, setHealth] = useState<SecurityHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getHealth(token);
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch subsystem health telemetry.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [token]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchHealth();
  };

  const getSubsystemIcon = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('database')) return Database;
    if (n.includes('proctoring') || n.includes('ai')) return Cpu;
    if (n.includes('lockdown') || n.includes('browser')) return Lock;
    if (n.includes('interruption')) return Activity;
    if (n.includes('watermark')) return ShieldCheck;
    if (n.includes('seb') || n.includes('desktop')) return Server;
    return Server;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <HeartPulse className="w-5 h-5 text-emerald-500" />
            <span>Anti-Cheating Subsystem Health & Diagnostics</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Real-time ping latency, service status, and operational diagnostics across all 6 security layers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-muted-foreground">
            {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : ''}
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-brand-500' : ''}`} />
            <span>Ping Services</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Overall Health Card */}
      <div className="glass-card rounded-2xl p-5 border border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`p-3 rounded-xl border ${
              health?.overall_status === 'healthy'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                : health?.overall_status === 'degraded'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
                : 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400'
            }`}
          >
            {health?.overall_status === 'healthy' ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : health?.overall_status === 'degraded' ? (
              <AlertTriangle className="w-6 h-6" />
            ) : (
              <XCircle className="w-6 h-6" />
            )}
          </div>
          <div>
            <div className="text-xs font-mono text-muted-foreground uppercase">
              Global Security Infrastructure
            </div>
            <div className="text-lg sm:text-xl font-display font-bold text-foreground capitalize">
              {health?.overall_status || 'Checking...'}
            </div>
          </div>
        </div>

        <div className="hidden sm:block text-right">
          <span className="text-xs font-mono text-muted-foreground">
            Monitored Subsystems: {health?.subsystems.length || 6} / 6
          </span>
        </div>
      </div>

      {/* 6 Subsystem Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          [...Array(6)].map((_, i) => (
            <div key={i} className="h-40 rounded-2xl glass-card border border-surface-border animate-pulse" />
          ))
        ) : (
          (health?.subsystems || []).map((sub) => {
            const Icon = getSubsystemIcon(sub.name);
            const isHealthy = sub.status === 'healthy';
            const isDegraded = sub.status === 'degraded';

            return (
              <div
                key={sub.name}
                className="glass-card rounded-2xl p-5 border border-surface-border flex flex-col justify-between hover:border-brand-500/30 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-xl bg-surface-surface border border-surface-border text-foreground">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold uppercase ${
                        isHealthy
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                          : isDegraded
                          ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                          : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isHealthy ? 'bg-emerald-500' : isDegraded ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                      />
                      <span>{sub.status}</span>
                    </span>
                  </div>

                  <h3 className="font-semibold text-foreground text-sm sm:text-base">
                    {sub.name}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {sub.message}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs font-mono">
                  <span className="text-muted-foreground">Response Latency:</span>
                  <span className={`font-semibold ${sub.latency_ms < 50 ? 'text-emerald-500' : 'text-amber-500'}`}>
                    {sub.latency_ms} ms
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
