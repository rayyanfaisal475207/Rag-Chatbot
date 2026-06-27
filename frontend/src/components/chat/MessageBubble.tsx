// ============================================================
// MessageBubble — renders a single chat message
// ============================================================

import type { ChatMessage } from '../../types';

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end animate-slide-in-right">
        <div
          className="max-w-[75%] px-4 py-3 rounded-2xl rounded-br-md"
          style={{
            background: 'rgba(59,130,246,0.18)',
            border: '1px solid rgba(59,130,246,0.25)',
          }}
        >
          <p className="text-[var(--text-primary)] text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start animate-slide-in-left">
      <div className="flex gap-3 max-w-[85%]">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0 mt-0.5">
          <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5">
            <circle cx="8" cy="8" r="3" fill="#3b82f6" />
            <circle cx="3" cy="4" r="1.5" fill="#3b82f6" opacity="0.5" />
            <circle cx="13" cy="12" r="1.5" fill="#3b82f6" opacity="0.5" />
          </svg>
        </div>

        <div className="flex flex-col gap-2 min-w-0">
          {/* Message content */}
          <div
            className="px-4 py-3 rounded-2xl rounded-tl-md"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
            }}
          >
            {message.content ? (
              <div
                className={`prose-chat text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap ${
                  message.isStreaming ? 'streaming-cursor' : ''
                }`}
              >
                {message.content}
              </div>
            ) : message.isStreaming ? (
              <div className="flex items-center gap-2 text-[var(--text-muted)] text-sm">
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-accent inline-block" />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-accent inline-block [animation-delay:0.2s]" />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-accent inline-block [animation-delay:0.4s]" />
              </div>
            ) : null}
          </div>

          {/* Source citations */}
          {!message.isStreaming && message.sources && message.sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-1">
              <span className="text-[11px] text-[var(--text-muted)] self-center">Sources:</span>
              {message.sources.map((src, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px]"
                  style={{
                    background: 'var(--bg-surface-2)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  📄 {src.filename}
                  {src.score !== undefined && (
                    <span className="text-[var(--text-muted)]">{src.score.toFixed(3)}</span>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
