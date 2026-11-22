'use client';

import React, { useState, useEffect } from 'react';
import {
  Monitor,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HardDrive,
  Trash2,
  Edit2,
  FileCheck,
  Building,
  Server,
  Layers,
  ChevronRight,
  Info,
} from 'lucide-react';
import {
  desktopExamService,
  ComputerLab,
  LabDevice,
  LabReadinessAudit,
} from '@/services/desktopExamService';

interface ComputerLabManagerProps {
  adminToken: string;
}

export function ComputerLabManager({ adminToken }: ComputerLabManagerProps) {
  const [labs, setLabs] = useState<ComputerLab[]>([]);
  const [selectedLab, setSelectedLab] = useState<ComputerLab | null>(null);
  const [devices, setDevices] = useState<LabDevice[]>([]);
  const [auditResult, setAuditResult] = useState<LabReadinessAudit | null>(null);

  const [loadingLabs, setLoadingLabs] = useState(true);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New Lab Modal
  const [showAddLab, setShowAddLab] = useState(false);
  const [newLabName, setNewLabName] = useState('');
  const [newLabCampus, setNewLabCampus] = useState('Main Campus');
  const [newLabRoom, setNewLabRoom] = useState('');
  const [newLabWorkstations, setNewLabWorkstations] = useState(30);
  const [newLabSubnet, setNewLabSubnet] = useState('');

  // New Device Modal
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [newDeviceRef, setNewDeviceRef] = useState('');
  const [newDeviceOS, setNewDeviceOS] = useState<'windows' | 'macos' | 'linux'>('windows');
  const [newDeviceSEB, setNewDeviceSEB] = useState('3.7.0');
  const [newDeviceIP, setNewDeviceIP] = useState('');
  const [newDeviceStatus, setNewDeviceStatus] = useState<'ready' | 'update_required' | 'incompatible'>('ready');

  const loadLabs = async () => {
    setLoadingLabs(true);
    setError(null);
    try {
      const data = await desktopExamService.listLabs(adminToken);
      setLabs(data);
      if (data.length > 0 && !selectedLab) {
        setSelectedLab(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load computer laboratories.');
    } finally {
      setLoadingLabs(false);
    }
  };

  const loadDevices = async (labId: string) => {
    setLoadingDevices(true);
    setAuditResult(null);
    try {
      const data = await desktopExamService.listLabDevices(labId, adminToken);
      setDevices(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load lab workstations.');
    } finally {
      setLoadingDevices(false);
    }
  };

  useEffect(() => {
    loadLabs();
  }, [adminToken]);

  useEffect(() => {
    if (selectedLab) {
      loadDevices(selectedLab.id);
    }
  }, [selectedLab]);

  const handleCreateLab = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLabName.trim()) return;
    try {
      const lab = await desktopExamService.createLab(
        {
          lab_name: newLabName.trim(),
          campus_name: newLabCampus.trim() || 'Main Campus',
          room_number: newLabRoom.trim() || undefined,
          total_workstations: Number(newLabWorkstations) || 0,
          network_subnet: newLabSubnet.trim() || undefined,
        },
        adminToken
      );
      setLabs((prev) => [...prev, lab]);
      setSelectedLab(lab);
      setShowAddLab(false);
      setNewLabName('');
      setNewLabRoom('');
      setNewLabSubnet('');
    } catch (err: any) {
      setError(err.message || 'Failed to create computer lab.');
    }
  };

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLab || !newDeviceRef.trim()) return;
    try {
      const device = await desktopExamService.registerLabDevice(
        selectedLab.id,
        {
          device_reference: newDeviceRef.trim(),
          os_platform: newDeviceOS,
          seb_version: newDeviceSEB.trim() || undefined,
          ip_address: newDeviceIP.trim() || undefined,
          compatibility_status: newDeviceStatus,
        },
        adminToken
      );
      setDevices((prev) => [...prev, device]);
      setShowAddDevice(false);
      setNewDeviceRef('');
      setNewDeviceIP('');
    } catch (err: any) {
      setError(err.message || 'Failed to register workstation.');
    }
  };

  const handleRunAudit = async () => {
    if (!selectedLab) return;
    setAuditing(true);
    try {
      const audit = await desktopExamService.auditLabReadiness(selectedLab.id, adminToken);
      setAuditResult(audit);
    } catch (err: any) {
      setError(err.message || 'Failed to execute laboratory readiness audit.');
    } finally {
      setAuditing(false);
    }
  };

  const handleDeleteDevice = async (deviceId: string) => {
    if (!selectedLab) return;
    try {
      await desktopExamService.deleteLabDevice(selectedLab.id, deviceId, adminToken);
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete workstation.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Error */}
      {error && (
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs font-semibold hover:underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Left Labs List | Right Devices & Audit */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Laboratories */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-primary-500" />
              <span>Computer Labs</span>
            </h3>
            <button
              type="button"
              onClick={() => setShowAddLab(true)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-[11px] font-semibold transition-colors cursor-pointer"
            >
              <Plus className="w-3 h-3" />
              <span>Add Lab</span>
            </button>
          </div>

          {loadingLabs ? (
            <div className="p-6 rounded-xl bg-surface-card border border-surface-border text-center">
              <RefreshCw className="w-4 h-4 animate-spin mx-auto text-primary-500" />
            </div>
          ) : labs.length === 0 ? (
            <div className="p-6 rounded-xl bg-surface-card border border-surface-border text-center space-y-2">
              <Monitor className="w-8 h-8 text-muted-foreground/40 mx-auto" />
              <p className="text-xs text-muted-foreground">No computer laboratories configured.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {labs.map((lab) => {
                const isSelected = selectedLab?.id === lab.id;
                return (
                  <button
                    key={lab.id}
                    type="button"
                    onClick={() => setSelectedLab(lab)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-primary-500/10 border-primary-500/30 shadow-sm'
                        : 'bg-surface-card border-surface-border hover:bg-surface-elevated'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">{lab.lab_name}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                          lab.status === 'active'
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : 'bg-surface-border text-muted-foreground'
                        }`}
                      >
                        {lab.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-1">
                      <span>{lab.campus_name}</span>
                      {lab.room_number && <span>• {lab.room_number}</span>}
                    </div>
                    <div className="flex items-center justify-between text-[11px] pt-2 mt-2 border-t border-surface-border/50 text-muted-foreground">
                      <span>Workstations: {lab.device_count || lab.total_workstations}</span>
                      {lab.ready_devices_count !== undefined && (
                        <span className="text-emerald-500 font-medium">Ready: {lab.ready_devices_count}</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Workstation Inventory & Readiness Audit */}
        <div className="lg:col-span-8 space-y-5">
          {selectedLab ? (
            <>
              {/* Lab Overview Header */}
              <div className="p-4 rounded-xl bg-surface-card border border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Monitor className="w-4 h-4 text-primary-500" />
                    <span>{selectedLab.lab_name}</span>
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {selectedLab.campus_name} {selectedLab.room_number ? `• Room ${selectedLab.room_number}` : ''}
                    {selectedLab.network_subnet ? ` • Subnet: ${selectedLab.network_subnet}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleRunAudit}
                    disabled={auditing}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold shadow transition-colors cursor-pointer"
                  >
                    <FileCheck className="w-3.5 h-3.5" />
                    <span>{auditing ? 'Auditing...' : 'Run Readiness Audit'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddDevice(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Workstation</span>
                  </button>
                </div>
              </div>

              {/* Audit Results Panel if triggered */}
              {auditResult && (
                <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-3 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {auditResult.is_ready_for_examination ? (
                        <ShieldCheck className="w-5 h-5 text-emerald-500" />
                      ) : (
                        <ShieldAlert className="w-5 h-5 text-amber-500" />
                      )}
                      <div>
                        <span className="text-xs font-bold text-foreground block">
                          Readiness Audit: {auditResult.readiness_percentage}% Compliant
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {auditResult.is_ready_for_examination
                            ? 'Approved for high-stakes SEB examination.'
                            : 'Action items required before examination.'}
                        </span>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        auditResult.is_ready_for_examination
                          ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      }`}
                    >
                      {auditResult.is_ready_for_examination ? 'Ready' : 'Action Required'}
                    </span>
                  </div>

                  {/* Device Count Matrix */}
                  <div className="grid grid-cols-4 gap-2 text-center text-xs">
                    <div className="p-2 rounded-lg bg-surface-card border border-surface-border">
                      <span className="text-muted-foreground block text-[10px]">Total</span>
                      <span className="font-bold text-foreground">{auditResult.total_devices}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                      <span className="text-emerald-600 dark:text-emerald-400 block text-[10px]">Ready</span>
                      <span className="font-bold text-emerald-600 dark:text-emerald-400">{auditResult.ready_devices}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <span className="text-amber-600 dark:text-amber-400 block text-[10px]">Updates</span>
                      <span className="font-bold text-amber-600 dark:text-amber-400">{auditResult.update_required_devices}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                      <span className="text-red-600 dark:text-red-400 block text-[10px]">Incompatible</span>
                      <span className="font-bold text-red-600 dark:text-red-400">{auditResult.incompatible_devices}</span>
                    </div>
                  </div>

                  {/* Recommendations */}
                  {auditResult.recommendations.length > 0 && (
                    <div className="pt-2 border-t border-surface-border/60 space-y-1">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider block">
                        Recommendations:
                      </span>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px] text-foreground/80">
                        {auditResult.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Workstation Inventory Table */}
              <div className="rounded-xl border border-surface-border overflow-hidden bg-surface-card">
                <div className="px-4 py-2.5 bg-surface-elevated/70 border-b border-surface-border flex items-center justify-between text-xs">
                  <span className="font-bold text-foreground">Workstations ({devices.length})</span>
                  <button
                    type="button"
                    onClick={() => selectedLab && loadDevices(selectedLab.id)}
                    className="p-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingDevices ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                {loadingDevices ? (
                  <div className="p-8 text-center">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto text-primary-500" />
                  </div>
                ) : devices.length === 0 ? (
                  <div className="p-8 text-center space-y-1 text-xs text-muted-foreground">
                    <p>No workstations registered in this lab yet.</p>
                    <p className="text-[11px]">Click &quot;Add Workstation&quot; to register PC clients.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-elevated/40 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-surface-border">
                        <tr>
                          <th className="py-2.5 px-3">Device Ref</th>
                          <th className="py-2.5 px-3">Platform</th>
                          <th className="py-2.5 px-3">SEB Version</th>
                          <th className="py-2.5 px-3">IP Address</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border/60">
                        {devices.map((d) => (
                          <tr key={d.id} className="hover:bg-surface-elevated/50 transition-colors">
                            <td className="py-2.5 px-3 font-mono font-semibold text-foreground">{d.device_reference}</td>
                            <td className="py-2.5 px-3 capitalize">{d.os_platform}</td>
                            <td className="py-2.5 px-3 font-mono text-[11px]">{d.seb_version || 'None'}</td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">{d.ip_address || '—'}</td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize ${
                                  d.compatibility_status === 'ready'
                                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                    : d.compatibility_status === 'update_required'
                                    ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                    : 'bg-red-500/10 text-red-600 dark:text-red-400'
                                }`}
                              >
                                {d.compatibility_status.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <button
                                type="button"
                                onClick={() => handleDeleteDevice(d.id)}
                                className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-12 rounded-xl bg-surface-card border border-surface-border text-center text-xs text-muted-foreground">
              Select a computer laboratory on the left to inspect workstations and run audits.
            </div>
          )}
        </div>
      </div>

      {/* Add Lab Modal */}
      {showAddLab && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <form
            onSubmit={handleCreateLab}
            className="w-full max-w-md rounded-2xl bg-surface-elevated border border-surface-border p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <span className="text-sm font-bold text-foreground">Add Computer Laboratory</span>
              <button
                type="button"
                onClick={() => setShowAddLab(false)}
                className="text-muted-foreground hover:text-foreground text-xs"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-muted-foreground block mb-1">Laboratory Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Turing Lab 301"
                  value={newLabName}
                  onChange={(e) => setNewLabName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                />
              </div>
              <div>
                <label className="text-muted-foreground block mb-1">Campus Name</label>
                <input
                  type="text"
                  placeholder="e.g. Main Campus"
                  value={newLabCampus}
                  onChange={(e) => setNewLabCampus(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-muted-foreground block mb-1">Room Number</label>
                  <input
                    type="text"
                    placeholder="e.g. Room 301-B"
                    value={newLabRoom}
                    onChange={(e) => setNewLabRoom(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="text-muted-foreground block mb-1">Capacity</label>
                  <input
                    type="number"
                    value={newLabWorkstations}
                    onChange={(e) => setNewLabWorkstations(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>
              <div>
                <label className="text-muted-foreground block mb-1">Subnet Range (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. 192.168.10.0/24"
                  value={newLabSubnet}
                  onChange={(e) => setNewLabSubnet(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500 font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={() => setShowAddLab(false)}
                className="px-3 py-1.5 rounded-lg border border-surface-border text-xs text-muted-foreground hover:bg-surface-border"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
              >
                Create Lab
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Add Device Modal */}
      {showAddDevice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <form
            onSubmit={handleCreateDevice}
            className="w-full max-w-md rounded-2xl bg-surface-elevated border border-surface-border p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <span className="text-sm font-bold text-foreground">Register Workstation in {selectedLab?.lab_name}</span>
              <button
                type="button"
                onClick={() => setShowAddDevice(false)}
                className="text-muted-foreground hover:text-foreground text-xs"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-muted-foreground block mb-1">Device Reference *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. LAB-01-PC-15"
                  value={newDeviceRef}
                  onChange={(e) => setNewDeviceRef(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs font-mono uppercase focus:outline-none focus:border-primary-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-muted-foreground block mb-1">OS Platform</label>
                  <select
                    value={newDeviceOS}
                    onChange={(e: any) => setNewDeviceOS(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                  >
                    <option value="windows">Windows</option>
                    <option value="macos">macOS</option>
                    <option value="linux">Linux</option>
                  </select>
                </div>
                <div>
                  <label className="text-muted-foreground block mb-1">SEB Version</label>
                  <input
                    type="text"
                    placeholder="e.g. 3.7.0"
                    value={newDeviceSEB}
                    onChange={(e) => setNewDeviceSEB(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs font-mono focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-muted-foreground block mb-1">IP Address</label>
                  <input
                    type="text"
                    placeholder="e.g. 192.168.10.15"
                    value={newDeviceIP}
                    onChange={(e) => setNewDeviceIP(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs font-mono focus:outline-none focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="text-muted-foreground block mb-1">Initial Status</label>
                  <select
                    value={newDeviceStatus}
                    onChange={(e: any) => setNewDeviceStatus(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-foreground text-xs focus:outline-none focus:border-primary-500"
                  >
                    <option value="ready">Ready</option>
                    <option value="update_required">Update Required</option>
                    <option value="incompatible">Incompatible</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={() => setShowAddDevice(false)}
                className="px-3 py-1.5 rounded-lg border border-surface-border text-xs text-muted-foreground hover:bg-surface-border"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold"
              >
                Register Workstation
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
