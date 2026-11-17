'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Layers,
  Users,
  BarChart3,
  BookOpen,
  Award,
  Menu,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

interface MobileBottomNavProps {
  onOpenDrawer: () => void;
  isSuperAdminContext?: boolean;
}

export function MobileBottomNav({
  onOpenDrawer,
  isSuperAdminContext = false,
}: MobileBottomNavProps) {
  const pathname = usePathname();
  const { isSuperAdmin, hasPermission } = useAuth();

  const superAdminNav = [
    { label: 'Overview', href: '/super-admin/dashboard', icon: LayoutDashboard },
    { label: 'Academic', href: '/super-admin/academic', icon: Layers },
    { label: 'Admins', href: '/super-admin/admins', icon: Users },
    { label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  ];

  const userAdminNav = [
    { label: 'Overview', href: '/admin/dashboard', icon: LayoutDashboard, show: true },
    { label: 'Quizzes', href: '/admin/quiz', icon: BookOpen, show: hasPermission('quiz.view') },
    { label: 'Academic', href: '/admin/academic', icon: Layers, show: hasPermission('academic.view') },
    { label: 'Analytics', href: '/admin/analytics', icon: Award, show: hasPermission('analytics.view') },
  ].filter((item) => item.show);

  const navItems = isSuperAdminContext || isSuperAdmin ? superAdminNav : userAdminNav;

  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface-base/95 backdrop-blur-xl border-t border-surface-border px-2 py-1.5 flex items-center justify-around shadow-2xl safe-area-pb"
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href.split('?')[0];

        return (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              'flex flex-col items-center justify-center flex-1 py-1 px-1 rounded-xl transition-all min-h-[48px] touch-manipulation',
              isActive
                ? 'text-brand-400 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            <div
              className={cn(
                'p-1 rounded-lg transition-transform',
                isActive && 'bg-brand-500/15 scale-110 shadow-sm'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
            </div>
            <span className="text-[10px] mt-0.5 tracking-tight truncate max-w-[64px]">
              {item.label}
            </span>
          </Link>
        );
      })}

      {/* Menu / Drawer Trigger */}
      <button
        type="button"
        onClick={onOpenDrawer}
        aria-label="Open complete menu"
        className="flex flex-col items-center justify-center flex-1 py-1 px-1 rounded-xl text-slate-400 hover:text-slate-200 transition-all min-h-[48px] touch-manipulation"
      >
        <div className="p-1 rounded-lg">
          <Menu className="w-4 h-4 shrink-0" />
        </div>
        <span className="text-[10px] mt-0.5 tracking-tight">Menu</span>
      </button>
    </nav>
  );
}
