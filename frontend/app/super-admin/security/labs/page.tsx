'use client';

import React from 'react';
import Link from 'next/link';
import { Monitor, ArrowLeft, Building } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { ComputerLabManager } from '@/components/desktop-security/ComputerLabManager';

export default function SuperAdminComputerLabsPage() {
  const { token } = useAuth();

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <Link
            href="/super-admin/dashboard"
            className="p-2 rounded-xl bg-surface-card hover:bg-surface-elevated border border-surface-border text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <Building className="w-5 h-5 text-primary-500" />
              <h1 className="text-xl font-bold text-foreground tracking-tight">Institutional Computer Laboratories</h1>
            </div>
            <p className="text-xs text-muted-foreground">
              Campus workstation pools, SEB readiness audits, and laboratory hardware inventories.
            </p>
          </div>
        </div>
      </div>

      {token ? (
        <ComputerLabManager adminToken={token} />
      ) : (
        <div className="p-8 text-center text-xs text-muted-foreground">
          Authenticating administrator session...
        </div>
      )}
    </div>
  );
}
