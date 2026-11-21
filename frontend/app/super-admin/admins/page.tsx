'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  X,
  GraduationCap,
  Trash2,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { FormField } from '@/components/ui/FormField';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';
import { useAuth } from '@/contexts/AuthContext';
import { academicService, Institution, Programme, Subject } from '@/services/academicService';

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
  const [admins, setAdmins] = useState<AdminUser[]>(INITIAL_MOCK_ADMINS);
  const [isSyncing, setIsSyncing] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'disabled'>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isPermissionsModalOpen, setIsPermissionsModalOpen] = useState(false);
  const [selectedAdmin, setSelectedAdmin] = useState<AdminUser | null>(null);

  // Form states for creating User Admin
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Academic Scopes modal state
  const [isScopeModalOpen, setIsScopeModalOpen] = useState(false);
  const [adminForScope, setAdminForScope] = useState<AdminUser | null>(null);
  const [scopesList, setScopesList] = useState<any[]>([]);
  const [loadingScopes, setLoadingScopes] = useState(false);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedInstId, setSelectedInstId] = useState('');
  const [selectedProgId, setSelectedProgId] = useState('');
  const [selectedSubjId, setSelectedSubjId] = useState('');
  const [assigningScope, setAssigningScope] = useState(false);
  const [scopeError, setScopeError] = useState<string | null>(null);

  const { token } = useAuth();
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  // Auto-dismiss toast
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // Fetch live admins from backend asynchronously
  const fetchAdmins = useCallback(async () => {
    if (!token) return;
    setIsSyncing(true);
    try {
      const res = await fetch(`${API_BASE}/admin-management/admins`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data && data.admins && data.admins.length > 0) {
          setAdmins(data.admins);
        }
      }
    } catch {
      // Non-blocking fallback to local state
    } finally {
      setIsSyncing(false);
    }
  }, [token, API_BASE]);

  useEffect(() => {
    if (token) {
      fetchAdmins();
    }
  }, [token, fetchAdmins]);

  const handleToggleStatus = async (admin: AdminUser) => {
    if (admin.is_super_admin) {
      setToastMessage({ type: 'error', text: 'Super Administrator accounts cannot be disabled.' });
      return;
    }

    const newStatus = admin.status === 'active' ? 'disabled' : 'active';
    const actionEndpoint = newStatus === 'disabled' ? 'disable' : 'reactivate';

    // Optimistic status update
    setAdmins((prev) =>
      prev.map((a) => (a.id === admin.id ? { ...a, status: newStatus } : a))
    );
    setToastMessage({
      type: 'success',
      text: `Administrator ${admin.email} marked as ${newStatus}.`,
    });

    if (token) {
      try {
        await fetch(`${API_BASE}/admin-management/admins/${admin.id}/${actionEndpoint}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch (err: any) {
        // Rollback
        setAdmins((prev) =>
          prev.map((a) => (a.id === admin.id ? { ...a, status: admin.status } : a))
        );
        setToastMessage({ type: 'error', text: `Failed to update status: ${err.message}` });
      }
    }
  };

  const handleRevokeSessions = async (admin: AdminUser) => {
    if (token) {
      try {
        await fetch(`${API_BASE}/admin-management/admins/${admin.id}/revoke-sessions`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        setToastMessage({
          type: 'success',
          text: `All active sessions for ${admin.email} have been revoked immediately.`,
        });
      } catch (err: any) {
        setToastMessage({ type: 'error', text: `Failed to revoke sessions: ${err.message}` });
      }
    }
  };

  const handleCreateUserAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    setIsSubmitting(true);

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
      } finally {
        setIsSubmitting(false);
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

  const openScopeModal = async (admin: AdminUser) => {
    setAdminForScope(admin);
    setIsScopeModalOpen(true);
    setScopeError(null);
    setLoadingScopes(true);
    setSelectedInstId('');
    setSelectedProgId('');
    setSelectedSubjId('');
    setProgrammes([]);
    setSubjects([]);

    try {
      const [scopes, insts, subjs] = await Promise.all([
        academicService.getScopes(token || '', admin.id).catch(() => []),
        academicService.getInstitutions(token || '').catch(() => []),
        academicService.getSubjects(token || '').catch(() => []),
      ]);
      setScopesList(scopes);
      setInstitutions(insts);
      setSubjects(subjs);
    } catch (err: any) {
      setScopeError(err.message || 'Failed to load academic scopes or structure.');
    } finally {
      setLoadingScopes(false);
    }
  };

  const handleInstChange = async (instId: string) => {
    setSelectedInstId(instId);
    setSelectedProgId('');
    setSelectedSubjId('');
    if (!instId) {
      setProgrammes([]);
      return;
    }
    try {
      const progs = await academicService.getProgrammes(token || '', instId).catch(() => []);
      setProgrammes(progs);
    } catch {
      setProgrammes([]);
    }
  };

  const handleAssignScope = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminForScope || !token) return;
    if (!selectedInstId) {
      setScopeError('Please select an Institution to assign scope.');
      return;
    }
    setAssigningScope(true);
    setScopeError(null);
    try {
      await academicService.assignScope(token, {
        admin_id: adminForScope.id,
        institution_id: selectedInstId,
        programme_id: selectedProgId || null,
        subject_id: selectedSubjId || null,
      });
      const updatedScopes = await academicService.getScopes(token, adminForScope.id);
      setScopesList(updatedScopes);
      setToastMessage({
        type: 'success',
        text: `Academic scope successfully assigned to ${adminForScope.full_name}.`,
      });
      setSelectedProgId('');
      setSelectedSubjId('');
    } catch (err: any) {
      setScopeError(err.message || 'Failed to assign academic scope.');
    } finally {
      setAssigningScope(false);
    }
  };

  const handleRevokeScope = async (scopeId: string) => {
    if (!adminForScope || !token) return;
    try {
      await academicService.revokeScope(token, scopeId);
      const updatedScopes = await academicService.getScopes(token, adminForScope.id);
      setScopesList(updatedScopes);
      setToastMessage({
        type: 'success',
        text: 'Academic scope revoked successfully.',
      });
    } catch (err: any) {
      setToastMessage({
        type: 'error',
        text: err.message || 'Failed to revoke scope.',
      });
    }
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

              <button
                onClick={() => openScopeModal(admin)}
                className="p-1 rounded-lg hover:bg-surface-highlight text-slate-400 hover:text-emerald-400 transition-colors"
                title="Assign & Manage Academic Curriculum Scopes"
              >
                <GraduationCap className="w-4 h-4" />
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
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Notifications Toast */}
      {toastMessage && (
        <div
          className={`fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl border text-xs font-medium shadow-xl backdrop-blur-md transition-all animate-in fade-in slide-in-from-bottom-2 ${
            toastMessage.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/90 border-rose-500/40 text-rose-200'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="p-1 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <Breadcrumb
        items={[
          { label: 'Super Admin Portal', href: '/super-admin/dashboard' },
          { label: 'User Admin Management' },
        ]}
      />

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-2">
              <Users className="w-6 h-6 text-purple-400" />
              <span>User Admin Management &amp; Role-Based Access</span>
              {isSyncing && (
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20 animate-pulse font-normal">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span>Syncing</span>
                </span>
              )}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Provision operational administrators, configure granular scopes, and enforce instant session terminations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchAdmins}
              disabled={isSyncing}
              className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border text-slate-400 hover:text-white transition-colors disabled:opacity-60"
              title="Refresh Administrators Asynchronously"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin text-purple-400' : ''}`} />
            </button>
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

      {/* Provision User Admin Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md max-h-[90vh] overflow-y-auto p-4 sm:p-6 rounded-2xl bg-surface-card border border-surface-border shadow-2xl space-y-4">
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
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-glow-purple disabled:opacity-60"
                >
                  {isSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isSubmitting ? 'Provisioning...' : 'Create User Admin'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Permissions Inspection Modal */}
      {isPermissionsModalOpen && selectedAdmin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 rounded-2xl bg-surface-card border border-surface-border shadow-2xl space-y-4">
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

      {/* Academic Curriculum Scopes Management Modal */}
      {isScopeModalOpen && adminForScope && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto p-4 sm:p-6 rounded-2xl bg-surface-card border border-surface-border shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-bold">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Academic Scope: {adminForScope.full_name}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    {adminForScope.email} &bull; Operational User Admin
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsScopeModalOpen(false)}
                className="text-slate-400 hover:text-white text-xl p-1"
              >
                &times;
              </button>
            </div>

            {scopeError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{scopeError}</span>
              </div>
            )}

            {/* Currently Assigned Scopes List */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                <span>Currently Assigned Scopes ({scopesList.length})</span>
              </h4>

              {loadingScopes ? (
                <div className="p-4 rounded-xl bg-surface-base border border-surface-border text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
                  <span>Loading scopes...</span>
                </div>
              ) : scopesList.length === 0 ? (
                <div className="p-4 rounded-xl bg-surface-base border border-dashed border-surface-border text-center space-y-1">
                  <p className="text-xs font-semibold text-slate-300">No Academic Scope Assigned</p>
                  <p className="text-[11px] text-slate-400">
                    This administrator currently has zero academic access. Use the form below to delegate an institution, programme, or subject.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                  {scopesList.map((sc) => (
                    <div
                      key={sc.id}
                      className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="font-semibold text-white flex items-center gap-1.5 truncate">
                          <span className="text-emerald-400 font-mono text-[11px]">Institution:</span>
                          <span className="truncate">{sc.institution_name || 'All Assigned'}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-3">
                          <span>
                            <strong className="text-purple-400">Prog:</strong> {sc.programme_name || 'All Programmes'}
                          </span>
                          <span>
                            <strong className="text-cyan-400">Subj:</strong> {sc.subject_name || 'All Subjects'}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleRevokeScope(sc.id)}
                        className="p-1.5 rounded-lg border border-rose-500/30 text-rose-300 hover:bg-rose-500/20 text-xs transition-colors shrink-0 flex items-center gap-1 cursor-pointer"
                        title="Revoke this academic scope"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span className="text-[10px]">Revoke</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Delegate New Academic Scope Form */}
            <form onSubmit={handleAssignScope} className="p-4 rounded-xl bg-surface-base border border-surface-border space-y-3.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-1.5">
                <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
                <span>Delegate New Scope Assignment</span>
              </h4>

              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-300">
                  Institution <span className="text-rose-400">*</span>
                </label>
                <select
                  value={selectedInstId}
                  onChange={(e) => handleInstChange(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-white focus:outline-none focus:border-purple-500"
                  required
                >
                  <option value="">-- Select Institution --</option>
                  {institutions.map((inst) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name} ({inst.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-300">
                  Programme <span className="text-slate-400 text-[10px]">(Optional — Leave blank for all programmes)</span>
                </label>
                <select
                  value={selectedProgId}
                  onChange={(e) => setSelectedProgId(e.target.value)}
                  disabled={!selectedInstId}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-white focus:outline-none focus:border-purple-500 disabled:opacity-50"
                >
                  <option value="">-- All Programmes in Institution --</option>
                  {programmes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-300">
                  Subject <span className="text-slate-400 text-[10px]">(Optional — Leave blank for all subjects)</span>
                </label>
                <select
                  value={selectedSubjId}
                  onChange={(e) => setSelectedSubjId(e.target.value)}
                  disabled={!selectedInstId}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-white focus:outline-none focus:border-purple-500 disabled:opacity-50"
                >
                  <option value="">-- All Subjects --</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.subject_name} ({s.subject_code || ''})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={assigningScope || !selectedInstId}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-glow-emerald disabled:opacity-50 transition-all cursor-pointer"
                >
                  {assigningScope && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{assigningScope ? 'Assigning...' : 'Assign Academic Scope'}</span>
                </button>
              </div>
            </form>

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={() => setIsScopeModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-surface-highlight hover:bg-surface-border text-slate-300 text-xs font-medium cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
