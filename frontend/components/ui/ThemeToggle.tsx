'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Laptop, ChevronDown, Check } from 'lucide-react';
import { useTheme, ThemeMode } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  className?: string;
  showDropdown?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ThemeToggle({ className, showDropdown = false, size = 'md' }: ThemeToggleProps) {
  const { theme, resolvedTheme, setTheme, toggleTheme, isMounted } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Prevent hydration mismatch
  if (!isMounted) {
    return (
      <div
        className={cn(
          'p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl bg-surface-elevated border border-surface-border text-slate-400 opacity-60',
          className
        )}
        aria-hidden="true"
      >
        <Moon className="w-4 h-4" />
      </div>
    );
  }

  // If simple toggle mode is requested (default for headers)
  if (!showDropdown) {
    return (
      <button
        onClick={toggleTheme}
        aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
        title={`Current: ${theme} (${resolvedTheme}). Click to switch.`}
        className={cn(
          'p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl bg-surface-elevated border border-surface-border text-slate-700 dark:text-slate-300 hover:text-brand-600 dark:hover:text-white hover:border-brand-500/40 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500 touch-manipulation shadow-sm',
          className
        )}
      >
        {resolvedTheme === 'dark' ? (
          <Sun className="w-4 h-4 text-amber-400 animate-in spin-in-90 duration-200" />
        ) : (
          <Moon className="w-4 h-4 text-brand-600 animate-in spin-in-90 duration-200" />
        )}
      </button>
    );
  }

  // Advanced Dropdown mode (with Light, Dark, System selector)
  const options: { mode: ThemeMode; label: string; icon: React.ElementType; description: string }[] = [
    { mode: 'light', label: 'Light', icon: Sun, description: 'Clean, modern SaaS studio appearance' },
    { mode: 'dark', label: 'Dark', icon: Moon, description: 'Deep cyber-glass focus mode' },
    { mode: 'system', label: 'System', icon: Laptop, description: 'Automatically matches your OS preference' },
  ];

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="Select appearance theme"
        className={cn(
          'flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-xl bg-surface-elevated border border-surface-border text-slate-700 dark:text-slate-200 hover:border-brand-500/40 transition-all text-xs font-medium focus:outline-none focus:ring-2 focus:ring-brand-500 shadow-sm touch-manipulation',
          className
        )}
      >
        {resolvedTheme === 'dark' ? (
          <Sun className="w-4 h-4 text-amber-400" />
        ) : (
          <Moon className="w-4 h-4 text-brand-600" />
        )}
        <span className="capitalize hidden sm:inline">{theme} Mode</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 transition-transform duration-150" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-surface-elevated border border-surface-border shadow-2xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl">
          <div className="px-2.5 py-1.5 border-b border-surface-border/60 mb-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Appearance Theme
            </span>
          </div>

          <div className="space-y-1">
            {options.map(({ mode, label, icon: Icon, description }) => {
              const isSelected = theme === mode;
              return (
                <button
                  key={mode}
                  onClick={() => {
                    setTheme(mode);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-start gap-2.5 px-2.5 py-2 rounded-xl text-left text-xs transition-colors',
                    isSelected
                      ? 'bg-brand-500/10 text-brand-600 dark:text-brand-300 font-semibold border border-brand-500/20'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-surface-panel/80'
                  )}
                >
                  <Icon
                    className={cn(
                      'w-4 h-4 mt-0.5 shrink-0',
                      isSelected ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400'
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span>{label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-brand-500 shrink-0" />}
                    </div>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 font-normal leading-tight mt-0.5">
                      {description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
