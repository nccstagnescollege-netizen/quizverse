'use client';

import { useState } from 'react';
import { Bell, Check, X, ShieldAlert } from 'lucide-react';

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type?: 'info' | 'warning' | 'success';
}

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: '1',
    title: 'Phase 1 Foundation Initialized',
    message: 'FastAPI backend and Next.js frontend architecture active.',
    time: 'Just now',
    read: false,
    type: 'success',
  },
  {
    id: '2',
    title: 'Database Preparation',
    message: 'Supabase PostgreSQL connection pooler and Alembic baseline ready.',
    time: '5m ago',
    read: false,
    type: 'info',
  },
];

export function NotificationPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open notifications"
        className="relative p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white hover:border-brand-500/30 transition-colors"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyber-cyan animate-pulse" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 glass-card rounded-2xl border border-surface-border shadow-glass-lg p-4 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <span className="text-xs font-mono uppercase text-slate-300">System Telemetry</span>
            <div className="flex items-center gap-2">
              <button
                onClick={markAllAsRead}
                className="text-[11px] text-cyber-cyan hover:underline flex items-center gap-1"
              >
                <Check className="w-3 h-3" /> Mark read
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="mt-3 space-y-2.5 max-h-72 overflow-y-auto">
            {notifications.map((item) => (
              <div
                key={item.id}
                className={`p-3 rounded-xl border text-xs transition-colors ${
                  item.read
                    ? 'bg-surface-base/50 border-surface-border text-slate-400'
                    : 'bg-surface-elevated border-brand-500/20 text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-white flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-cyber-cyan" />
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">{item.time}</span>
                </div>
                <p className="text-[11px] text-slate-300">{item.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
