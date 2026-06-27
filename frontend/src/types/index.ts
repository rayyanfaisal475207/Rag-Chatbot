// ============================================================
// Shared TypeScript Types
// ============================================================

/** A single Server-Sent Event from the /chat endpoint */
export interface PipelineEvent {
  step: string;
  status: 'active' | 'done' | 'skipped' | 'error' | 'streaming' | 'waiting';
  detail?: string;
  ms?: number;
  retry_num?: number;
}

/** Visual state of one step card in the pipeline panel */
export interface PipelineStep {
  name: string;
  label: string;
  status: 'waiting' | 'active' | 'done' | 'skipped' | 'error' | 'retry';
  detail?: string;
  ms?: number;
  retryNum?: number;
}

/** A source citation extracted from retrieval events */
export interface Source {
  filename: string;
  score?: number;
}

/** A single chat message (user or assistant) */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  pipelineEvents?: PipelineEvent[];
  isStreaming?: boolean;
}

/** A document from GET /documents */
export interface KnowledgeDocument {
  source_file: string;
  file_type: string;
  chunk_count: number;
  total_chars: number;
  first_ingested: string;
  last_ingested: string;
}

/** A file staged for upload */
export interface StagedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
}

/** Canonical pipeline step order and labels */
export const PIPELINE_STEPS: Array<{ name: string; label: string }> = [
  { name: 'query_rewriter', label: 'Query Rewriter' },
  { name: 'router',         label: 'Router' },
  { name: 'retrieval',      label: 'Retrieval' },
  { name: 'reranker',       label: 'Re-ranker' },
  { name: 'evaluator',      label: 'Evaluator' },
  { name: 'response',       label: 'Response' },
  { name: 'memory',         label: 'Memory' },
];
