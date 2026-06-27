// ============================================================
// API Layer — all fetch/SSE/REST calls live here
// ============================================================

import type { KnowledgeDocument, PipelineEvent } from '../types';

const BASE_URL = '/api';

// ── SSE Streaming Chat ──────────────────────────────────────────────────────
/**
 * POST /chat with session_id + message.
 * Uses fetch + ReadableStream to consume SSE (not EventSource, which
 * doesn't support POST or custom headers).
 *
 * @param sessionId  UUID of the current session
 * @param message    The user's message text
 * @param onEvent    Callback fired for every parsed SSE event
 * @param signal     AbortSignal to cancel the stream
 */
export async function streamChat(
  sessionId: string,
  message: string,
  onEvent: (event: PipelineEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Chat request failed: ${response.status} ${text}`);
  }

  if (!response.body) {
    throw new Error('No response body received');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE format: "data: {...}\n\n"
    // Split on double newlines to get complete events
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? ''; // keep the incomplete trailing chunk

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data: ')) continue;
      const json = line.slice(6); // remove "data: " prefix
      try {
        const event = JSON.parse(json) as PipelineEvent;
        onEvent(event);
      } catch {
        // Malformed JSON — skip silently
      }
    }
  }

  // Flush any remaining buffer content
  if (buffer.trim().startsWith('data: ')) {
    try {
      const event = JSON.parse(buffer.trim().slice(6)) as PipelineEvent;
      onEvent(event);
    } catch {
      // ignore
    }
  }
}

// ── Documents ───────────────────────────────────────────────────────────────
export async function getDocuments(): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${BASE_URL}/documents`);
  if (!res.ok) throw new Error(`Failed to fetch documents: ${res.status}`);
  return res.json();
}

export async function deleteDocument(sourceFile: string): Promise<{ message: string }> {
  const res = await fetch(`${BASE_URL}/documents/${encodeURIComponent(sourceFile)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete document: ${res.status}`);
  return res.json();
}

// ── Ingestion ───────────────────────────────────────────────────────────────
export async function triggerIngest(): Promise<{ message: string }> {
  const res = await fetch(`${BASE_URL}/ingest`, { method: 'POST' });
  if (!res.ok) throw new Error(`Ingest request failed: ${res.status}`);
  return res.json();
}

// ── Health ──────────────────────────────────────────────────────────────────
export async function getHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
