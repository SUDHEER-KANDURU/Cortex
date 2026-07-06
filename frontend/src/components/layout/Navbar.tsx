'use client';

// =============================================================================
// Navbar — Premium Minimalist Navigation
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { Github } from 'lucide-react';

export default function Navbar() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-[600] flex h-14 items-center justify-between px-8"
      style={{
        background: 'rgba(0, 0, 0, 0.4)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
      aria-label="Main navigation"
    >
      <Link
        href="/"
        className="flex items-center gap-2.5 text-sm font-semibold text-white tracking-tight"
        aria-label="Cortex — home"
      >
        <div className="w-4 h-4 rounded-[3px] bg-gradient-to-br from-violet-500 to-cyan-400" />
        Cortex
      </Link>

      <div className="flex items-center gap-6 text-[13px]">
        <Link
          href="/dashboard"
          className="text-slate-400 transition-colors hover:text-white font-medium"
        >
          Dashboard
        </Link>
        <a
          href="https://github.com/SUDHEER-KANDURU/cortex"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View Cortex on GitHub"
          className="flex items-center gap-1.5 text-slate-400 transition-colors hover:text-white font-medium"
        >
          <Github className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </div>
    </nav>
  );
}
