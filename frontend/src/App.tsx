// ============================================================
// App — Router + Layout
// ============================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { IngestPage } from './pages/IngestPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
