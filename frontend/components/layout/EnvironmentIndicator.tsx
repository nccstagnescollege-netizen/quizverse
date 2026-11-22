'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle, X, ShieldAlert } from 'lucide-react';

export function EnvironmentIndicator() {
  const [env, setEnv] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Determine non-production environment cleanly without exposing sensitive URLs
    const publicEnv = process.env.NEXT_PUBLIC_APP_ENV || 'production';
    const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    const isVercelPreview = typeof window !== 'undefined' && window.location.hostname.includes('-git-');

    if (publicEnv === 'staging' || isVercelPreview) {
      setEnv('STAGING');
    } else if (publicEnv === 'development' || isLocal) {
      setEnv('DEVELOPMENT');
    } else {
      setEnv(null); // Production: no banner
    }
  }, []);

  if (!env || dismissed) return null;

  return (
    <div className="bg-amber-500/90 text-slate-950 px-3 py-1 text-xs font-semibold flex items-center justify-between border-b border-amber-600/50 shadow-sm z-50 sticky top-0 backdrop-blur">
      <div className="flex items-center gap-2 mx-auto">
        <span className="w-2 h-2 rounded-full bg-slate-950 animate-ping inline-block" />
        <span className="font-mono tracking-wider uppercase font-bold">[{env} ENVIRONMENT]</span>
        <span className="hidden sm:inline font-normal text-slate-900">
          Synthetic test accounts active. Do not use for real examinations.
        </span>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-slate-900 hover:text-black p-0.5 rounded transition-colors"
        title="Dismiss indicator"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
