'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Layers, ShieldCheck, KeyRound, Sparkles } from 'lucide-react';
import { ThemeToggle } from '../ui/ThemeToggle';
import { NotificationPanel } from '../ui/NotificationPanel';

interface TopNavbarProps {
  onToggleMobileMenu?: () => void;
  isMobileMenuOpen?: boolean;
}

export function TopNavbar({ onToggleMobileMenu, isMobileMenuOpen }: TopNavbarProps) {
  const pathname = usePathname();

  const isCurrent = (path: string) => pathname === path;

  return (
    <header className="sticky top-0 z-40 w-full glass-nav border-b border-surface-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Mobile Toggle */}
          <div className="flex items-center gap-3">
            {onToggleMobileMenu && (
              <button
                onClick={onToggleMobileMenu}
                aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
                className="md:hidden p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white"
              >
                <div className="w-4 h-4 flex flex-col justify-around">
                  <span
                    className={`h-0.5 w-full bg-current transform transition-transform ${
                      isMobileMenuOpen ? 'rotate-45 translate-y-1.5' : ''
                    }`}
                  />
                  <span
                    className={`h-0.5 w-full bg-current transition-opacity ${
                      isMobileMenuOpen ? 'opacity-0' : ''
                    }`}
                  />
                  <span
                    className={`h-0.5 w-full bg-current transform transition-transform ${
                      isMobileMenuOpen ? '-rotate-45 -translate-y-1.5' : ''
                    }`}
                  />
                </div>
              </button>
            )}

            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 via-cyber-purple to-cyber-cyan p-0.5 shadow-glow-primary group-hover:scale-105 transition-transform duration-200">
                <div className="w-full h-full bg-surface-base rounded-[10px] flex items-center justify-center">
                  <Layers className="w-4 h-4 text-cyber-cyan" />
                </div>
              </div>
              <div>
                <span className="font-display font-bold text-base tracking-wider text-white">
                  QUIZ<span className="text-cyber-cyan">VERSE</span>
                </span>
                <span className="hidden sm:block text-[9px] text-slate-400 font-mono tracking-widest uppercase">
                  3D Assessment Engine
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              href="/"
              className={`text-xs font-medium transition-colors ${
                isCurrent('/') ? 'text-cyber-cyan' : 'text-slate-300 hover:text-white'
              }`}
            >
              Overview
            </Link>
            <Link
              href="/about"
              className={`text-xs font-medium transition-colors ${
                isCurrent('/about') ? 'text-cyber-cyan' : 'text-slate-300 hover:text-white'
              }`}
            >
              About
            </Link>
            <Link
              href="/exam/demo-test"
              className={`text-xs font-medium transition-colors flex items-center gap-1.5 ${
                pathname?.startsWith('/exam') ? 'text-cyber-cyan' : 'text-slate-300 hover:text-white'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Candidate Exam
            </Link>
            <Link
              href="/admin/dashboard"
              className={`text-xs font-medium transition-colors flex items-center gap-1.5 ${
                pathname?.startsWith('/admin') ? 'text-brand-400' : 'text-slate-300 hover:text-white'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Admin Portal
            </Link>
          </nav>

          {/* Right Action Icons & Auth */}
          <div className="flex items-center gap-2.5">
            <ThemeToggle />
            <NotificationPanel />

            <Link href="/login">
              <button className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:from-brand-500 hover:to-purple-500 text-white text-xs font-medium shadow-glow-purple border border-purple-400/30 transition-all">
                <Sparkles className="w-3.5 h-3.5" />
                Sign In
              </button>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
