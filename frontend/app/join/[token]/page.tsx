'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
  GraduationCap,
  Clock,
  Award,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Lock,
  Copy,
  Check,
  Printer,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  User,
  Mail,
  Phone,
  Hash,
  Building,
} from 'lucide-react';
import {
  invitationService,
  PublicInvitationValidation,
  PublicRegistrationReceipt,
  RegistrationFormFieldConfig,
} from '@/services/invitationService';

export default function PublicRegistrationPage() {
  const params = useParams();
  const token = params?.token as string;

  const [loading, setLoading] = useState(true);
  const [validation, setValidation] = useState<PublicInvitationValidation | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<PublicRegistrationReceipt | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  useEffect(() => {
    async function validateToken() {
      if (!token) return;
      try {
        setLoading(true);
        const res = await invitationService.validatePublicToken(token);
        setValidation(res);

        // Initialize default empty values for form fields
        if (res.registration_form) {
          const initialData: Record<string, any> = {};
          res.registration_form.forEach((field) => {
            initialData[field.field_name] = field.field_type === 'checkbox' ? false : '';
          });
          setFormData(initialData);
        }
      } catch (err: any) {
        setValidation({
          is_valid: false,
          error_code: 'CLIENT_NETWORK_ERROR',
          error_message: err.message || 'Unable to communicate with the verification server.',
          require_approval: false,
        });
      } finally {
        setLoading(false);
      }
    }
    validateToken();
  }, [token]);

  const handleInputChange = (fieldName: string, value: any) => {
    setFormData((prev) => ({ ...prev, [fieldName]: value }));
    if (validationErrors[fieldName]) {
      setValidationErrors((prev) => {
        const copy = { ...prev };
        delete copy[fieldName];
        return copy;
      });
    }
  };

  const validateForm = (): boolean => {
    if (!validation?.registration_form) return true;
    const errors: Record<string, string> = {};

    for (const field of validation.registration_form) {
      const val = formData[field.field_name];
      if (field.is_required) {
        if (val === undefined || val === null || val === '' || (field.field_type === 'checkbox' && !val)) {
          errors[field.field_name] = `${field.field_label} is required.`;
          continue;
        }
      }

      if (field.field_type === 'email' && val) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(String(val))) {
          errors[field.field_name] = 'Please enter a valid email address.';
        }
      }

      if (field.min_length && typeof val === 'string' && val.length < field.min_length) {
        errors[field.field_name] = `Must be at least ${field.min_length} characters.`;
      }
      if (field.max_length && typeof val === 'string' && val.length > field.max_length) {
        errors[field.field_name] = `Cannot exceed ${field.max_length} characters.`;
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await invitationService.registerCandidate(token, formData);
      setReceipt(res);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to complete registration. Please check your information.');
    } finally {
      setSubmitting(false);
    }
  };

  const copyRegistrationCode = () => {
    if (!receipt?.registration_code) return;
    navigator.clipboard.writeText(receipt.registration_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // 1. Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Verifying Examination Invitation...</h2>
        <p className="text-xs text-slate-500 mt-1">Checking cryptographic credentials and access capacity</p>
      </div>
    );
  }

  // 2. Invalid / Expired / Revoked / Exhausted State
  if (!validation || !validation.is_valid) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 sm:p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto border border-rose-500/20">
            <Lock className="w-7 h-7" />
          </div>

          <div className="space-y-1.5">
            <h1 className="text-lg font-bold text-white">Invitation Unavailable</h1>
            <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">
              Code: {validation?.error_code || 'INVALID_LINK'}
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {validation?.error_message || 'This examination link is invalid, expired, revoked, or has reached maximum candidate capacity.'}
          </p>

          <div className="pt-4 border-t border-surface-border text-[11px] text-slate-400">
            Please contact your course instructor or exam administrator to request a valid invitation token.
          </div>
        </div>
      </div>
    );
  }

  // 3. Success / Receipt Confirmation State
  if (receipt) {
    return (
      <div className="min-h-screen bg-slate-950 py-12 px-4 flex flex-col items-center justify-center">
        <div className="max-w-xl w-full glass-card rounded-3xl border border-emerald-500/30 p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
          {/* Top banner accent */}
          <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-emerald-500 via-teal-500 to-primary-500" />

          {/* Status Icon */}
          <div className="flex items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8" />
            </div>
          </div>

          {/* Title & Status */}
          <div className="text-center space-y-2">
            <span className="text-[11px] uppercase tracking-wider font-bold px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 inline-flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Registration Confirmed</span>
            </span>
            <h1 className="text-xl sm:text-2xl font-bold text-white">
              {receipt.quiz_title}
            </h1>
            {receipt.subject_name && (
              <p className="text-xs text-slate-400">{receipt.subject_name}</p>
            )}
          </div>

          {/* Registration Code Badge */}
          <div className="p-4 rounded-2xl bg-surface-elevated border border-surface-border text-center space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Your Registration Code
            </span>
            <div className="flex items-center justify-center gap-2">
              <span className="text-xl sm:text-2xl font-mono font-bold text-primary-400 tracking-wider">
                {receipt.registration_code}
              </span>
              <button
                onClick={copyRegistrationCode}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                title="Copy Registration Code"
              >
                {copiedCode ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-slate-400">
              Save this code. You will need it to verify your identity on the examination portal.
            </p>
          </div>

          {/* Registration Details Summary */}
          <div className="space-y-2 text-xs divide-y divide-surface-border/60">
            <div className="flex items-center justify-between py-2 text-slate-300">
              <span className="text-slate-400">Candidate Name</span>
              <span className="font-semibold text-white">{receipt.student_name}</span>
            </div>
            {receipt.student_identifier && (
              <div className="flex items-center justify-between py-2 text-slate-300">
                <span className="text-slate-400">Register / Roll Number</span>
                <span className="font-mono text-white">{receipt.student_identifier}</span>
              </div>
            )}
            <div className="flex items-center justify-between py-2 text-slate-300">
              <span className="text-slate-400">Approval Status</span>
              <span
                className={`font-semibold capitalize ${
                  receipt.status === 'approved' ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {receipt.status.replace('_', ' ')}
              </span>
            </div>
            {receipt.scheduled_start && (
              <div className="flex items-center justify-between py-2 text-slate-300">
                <span className="text-slate-400">Scheduled Examination Time</span>
                <span className="font-medium text-white">
                  {new Date(receipt.scheduled_start).toLocaleString()}
                </span>
              </div>
            )}
            {receipt.examination_duration_minutes && (
              <div className="flex items-center justify-between py-2 text-slate-300">
                <span className="text-slate-400">Duration</span>
                <span className="text-white font-medium">{receipt.examination_duration_minutes} minutes</span>
              </div>
            )}
          </div>

          {/* Status Note */}
          {receipt.status === 'pending_approval' ? (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2.5">
              <Clock className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Pending Administrator Approval</p>
                <p className="text-[11px] text-amber-300/80 mt-0.5">
                  Your registration requires verification by the examination administrator. You will be permitted to enter the exam room once your registration is approved.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Admission Approved</p>
                <p className="text-[11px] text-emerald-300/80 mt-0.5">
                  Your seat has been reserved. Please return to the exam portal at the scheduled time with your registration code.
                </p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => window.print()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-surface-elevated hover:bg-slate-800 border border-surface-border text-xs text-white font-semibold transition-colors"
            >
              <Printer className="w-4 h-4" />
              <span>Print Registration Slip</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 4. Registration Form State
  return (
    <div className="min-h-screen bg-slate-950 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Portal Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 text-primary-400 border border-primary-500/20 text-xs font-semibold">
            <GraduationCap className="w-4 h-4" />
            <span>QUIZVERSE Candidate Admission Portal</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {validation.quiz_title || 'Examination Registration'}
          </h1>
          {validation.subject_name && (
            <p className="text-sm font-medium text-slate-400">{validation.subject_name}</p>
          )}
        </div>

        {/* Examination Metadata Pill Strip */}
        <div className="glass-card rounded-2xl border border-surface-border p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Duration</span>
            <p className="text-sm font-bold text-white flex items-center justify-center gap-1">
              <Clock className="w-3.5 h-3.5 text-primary-400" />
              <span>{validation.duration_minutes || '--'} mins</span>
            </p>
          </div>
          <div className="space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Total Marks</span>
            <p className="text-sm font-bold text-white flex items-center justify-center gap-1">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>{validation.total_marks || '--'} pts</span>
            </p>
          </div>
          <div className="space-y-0.5 col-span-2 sm:col-span-2">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Schedule</span>
            <p className="text-xs font-semibold text-white flex items-center justify-center gap-1 truncate">
              <Calendar className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                {validation.schedule_start
                  ? new Date(validation.schedule_start).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Open Anytime'}
              </span>
            </p>
          </div>
        </div>

        {/* Examination Instructions */}
        {validation.instructions && (
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-2">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Candidate Instructions</h3>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
              {validation.instructions}
            </p>
          </div>
        )}

        {/* Dynamic Registration Form Card */}
        <div className="glass-card rounded-3xl border border-surface-border p-6 sm:p-8 space-y-6 shadow-2xl">
          <div className="border-b border-surface-border pb-4 space-y-1">
            <h2 className="text-base font-bold text-white">Candidate Registration</h2>
            <p className="text-xs text-slate-400">
              Provide accurate information. Your details will be registered for this examination session.
            </p>
          </div>

          {submitError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Registration Incomplete</p>
                <p className="text-[11px] text-rose-300/80 mt-0.5">{submitError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {validation.registration_form && validation.registration_form.length > 0 ? (
              validation.registration_form.map((field: RegistrationFormFieldConfig) => {
                const error = validationErrors[field.field_name];
                return (
                  <div key={field.field_name} className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex items-center gap-1">
                      <span>{field.field_label}</span>
                      {field.is_required && <span className="text-rose-400">*</span>}
                    </label>

                    {/* Field input types */}
                    {field.field_type === 'textarea' ? (
                      <textarea
                        value={formData[field.field_name] || ''}
                        onChange={(e) => handleInputChange(field.field_name, e.target.value)}
                        placeholder={field.placeholder || `Enter ${field.field_label.toLowerCase()}`}
                        rows={3}
                        className={`w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border text-xs text-white focus:outline-none transition-colors resize-none ${
                          error ? 'border-rose-500' : 'border-surface-border focus:border-primary-500'
                        }`}
                      />
                    ) : field.field_type === 'select' ? (
                      <select
                        value={formData[field.field_name] || ''}
                        onChange={(e) => handleInputChange(field.field_name, e.target.value)}
                        className={`w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border text-xs text-white focus:outline-none transition-colors ${
                          error ? 'border-rose-500' : 'border-surface-border focus:border-primary-500'
                        }`}
                      >
                        <option value="">-- Select {field.field_label} --</option>
                        {field.options?.map((opt, i) => (
                          <option key={i} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : field.field_type === 'radio' ? (
                      <div className="space-y-2 pt-1">
                        {field.options?.map((opt, i) => (
                          <label key={i} className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                            <input
                              type="radio"
                              name={field.field_name}
                              value={opt}
                              checked={formData[field.field_name] === opt}
                              onChange={(e) => handleInputChange(field.field_name, e.target.value)}
                              className="text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                            />
                            <span>{opt}</span>
                          </label>
                        ))}
                      </div>
                    ) : field.field_type === 'checkbox' ? (
                      <label className="flex items-center gap-2.5 text-xs text-slate-300 pt-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={!!formData[field.field_name]}
                          onChange={(e) => handleInputChange(field.field_name, e.target.checked)}
                          className="rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                        />
                        <span>{field.placeholder || `I agree to the ${field.field_label}`}</span>
                      </label>
                    ) : (
                      <input
                        type={field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : field.field_type === 'email' ? 'email' : 'text'}
                        value={formData[field.field_name] || ''}
                        onChange={(e) => handleInputChange(field.field_name, e.target.value)}
                        placeholder={field.placeholder || `Enter your ${field.field_label.toLowerCase()}`}
                        className={`w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border text-xs text-white focus:outline-none transition-colors ${
                          error ? 'border-rose-500' : 'border-surface-border focus:border-primary-500'
                        }`}
                      />
                    )}

                    {error && (
                      <p className="text-[11px] text-rose-400 font-medium">{error}</p>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">Loading registration form fields...</p>
            )}

            <div className="pt-4">
              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all"
              >
                {submitting ? (
                  <span>Submitting Registration...</span>
                ) : (
                  <>
                    <span>Complete Examination Registration</span>
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Footer info */}
        <p className="text-center text-[11px] text-slate-500">
          QUIZVERSE Secure Examination Environment • Automated Session Control
        </p>
      </div>
    </div>
  );
}
