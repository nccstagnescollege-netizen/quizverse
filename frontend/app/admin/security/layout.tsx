'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  Activity,
  Sliders,
  ShieldAlert,
  Laptop,
  Eye,
  BellRing,
  BarChart3,
  FileText,
  Lock,
  HeartPulse,
  Home,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
}

const navItems: NavItem[] = [
  { name: 'Overview', href: '/admin/security', icon: ShieldCheck, exact: true },
  { name: 'Live Monitoring', href: '/admin/security/live', icon: Activity },
  { name: 'Policies', href: '/admin/security/policies', icon: Sliders },
  { name: 'Incidents', href: '/admin/security/incidents', icon: ShieldAlert },
  { name: 'Compatibility', href: '/admin/security/compatibility', icon: Laptop },
  { name: 'AI Proctoring', href: '/admin/security/proctoring', icon: Eye },
  { name: 'Alert Rules', href: '/admin/security/alerts', icon: BellRing },
  { name: 'Reports', href: '/admin/security/reports', icon: BarChart3 },
  { name: 'Audit Logs', href: '/admin/security/audit', icon: FileText },
  { name: 'Privacy & Data', href: '/admin/security/privacy', icon: Lock },
  { name: 'System Health', href: '/admin/security/health', icon: HeartPulse },
];

export default function SecurityCenterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const isCurrentActive = (item: NavItem) => {
    if (item.exact) {
      return pathname === item.href;
    }
    return pathname.startsWith(item.href);
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Control Center Banner */}
      <div className="glass-card rounded-2xl p-4 sm:p-5 border border-surface-border">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-1.5">
              <Link href="/admin/dashboard" className="hover:text-foreground transition-colors flex items-center gap-1">
                <Home className="w-3.5 h-3.5" />
                <span>Admin</span>
              </Link>
              <ChevronRight className="w-3 h-3" />
              <span className="text-brand-500 font-semibold">Anti-Cheating Control Center</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-display font-bold text-foreground flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-brand-500/10 text-brand-500 border border-brand-500/20">
                <ShieldCheck className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <span>Anti-Cheating Control Center</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30 font-mono uppercase tracking-wider">
                Phase 28
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
              Unified database-driven examination security hub consolidating browser lockdown, dynamic watermarking, mobile & SEB modes, AI proctoring, and interruption recovery.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 self-start md:self-auto">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>TELEMETRY ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Scrollable Navigation Pill Bar */}
        <div className="mt-5 pt-4 border-t border-surface-border overflow-x-auto no-scrollbar">
          <nav className="flex items-center gap-1.5 min-w-max pb-1">
            {navItems.map((item) => {
              const active = isCurrentActive(item);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all duration-200 shrink-0',
                    active
                      ? 'bg-brand-500 text-white shadow-brand font-semibold shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-surface-surface/60'
                  )}
                >
                  <Icon className={cn('w-4 h-4', active ? 'text-white' : 'text-muted-foreground')} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Sub-Page Content */}
      <div>{children}</div>
    </div>
  );
}
