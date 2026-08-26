'use client';

// =============================================================================
// DashboardLink — drop-in for every "Open App" / "Launch App" CTA
//
// On hover   → prefetches /dashboard so the route bundle is warm before click
// On click   → shows TransitionOverlay while Next.js navigates
// Result     → navigation feels near-instant
// =============================================================================

import React, { useState, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import { TransitionOverlay } from './BrandedLoader';

interface DashboardLinkProps extends Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  children: React.ReactNode;
}

export function DashboardLink({ children, onClick, onMouseEnter, onMouseLeave, ...rest }: DashboardLinkProps) {
  const router = useRouter();
  const [transitioning, setTransitioning] = useState(false);
  const prefetchedRef = useRef(false);

  // Prefetch on first hover — only once per mount, fires immediately
  const handleMouseEnter = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      if (!prefetchedRef.current) {
        prefetchedRef.current = true;
        router.prefetch('/dashboard');
      }
      onMouseEnter?.(e);
    },
    [router, onMouseEnter],
  );

  const handleMouseLeave = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      onMouseLeave?.(e);
    },
    [onMouseLeave],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      // Let modifier-key clicks (new tab, etc.) pass through normally
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

      e.preventDefault();
      onClick?.(e);

      setTransitioning(true);
      // Navigate after one rAF so the overlay renders before the route swap
      requestAnimationFrame(() => {
        router.push('/dashboard');
      });
    },
    [router, onClick],
  );

  // Portal the overlay to document.body so it is never a descendant of any
  // element with backdrop-filter / transform / will-change (which would create
  // a new containing block and break position:fixed centering).
  const overlay =
    typeof document !== 'undefined'
      ? createPortal(<TransitionOverlay visible={transitioning} />, document.body)
      : null;

  return (
    <>
      {overlay}
      <a
        href="/dashboard"
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        {...rest}
      >
        {children}
      </a>
    </>
  );
}
