// =============================================================================
// Sidebar — Collapsible sidebar navigation using Cortex design tokens
// Ready for extension with route-based highlighting.
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { LayoutDashboard, Briefcase, GitGraph } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface SidebarProps {
  activePath?: string;
}

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/jobs',      label: 'Jobs',       icon: Briefcase },
  { href: '/graph',     label: 'Graph',      icon: GitGraph },
] as const;

export default function Sidebar({ activePath }: SidebarProps) {
  return (
    <aside
      className="hidden md:flex w-56 shrink-0 flex-col gap-1 py-4 px-3"
      style={{
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
      }}
      aria-label="Sidebar navigation"
    >
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            'flex items-center gap-3 rounded-[var(--radius-sm)] px-3 py-2 text-sm font-medium transition-colors',
            activePath === href
              ? 'bg-[var(--primary-dim)] text-[var(--primary)]'
              : 'text-[var(--text-muted)] hover:bg-[rgba(255,255,255,0.06)] hover:text-[var(--text)]'
          )}
          aria-current={activePath === href ? 'page' : undefined}
        >
          <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
          {label}
        </Link>
      ))}
    </aside>
  );
}
