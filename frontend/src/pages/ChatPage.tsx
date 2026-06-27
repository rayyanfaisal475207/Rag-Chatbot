// ============================================================
// ChatPage — two-column layout (60% chat, 40% pipeline)
// ============================================================

import { ChatPanel } from '../components/chat/ChatPanel';
import { PipelinePanel } from '../components/pipeline/PipelinePanel';

export function ChatPage() {
  return (
    <div className="flex justify-center h-full bg-[var(--bg-base)] py-6 px-6">
      <div className="flex w-full max-w-7xl h-full shadow-lg rounded-2xl overflow-hidden border border-[var(--border)] bg-[var(--bg-surface)]">
        {/* Left: Chat (60%) */}
        <div className="flex flex-col border-r border-[var(--border)]" style={{ flex: '0 0 60%' }}>
          <ChatPanel />
        </div>

        {/* Right: Pipeline Trace (40%) */}
        <div className="bg-[var(--bg-surface-2)]" style={{ flex: '0 0 40%' }}>
          <PipelinePanel />
        </div>
      </div>
    </div>
  );
}
