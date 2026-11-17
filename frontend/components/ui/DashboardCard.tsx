'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface DashboardCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: 'cyan' | 'brand' | 'purple' | 'none';
  header?: React.ReactNode;
  title?: string;
  subtitle?: string;
}

export function DashboardCard({
  children,
  className,
  glow = 'none',
  header,
  title,
  subtitle,
}: DashboardCardProps) {
  const glowStyles = {
    cyan: 'hover:shadow-glow-cyan hover:border-cyber-cyan/40',
    brand: 'hover:shadow-glow-primary hover:border-brand-500/40',
    purple: 'hover:shadow-glow-purple hover:border-cyber-purple/40',
    none: '',
  };

  const cardHeader =
    header ||
    (title && (
      <div>
        <h3 className="text-sm font-semibold text-white tracking-wide">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
    ));

  return (
    <div
      className={cn(
        'glass-card rounded-2xl p-5 md:p-6 transition-all duration-300 shadow-glass-sm',
        glowStyles[glow],
        className
      )}
    >
      {cardHeader && <div className="mb-4 pb-3 border-b border-surface-border">{cardHeader}</div>}
      {children}
    </div>
  );
}
