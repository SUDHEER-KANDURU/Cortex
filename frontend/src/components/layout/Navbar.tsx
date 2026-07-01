// =============================================================================
// Navbar — Premium 48px app nav for dashboard / job detail pages
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { Github } from 'lucide-react';

export default function Navbar() {
  return (
    <nav
      className="sticky top-0 z-50 flex h-12 shrink-0 items-center justify-between px-6"
      style={{
        background: 'rgba(10, 15, 26, 0.95)',
        borderBottom: '1px solid #1A2340',
        backdropFilter: 'blur(12px)',
      }}
      aria-label="Main navigation"
    >
      <Link
        href="/"
        className="flex items-center gap-2 text-sm font-medium text-white transition-opacity hover:opacity-80"
        aria-label="Cortex — home"
      >
        <span className="text-violet-400">✦</span>
        Cortex
      </Link>

      <div className="flex items-center gap-4 text-sm">
        <Link
          href="/dashboard"
          className="text-slate-400 transition-colors hover:text-white"
        >
          Dashboard
        </Link>
        <a
          href="https://github.com/SUDHEER-KANDURU/cortex"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View Cortex on GitHub"
          className="flex items-center gap-1.5 text-slate-400 transition-colors hover:text-white"
        >
          <Github className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </div>
    </nav>
  );
}
