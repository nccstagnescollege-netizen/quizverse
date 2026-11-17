import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title: string;
  description?: string;
  message?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  message,
  icon: Icon = Inbox,
  action,
  className,
}: EmptyStateProps) {
  const displayText = description || message || '';
  return (
    <div
      className={cn(
        'glass-card rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center border border-surface-border',
        className
      )}
    >
      <div className="w-12 h-12 rounded-2xl bg-surface-elevated border border-surface-border text-slate-400 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-white tracking-wide">{title}</h3>
      {displayText && (
        <p className="text-xs text-slate-400 max-w-sm mt-1.5 leading-relaxed">
          {displayText}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
