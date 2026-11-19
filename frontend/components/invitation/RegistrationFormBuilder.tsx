'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  FileText,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
  ArrowLeft,
  Save,
  Eye,
  Sliders,
  Check,
  ChevronDown,
  ChevronUp,
  MoveUp,
  MoveDown,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  invitationService,
  EligibleQuizItem,
  RegistrationFormFieldConfig,
  RegistrationFormResponse,
} from '@/services/invitationService';

interface RegistrationFormBuilderProps {
  basePath: string; // '/admin' or '/super-admin'
}

const FIELD_TYPES: { value: RegistrationFormFieldConfig['field_type']; label: string }[] = [
  { value: 'text', label: 'Short Text' },
  { value: 'textarea', label: 'Long Text (Textarea)' },
  { value: 'email', label: 'Email Address' },
  { value: 'phone', label: 'Phone Number' },
  { value: 'number', label: 'Number' },
  { value: 'select', label: 'Dropdown Select' },
  { value: 'radio', label: 'Radio Choice' },
  { value: 'checkbox', label: 'Checkbox (Yes/No)' },
  { value: 'date', label: 'Date' },
];

export function RegistrationFormBuilder({ basePath }: RegistrationFormBuilderProps) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [quizzes, setQuizzes] = useState<EligibleQuizItem[]>([]);
  const [selectedQuizId, setSelectedQuizId] = useState<string>('');

  const [formConfig, setFormConfig] = useState<RegistrationFormResponse | null>(null);
  const [fields, setFields] = useState<RegistrationFormFieldConfig[]>([]);
  const [formTitle, setFormTitle] = useState('Student Examination Registration');
  const [formDescription, setFormDescription] = useState('Please fill in your details to register for the examination.');
  const [requireManualApproval, setRequireManualApproval] = useState(false);
  const [uniqueFieldNames, setUniqueFieldNames] = useState<string[]>(['email', 'register_number']);

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New field modal / inline state
  const [showAddField, setShowAddField] = useState(false);
  const [newFieldType, setNewFieldType] = useState<RegistrationFormFieldConfig['field_type']>('text');
  const [newFieldLabel, setNewFieldLabel] = useState('');
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldRequired, setNewFieldRequired] = useState(true);
  const [newFieldPlaceholder, setNewFieldPlaceholder] = useState('');
  const [newFieldOptions, setNewFieldOptions] = useState('');

  useEffect(() => {
    async function loadQuizzes() {
      if (!token) return;
      try {
        setLoading(true);
        const data = await invitationService.getEligibleQuizzes(token);
        setQuizzes(data);
        if (data.length > 0) {
          setSelectedQuizId(data[0].id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load eligible quizzes');
      } finally {
        setLoading(false);
      }
    }
    loadQuizzes();
  }, [token]);

  useEffect(() => {
    async function loadForm() {
      if (!token || !selectedQuizId) return;
      try {
        setLoading(true);
        const res = await invitationService.getQuizRegistrationForm(token, selectedQuizId);
        setFormConfig(res);
        setFormTitle(res.title || 'Student Examination Registration');
        setFormDescription(res.description || '');
        setRequireManualApproval(!!res.require_manual_approval);
        setFields(res.fields_config || []);
        setUniqueFieldNames(res.unique_fields || ['email', 'register_number']);
      } catch (err: any) {
        setError(err.message || 'Failed to load form configuration');
      } finally {
        setLoading(false);
      }
    }
    loadForm();
  }, [token, selectedQuizId]);

  const handleAddField = () => {
    if (!newFieldLabel.trim()) return;
    const name = (newFieldName || newFieldLabel)
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, '_')
      .replace(/_+/g, '_');

    const optionsList = ['select', 'radio'].includes(newFieldType)
      ? newFieldOptions.split(',').map((s) => s.trim()).filter(Boolean)
      : undefined;

    const newField: RegistrationFormFieldConfig = {
      field_name: name,
      field_label: newFieldLabel.trim(),
      field_type: newFieldType,
      is_required: newFieldRequired,
      placeholder: newFieldPlaceholder.trim() || undefined,
      options: optionsList,
      is_built_in: false,
    };

    setFields([...fields, newField]);
    setShowAddField(false);
    setNewFieldLabel('');
    setNewFieldName('');
    setNewFieldPlaceholder('');
    setNewFieldOptions('');
  };

  const handleRemoveField = (index: number) => {
    const updated = [...fields];
    updated.splice(index, 1);
    setFields(updated);
  };

  const handleToggleRequired = (index: number) => {
    const updated = [...fields];
    updated[index].is_required = !updated[index].is_required;
    setFields(updated);
  };

  const handleToggleUnique = (fieldName: string) => {
    if (uniqueFieldNames.includes(fieldName)) {
      setUniqueFieldNames(uniqueFieldNames.filter((f) => f !== fieldName));
    } else {
      setUniqueFieldNames([...uniqueFieldNames, fieldName]);
    }
  };

  const moveField = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === fields.length - 1) return;
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const updated = [...fields];
    const temp = updated[index];
    updated[index] = updated[targetIndex];
    updated[targetIndex] = temp;
    setFields(updated);
  };

  const handleSave = async () => {
    if (!token || !selectedQuizId) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const res = await invitationService.saveQuizRegistrationForm(token, selectedQuizId, {
        title: formTitle,
        description: formDescription,
        fields_config: fields,
        unique_fields: uniqueFieldNames,
        require_manual_approval: requireManualApproval,
      });
      setFormConfig(res);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to save form template');
    } finally {
      setSaving(false);
    }
  };

  const selectedQuiz = quizzes.find((q) => q.id === selectedQuizId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              href={`${basePath}/invitations`}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Invitations</span>
            </Link>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-primary-400" />
            <span>Registration Form Builder</span>
            {formConfig && (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary-500/10 text-primary-400 border border-primary-500/20 font-mono">
                v{formConfig.version_number}
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Design dynamic candidate intake forms, uniqueness constraints, and approval workflows.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving || !selectedQuizId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Publishing...' : 'Publish Form Version'}</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Form version updated and published successfully! All active invitations will use this configuration.</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Select Quiz Target */}
      <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
        <label className="text-xs font-semibold text-slate-300 block">
          Select Target Examination / Quiz
        </label>
        {quizzes.length === 0 ? (
          <p className="text-xs text-slate-400">
            No published or scheduled quizzes found. Publish a quiz first from the Quiz Management Console.
          </p>
        ) : (
          <select
            value={selectedQuizId}
            onChange={(e) => setSelectedQuizId(e.target.value)}
            className="w-full sm:max-w-md px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-sm text-white focus:outline-none focus:border-primary-500"
          >
            {quizzes.map((q) => (
              <option key={q.id} value={q.id}>
                {q.title} ({q.subject_name || 'No Subject'}) — {q.status.toUpperCase()}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Two Column Layout: Builder & Live Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Form Builder Settings */}
        <div className="lg:col-span-7 space-y-5">
          {/* General Properties */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-primary-400" />
              <span>Form Headers & Approvals</span>
            </h3>

            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1">Form Heading</label>
              <input
                type="text"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1">Candidate Instructions</label>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
                className="w-full px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 resize-none"
              />
            </div>

            <div className="pt-2 border-t border-surface-border/40 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-white">Manual Candidate Approval Required</p>
                <p className="text-[11px] text-slate-400">
                  When enabled, registered students must be explicitly approved by an administrator before they can enter the quiz.
                </p>
              </div>
              <input
                type="checkbox"
                checked={requireManualApproval}
                onChange={(e) => setRequireManualApproval(e.target.checked)}
                className="w-4 h-4 text-primary-600 rounded bg-slate-800 border-slate-700 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Form Fields List */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary-400" />
                <span>Form Fields ({fields.length})</span>
              </h3>
              <button
                type="button"
                onClick={() => setShowAddField(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600/20 text-primary-400 hover:bg-primary-600/30 text-xs font-medium border border-primary-500/30"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Custom Field</span>
              </button>
            </div>

            {/* Fields reorderable list */}
            <div className="space-y-2.5">
              {fields.map((field, idx) => {
                const isUnique = uniqueFieldNames.includes(field.field_name);
                return (
                  <div
                    key={field.field_name + idx}
                    className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="flex flex-col gap-1">
                        <button
                          type="button"
                          onClick={() => moveField(idx, 'up')}
                          disabled={idx === 0}
                          className="text-slate-500 hover:text-white disabled:opacity-20 p-0.5"
                        >
                          <MoveUp className="w-3 h-3" />
                        </button>
                        <button
                          type="button"
                          onClick={() => moveField(idx, 'down')}
                          disabled={idx === fields.length - 1}
                          className="text-slate-500 hover:text-white disabled:opacity-20 p-0.5"
                        >
                          <MoveDown className="w-3 h-3" />
                        </button>
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-white">{field.field_label}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {field.field_name}
                          </span>
                          <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-400">
                            {field.field_type}
                          </span>
                          {field.is_built_in && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              Built-in
                            </span>
                          )}
                        </div>
                        {field.placeholder && (
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            Placeholder: &quot;{field.placeholder}&quot;
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 self-end sm:self-center shrink-0">
                      {/* Required Toggle */}
                      <button
                        type="button"
                        onClick={() => handleToggleRequired(idx)}
                        className={`text-[10px] px-2 py-1 rounded-md font-medium border ${
                          field.is_required
                            ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                        title="Toggle Required"
                      >
                        {field.is_required ? 'Required' : 'Optional'}
                      </button>

                      {/* Unique constraint toggle */}
                      <button
                        type="button"
                        onClick={() => handleToggleUnique(field.field_name)}
                        className={`text-[10px] px-2 py-1 rounded-md font-medium border ${
                          isUnique
                            ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                            : 'bg-slate-800 text-slate-500 border-slate-700'
                        }`}
                        title="Enforce Uniqueness Across Exam Registrations"
                      >
                        {isUnique ? 'Unique Key' : 'Not Unique'}
                      </button>

                      {/* Remove custom field */}
                      {!field.is_built_in && (
                        <button
                          type="button"
                          onClick={() => handleRemoveField(idx)}
                          className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="Delete Field"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Modal / Inset for Adding Custom Field */}
            {showAddField && (
              <div className="p-4 rounded-xl bg-slate-900 border border-primary-500/30 space-y-3 mt-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Add Custom Field
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">
                      Field Label *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Department or Roll Number"
                      value={newFieldLabel}
                      onChange={(e) => {
                        setNewFieldLabel(e.target.value);
                        if (!newFieldName) {
                          setNewFieldName(
                            e.target.value
                              .toLowerCase()
                              .replace(/[^a-z0-9_]/g, '_')
                              .replace(/_+/g, '_')
                          );
                        }
                      }}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">
                      Field Type
                    </label>
                    <select
                      value={newFieldType}
                      onChange={(e) => setNewFieldType(e.target.value as RegistrationFormFieldConfig['field_type'])}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none"
                    >
                      {FIELD_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">
                      Identifier Name (Variable)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. department_name"
                      value={newFieldName}
                      onChange={(e) => setNewFieldName(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">
                      Placeholder Text
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Select your branch"
                      value={newFieldPlaceholder}
                      onChange={(e) => setNewFieldPlaceholder(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none"
                    />
                  </div>
                </div>

                {['select', 'radio'].includes(newFieldType) && (
                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">
                      Choices / Options (comma separated)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Computer Science, Electrical, Mechanical"
                      value={newFieldOptions}
                      onChange={(e) => setNewFieldOptions(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none"
                    />
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={newFieldRequired}
                      onChange={(e) => setNewFieldRequired(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-primary-500"
                    />
                    <span>Required Field</span>
                  </label>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setShowAddField(false)}
                      className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleAddField}
                      className="px-4 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white"
                    >
                      Add Field
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Candidate Preview */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4 sticky top-6">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Eye className="w-3.5 h-3.5 text-primary-400" />
                <span>Live Candidate Intake Preview</span>
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Live Rendering
              </span>
            </div>

            <div className="space-y-1">
              <h4 className="text-base font-bold text-white">{formTitle}</h4>
              <p className="text-xs text-slate-400">{formDescription}</p>
              {selectedQuiz && (
                <div className="text-[11px] text-primary-400 pt-1">
                  Examination: <span className="font-semibold">{selectedQuiz.title}</span>
                </div>
              )}
            </div>

            <div className="space-y-3.5 pt-2">
              {fields.map((f, idx) => (
                <div key={idx} className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1">
                    <span>{f.field_label}</span>
                    {f.is_required && <span className="text-rose-400">*</span>}
                    {uniqueFieldNames.includes(f.field_name) && (
                      <span className="text-[10px] text-purple-400 font-mono ml-auto">(Unique)</span>
                    )}
                  </label>

                  {f.field_type === 'textarea' ? (
                    <textarea
                      disabled
                      placeholder={f.placeholder || `Enter ${f.field_label.toLowerCase()}`}
                      rows={2}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700/60 text-xs text-slate-400 opacity-80 cursor-not-allowed resize-none"
                    />
                  ) : f.field_type === 'select' ? (
                    <select
                      disabled
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700/60 text-xs text-slate-400 opacity-80 cursor-not-allowed"
                    >
                      <option>-- Select {f.field_label} --</option>
                      {f.options?.map((opt, i) => (
                        <option key={i}>{opt}</option>
                      ))}
                    </select>
                  ) : f.field_type === 'radio' ? (
                    <div className="space-y-1.5 pt-0.5">
                      {f.options?.map((opt, i) => (
                        <label key={i} className="flex items-center gap-2 text-xs text-slate-400">
                          <input type="radio" disabled name={`preview_${f.field_name}`} />
                          <span>{opt}</span>
                        </label>
                      ))}
                    </div>
                  ) : f.field_type === 'checkbox' ? (
                    <label className="flex items-center gap-2 text-xs text-slate-300">
                      <input type="checkbox" disabled className="rounded bg-slate-900 border-slate-700" />
                      <span>I agree / confirm {f.field_label}</span>
                    </label>
                  ) : (
                    <input
                      type={f.field_type === 'number' ? 'number' : f.field_type === 'date' ? 'date' : 'text'}
                      disabled
                      placeholder={f.placeholder || `Enter ${f.field_label.toLowerCase()}`}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700/60 text-xs text-slate-400 opacity-80 cursor-not-allowed"
                    />
                  )}
                </div>
              ))}

              <div className="pt-2">
                <button
                  type="button"
                  disabled
                  className="w-full py-2.5 rounded-xl bg-primary-600/40 text-primary-200 text-xs font-semibold cursor-not-allowed text-center"
                >
                  Register & Continue to Examination Room
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
