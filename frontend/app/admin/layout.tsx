'use client';

import { useState } from 'react';
import { ResponsiveSidebar } from '@/components/layout/ResponsiveSidebar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { NotificationPanel } from '@/components/ui/NotificationPanel';
import { Layers } from 'lucide-react';
import Link from 'next/link';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-surface-base text-slate-100">
      {/* Desktop Responsive Sidebar */}
      <ResponsiveSidebar />

      {/* Mobile Drawer */}
      <MobileNavigation
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Admin Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header for Admin */}
        <header className="h-16 border-b border-surface-border px-4 sm:px-6 lg:px-8 flex items-center justify-between bg-surface-elevated/40 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            {/* Mobile Hamburger */}
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              aria-label="Open administration menu"
              className="md:hidden p-2.5 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white min-h-[44px] min-w-[44px] flex items-center justify-center active:scale-95"
            >
              <div className="w-4 h-4 flex flex-col justify-around">
                <span className="h-0.5 w-full bg-current" />
                <span className="h-0.5 w-full bg-current" />
                <span className="h-0.5 w-full bg-current" />
              </div>
            </button>

            <Link href="/" className="md:hidden flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
                <Layers className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-display font-bold text-xs text-white">QUIZVERSE</span>
            </Link>

            <span className="hidden md:inline-flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse" />
              ADMINISTRATION CONSOLE &bull; PHASE 1
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-cyber-purple/15 border border-cyber-purple/30 text-purple-300">
              Role: System Architect
            </span>
            <ThemeToggle />
            <NotificationPanel />
          </div>
        </header>

        {/* Dynamic Route Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto bg-grid-pattern">
          {children}
        </main>
      </div>
    </div>
  );
}
