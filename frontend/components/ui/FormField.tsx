import React from 'react';
import { cn } from '@/lib/utils';

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
}

export const FormField = React.forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, hint, icon, className, id, ...props }, ref) => {
    const inputId = id || label.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="space-y-1.5 w-full">
        <label
          htmlFor={inputId}
          className="block text-xs font-mono uppercase tracking-wider text-slate-300"
        >
          {label}
        </label>

        <div className="relative">
          {icon && (
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              {icon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={cn(
              'w-full bg-surface-base border rounded-xl py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors duration-200',
              icon ? 'pl-10 pr-4' : 'px-4',
              error
                ? 'border-rose-500/60 focus:border-rose-500 focus:ring-1 focus:ring-rose-500'
                : 'border-surface-border focus:border-brand-500 focus:ring-1 focus:ring-brand-500',
              className
            )}
            {...props}
          />
        </div>

        {hint && !error && <p className="text-[11px] text-slate-400">{hint}</p>}
        {error && <p className="text-[11px] text-rose-400 font-medium">{error}</p>}
      </div>
    );
  }
);

FormField.displayName = 'FormField';
