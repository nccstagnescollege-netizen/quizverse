'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface ChartContainerProps {
  title: string;
  subtitle?: string;
  height?: number;
  action?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function ChartContainer({
  title,
  subtitle,
  height = 260,
  action,
  actions,
  children,
  className,
}: ChartContainerProps) {
  const topAction = action || actions;

  return (
    <div
      className={cn(
        'glass-card rounded-2xl p-5 border border-surface-border shadow-glass-sm flex flex-col',
        className
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {topAction && <div>{topAction}</div>}
      </div>

      <div className="w-full flex-1 min-h-[200px]" style={{ minHeight: height }}>
        {children}
      </div>
    </div>
  );
}
