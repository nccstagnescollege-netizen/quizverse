'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  ShieldCheck,
  Layers,
  HelpCircle,
  BookOpen,
  ClipboardList,
  GraduationCap,
  Award,
  BarChart3,
  Activity,
  ShieldAlert,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  Lock,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export const SUPER_ADMIN_NAV_ITEMS = [
  { label: 'Overview', href: '/super-admin/dashboard', icon: LayoutDashboard },
  { label: 'Administrator Management', href: '/super-admin/admins', icon: Users, badge: 'Core' },
  { label: 'Roles & Permissions', href: '/super-admin/admins?tab=roles', icon: ShieldCheck },
  { label: 'Academic Structure', href: '/super-admin/academic', icon: Layers },
  { label: 'Question Bank', href: '/super-admin/question-bank', icon: HelpCircle },
  { label: 'Quiz Management', href: '/admin/quiz', icon: BookOpen },
  { label: 'Examination Management', href: '/super-admin/dashboard#exams', icon: ClipboardList },
  { label: 'Student Management', href: '/super-admin/dashboard#students', icon: GraduationCap },
  { label: 'Results', href: '/admin/analytics?tab=results', icon: Award },
  { label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  { label: 'Live Monitoring', href: '/super-admin/dashboard#monitoring', icon: Activity },
  { label: 'Security Center', href: '/super-admin/admins?tab=security', icon: ShieldAlert },
  { label: 'Audit Logs', href: '/super-admin/admins?tab=audit', icon: FileText },
  { label: 'Platform Settings', href: '/admin/settings', icon: Settings },
];

interface SuperAdminSidebarProps {
  className?: string;
  isMobileDrawer?: boolean;
  onCloseMobileDrawer?: () => void;
}

export function SuperAdminSidebar({
  className,
  isMobileDrawer = false,
  onCloseMobileDrawer,
}: SuperAdminSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        isMobileDrawer
          ? 'flex flex-col w-72 bg-surface-base h-full border-r border-surface-border'
          : cn(
              'hidden lg:flex flex-col border-r border-surface-border bg-surface-base/95 backdrop-blur-xl h-screen sticky top-0 transition-all duration-300 z-30',
              isCollapsed ? 'w-20' : 'w-64',
              className
            )
      )}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-surface-border flex items-center justify-between h-16">
        <Link
          href="/super-admin/dashboard"
          onClick={onCloseMobileDrawer}
          className="flex items-center gap-2.5 overflow-hidden"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 to-cyber-purple flex items-center justify-center shrink-0 shadow-glow-purple">
            <ShieldAlert className="w-4 h-4 text-white" />
          </div>
          {(!isCollapsed || isMobileDrawer) && (
            <div className="min-w-0">
              <span className="font-display font-bold text-sm text-white block truncate">
                QUIZVERSE
              </span>
              <span className="text-[10px] text-purple-400 font-mono tracking-widest block uppercase">
                Super Admin Hub
              </span>
            </div>
          )}
        </Link>

        {!isMobileDrawer ? (
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            suppressHydrationWarning
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        ) : (
          <button
            onClick={onCloseMobileDrawer}
            aria-label="Close navigation menu"
            suppressHydrationWarning
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation List */}
      <nav className="p-3 space-y-1 flex-1 overflow-y-auto">
        {(!isCollapsed || isMobileDrawer) && (
          <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
            Platform Domains (14)
          </p>
        )}
        {SUPER_ADMIN_NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href.split('?')[0].split('#')[0] && item.href.startsWith(pathname);

          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={onCloseMobileDrawer}
              title={isCollapsed && !isMobileDrawer ? item.label : undefined}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors min-h-[44px] touch-manipulation',
                isActive
                  ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40 shadow-glow-purple'
                  : 'text-slate-300 hover:text-white hover:bg-surface-elevated',
                isCollapsed && !isMobileDrawer && 'justify-center px-0'
              )}
            >
              <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-purple-400' : 'text-slate-400')} />
              {(!isCollapsed || isMobileDrawer) && (
                <div className="flex-1 flex items-center justify-between min-w-0">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Switch to Operational Admin */}
      <div className="p-3 border-t border-surface-border">
        <Link
          href="/admin/dashboard"
          onClick={onCloseMobileDrawer}
          className={cn(
            'flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-400 hover:text-cyan-300 transition-colors rounded-xl hover:bg-cyan-500/10',
            isCollapsed && !isMobileDrawer && 'justify-center px-0'
          )}
          title="Switch to User Admin Dashboard"
        >
          <Layers className="w-4 h-4 shrink-0 text-cyan-400" />
          {(!isCollapsed || isMobileDrawer) && <span>Operational View</span>}
        </Link>
      </div>
    </aside>
  );
}
