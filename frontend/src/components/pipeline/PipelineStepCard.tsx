// ============================================================
// PipelineStepCard — one step in the live pipeline trace
// ============================================================

import type { PipelineStep } from '../../types';
import { formatMs } from '../../lib/utils';

interface Props {
  step: PipelineStep;
}

// Status-specific visual config
const STATUS_CONFIG = {
  waiting: {
    border: 'border-black/[0.08]',
    bg: 'bg-black/[0.02]',
    textColor: 'text-[var(--text-muted)]',
    opacity: 'opacity-80',
    icon: <DashIcon />,
    dotColor: '',
  },
  active: {
    border: 'border-accent/40',
    bg: 'bg-accent/[0.05]',
    textColor: 'text-[var(--text-primary)]',
    opacity: '',
    icon: <SpinnerIcon />,
    dotColor: 'bg-accent',
  },
  done: {
    border: 'border-success/30',
    bg: 'bg-success/[0.04]',
    textColor: 'text-[var(--text-primary)]',
    opacity: '',
    icon: <CheckIcon />,
    dotColor: 'bg-success',
  },
  skipped: {
    border: 'border-black/[0.08]',
    bg: 'bg-transparent',
    textColor: 'text-[var(--text-muted)]',
    opacity: 'opacity-60',
    icon: <SlashIcon />,
    dotColor: '',
  },
  error: {
    border: 'border-error/40',
    bg: 'bg-error/[0.05]',
    textColor: 'text-error',
    opacity: '',
    icon: <XIcon />,
    dotColor: 'bg-error',
  },
  retry: {
    border: 'border-warning/40',
    bg: 'bg-warning/[0.05]',
    textColor: 'text-warning',
    opacity: '',
    icon: <RetryIcon />,
    dotColor: 'bg-warning',
  },
};

export function PipelineStepCard({ step }: Props) {
  const cfg = STATUS_CONFIG[step.status];

  return (
    <div
      className={`
        flex items-start gap-3 px-3 py-2.5 rounded-lg border transition-all duration-300
        ${cfg.border} ${cfg.bg} ${cfg.opacity} animate-fade-in
      `}
    >
      {/* Status icon */}
      <div className={`shrink-0 mt-0.5 ${cfg.textColor}`}>
        {cfg.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-xs font-medium ${cfg.textColor}`}>
            {step.label}
            {step.status === 'retry' && step.retryNum !== undefined && (
              <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-warning/20 text-warning">
                retry #{step.retryNum}
              </span>
            )}
          </span>
          {step.ms !== undefined && (
            <span className="text-[10px] text-[var(--text-muted)] shrink-0">
              {formatMs(step.ms)}
            </span>
          )}
        </div>

        {step.detail && step.status !== 'waiting' && (
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5 truncate" title={step.detail}>
            {step.detail}
          </p>
        )}

        {/* Active pulsing progress bar */}
        {step.status === 'active' && (
          <div className="mt-1.5 h-0.5 rounded-full bg-black/[0.05] overflow-hidden">
            <div
              className="h-full rounded-full bg-accent/60"
              style={{
                width: '40%',
                animation: 'shimmer 1.5s infinite linear',
                background: 'linear-gradient(90deg, transparent, rgba(59,130,246,0.6), transparent)',
                backgroundSize: '200% 100%',
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Icon components ────────────────────────────────────────────

function DashIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
      <path d="M3.75 7.25h8.5a.75.75 0 010 1.5h-8.5a.75.75 0 010-1.5z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-success" viewBox="0 0 16 16" fill="currentColor">
      <path fillRule="evenodd" d="M12.416 3.376a.75.75 0 01.208 1.04l-5 7.5a.75.75 0 01-1.154.114l-3-3a.75.75 0 011.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 011.04-.207z" clipRule="evenodd" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
      <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
    </svg>
  );
}

function SlashIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
      <path fillRule="evenodd" d="M4.22 11.78a.75.75 0 001.06 0l6.5-6.5a.75.75 0 00-1.06-1.06l-6.5 6.5a.75.75 0 000 1.06z" clipRule="evenodd" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-accent animate-spin-slow" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" />
      <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function RetryIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-warning" viewBox="0 0 16 16" fill="currentColor">
      <path fillRule="evenodd" d="M8 3a5 5 0 104.546 2.914.5.5 0 01.908-.417A6 6 0 118 2v1z" clipRule="evenodd" />
      <path d="M8 4.466V.534a.25.25 0 01.41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 018 4.466z" />
    </svg>
  );
}
