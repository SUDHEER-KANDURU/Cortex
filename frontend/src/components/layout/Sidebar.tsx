// =============================================================================
// Sidebar — Optional collapsible sidebar for future navigation items
// Currently a stub; ready to be extended with route-based highlighting.
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { LayoutDashboard, Briefcase, GitGraph } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface SidebarProps {
  /** Currently active route path for highlighting */
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
      className="hidden md:flex w-56 shrink-0 flex-col gap-1 border-r border-gray-800 bg-gray-900 py-4 px-3"
      aria-label="Sidebar navigation"
    >
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
            activePath === href
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
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
