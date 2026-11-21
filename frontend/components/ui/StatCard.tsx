import React from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label?: string;
  title?: string;
  value: string | number;
  subtitle?: string;
  description?: string;
  icon: LucideIcon;
  variant?: 'cyan' | 'brand' | 'purple' | 'emerald';
  trend?: string;
  className?: string;
}

export function StatCard({
  label,
  title,
  value,
  subtitle,
  description,
  icon: Icon,
  variant = 'brand',
  trend,
  className,
}: StatCardProps) {
  const displayLabel = label || title || '';
  const displaySubtitle = subtitle || description;
  const iconVariants = {
    cyan: 'bg-cyber-cyan/10 border-cyber-cyan/30 text-cyber-cyan',
    brand: 'bg-brand-500/10 border-brand-500/30 text-brand-500 dark:text-brand-400',
    purple: 'bg-cyber-purple/10 border-cyber-purple/30 text-purple-600 dark:text-purple-400',
    emerald: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400',
  };

  return (
    <div
      className={cn(
        'glass-card rounded-2xl p-3.5 sm:p-5 border border-surface-border transition-all duration-300 hover:-translate-y-0.5 shadow-glass-sm',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground truncate pr-2">{displayLabel}</span>
        <div className={cn('p-2 sm:p-2.5 rounded-xl border shrink-0', iconVariants[variant])}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-2.5 sm:mt-3 flex items-baseline gap-2">
        <span className="text-xl sm:text-2xl md:text-3xl font-display font-bold text-foreground tracking-tight">
          {value}
        </span>
        {trend && (
          <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-medium">
            {trend}
          </span>
        )}
      </div>

      {displaySubtitle && (
        <p className="mt-1 text-xs text-muted-foreground font-sans truncate sm:whitespace-normal">{displaySubtitle}</p>
      )}
    </div>
  );
}
