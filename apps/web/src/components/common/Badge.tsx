import React from 'react';
import { cn } from '../../utils/cn';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'brand' | 'cyan' | 'purple' | 'emerald' | 'amber' | 'rose' | 'neutral';
  className?: string;
  dot?: boolean;
}

export function Badge({
  children,
  variant = 'brand',
  className,
  dot = false,
}: BadgeProps) {
  const variantStyles = {
    brand: 'bg-brand-500/15 text-brand-300 border-brand-500/30',
    cyan: 'bg-cyber-cyan/15 text-cyber-cyan border-cyber-cyan/30',
    purple: 'bg-cyber-purple/15 text-purple-300 border-cyber-purple/30',
    emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    rose: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const dotStyles = {
    brand: 'bg-brand-400',
    cyan: 'bg-cyber-cyan',
    purple: 'bg-cyber-purple',
    emerald: 'bg-emerald-400',
    amber: 'bg-amber-400',
    rose: 'bg-rose-400',
    neutral: 'bg-slate-400',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border tracking-wide uppercase',
        variantStyles[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn('w-1.5 h-1.5 rounded-full animate-pulse', dotStyles[variant])}
        />
      )}
      {children}
    </span>
  );
}
