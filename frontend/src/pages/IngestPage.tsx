// ============================================================
// IngestPage — drag-and-drop file upload
// ============================================================

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { triggerIngest } from '../lib/api';
import { getFileTypeIcon, formatBytes } from '../lib/utils';
import type { StagedFile } from '../types';

const ACCEPTED_TYPES = {
  'text/plain': ['.txt', '.md'],
  'application/pdf': ['.pdf'],
  'text/csv': ['.csv'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/html': ['.html', '.htm'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
};

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

export function IngestPage() {
  const [files, setFiles] = useState<StagedFile[]>([]);
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [statusMsg, setStatusMsg] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const staged: StagedFile[] = acceptedFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      type: file.name.split('.').pop()?.toLowerCase() ?? '',
    }));
    setFiles((prev) => {
      // Deduplicate by name
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...staged.filter((f) => !existing.has(f.name))];
    });
    setStatus('idle');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: true,
  });

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setStatus('uploading');
    setStatusMsg('');
    try {
      // Note: The backend's POST /ingest triggers ingestion of the DOCUMENTS_DIR.
      // For a production system you'd upload files via multipart form.
      // Here we call the trigger endpoint which processes whatever is in data/documents/.
      const result = await triggerIngest();
      setStatus('success');
      setStatusMsg(result.message ?? 'Ingestion started in the background.');
      setFiles([]);
    } catch (err) {
      setStatus('error');
      setStatusMsg(err instanceof Error ? err.message : 'Upload failed');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b shrink-0"
        style={{ borderColor: 'var(--border)' }}
      >
        <div>
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">Ingest Files</h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Add documents to your knowledge base
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-5 max-w-2xl">
        {/* Status banner */}
        {status === 'success' && (
          <div
            className="px-4 py-3 rounded-lg text-sm border flex items-center gap-2 animate-fade-in"
            style={{ background: 'var(--success-bg)', borderColor: 'var(--success-border)', color: 'var(--success)' }}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {statusMsg}
          </div>
        )}
        {status === 'error' && (
          <div
            className="px-4 py-3 rounded-lg text-sm border flex items-center gap-2 animate-fade-in"
            style={{ background: 'var(--error-bg)', borderColor: 'var(--error-border)', color: 'var(--error)' }}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {statusMsg}
          </div>
        )}

        {/* Drop zone */}
        <div
          {...getRootProps()}
          id="dropzone"
          className="rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200 flex flex-col items-center gap-4"
          style={{
            borderColor: isDragActive ? 'var(--accent)' : 'rgba(255,255,255,0.12)',
            background: isDragActive ? 'var(--accent-bg)' : 'var(--bg-surface)',
          }}
        >
          <input {...getInputProps()} id="file-input" />
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center transition-colors"
            style={{
              background: isDragActive ? 'rgba(59,130,246,0.2)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${isDragActive ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.08)'}`,
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7" style={{ color: isDragActive ? 'var(--accent)' : 'var(--text-muted)' }}>
              <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {isDragActive ? 'Drop files here…' : 'Drag & drop files here'}
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              or <span className="text-accent underline-offset-2 underline">browse</span> to select
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-1.5">
            {['.pdf', '.docx', '.xlsx', '.csv', '.html', '.txt', '.md', '.jpg', '.png'].map((ext) => (
              <span
                key={ext}
                className="text-[10px] px-2 py-0.5 rounded-full"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: 'var(--text-muted)',
                }}
              >
                {ext}
              </span>
            ))}
          </div>
        </div>

        {/* Staged files list */}
        {files.length > 0 && (
          <div
            className="rounded-xl border overflow-hidden"
            style={{ borderColor: 'var(--border)' }}
          >
            <div
              className="flex items-center justify-between px-4 py-2.5 border-b"
              style={{
                borderColor: 'var(--border)',
                background: 'var(--bg-surface)',
              }}
            >
              <span className="text-xs font-medium text-[var(--text-secondary)]">
                {files.length} file{files.length > 1 ? 's' : ''} selected
              </span>
              <button
                onClick={() => setFiles([])}
                className="text-[11px] text-[var(--text-muted)] hover:text-error transition-colors"
              >
                Clear all
              </button>
            </div>

            {files.map((f, i) => (
              <div
                key={f.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-white/[0.015] transition-colors"
                style={{
                  borderBottom: i < files.length - 1 ? '1px solid var(--border)' : 'none',
                  background: 'var(--bg-base)',
                }}
              >
                <span className="text-base shrink-0">{getFileTypeIcon(f.type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[var(--text-primary)] truncate font-medium" title={f.name}>
                    {f.name}
                  </p>
                  <p className="text-[10px] text-[var(--text-muted)]">
                    {formatBytes(f.size)} · {f.type.toUpperCase()}
                  </p>
                </div>
                <button
                  onClick={() => removeFile(f.id)}
                  className="shrink-0 w-6 h-6 rounded flex items-center justify-center text-[var(--text-muted)] hover:text-error hover:bg-error/10 transition-all"
                >
                  <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
                    <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Upload button */}
        <button
          id="upload-btn"
          onClick={handleUpload}
          disabled={files.length === 0 || status === 'uploading'}
          className="w-full py-2.5 rounded-lg text-sm font-medium transition-all duration-150 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: files.length > 0 && status !== 'uploading' ? 'var(--accent)' : 'var(--bg-surface)',
            color: files.length > 0 && status !== 'uploading' ? 'white' : 'var(--text-muted)',
            border: '1px solid',
            borderColor: files.length > 0 ? 'var(--accent)' : 'var(--border)',
          }}
        >
          {status === 'uploading' ? (
            <>
              <svg className="w-4 h-4 animate-spin-slow" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Triggering ingestion…
            </>
          ) : (
            <>
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
              Trigger Ingestion
            </>
          )}
        </button>

        {/* Note */}
        <p className="text-[11px] text-[var(--text-muted)] text-center leading-relaxed">
          Place your files in <code className="text-[var(--text-secondary)] bg-white/[0.05] px-1 rounded">data/documents/</code> and click Trigger Ingestion. The backend processes them asynchronously.
        </p>
      </div>
    </div>
  );
}
