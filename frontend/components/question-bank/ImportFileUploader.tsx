'use client';

import React, { useState, useRef } from 'react';
import { FileCheck, FileSpreadsheet, FileText, FolderUp, UploadCloud, RefreshCw, X } from 'lucide-react';
import { questionImportExportService } from '../../services/questionImportExportService';

interface ImportFileUploaderProps {
  token: string;
  onUploadSuccess: (job: any) => void;
  onError: (msg: string) => void;
}

export default function ImportFileUploader({ token, onUploadSuccess, onError }: ImportFileUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState<'csv' | 'xlsx' | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx') {
      onError('Invalid file format. Only .xlsx and .csv files are supported.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      onError('File size exceeds 10 MB limit.');
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      const job = await questionImportExportService.uploadImportFile(selectedFile, token);
      onUploadSuccess(job);
    } catch (err: any) {
      onError(err.message || 'Failed to upload and validate file.');
    } finally {
      setUploading(false);
    }
  };

  const handleDownloadTemplate = async (format: 'csv' | 'xlsx') => {
    setDownloadingTemplate(format);
    try {
      const blob = await questionImportExportService.downloadTemplate(format, token);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `QUIZVERSE_Question_Import_Template.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      onError(`Failed to download template: ${err.message}`);
    } finally {
      setDownloadingTemplate(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Template Download Banner */}
      <div className="bg-gradient-to-r from-blue-900/40 via-indigo-900/30 to-purple-900/40 border border-blue-500/30 rounded-xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg backdrop-blur-sm">
        <div>
          <h3 className="text-white font-semibold text-lg flex items-center gap-2">
            <span className="p-1.5 bg-blue-500/20 text-blue-400 rounded-lg">
              <FileCheck className="w-5 h-5 text-blue-400" />
            </span>
            <span>Official Question Import Templates</span>
          </h3>
          <p className="text-slate-400 text-sm mt-1">
            Download our verified templates with column definitions, instructions, and examples for Single Choice, Multiple Choice, True/False, and Short Answer.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => handleDownloadTemplate('xlsx')}
            disabled={downloadingTemplate !== null}
            className="px-4 py-2 bg-emerald-600/80 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition flex items-center gap-2 border border-emerald-400/30 shadow-md shadow-emerald-950/40 disabled:opacity-50"
          >
            {downloadingTemplate === 'xlsx' ? (
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
            ) : (
              <FileSpreadsheet className="w-4 h-4 text-emerald-200" />
            )}
            <span>Download Excel (.xlsx)</span>
          </button>
          <button
            onClick={() => handleDownloadTemplate('csv')}
            disabled={downloadingTemplate !== null}
            className="px-4 py-2 bg-blue-600/80 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition flex items-center gap-2 border border-blue-400/30 shadow-md shadow-blue-950/40 disabled:opacity-50"
          >
            {downloadingTemplate === 'csv' ? (
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
            ) : (
              <FileText className="w-4 h-4 text-cyan-200" />
            )}
            <span>Download CSV (.csv)</span>
          </button>
        </div>
      </div>

      {/* Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 md:p-12 text-center cursor-pointer transition-all duration-200 ${
          dragActive
            ? 'border-indigo-400 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:bg-slate-900/80'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv"
          onChange={handleChange}
          className="hidden"
        />

        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center shadow-inner">
            <FolderUp className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h4 className="text-white font-medium text-lg">
              {selectedFile ? selectedFile.name : 'Choose or drag question file here'}
            </h4>
            <p className="text-slate-400 text-sm mt-1">
              Supports Microsoft Excel (.xlsx) and CSV (.csv) up to 10 MB (max 1,000 questions per batch)
            </p>
          </div>

          {selectedFile && (
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-slate-800/80 border border-slate-700 rounded-xl text-xs text-slate-300">
              <span>File size: {(selectedFile.size / 1024).toFixed(1)} KB</span>
              <span>•</span>
              <span className="text-indigo-400 uppercase font-semibold">
                {selectedFile.name.split('.').pop()}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
                className="text-red-400 hover:text-red-300 ml-2 inline-flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Remove</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      {selectedFile && (
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={() => setSelectedFile(null)}
            disabled={uploading}
            className="px-5 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={uploading}
            className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-xl text-sm transition shadow-lg shadow-indigo-900/40 flex items-center gap-2 disabled:opacity-50"
          >
            {uploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>Validating Questions...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4 text-white" />
                <span>Upload & Validate Preview</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
