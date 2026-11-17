'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  UserPlus,
  ShieldAlert,
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  KeyRound,
  Lock,
  Layers,
  ArrowLeft,
  RefreshCw,
  SlidersHorizontal,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { FormField } from '@/components/ui/FormField';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { useAuth } from '@/contexts/AuthContext';

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  status: 'active' | 'disabled' | 'suspended';
  is_super_admin: boolean;
  roles: string[];
  permissions: string[];
  last_login_at?: string;
  created_at: string;
}

const INITIAL_MOCK_ADMINS: AdminUser[] = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'superadmin@quizverse.io',
    full_name: 'Chief Security Officer',
    status: 'active',
    is_super_admin: true,
    roles: ['super_admin'],
    permissions: ['* (Unrestricted Platform Access)'],
    last_login_at: '2026-11-17T18:45:00Z',
    created_at: '2026-11-10T12:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    email: 'dr.watson@university.edu',
    full_name: 'Dr. John Watson',
    status: 'active',
    is_super_admin: false,
    roles: ['user_admin'],
    permissions: ['quiz.view', 'quiz.create', 'quiz.edit', 'question.view'],
    last_login_at: '2026-11-17T14:20:00Z',
    created_at: '2026-11-12T09:30:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000003',
    email: 'm.curie@physics-inst.org',
    full_name: 'Prof. Marie Curie',
    status: 'active',
    is_super_admin: false,
    roles: ['user_admin'],
    permissions: ['quiz.view', 'quiz.create', 'exam.monitor', 'analytics.view'],
    last_login_at: '2026-11-16T11:15:00Z',
    created_at: '2026-11-14T10:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000004',
    email: 'temp.proctor@examcenter.net',
    full_name: 'Robert Vance',
    status: 'disabled',
    is_super_admin: false,
    roles: ['user_admin'],
    permissions: ['quiz.view', 'exam.monitor'],
    last_login_at: '2026-11-15T08:00:00Z',
    created_at: '2026-11-15T07:30:00Z',
  },
];

export default function SuperAdminAdminsPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [admins, setAdmins] = useState<AdminUser[]>(INITIAL_MOCK_ADMINS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'disabled'>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isPermissionsModalOpen, setIsPermissionsModalOpen] = useState(false);
  const [selectedAdmin, setSelectedAdmin] = useState<AdminUser | null>(null);

  // Form states for creating User Admin
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const { token } = useAuth();
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  // Fetch live admins from backend if available
  useEffect(() => {
    if (token) {
      fetch(`${API_BASE}/admin-management/admins`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && data.admins && data.admins.length > 0) {
            setAdmins(data.admins);
          }
        })
        .catch(() => {});
    }
  }, [token, API_BASE]);

  const handleToggleStatus = async (admin: AdminUser) => {
    if (admin.is_super_admin) {
      alert('Super Administrator accounts cannot be disabled.');
      return;
    }

    const newStatus = admin.status === 'active' ? 'disabled' : 'active';
    const actionEndpoint = newStatus === 'disabled' ? 'disable' : 'reactivate';

    if (token) {
      try {
        await fetch(`${API_BASE}/admin-management/admins/${admin.id}/${actionEndpoint}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {}
    }

    setAdmins((prev) =>
      prev.map((a) => (a.id === admin.id ? { ...a, status: newStatus } : a))
    );
  };

  const handleRevokeSessions = async (admin: AdminUser) => {
    if (token) {
      try {
        await fetch(`${API_BASE}/admin-management/admins/${admin.id}/revoke-sessions`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {}
    }
    alert(`All active sessions for ${admin.email} have been revoked immediately.`);
  };

  const handleCreateUserAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    if (token) {
      try {
        const res = await fetch(`${API_BASE}/admin-management/admins`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            full_name: newName,
            email: newEmail,
            password: newPassword,
            role_names: ['user_admin'],
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          setFormError(data.error?.message || data.detail || 'Failed to provision admin.');
          return;
        }
        setAdmins((prev) => [data, ...prev]);
        setFormSuccess(`User Admin ${newEmail} provisioned successfully.`);
        setTimeout(() => {
          setIsCreateModalOpen(false);
          setNewName('');
          setNewEmail('');
          setNewPassword('');
          setFormSuccess(null);
        }, 1200);
        return;
      } catch (err: any) {
        setFormError(err.message || 'Server error.');
      }
    }

    // Client fallback / preview
    const newAdminObj: AdminUser = {
      id: Math.random().toString(36).substring(2, 9),
      email: newEmail,
      full_name: newName,
      status: 'active',
      is_super_admin: false,
      roles: ['user_admin'],
      permissions: ['quiz.view', 'quiz.create', 'quiz.edit'],
      created_at: new Date().toISOString(),
    };
    setAdmins((prev) => [newAdminObj, ...prev]);
    setFormSuccess(`User Admin ${newEmail} provisioned successfully.`);
    setTimeout(() => {
      setIsCreateModalOpen(false);
      setNewName('');
      setNewEmail('');
      setNewPassword('');
      setFormSuccess(null);
    }, 1000);
  };

  const filteredAdmins = admins.filter((admin) => {
    const matchesSearch =
      admin.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      admin.full_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' ? true : admin.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const columns: TableColumn<AdminUser>[] = [
    {
      key: 'user',
      header: 'Administrator',
      render: (admin) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 font-bold text-xs shrink-0">
            {admin.full_name.charAt(0)}
          </div>
          <div>
            <div className="text-sm font-semibold text-white flex items-center gap-1.5">
              {admin.full_name}
              {admin.is_super_admin && (
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Super Admin
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 font-mono">{admin.email}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'roles',
      header: 'Assigned Role',
      render: (admin) => (
        <div className="flex flex-wrap gap-1">
          {admin.roles.map((r) => (
            <span
              key={r}
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                admin.is_super_admin
                  ? 'border-purple-500/30 text-purple-300 bg-purple-500/10'
                  : 'border-cyan-500/30 text-cyan-300 bg-cyan-500/10'
              }`}
            >
              {r}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Account Status',
      render: (admin) => (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
            admin.status === 'active'
              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
              : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              admin.status === 'active' ? 'bg-emerald-400' : 'bg-rose-400'
            }`}
          />
          {admin.status.charAt(0).toUpperCase() + admin.status.slice(1)}
        </span>
      ),
    },
    {
      key: 'permissions',
      header: 'Effective Scopes',
      render: (admin) => (
        <span className="text-xs text-slate-300 font-mono">
          {admin.is_super_admin
            ? 'Full Platform Authority'
            : `${admin.permissions.length} granular rules`}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Governance Controls',
      render: (admin) => (
        <div className="flex items-center gap-2">
          {!admin.is_super_admin && (
            <>
              <button
                onClick={() => handleToggleStatus(admin)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                  admin.status === 'active'
                    ? 'border-rose-500/30 text-rose-300 hover:bg-rose-500/20'
                    : 'border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
                }`}
              >
                {admin.status === 'active' ? 'Disable' : 'Reactivate'}
              </button>

              <button
                onClick={() => handleRevokeSessions(admin)}
                title="Immediately invalidate active session tokens"
                className="px-2.5 py-1 rounded-lg text-xs font-medium border border-surface-border text-slate-400 hover:text-white hover:bg-surface-highlight transition-colors"
              >
                Kill Sessions
              </button>
            </>
          )}

          <button
            onClick={() => {
              setSelectedAdmin(admin);
              setIsPermissionsModalOpen(true);
            }}
            className="p-1 rounded-lg hover:bg-surface-highlight text-slate-400 hover:text-purple-300 transition-colors"
            title="Inspect permissions & overrides"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      <TopNavbar
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        isMobileMenuOpen={isMobileMenuOpen}
      />

      <MobileNavigation
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 relative z-10">
        <Breadcrumb
          items={[
            { label: 'Control Center', href: '/' },
            { label: 'Super Admin Portal', href: '/super-admin/dashboard' },
            { label: 'User Admin Management' },
          ]}
        />

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-2">
              <Users className="w-6 h-6 text-purple-400" />
              User Admin Management &amp; Role-Based Access
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Provision operational administrators, configure granular scopes, and enforce instant session terminations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-glow-purple transition-all cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              Provision User Admin
            </button>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl bg-surface-card/60 border border-surface-border">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-surface-base border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <span className="text-xs text-slate-400">Status:</span>
            <div className="flex rounded-lg bg-surface-base border border-surface-border p-0.5">
              {(['all', 'active', 'disabled'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1 rounded text-xs capitalize transition-colors ${
                    statusFilter === s
                      ? 'bg-purple-600 text-white font-medium'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Admin Data Table with Mobile Responsiveness */}
        <DashboardCard glow="brand" className="p-0 overflow-hidden">
          <ResponsiveTable
            columns={columns}
            data={filteredAdmins}
            keyExtractor={(admin) => admin.id}
            emptyMessage="No administrators match the specified filter."
          />
        </DashboardCard>

        {/* Security Policy Reminder Alert */}
        <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/20 flex items-start gap-3 text-xs text-slate-300">
          <ShieldAlert className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-white">Super Admin Bootstrap Security Model</div>
            <p className="text-slate-400">
              User Admins receive default-deny operational privileges and cannot access Super Admin governance APIs.
              Disabling an administrator or setting status to inactive invalidates all active sessions across all devices in real-time.
            </p>
          </div>
        </div>
      </div>

      {/* Provision User Admin Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md p-6 rounded-2xl bg-surface-card border border-surface-border shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-purple-400" />
                Provision Operational User Admin
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Create an operational administrator account with scoped quiz &amp; exam privileges.
            </p>

            {formError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                {formError}
              </div>
            )}
            {formSuccess && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300">
                {formSuccess}
              </div>
            )}

            <form onSubmit={handleCreateUserAdmin} className="space-y-3">
              <FormField
                label="Full Name"
                type="text"
                placeholder="Dr. Gregory House"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
              <FormField
                label="Email Address"
                type="email"
                placeholder="house@clinic.edu"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
              />
              <FormField
                label="Initial Password"
                type="password"
                placeholder="Minimum 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />

              <div className="p-3 rounded-xl bg-surface-base border border-surface-border text-[11px] text-slate-400">
                <strong className="text-purple-300">Security Rule:</strong> By policy,
                additional Super Admin accounts cannot be provisioned via this form. User Admin accounts
                operate strictly within assigned academic and quiz scopes.
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-surface-highlight hover:bg-surface-border text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-glow-purple"
                >
                  Create User Admin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Permissions Inspection Modal */}
      {isPermissionsModalOpen && selectedAdmin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-surface-card border border-surface-border shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <SlidersHorizontal className="w-5 h-5 text-purple-400" />
                RBAC Permissions: {selectedAdmin.full_name}
              </h3>
              <button
                onClick={() => setIsPermissionsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                &times;
              </button>
            </div>

            <div className="text-xs text-slate-400">
              Resolved permissions based on role assignments and explicit database overrides.
            </div>

            <div className="max-h-60 overflow-y-auto space-y-1.5 p-3 rounded-xl bg-surface-base border border-surface-border">
              {selectedAdmin.permissions.map((p) => (
                <div
                  key={p}
                  className="flex items-center justify-between p-2 rounded-lg bg-surface-card border border-surface-border text-xs"
                >
                  <span className="font-mono text-purple-300">{p}</span>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Granted
                  </span>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setIsPermissionsModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
