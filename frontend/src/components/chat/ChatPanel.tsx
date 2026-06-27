// ============================================================
// ChatPanel — left column: message list + input
// ============================================================

import { useEffect, useRef } from 'react';
import { useChatStore } from '../../store/chatStore';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';

export function ChatPanel() {
  const { messages, isStreaming, sendMessage, newSession, sessionId } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">Chat</h1>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-md font-mono"
            style={{
              background: 'var(--bg-surface-2)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
            }}
          >
            {sessionId.slice(0, 8)}
          </span>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
            <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-accent inline-block" />
            Processing…
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col gap-5">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        onNewSession={newSession}
        disabled={isStreaming}
      />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-8">
      <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center">
        <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8 text-accent">
          <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="text-xl font-semibold gradient-text tracking-tight pb-1">
          Ask your knowledge base
        </h2>
        <p className="text-sm text-[var(--text-muted)] max-w-xs leading-relaxed">
          The pipeline will search your ingested documents, evaluate relevance, and stream a grounded response — all visible in real time on the right.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 w-full max-w-sm mt-4">
        {[
          'According to the SPRINT trial, what was the hazard ratio for all-cause mortality?',
          'What is the daily sodium limit recommended by the DASH diet?',
          'Based on the AHA categories, what is the range for Stage 1 High Blood Pressure?',
        ].map((suggestion) => (
          <button
            key={suggestion}
            className="text-left text-sm text-[var(--text-secondary)] px-4 py-3 rounded-xl transition-all duration-200 hover:text-[var(--text-primary)] glass-panel hover-glow border-[var(--border)]"
            onClick={() => {
              // Dispatch a custom event that ChatInput can pick up, or use the store
              // For simplicity, we'll use the store directly
              useChatStore.getState().sendMessage(suggestion);
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
