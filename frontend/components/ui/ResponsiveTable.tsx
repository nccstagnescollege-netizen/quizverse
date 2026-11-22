'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { LayoutGrid, Table as TableIcon } from 'lucide-react';

export interface TableColumn<T> {
  key: string;
  header: React.ReactNode;
  render?: (row: T) => React.ReactNode;
  className?: string;
  hideOnMobile?: boolean;
}

interface ResponsiveTableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  mobileCardRender?: (row: T) => React.ReactNode;
  emptyMessage?: string;
  className?: string;
  allowViewToggle?: boolean;
}

export function ResponsiveTable<T>({
  columns,
  data,
  keyExtractor,
  mobileCardRender,
  emptyMessage = 'No records found',
  className,
  allowViewToggle = true,
}: ResponsiveTableProps<T>) {
  const [viewMode, setViewMode] = useState<'auto' | 'table' | 'cards'>('auto');
  const safeData = Array.isArray(data) ? data : [];

  if (safeData.length === 0) {
    return (
      <div className={cn('w-full rounded-2xl border border-surface-border glass-card p-8 text-center text-muted-foreground', className)}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={cn('w-full space-y-3', className)}>
      {/* Optional View Switcher on Tablets/Mobiles */}
      {allowViewToggle && (
        <div className="flex justify-end items-center gap-1.5 md:hidden">
          <button
            onClick={() => setViewMode(viewMode === 'cards' ? 'table' : 'cards')}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-[11px] text-muted-foreground hover:text-foreground"
            title="Toggle between Card Stack and Horizontal Table"
          >
            {viewMode === 'cards' ? (
              <>
                <TableIcon className="w-3.5 h-3.5" />
                <span>Table View</span>
              </>
            ) : (
              <>
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Card View</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* 1. Mobile Cards View (Active on mobile unless forced to table) */}
      <div className={cn('space-y-3', viewMode === 'table' ? 'hidden' : viewMode === 'cards' ? 'block' : 'block md:hidden')}>
        {safeData.map((row) =>
          mobileCardRender ? (
            <div key={keyExtractor(row)} className="w-full">
              {mobileCardRender(row)}
            </div>
          ) : (
            <div
              key={keyExtractor(row)}
              className="glass-card rounded-2xl border border-surface-border p-4 space-y-3 transition-colors hover:border-primary-500/40"
            >
              <div className="space-y-2">
                {columns.map((col) => (
                  <div key={col.key} className="flex items-center justify-between text-xs py-1 border-b border-surface-border/40 last:border-b-0">
                    <span className="text-muted-foreground font-mono text-[11px] uppercase tracking-wider">{col.header}</span>
                    <span className="text-foreground font-medium">
                      {col.render ? col.render(row) : ((row as Record<string, unknown>)[col.key] as React.ReactNode)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )
        )}
      </div>

      {/* 2. Desktop Full Table View (Active on md+ screens or when forced to table) */}
      <div
        className={cn(
          'w-full overflow-x-auto rounded-2xl border border-surface-border glass-card shadow-lg scrollbar-thin scrollbar-thumb-surface-border',
          viewMode === 'cards' ? 'hidden' : viewMode === 'table' ? 'block' : 'hidden md:block'
        )}
      >
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-surface-border bg-surface-elevated text-muted-foreground font-mono uppercase tracking-wider">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    'px-4 py-3.5 font-semibold whitespace-nowrap',
                    col.hideOnMobile && 'hidden lg:table-cell',
                    col.className
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border/60">
            {safeData.map((row) => (
              <tr key={keyExtractor(row)} className="hover:bg-primary-500/[0.04] transition-colors group">
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      'px-4 py-3.5 text-foreground align-middle',
                      col.hideOnMobile && 'hidden lg:table-cell',
                      col.className
                    )}
                  >
                    {col.render ? col.render(row) : ((row as Record<string, unknown>)[col.key] as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
