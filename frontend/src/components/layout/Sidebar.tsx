// ============================================================
// Sidebar Navigation
// ============================================================

import { NavLink } from 'react-router-dom';

const navItems = [
  {
    to: '/',
    label: 'Chat',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
        <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
      </svg>
    ),
  },
  {
    to: '/knowledge-base',
    label: 'Knowledge Base',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
      </svg>
    ),
  },
  {
    to: '/ingest',
    label: 'Ingest Files',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
      </svg>
    ),
  },
];

export function Sidebar() {
  return (
    <aside className="flex flex-col items-center w-14 h-full glass-panel border-r border-[var(--border)] py-4 gap-1 shrink-0 z-10">
      {/* Logo mark */}
      <div className="w-8 h-8 rounded-lg gradient-bg shadow-md border-none flex items-center justify-center mb-4 hover-glow cursor-pointer">
        <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4">
          <circle cx="8" cy="8" r="3" fill="#ffffff" />
          <circle cx="3" cy="4" r="1.5" fill="#ffffff" opacity="0.8" />
          <circle cx="13" cy="4" r="1.5" fill="#ffffff" opacity="0.8" />
          <circle cx="3" cy="12" r="1.5" fill="#ffffff" opacity="0.8" />
          <circle cx="13" cy="12" r="1.5" fill="#ffffff" opacity="0.8" />
          <line x1="8" y1="5" x2="3" y2="4" stroke="#ffffff" strokeWidth="1" opacity="0.6" />
          <line x1="8" y1="5" x2="13" y2="4" stroke="#ffffff" strokeWidth="1" opacity="0.6" />
          <line x1="8" y1="11" x2="3" y2="12" stroke="#ffffff" strokeWidth="1" opacity="0.6" />
          <line x1="8" y1="11" x2="13" y2="12" stroke="#ffffff" strokeWidth="1" opacity="0.6" />
        </svg>
      </div>

      {/* Nav items */}
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          title={item.label}
          className={({ isActive }) =>
            `group relative w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-150 ${
              isActive
                ? 'bg-accent/15 text-accent'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-black/[0.05]'
            }`
          }
        >
          {item.icon}
          {/* Tooltip */}
          <span className="absolute left-full ml-2 px-2 py-1 rounded-md bg-surface border border-black/[0.08] text-xs text-[var(--text-primary)] whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-sm">
            {item.label}
          </span>
        </NavLink>
      ))}
    </aside>
  );
}
