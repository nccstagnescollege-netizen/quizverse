'use client';

import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  FileSpreadsheet,
  Download,
  Calendar,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Clock,
  PieChart,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  SecurityReportsData,
} from '@/services/securityCenterService';
import { StatCard } from '@/components/ui/StatCard';

export default function SecurityCenterReportsPage() {
  const { token } = useAuth();
  const [reports, setReports] = useState<SecurityReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    if (!token) return;
    try {
      setError(null);
      setLoading(true);
      const data = await securityCenterService.getSecurityReports(token, days);
      setReports(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch security analytics reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [token, days]);

  const handleExportJSON = () => {
    if (!reports) return;
    const blob = new Blob([JSON.stringify(reports, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quizverse_security_report_${days}d.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!reports) return;
    let csv = 'Category,Count\n';
    Object.entries(reports.incidents_by_category || {}).forEach(([cat, cnt]) => {
      csv += `"${cat}",${cnt}\n`;
    });
    csv += '\nSeverity,Count\n';
    Object.entries(reports.incidents_by_severity || {}).forEach(([sev, cnt]) => {
      csv += `"${sev}",${cnt}\n`;
    });
    csv += `\nTotal Incidents,${reports.total_incidents}\n`;
    csv += `Resolution Rate,${reports.incident_resolution_rate}%\n`;
    csv += `Average Recovery Time (s),${reports.average_recovery_time_seconds}\n`;
    csv += `False Positive Rate,${reports.false_positive_rate_estimate}%\n`;

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quizverse_security_report_${days}d.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-emerald-500" />
            <span>Security Analytics, Compliance & Incident Reports</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Empirical incident distribution, false positive rates, recovery latency, and policy adherence.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value) || 30)}
            className="px-3 py-1.5 rounded-xl border border-surface-border bg-surface-surface text-xs font-medium focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>

          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 rounded-2xl glass-card border border-surface-border animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Incidents"
            value={reports?.total_incidents ?? 0}
            icon={BarChart3}
            variant="purple"
            description={`In the last ${days} days`}
          />
          <StatCard
            label="Resolution Rate"
            value={`${reports?.incident_resolution_rate ?? 0}%`}
            icon={CheckCircle2}
            variant="emerald"
            description="Human-reviewed determination"
          />
          <StatCard
            label="Avg Recovery Latency"
            value={`${reports?.average_recovery_time_seconds ?? 0}s`}
            icon={Clock}
            variant="cyan"
            description="From interruption to reconnect"
          />
          <StatCard
            label="False Positive Rate"
            value={`${reports?.false_positive_rate_estimate ?? 0}%`}
            icon={ShieldCheck}
            variant="brand"
            description="Discounted non-violating flags"
          />
        </div>
      )}

      {/* Incidents Breakdown by Category & Severity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-5 border border-surface-border">
          <h3 className="font-display font-bold text-sm sm:text-base text-foreground mb-4 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-brand-500" />
            <span>Incidents by Category</span>
          </h3>

          {Object.keys(reports?.incidents_by_category || {}).length === 0 ? (
            <p className="text-xs text-muted-foreground">No incident category records found for this period.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(reports?.incidents_by_category || {}).map(([cat, count]) => {
                const total = reports?.total_incidents || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-foreground capitalize">
                        {cat.replace(/_/g, ' ')}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-surface-surface overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 4)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="glass-card rounded-2xl p-5 border border-surface-border">
          <h3 className="font-display font-bold text-sm sm:text-base text-foreground mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span>Incidents by Severity</span>
          </h3>

          {Object.keys(reports?.incidents_by_severity || {}).length === 0 ? (
            <p className="text-xs text-muted-foreground">No severity breakdown records found for this period.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(reports?.incidents_by_severity || {}).map(([sev, count]) => {
                const total = reports?.total_incidents || 1;
                const pct = Math.round((count / total) * 100);
                const color =
                  sev === 'critical'
                    ? 'bg-red-500'
                    : sev === 'high'
                    ? 'bg-amber-500'
                    : sev === 'medium'
                    ? 'bg-yellow-500'
                    : 'bg-emerald-500';

                return (
                  <div key={sev} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-foreground uppercase">{sev}</span>
                      <span className="font-mono text-muted-foreground">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-surface-surface overflow-hidden">
                      <div
                        className={`h-full ${color} rounded-full transition-all duration-500`}
                        style={{ width: `${Math.max(pct, 4)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
