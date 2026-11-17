'use client';

import React from 'react';
import { ResponsiveContainer } from 'recharts';
import { cn } from '@/lib/utils';

interface ChartContainerProps {
  title: string;
  subtitle?: string;
  height?: number;
  action?: React.ReactNode;
  children: React.ReactElement;
  className?: string;
}

export function ChartContainer({
  title,
  subtitle,
  height = 260,
  action,
  children,
  className,
}: ChartContainerProps) {
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
        {action && <div>{action}</div>}
      </div>

      <div className="w-full flex-1 min-h-[200px]" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
