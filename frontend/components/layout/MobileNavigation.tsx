'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X, Layers, ShieldCheck, KeyRound, Sparkles, Home, Info } from 'lucide-react';
import { ADMIN_NAV_ITEMS } from './ResponsiveSidebar';

interface MobileNavigationProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileNavigation({ isOpen, onClose }: MobileNavigationProps) {
  const pathname = usePathname();

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 md:hidden bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="fixed inset-y-0 left-0 w-4/5 max-w-sm glass-card bg-surface-base border-r border-surface-border p-5 flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-surface-border">
            <Link href="/" onClick={onClose} className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center">
                <Layers className="w-4 h-4 text-white" />
              </div>
              <span className="font-display font-bold text-sm text-white">QUIZVERSE</span>
            </Link>

            <button
              onClick={onClose}
              aria-label="Close navigation"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Links */}
          <div className="py-4 space-y-4">
            <div>
              <p className="text-[10px] font-mono uppercase text-slate-400 tracking-wider mb-2">
                Public Portal
              </p>
              <nav className="space-y-1.5">
                <Link
                  href="/"
                  onClick={onClose}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium min-h-[44px] transition-colors ${
                    pathname === '/' ? 'bg-cyber-cyan/15 text-cyber-cyan font-semibold' : 'text-slate-300 hover:text-white hover:bg-surface-elevated'
                  }`}
                >
                  <Home className="w-4 h-4 shrink-0" />
                  <span>Overview</span>
                </Link>
                <Link
                  href="/about"
                  onClick={onClose}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium min-h-[44px] transition-colors ${
                    pathname === '/about' ? 'bg-cyber-cyan/15 text-cyber-cyan font-semibold' : 'text-slate-300 hover:text-white hover:bg-surface-elevated'
                  }`}
                >
                  <Info className="w-4 h-4 shrink-0" />
                  <span>About Platform</span>
                </Link>
                <Link
                  href="/exam"
                  onClick={onClose}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium min-h-[44px] transition-colors ${
                    pathname?.startsWith('/exam') ? 'bg-cyber-cyan/15 text-cyber-cyan font-semibold' : 'text-slate-300 hover:text-white hover:bg-surface-elevated'
                  }`}
                >
                  <KeyRound className="w-4 h-4 shrink-0" />
                  <span>Candidate Examination</span>
                </Link>
              </nav>
            </div>

            <div>
              <p className="text-[10px] font-mono uppercase text-slate-400 tracking-wider mb-2">
                Admin Console
              </p>
              <nav className="space-y-1.5">
                {ADMIN_NAV_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onClose}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium min-h-[44px] transition-colors ${
                        isActive ? 'bg-brand-600 text-white shadow-glow-primary font-semibold' : 'text-slate-300 hover:text-white hover:bg-surface-elevated'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="w-4 h-4 shrink-0" />
                        <span>{item.label}</span>
                      </div>
                      {item.badge && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/10 font-mono">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </div>
        </div>

        {/* Bottom Auth Action */}
        <div className="pt-4 border-t border-surface-border">
          <Link href="/login" onClick={onClose} className="block w-full">
            <button className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple min-h-[44px]">
              <Sparkles className="w-4 h-4" />
              Sign In to Account
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
