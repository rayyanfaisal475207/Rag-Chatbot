// ============================================================
// ChatInput — textarea + send + new session buttons
// ============================================================

import { useState, useRef, useCallback } from 'react';

interface Props {
  onSend: (text: string) => void;
  onNewSession: () => void;
  disabled: boolean;
}

export function ChatInput({ onSend, onNewSession, disabled }: Props) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-expand textarea
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  };

  return (
    <div
      className="p-4 border-t"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-base)' }}
    >
      <div
        className="flex items-end gap-3 px-4 py-3 rounded-xl transition-all duration-150"
        style={{
          background: 'var(--bg-surface)',
          border: `1px solid ${disabled ? 'var(--border)' : 'var(--border-hover)'}`,
        }}
      >
        {/* New Session Button */}
        <button
          id="new-session-btn"
          onClick={onNewSession}
          title="Start a new session"
          disabled={disabled}
          className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-black/[0.06] transition-all duration-150 disabled:opacity-40"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents…"
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] resize-none outline-none leading-relaxed disabled:opacity-50"
          style={{ maxHeight: '160px' }}
        />

        {/* Send Button */}
        <button
          id="send-btn"
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-150 disabled:opacity-30"
          style={{
            background: disabled || !text.trim() ? 'transparent' : 'var(--accent)',
            color: disabled || !text.trim() ? 'var(--text-muted)' : 'white',
          }}
        >
          {disabled ? (
            <svg className="w-4 h-4 animate-spin-slow" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-center text-[11px] text-[var(--text-muted)] mt-2">
        Press <kbd className="px-1 py-0.5 rounded text-[10px] bg-black/[0.06] border border-black/[0.08]">Enter</kbd> to send · <kbd className="px-1 py-0.5 rounded text-[10px] bg-black/[0.06] border border-black/[0.08]">Shift+Enter</kbd> for new line ·{' '}
        <button onClick={onNewSession} className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] underline-offset-2 hover:underline transition-colors">
          New session
        </button>
      </p>
    </div>
  );
}
