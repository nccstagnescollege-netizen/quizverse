'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  HelpCircle,
  BookOpen,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Layers,
  ArrowLeft,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export const ADMIN_NAV_ITEMS = [
  {
    label: 'Dashboard',
    href: '/admin/dashboard',
    icon: LayoutDashboard,
    badge: 'v1.0',
  },
  {
    label: 'Super Admin Hub',
    href: '/super-admin/dashboard',
    icon: ShieldAlert,
    badge: 'Super',
  },
  {
    label: 'User Admins',
    href: '/super-admin/admins',
    icon: Users,
  },
  {
    label: 'Question Bank',
    href: '/admin/question-bank',
    icon: HelpCircle,
  },
  {
    label: 'Quiz Management',
    href: '/admin/quiz',
    icon: BookOpen,
  },
  {
    label: 'Analytics',
    href: '/admin/analytics',
    icon: BarChart3,
  },
  {
    label: 'Settings',
    href: '/admin/settings',
    icon: Settings,
  },
];

interface ResponsiveSidebarProps {
  className?: string;
}

export function ResponsiveSidebar({ className }: ResponsiveSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col border-r border-surface-border bg-surface-base/90 backdrop-blur-xl h-screen sticky top-0 transition-all duration-300 z-30',
        isCollapsed ? 'w-20' : 'w-64',
        className
      )}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-surface-border flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center shrink-0 shadow-glow-primary">
            <Layers className="w-4 h-4 text-white" />
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <span className="font-display font-bold text-sm text-white block truncate">
                QUIZVERSE
              </span>
              <span className="text-[10px] text-brand-400 font-mono tracking-widest block uppercase">
                Admin Console
              </span>
            </div>
          )}
        </Link>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="p-3 space-y-1 flex-1 overflow-y-auto">
        {!isCollapsed && (
          <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
            Navigation
          </p>
        )}
        {ADMIN_NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={isCollapsed ? item.label : undefined}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors',
                isActive
                  ? 'bg-brand-600 text-white shadow-glow-primary'
                  : 'text-slate-300 hover:text-white hover:bg-surface-elevated',
                isCollapsed && 'justify-center px-0'
              )}
            >
              <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-white' : 'text-slate-400')} />
              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between">
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/15 text-white font-mono">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer / Back to site */}
      <div className="p-3 border-t border-surface-border">
        <Link
          href="/"
          className={cn(
            'flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors rounded-xl hover:bg-surface-elevated',
            isCollapsed && 'justify-center px-0'
          )}
          title="Return to Public Site"
        >
          <ArrowLeft className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>Public Portal</span>}
        </Link>
      </div>
    </aside>
  );
}
