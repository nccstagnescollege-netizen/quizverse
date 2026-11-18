'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  BookOpen,
  PlusCircle,
  HelpCircle,
  Layers,
  GraduationCap,
  Award,
  BarChart3,
  Activity,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  X,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

interface UserAdminSidebarProps {
  className?: string;
  isMobileDrawer?: boolean;
  onCloseMobileDrawer?: () => void;
}

export function UserAdminSidebar({
  className,
  isMobileDrawer = false,
  onCloseMobileDrawer,
}: UserAdminSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();
  const { hasPermission, isSuperAdmin } = useAuth();

  // Dynamically derive authorized navigation items
  const authorizedNavItems = useMemo(() => {
    const items = [
      {
        label: 'Overview',
        href: '/admin/dashboard',
        icon: LayoutDashboard,
        authorized: true,
      },
      {
        label: 'My Quizzes',
        href: '/admin/quiz',
        icon: BookOpen,
        authorized: hasPermission('quiz.view'),
      },
      {
        label: 'Create Quiz',
        href: '/admin/quiz#create',
        icon: PlusCircle,
        authorized: hasPermission('quiz.create'),
      },
      {
        label: 'Question Bank',
        href: '/admin/question-bank',
        icon: HelpCircle,
        authorized: hasPermission('question.view'),
      },
      {
        label: 'Quiz Generator',
        href: '/admin/quiz-generator',
        icon: Sparkles,
        authorized: hasPermission('quiz.generate') || hasPermission('quiz.create'),
      },
      {
        label: 'Academic Structure',
        href: '/admin/academic',
        icon: Layers,
        authorized: hasPermission('academic.view'),
      },
      {
        label: 'Student Registrations',
        href: '/admin/dashboard#students',
        icon: GraduationCap,
        authorized: hasPermission('student.view'),
      },
      {
        label: 'Results',
        href: '/admin/analytics?tab=results',
        icon: Award,
        authorized: hasPermission('analytics.view') || hasPermission('examination.grade'),
      },
      {
        label: 'Analytics',
        href: '/admin/analytics',
        icon: BarChart3,
        authorized: hasPermission('analytics.view'),
      },
      {
        label: 'Examination Monitoring',
        href: '/admin/dashboard#monitoring',
        icon: Activity,
        authorized: hasPermission('examination.monitor'),
      },
      {
        label: 'Profile & Security',
        href: '/admin/settings',
        icon: ShieldCheck,
        authorized: true,
      },
    ];

    return items.filter((item) => item.authorized);
  }, [hasPermission]);

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
          href="/admin/dashboard"
          onClick={onCloseMobileDrawer}
          className="flex items-center gap-2.5 overflow-hidden"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-brand-600 flex items-center justify-center shrink-0 shadow-glow-primary">
            <Layers className="w-4 h-4 text-white" />
          </div>
          {(!isCollapsed || isMobileDrawer) && (
            <div className="min-w-0">
              <span className="font-display font-bold text-sm text-white block truncate">
                QUIZVERSE
              </span>
              <span className="text-[10px] text-cyan-400 font-mono tracking-widest block uppercase">
                Operational Admin
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
            Authorized Modules ({authorizedNavItems.length})
          </p>
        )}
        {authorizedNavItems.map((item) => {
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
                  ? 'bg-brand-600/30 text-cyan-200 border border-brand-500/40 shadow-glow-primary'
                  : 'text-slate-300 hover:text-white hover:bg-surface-elevated',
                isCollapsed && !isMobileDrawer && 'justify-center px-0'
              )}
            >
              <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-cyan-400' : 'text-slate-400')} />
              {(!isCollapsed || isMobileDrawer) && (
                <span className="truncate">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Super Admin Switch if logged in as Super Admin */}
      {isSuperAdmin && (
        <div className="p-3 border-t border-surface-border">
          <Link
            href="/super-admin/dashboard"
            onClick={onCloseMobileDrawer}
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-xs font-medium text-purple-300 hover:text-purple-100 transition-colors rounded-xl bg-purple-500/10 border border-purple-500/20',
              isCollapsed && !isMobileDrawer && 'justify-center px-0'
            )}
            title="Switch to Super Admin Hub"
          >
            <ShieldAlert className="w-4 h-4 shrink-0 text-purple-400" />
            {(!isCollapsed || isMobileDrawer) && <span>Super Admin Hub</span>}
          </Link>
        </div>
      )}
    </aside>
  );
}
