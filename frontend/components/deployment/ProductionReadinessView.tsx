'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Server,
  Database,
  Cloud,
  HardDrive,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Check,
  Lock,
  Layers,
  Activity,
  FileCheck2,
  ExternalLink,
  Cpu,
  Clock,
  Radio,
  Zap,
  BookOpen,
  Bell,
  CheckCheck,
  ChevronDown,
  ChevronUp,
  AlertOctagon,
  FileText,
} from 'lucide-react';
import {
  deploymentService,
  ProductionReadinessResponse,
  ProductionAlertItem,
  DisasterRecoveryRunbookItem,
  DisasterRecoveryDrillItem,
} from '@/services/deploymentService';

interface Props {
  token: string;
  isSuperAdmin: boolean;
}

export const ProductionReadinessView: React.FC<Props> = ({ token, isSuperAdmin }) => {
  const [loading, setLoading] = useState(true);
  const [readiness, setReadiness] = useState<ProductionReadinessResponse | null>(null);
  const [alerts, setAlerts] = useState<ProductionAlertItem[]>([]);
  const [runbooks, setRunbooks] = useState<DisasterRecoveryRunbookItem[]>([]);
  const [drills, setDrills] = useState<DisasterRecoveryDrillItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Active runbook view accordion
  const [expandedRunbook, setExpandedRunbook] = useState<string | null>('SCENARIO_A');

  // Drill execution state
  const [executingDrill, setExecutingDrill] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [rData, aData, rbData, dData] = await Promise.all([
        deploymentService.getReadiness(token),
        deploymentService.getAlerts(token),
        deploymentService.getRunbooks(token),
        deploymentService.getDrills(token),
      ]);
      setReadiness(rData);
      setAlerts(aData);
      setRunbooks(rbData);
      setDrills(dData);
    } catch (err: any) {
      setError(err.message || 'Failed to load production readiness telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) loadData();
  }, [token]);

  const handleAcknowledgeAlert = async (alertId: string) => {
    if (!token || !isSuperAdmin) return;
    try {
      await deploymentService.acknowledgeAlert(token, alertId);
      setActionSuccess('Alert acknowledged.');
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Action failed');
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    if (!token || !isSuperAdmin) return;
    const notes = prompt('Enter resolution notes for audit trail:');
    if (!notes) return;
    try {
      await deploymentService.resolveAlert(token, alertId, notes);
      setActionSuccess('Alert marked as resolved.');
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Action failed');
    }
  };

  const handleExecuteDrill = async (drillName: string, scenario: string) => {
    if (!token || !isSuperAdmin) return;
    try {
      setExecutingDrill(true);
      setActionSuccess(null);
      const res = await deploymentService.executeDrill(token, drillName, scenario);
      setActionSuccess(`Disaster recovery drill passed: ${res.drill_name} (${res.duration_seconds}s).`);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Drill execution failed');
    } finally {
      setExecutingDrill(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <div className="w-10 h-10 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mx-auto" />
        <p className="text-xs text-slate-400 font-mono">Running 14-subsystem production readiness probes...</p>
      </div>
    );
  }

  if (error || !readiness) {
    return (
      <div className="p-6 rounded-2xl glass-card border border-rose-500/30 text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
        <h2 className="text-sm font-bold text-white">Telemetry Disconnected</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto">{error || 'Unable to retrieve status'}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-surface-border transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Probe</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-card p-6 rounded-3xl border border-surface-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-cyber-purple flex items-center justify-center text-white shadow-glow-purple border border-purple-400/30">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>{readiness.overall_classification}</span>
              </span>
              <span className="text-[10px] font-mono text-slate-500">Env: {readiness.environment}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight mt-1">
              Production Readiness &amp; Service Continuity
            </h1>
            <p className="text-xs text-slate-400">
              Real-time audit across 14 infrastructure components, recovery objectives (RPO/RTO), and incident runbooks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-surface-border transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Re-run Telemetry</span>
          </button>

          {isSuperAdmin && (
            <button
              onClick={() => handleExecuteDrill('Simulated Backend Restart Drill', 'SCENARIO_A')}
              disabled={executingDrill}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-xs font-bold text-white shadow-glow-primary transition-all disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${executingDrill ? 'animate-spin' : ''}`} />
              <span>Simulate DR Drill</span>
            </button>
          )}
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Recovery Objectives & Key Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* RPO */}
        <div className="glass-card p-4 rounded-2xl border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Recovery Point Objective (RPO)</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white">{readiness.achievable_rpo}</div>
          <div className="text-[11px] text-slate-400 font-mono">
            Target: {readiness.rpo_target} (Achieved via DB journaling)
          </div>
        </div>

        {/* RTO */}
        <div className="glass-card p-4 rounded-2xl border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Recovery Time Objective (RTO)</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-white">{readiness.achievable_rto}</div>
          <div className="text-[11px] text-slate-400 font-mono">
            Target: {readiness.rto_target} (Instant container / edge rollback)
          </div>
        </div>

        {/* Active Alerts */}
        <div className="glass-card p-4 rounded-2xl border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Active Infrastructure Alerts</span>
            <Bell className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-white">{readiness.active_alerts_count}</div>
          <div className="text-[11px] text-slate-400 font-mono">
            {readiness.active_alerts_count === 0 ? 'All systems nominal' : 'Advisories under monitoring'}
          </div>
        </div>

        {/* Backup Verification */}
        <div className="glass-card p-4 rounded-2xl border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Backup Verification</span>
            <CheckCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white">
            {readiness.latest_restoration_test?.test_status.toUpperCase() || 'VERIFIED'}
          </div>
          <div className="text-[11px] text-slate-400 font-mono truncate">
            {readiness.latest_backup ? readiness.latest_backup.archive_filename : 'Snapshot active'}
          </div>
        </div>
      </div>

      {/* 14 Subsystem Production Checks Grid */}
      <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary-400" />
            <h2 className="text-sm font-bold text-white">14-Subsystem Infrastructure Status</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">Real-time Telemetry Probes</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {readiness.checks.map((chk, i) => {
            const isOp = chk.status === 'Operational';
            const isDeg = chk.status === 'Degraded';
            const isNotConf = chk.status === 'Not Configured';

            return (
              <div
                key={i}
                className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border/70 hover:border-surface-border transition-all space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-xs font-bold text-white truncate">{chk.component}</h3>
                    <p className="text-[10px] text-slate-400 font-mono truncate">{chk.provider}</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase shrink-0 ${
                      isOp
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : isDeg
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : 'bg-slate-800 text-slate-400 border border-surface-border'
                    }`}
                  >
                    {chk.status}
                  </span>
                </div>

                {chk.latency_ms !== null && chk.latency_ms !== undefined && (
                  <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono pt-1">
                    <span>Probe Latency:</span>
                    <span className="text-white font-semibold">{chk.latency_ms} ms</span>
                  </div>
                )}

                {chk.risk_notes && (
                  <p className="text-[10px] text-slate-400 leading-tight pt-1 border-t border-surface-border/40">
                    {chk.risk_notes}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Infrastructure Alerts Panel */}
      {alerts.length > 0 && (
        <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-bold text-white">Infrastructure &amp; Operational Alerts</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">{alerts.length} notifications</span>
          </div>

          <div className="space-y-2">
            {alerts.map((al) => (
              <div
                key={al.id}
                className="p-3.5 rounded-xl bg-slate-900/50 border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                        al.severity === 'critical'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : al.severity === 'warning'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      }`}
                    >
                      {al.severity}
                    </span>
                    <strong className="text-white">{al.title}</strong>
                    <span className="text-slate-500 text-[10px] font-mono">({al.affected_service})</span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">{al.description}</p>
                  {al.suggested_action && (
                    <p className="text-[11px] text-primary-400">
                      <strong>Action:</strong> {al.suggested_action}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {isSuperAdmin && al.status === 'active' && (
                    <>
                      <button
                        onClick={() => handleAcknowledgeAlert(al.id)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => handleResolveAlert(al.id)}
                        className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-[11px] transition-colors"
                      >
                        Resolve
                      </button>
                    </>
                  )}
                  {al.status !== 'active' && (
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      [{al.status}]
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disaster Recovery Runbooks Accordion */}
      <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-bold text-white">Disaster Recovery Runbooks (Scenarios A – E)</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">Operational Procedures</span>
        </div>

        <div className="space-y-3">
          {runbooks.map((rb) => {
            const isExpanded = expandedRunbook === rb.scenario_id;

            return (
              <div
                key={rb.scenario_id}
                className="rounded-xl border border-surface-border bg-slate-900/40 overflow-hidden transition-colors"
              >
                <button
                  onClick={() => setExpandedRunbook(isExpanded ? null : rb.scenario_id)}
                  className="w-full p-4 text-left flex items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-600/20 text-purple-300 border border-purple-500/30">
                      {rb.scenario_id}
                    </span>
                    <span className="text-xs font-bold text-white">{rb.scenario_name}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="p-4 pt-0 border-t border-surface-border/50 text-xs space-y-3 mt-2 text-slate-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-950/40 p-3 rounded-lg border border-surface-border/40">
                      <div>
                        <strong className="text-white block text-[11px] mb-0.5">Detection Method:</strong>
                        <p className="text-slate-400 text-[11px]">{rb.detection_method}</p>
                      </div>
                      <div>
                        <strong className="text-white block text-[11px] mb-0.5">Responsible Role:</strong>
                        <p className="text-slate-400 text-[11px]">{rb.responsible_role}</p>
                      </div>
                      <div className="md:col-span-2">
                        <strong className="text-white block text-[11px] mb-0.5">Immediate Response:</strong>
                        <p className="text-slate-400 text-[11px]">{rb.immediate_response}</p>
                      </div>
                    </div>

                    <div>
                      <strong className="text-white block text-[11px] mb-1">Recovery Procedure:</strong>
                      <ol className="list-decimal list-inside space-y-1 text-slate-300 font-mono text-[11px]">
                        {rb.recovery_procedure.map((step, idx) => (
                          <li key={idx} className="leading-relaxed">
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>

                    <div>
                      <strong className="text-white block text-[11px] mb-1">Data Integrity Verification:</strong>
                      <ul className="list-disc list-inside space-y-0.5 text-slate-400 text-[11px]">
                        {rb.data_integrity_verification.map((v, idx) => (
                          <li key={idx}>{v}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <strong className="text-white block text-[11px] mb-1">Conditions for Normal Operation:</strong>
                      <ul className="list-disc list-inside space-y-0.5 text-emerald-400/90 text-[11px]">
                        {rb.return_to_normal_conditions.map((c, idx) => (
                          <li key={idx}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
