// ============================================================
// KnowledgeBasePage — lists ingested documents with CRUD
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { getDocuments, deleteDocument } from '../lib/api';
import { getFileTypeBadgeBg, formatDate } from '../lib/utils';
import type { KnowledgeDocument } from '../types';

export function KnowledgeBasePage() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleDelete = async (sourceFile: string) => {
    setDeletingId(sourceFile);
    try {
      await deleteDocument(sourceFile);
      setDocs((prev) => prev.filter((d) => d.source_file !== sourceFile));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setDeletingId(null);
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
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">Knowledge Base</h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            {docs.length} document{docs.length !== 1 ? 's' : ''} ingested
          </p>
        </div>
        <button
          id="refresh-docs-btn"
          onClick={fetchDocs}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] border transition-all duration-150 hover:text-[var(--text-primary)] hover:border-white/[0.15] disabled:opacity-50"
          style={{ borderColor: 'var(--border)', background: 'var(--bg-surface)' }}
        >
          <svg
            viewBox="0 0 16 16"
            fill="currentColor"
            className={`w-3.5 h-3.5 ${loading ? 'animate-spin-slow' : ''}`}
          >
            <path fillRule="evenodd" d="M8 3a5 5 0 104.546 2.914.5.5 0 01.908-.417A6 6 0 118 2v1z" clipRule="evenodd" />
            <path d="M8 4.466V.534a.25.25 0 01.41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 018 4.466z" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="mx-6 mt-4 px-4 py-3 rounded-lg text-sm text-error border"
          style={{ background: 'var(--error-bg)', borderColor: 'var(--error-border)' }}
        >
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">dismiss</button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <LoadingSkeleton />
        ) : docs.length === 0 ? (
          <EmptyState />
        ) : (
          <div
            className="rounded-xl border overflow-hidden"
            style={{ borderColor: 'var(--border)' }}
          >
            {/* Table header */}
            <div
              className="grid text-[11px] font-medium uppercase tracking-wide px-4 py-2.5"
              style={{
                gridTemplateColumns: '1fr 90px 70px 120px 90px',
                background: 'var(--bg-surface)',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-muted)',
              }}
            >
              <span>Filename</span>
              <span>Type</span>
              <span>Chunks</span>
              <span>Ingested</span>
              <span></span>
            </div>

            {/* Table rows */}
            {docs.map((doc, i) => {
              const ext = doc.file_type || doc.source_file.split('.').pop() || '';
              const isDeleting = deletingId === doc.source_file;

              return (
                <div
                  key={doc.source_file}
                  id={`doc-row-${i}`}
                  className="grid items-center px-4 py-3 transition-all duration-150 hover:bg-white/[0.02]"
                  style={{
                    gridTemplateColumns: '1fr 90px 70px 120px 90px',
                    borderBottom: i < docs.length - 1 ? '1px solid var(--border)' : 'none',
                    background: 'var(--bg-base)',
                    opacity: isDeleting ? 0.5 : 1,
                  }}
                >
                  {/* Filename */}
                  <div className="min-w-0">
                    <span
                      className="text-xs text-[var(--text-primary)] truncate block font-medium"
                      title={doc.source_file}
                    >
                      {doc.source_file}
                    </span>
                  </div>

                  {/* Type badge */}
                  <div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset uppercase ${getFileTypeBadgeBg(ext)}`}
                    >
                      {ext || '?'}
                    </span>
                  </div>

                  {/* Chunks */}
                  <span className="text-xs text-[var(--text-secondary)]">
                    {doc.chunk_count?.toLocaleString() ?? '—'}
                  </span>

                  {/* Date */}
                  <span className="text-xs text-[var(--text-muted)]">
                    {formatDate(doc.last_ingested)}
                  </span>

                  {/* Delete */}
                  <div className="flex justify-end">
                    <button
                      id={`delete-doc-${i}`}
                      onClick={() => handleDelete(doc.source_file)}
                      disabled={isDeleting || loading}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-error/70 border border-error/0 hover:border-error/25 hover:text-error hover:bg-error/5 transition-all duration-150 disabled:opacity-40"
                    >
                      {isDeleting ? (
                        <svg className="w-3 h-3 animate-spin-slow" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                          <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3">
                          <path d="M6.5 1h3a.5.5 0 01.5.5v1H6v-1a.5.5 0 01.5-.5zM11 2.5v-1A1.5 1.5 0 009.5 0h-3A1.5 1.5 0 005 1.5v1H2.506a.58.58 0 00-.01 1.158l.875 10.5A1.5 1.5 0 004.865 16h6.27a1.5 1.5 0 001.494-1.342l.875-10.5a.58.58 0 00-.01-1.158H11z" />
                        </svg>
                      )}
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="h-12 rounded-lg"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            opacity: 1 - i * 0.15,
          }}
        />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <div
        className="w-14 h-14 rounded-xl flex items-center justify-center border"
        style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7 text-[var(--text-muted)]">
          <path d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-[var(--text-secondary)]">No documents ingested</p>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Go to <strong>Ingest Files</strong> to add documents to your knowledge base.
        </p>
      </div>
    </div>
  );
}
