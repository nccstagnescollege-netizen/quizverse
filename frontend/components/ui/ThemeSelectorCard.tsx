'use client';

import React from 'react';
import { Sun, Moon, Monitor, Check } from 'lucide-react';
import { useTheme, ThemeMode } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

export function ThemeSelectorCard({ className }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme();

  const THEME_OPTIONS: Array<{
    mode: ThemeMode;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    previewBg: string;
    previewSurface: string;
    previewBorder: string;
    previewAccent: string;
  }> = [
    {
      mode: 'light',
      label: 'Light Mode',
      description: 'Soft off-white background, crisp dark typography, and calm SaaS borders.',
      icon: Sun,
      previewBg: 'bg-[#F7F8FC]',
      previewSurface: 'bg-[#FFFFFF]',
      previewBorder: 'border-[#E4E7EC]',
      previewAccent: 'bg-[#6257E8]',
    },
    {
      mode: 'dark',
      label: 'Dark Mode',
      description: 'Layered dark surfaces, low-glare cyber aesthetic, and deep contrast.',
      icon: Moon,
      previewBg: 'bg-[#06080F]',
      previewSurface: 'bg-[#0E131F]',
      previewBorder: 'border-[#1E293B]',
      previewAccent: 'bg-[#6366F1]',
    },
    {
      mode: 'system',
      label: 'System Default',
      description: 'Automatically synchronizes with your device operating system preference.',
      icon: Monitor,
      previewBg: 'bg-gradient-to-r from-[#F7F8FC] to-[#06080F]',
      previewSurface: 'bg-gradient-to-r from-[#FFFFFF] to-[#0E131F]',
      previewBorder: 'border-surface-border',
      previewAccent: 'bg-gradient-to-r from-[#6257E8] to-[#06B6D4]',
    },
  ];

  return (
    <div
      className={cn(
        'glass-card rounded-2xl p-5 sm:p-6 border border-surface-border shadow-glass-sm space-y-5',
        className
      )}
      role="region"
      aria-labelledby="theme-selector-title"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-4">
        <div>
          <h2 id="theme-selector-title" className="text-sm sm:text-base font-semibold text-foreground tracking-tight">
            Appearance &amp; Theme
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Select your preferred visual interface mode. Currently active: {' '}
            <span className="font-semibold text-primary-500 capitalize">{resolvedTheme}</span>
            {theme === 'system' && ' (Follows System)'}.
          </p>
        </div>
      </div>

      <div
        role="radiogroup"
        aria-label="Theme Selection"
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      >
        {THEME_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isSelected = theme === opt.mode;

          return (
            <button
              key={opt.mode}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => setTheme(opt.mode)}
              className={cn(
                'group relative rounded-2xl p-4 text-left border transition-all duration-200 flex flex-col justify-between space-y-3 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
                isSelected
                  ? 'border-primary-500 bg-primary-500/[0.08] shadow-md shadow-primary-500/10'
                  : 'border-surface-border bg-surface-elevated hover:border-slate-400/40 hover:bg-surface-elevated/80'
              )}
            >
              {/* Top Row: Icon + Checkmark */}
              <div className="flex items-center justify-between">
                <div
                  className={cn(
                    'w-9 h-9 rounded-xl flex items-center justify-center border transition-colors',
                    isSelected
                      ? 'bg-primary-500 text-white border-primary-500'
                      : 'bg-surface-base text-muted-foreground border-surface-border group-hover:text-foreground'
                  )}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {isSelected && (
                  <div className="w-5 h-5 rounded-full bg-primary-500 text-white flex items-center justify-center">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </div>
                )}
              </div>

              {/* Mini UI Layout Mockup */}
              <div
                className={cn(
                  'w-full h-16 rounded-xl border p-2 flex flex-col justify-between overflow-hidden',
                  opt.previewBg,
                  opt.previewBorder
                )}
                aria-hidden="true"
              >
                <div className="flex items-center gap-1.5">
                  <div className={cn('w-2 h-2 rounded-full', opt.previewAccent)} />
                  <div className={cn('h-1.5 w-12 rounded-full opacity-60', opt.previewAccent)} />
                </div>
                <div className="grid grid-cols-3 gap-1">
                  <div className={cn('h-6 rounded-md border', opt.previewSurface, opt.previewBorder)} />
                  <div className={cn('h-6 rounded-md border', opt.previewSurface, opt.previewBorder)} />
                  <div className={cn('h-6 rounded-md border', opt.previewSurface, opt.previewBorder)} />
                </div>
              </div>

              {/* Label & Description */}
              <div className="space-y-1">
                <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span>{opt.label}</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                  {opt.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
