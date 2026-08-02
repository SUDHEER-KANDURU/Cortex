'use client';

// =============================================================================
// Navbar — Premium Liquid Glass floating capsule
// Apple-style floating pill above content, deep glass, specular edge highlights
// =============================================================================

import React from 'react';
import Link from 'next/link';
import { Github, LayoutDashboard } from 'lucide-react';

export default function Navbar() {
  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 600,
        display: 'flex', justifyContent: 'center',
        padding: '14px 24px', pointerEvents: 'none',
      }}
    >
      <nav
        aria-label="Main navigation"
        style={{
          pointerEvents: 'auto',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          width: '100%', maxWidth: 840,
          padding: '7px 10px',
          borderRadius: 9999,
          background: 'var(--glass-nav, rgba(10,13,22,0.72))',
          backdropFilter: 'blur(44px) saturate(220%)',
          WebkitBackdropFilter: 'blur(44px) saturate(220%)',
          border: '1px solid var(--border, rgba(255,255,255,0.07))',
          boxShadow: 'var(--shadow-nav)',
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 px-3 py-1.5 rounded-2xl transition-colors"
          style={{ textDecoration: 'none', color: 'inherit' }}
          aria-label="Cortex — home"
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <span style={{
            width: 26, height: 26, borderRadius: 8, flexShrink: 0,
            background: 'var(--primary-dim, rgba(0,229,168,0.12))',
            border: '1px solid rgba(0,229,168,0.25)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 10px rgba(0,229,168,0.12), inset 0 1px 0 rgba(255,255,255,0.12)',
          }}>
            <LayoutDashboard style={{ width: 12, height: 12, color: 'var(--primary)' }} />
          </span>
          <span style={{
            fontSize: 14, fontWeight: 700, letterSpacing: '-0.03em',
            color: 'var(--text)',
            fontFamily: 'var(--font-sans)',
          }}>
            Cortex
          </span>
        </Link>

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <NavLink href="/dashboard">Dashboard</NavLink>
          <NavLink
            href="https://github.com/SUDHEER-KANDURU/cortex"
            external
            icon={<Github style={{ width: 14, height: 14 }} aria-hidden="true" />}
          >
            <span className="hidden sm:inline">GitHub</span>
          </NavLink>
        </div>
      </nav>
    </div>
  );
}

function NavLink({
  href, children, external, icon,
}: {
  href: string;
  children: React.ReactNode;
  external?: boolean;
  icon?: React.ReactNode;
}) {
  const props = external
    ? { target: '_blank', rel: 'noopener noreferrer' }
    : {};

  return (
    <Link
      href={href}
      {...props}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        fontSize: 13, fontWeight: 500, letterSpacing: '-0.01em',
        color: 'var(--text-muted)',
        padding: '6px 14px', borderRadius: 14,
        textDecoration: 'none',
        transition: 'background 0.18s ease, color 0.18s ease',
        fontFamily: 'var(--font-sans)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'rgba(255,255,255,0.07)';
        e.currentTarget.style.color = 'var(--text)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent';
        e.currentTarget.style.color = 'var(--text-muted)';
      }}
    >
      {icon}
      {children}
    </Link>
  );
}
