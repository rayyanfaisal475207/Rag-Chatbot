// ============================================================
// Chat Store — Zustand
// Manages all state for the chat interface:
//   - Session ID
//   - Message history
//   - Live pipeline events for the current response
//   - Streaming state
// ============================================================

import { create } from 'zustand';
import { generateSessionId } from '../lib/utils';
import { streamChat } from '../lib/api';
import type { ChatMessage, PipelineEvent, Source, PipelineStep } from '../types';
import { PIPELINE_STEPS } from '../types';

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildInitialSteps(): PipelineStep[] {
  return PIPELINE_STEPS.map((s) => ({
    name: s.name,
    label: s.label,
    status: 'waiting' as const,
  }));
}

function applyEventToSteps(
  steps: PipelineStep[],
  event: PipelineEvent,
): PipelineStep[] {
  return steps.map((step) => {
    if (step.name !== event.step) return step;

    // Determine visual status
    let status: PipelineStep['status'] = step.status;
    if (event.status === 'active') status = 'active';
    else if (event.status === 'done') status = 'done';
    else if (event.status === 'skipped') status = 'skipped';
    else if (event.status === 'error') status = 'error';
    // Retry: evaluator with retry_num > 0 and status != done
    if (
      event.step === 'evaluator' &&
      event.status === 'done' &&
      event.retry_num !== undefined &&
      event.retry_num > 0
    ) {
      status = 'retry';
    }

    return {
      ...step,
      status,
      detail: event.detail ?? step.detail,
      ms: event.ms ?? step.ms,
      retryNum: event.retry_num,
    };
  });
}

// Extract source citations from retrieval/evaluator events
function extractSources(events: PipelineEvent[]): Source[] {
  const sources: Source[] = [];
  for (const e of events) {
    if (e.step === 'retrieval' && e.status === 'done' && e.detail) {
      // detail is like "8 chunks retrieved" — sources come from reranker detail
    }
    if (e.step === 'reranker' && e.status === 'done' && e.detail) {
      // We may get filenames from the detail string in future; for now leave empty
      // Real source extraction would require the backend to emit a sources event
    }
  }
  return sources;
}

// ── Store Interface ───────────────────────────────────────────────────────────

interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  currentSteps: PipelineStep[];
  currentEvents: PipelineEvent[];
  currentSources: Source[];
  isStreaming: boolean;
  error: string | null;

  // Actions
  newSession: () => void;
  sendMessage: (text: string) => Promise<void>;
  clearError: () => void;
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: generateSessionId(),
  messages: [],
  currentSteps: buildInitialSteps(),
  currentEvents: [],
  currentSources: [],
  isStreaming: false,
  error: null,

  newSession: () => {
    set({
      sessionId: generateSessionId(),
      messages: [],
      currentSteps: buildInitialSteps(),
      currentEvents: [],
      currentSources: [],
      isStreaming: false,
      error: null,
    });
  },

  clearError: () => set({ error: null }),

  sendMessage: async (text: string) => {
    const { sessionId } = get();

    // Add user message immediately
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    };

    // Add a placeholder assistant message that we'll fill in
    const assistantMsgId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      sources: [],
      isStreaming: true,
    };

    set((state) => ({
      messages: [...state.messages, userMsg, assistantMsg],
      currentSteps: buildInitialSteps(),
      currentEvents: [],
      currentSources: [],
      isStreaming: true,
      error: null,
    }));

    let accumulatedResponse = '';
    const accumulatedEvents: PipelineEvent[] = [];

    try {
      await streamChat(sessionId, text, (event: PipelineEvent) => {
        accumulatedEvents.push(event);

        if (event.step === 'response' && event.status === 'streaming' && event.detail) {
          // Streaming token — append to the assistant message content
          accumulatedResponse += event.detail;
          set((state) => ({
            messages: state.messages.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: accumulatedResponse }
                : m,
            ),
            currentEvents: [...state.currentEvents, event],
          }));
        } else {
          // Pipeline step event — update the step card
          set((state) => ({
            currentSteps: applyEventToSteps(state.currentSteps, event),
            currentEvents: [...state.currentEvents, event],
          }));
        }
      });

      // Extract any sources from events
      const sources = extractSources(accumulatedEvents);

      // Finalize the assistant message
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === assistantMsgId
            ? { ...m, isStreaming: false, sources, pipelineEvents: accumulatedEvents }
            : m,
        ),
        currentSources: sources,
        isStreaming: false,
      }));
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred';
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: accumulatedResponse || '⚠️ An error occurred while processing your request.',
                isStreaming: false,
              }
            : m,
        ),
        currentSteps: state.currentSteps.map((s) =>
          s.status === 'active' ? { ...s, status: 'error' as const } : s,
        ),
        isStreaming: false,
        error: errorMsg,
      }));
    }
  },
}));
