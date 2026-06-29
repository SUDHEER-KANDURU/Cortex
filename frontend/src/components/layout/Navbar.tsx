// =============================================================================
// Navbar — Top navigation bar for Cortex
// Dark background, Cortex logo on the left, GitHub link on the right.
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { Brain, Github } from 'lucide-react';

export default function Navbar() {
  return (
    <nav
      className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-gray-800 bg-gray-900 px-6"
      aria-label="Main navigation"
    >
      {/* Logo + Brand */}
      <Link
        href="/dashboard"
        className="flex items-center gap-2 text-white hover:opacity-80 transition-opacity"
        aria-label="Cortex — go to dashboard"
      >
        <Brain className="h-5 w-5 text-violet-400" aria-hidden="true" />
        <span className="text-lg font-semibold tracking-tight">Cortex</span>
        <span className="hidden sm:inline-block text-xs text-gray-500 font-normal ml-1">
          Engineering Reasoning Engine
        </span>
      </Link>

      {/* Right-side actions */}
      <div className="flex items-center gap-4">
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View Cortex on GitHub (opens in new tab)"
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <Github className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </div>
    </nav>
  );
}
