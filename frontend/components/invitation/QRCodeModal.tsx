'use client';

import React, { useState, useRef } from 'react';
import { QRCodeSVG, QRCodeCanvas } from 'qrcode.react';
import {
  X,
  Copy,
  Check,
  Download,
  Printer,
  QrCode,
  ExternalLink,
  ShieldAlert,
  Calendar,
  Clock,
  BookOpen,
} from 'lucide-react';
import { InvitationItem } from '@/services/invitationService';

interface QRCodeModalProps {
  invitation: InvitationItem;
  accessUrl: string;
  isOpen: boolean;
  onClose: () => void;
}

export function QRCodeModal({ invitation, accessUrl, isOpen, onClose }: QRCodeModalProps) {
  const [copied, setCopied] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [domainMode, setDomainMode] = useState<'production' | 'current'>('production');
  const printRef = useRef<HTMLDivElement>(null);

  const resolvedUrl = React.useMemo(() => {
    if (!accessUrl) return '';
    const currentOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
    const prodUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://quizverse-iota.vercel.app';
    const targetOrigin = domainMode === 'production' ? prodUrl : currentOrigin;
    return accessUrl.replace(/https?:\/\/[^/]+/, targetOrigin);
  }, [accessUrl, domainMode]);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(resolvedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPNG = () => {
    const canvas = document.getElementById('qr-canvas-download') as HTMLCanvasElement;
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.download = `QR_${invitation.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`;
    a.href = url;
    a.click();
  };

  const handleDownloadSVG = () => {
    const svgElem = document.getElementById('qr-svg-download');
    if (!svgElem) return;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgElem);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.download = `QR_${invitation.name.replace(/[^a-zA-Z0-9]/g, '_')}.svg`;
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      {/* Hidden canvas & svg for high-res exports */}
      <div className="hidden">
        <QRCodeCanvas
          id="qr-canvas-download"
          value={resolvedUrl}
          size={1024}
          level="H"
          includeMargin={true}
        />
        <QRCodeSVG
          id="qr-svg-download"
          value={resolvedUrl}
          size={1024}
          level="H"
          includeMargin={true}
        />
      </div>

      <div className="relative w-full max-w-lg bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 sm:p-7 overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white truncate max-w-xs sm:max-w-sm">
                {invitation.name}
              </h3>
              <p className="text-xs text-slate-400 truncate max-w-xs">
                {invitation.quiz_title || 'Examination Registration'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Printable Card Area */}
        <div
          ref={printRef}
          className={`mt-5 p-5 rounded-xl border flex flex-col items-center transition-colors print:p-8 print:border-black print:text-black ${
            highContrast
              ? 'bg-white text-slate-900 border-slate-300'
              : 'bg-slate-900/60 text-slate-200 border-surface-border'
          }`}
        >
          {/* Print-only Header */}
          <div className="hidden print:block text-center w-full mb-4">
            <h1 className="text-xl font-bold text-black uppercase tracking-wider">
              {invitation.quiz_title || 'QUIZVERSE EXAMINATION'}
            </h1>
            <p className="text-xs text-gray-700 font-medium">
              Academic Registration Pass — {invitation.name}
            </p>
          </div>

          {/* QR Container */}
          <div className="p-3.5 bg-white rounded-xl shadow-md border border-slate-200 flex items-center justify-center">
            <QRCodeSVG
              value={resolvedUrl}
              size={180}
              level="H"
              includeMargin={false}
              fgColor="#090d16"
              bgColor="#ffffff"
            />
          </div>

          {/* Details below QR */}
          <div className="mt-4 text-center space-y-1 w-full max-w-xs">
            <div className="flex items-center justify-between text-[11px] mb-1">
              <span className="font-mono tracking-wide text-slate-400 uppercase">
                Target Domain:
              </span>
              <div className="flex items-center bg-slate-950 border border-slate-700/60 rounded-lg p-0.5 text-[10px]">
                <button
                  type="button"
                  onClick={() => setDomainMode('production')}
                  className={`px-2 py-0.5 rounded font-semibold transition-colors ${
                    domainMode === 'production'
                      ? 'bg-cyan-500 text-slate-950'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Vercel
                </button>
                <button
                  type="button"
                  onClick={() => setDomainMode('current')}
                  className={`px-2 py-0.5 rounded font-semibold transition-colors ${
                    domainMode === 'current'
                      ? 'bg-cyan-500 text-slate-950'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Localhost
                </button>
              </div>
            </div>
            <p className="text-xs font-medium break-all select-all font-mono py-1 px-2 rounded bg-slate-800/40 border border-slate-700/50 mt-1">
              {resolvedUrl}
            </p>
          </div>

          {/* Meta Info */}
          <div className="w-full grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-700/40 text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span className="truncate">{invitation.subject_name || 'General Subject'}</span>
            </div>
            <div className="flex items-center gap-1.5 justify-end">
              <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>
                {invitation.expires_at
                  ? `Exp: ${new Date(invitation.expires_at).toLocaleDateString()}`
                  : 'No expiration'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="mt-5 space-y-3">
          {/* Quick Copy Link Box */}
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-slate-300 font-mono truncate select-all">
              {resolvedUrl}
            </div>
            <button
              onClick={handleCopy}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 ${
                copied
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-primary-600 hover:bg-primary-500 text-white'
              }`}
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>

          {/* Action Buttons Toolbar */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-surface-border flex-wrap">
            <button
              onClick={() => setHighContrast(!highContrast)}
              className="px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
            >
              Mode: {highContrast ? 'Light' : 'Dark'}
            </button>

            <div className="flex items-center gap-1.5">
              <button
                onClick={handleDownloadPNG}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" />
                PNG
              </button>
              <button
                onClick={handleDownloadSVG}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-purple-400" />
                SVG
              </button>
              <button
                onClick={handlePrint}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <Printer className="w-3.5 h-3.5" />
                Print Sheet
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
