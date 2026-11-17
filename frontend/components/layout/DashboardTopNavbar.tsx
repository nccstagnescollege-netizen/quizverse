'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Layers,
  Search,
  LogOut,
  User,
  ShieldAlert,
  ShieldCheck,
  ChevronDown,
  Menu,
  X,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '../ui/ThemeToggle';
import { NotificationPanel } from '../ui/NotificationPanel';

interface DashboardTopNavbarProps {
  title?: string;
  breadcrumbs?: { label: string; href?: string }[];
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export function DashboardTopNavbar({
  title = 'QUIZVERSE Portal',
  breadcrumbs,
  onToggleSidebar,
  isSidebarOpen,
}: DashboardTopNavbarProps) {
  const { user, isSuperAdmin, logout } = useAuth();
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-30 w-full bg-surface-base/80 backdrop-blur-xl border-b border-surface-border">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Left: Mobile Toggle & Title/Breadcrumbs */}
          <div className="flex items-center gap-3 min-w-0">
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                aria-label="Toggle navigation menu"
                className="lg:hidden p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors"
              >
                {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            )}

            <div className="flex items-center gap-2.5">
              <Link href="/" className="lg:hidden flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 to-cyber-purple flex items-center justify-center shadow-glow-primary">
                  <Layers className="w-4 h-4 text-white" />
                </div>
              </Link>

              <div className="min-w-0">
                {breadcrumbs && breadcrumbs.length > 0 && (
                  <nav className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-400 mb-0.5">
                    {breadcrumbs.map((b, i) => (
                      <React.Fragment key={i}>
                        {i > 0 && <span>/</span>}
                        {b.href ? (
                          <Link href={b.href} className="hover:text-slate-200 transition-colors">
                            {b.label}
                          </Link>
                        ) : (
                          <span className="text-slate-300 truncate">{b.label}</span>
                        )}
                      </React.Fragment>
                    ))}
                  </nav>
                )}
                <h1 className="text-base sm:text-lg font-display font-bold text-white tracking-tight truncate">
                  {title}
                </h1>
              </div>
            </div>
          </div>

          {/* Center: Global Search Bar */}
          <div className="hidden md:flex flex-1 max-w-md items-center">
            <div className="relative w-full">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search quizzes, candidates, question items..."
                className="w-full pl-9 pr-4 py-1.5 text-xs rounded-xl bg-surface-elevated/70 border border-surface-border text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-all"
              />
            </div>
          </div>

          {/* Right: Actions, Notifications, Theme, Profile */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <ThemeToggle />
            <NotificationPanel />

            {/* Profile Menu */}
            <div className="relative">
              <button
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="flex items-center gap-2 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-surface-elevated/60 border border-surface-border hover:border-surface-border/80 transition-all"
                aria-expanded={isProfileMenuOpen}
              >
                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-brand-600 to-cyber-cyan flex items-center justify-center text-white text-xs font-bold">
                  {user?.full_name ? user.full_name[0].toUpperCase() : 'A'}
                </div>
                <div className="hidden sm:block text-left">
                  <span className="block text-xs font-medium text-white truncate max-w-[100px]">
                    {user?.full_name || 'Administrator'}
                  </span>
                  <span className="block text-[10px] text-slate-400 font-mono">
                    {isSuperAdmin ? 'Super Admin' : 'User Admin'}
                  </span>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
              </button>

              {/* Dropdown Menu */}
              {isProfileMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl bg-surface-base border border-surface-border shadow-xl backdrop-blur-2xl py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-3.5 py-2 border-b border-surface-border">
                    <p className="text-xs font-semibold text-white truncate">
                      {user?.full_name || 'Administrator'}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
                    <div className="mt-1.5">
                      {isSuperAdmin ? (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono">
                          <ShieldAlert className="w-3 h-3" /> Super Admin
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 font-mono">
                          <ShieldCheck className="w-3 h-3" /> User Admin
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="py-1">
                    {isSuperAdmin ? (
                      <Link
                        href="/super-admin/dashboard"
                        onClick={() => setIsProfileMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                      >
                        <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
                        Super Admin Hub
                      </Link>
                    ) : null}

                    <Link
                      href="/admin/dashboard"
                      onClick={() => setIsProfileMenuOpen(false)}
                      className="flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                    >
                      <Layers className="w-3.5 h-3.5 text-brand-400" />
                      Operational Dashboard
                    </Link>

                    <Link
                      href="/admin/settings"
                      onClick={() => setIsProfileMenuOpen(false)}
                      className="flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                    >
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      Profile &amp; Settings
                    </Link>
                  </div>

                  <div className="pt-1 border-t border-surface-border">
                    <button
                      onClick={() => {
                        setIsProfileMenuOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-rose-300 hover:bg-rose-500/10 hover:text-rose-200 transition-colors"
                    >
                      <LogOut className="w-3.5 h-3.5 text-rose-400" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
