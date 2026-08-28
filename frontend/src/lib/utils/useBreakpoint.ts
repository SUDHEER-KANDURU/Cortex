/**
 * useBreakpoint — viewport-width aware hooks for inline-style layouts
 *
 * The Cortex product surface is built with inline `style={{}}` objects that
 * cannot use Tailwind's `sm:/md:/lg:` prefixes. These hooks expose the same
 * breakpoints to JS so components can switch layout (stack vs. side-by-side,
 * drawer vs. fixed sidebar, etc.) at the right width.
 *
 * Breakpoints mirror Tailwind defaults:
 *   sm 640  ·  md 768  ·  lg 1024  ·  xl 1280
 *
 * SSR-safe: returns `false` on the server / first paint, then updates after
 * mount. Components that must avoid a hydration flash should gate on a
 * `mounted` flag where one already exists.
 */
'use client';

import { useEffect, useState } from 'react';

/** Reactively evaluate a CSS media query. Returns false during SSR. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia(query);
    setMatches(mq.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

/** True below the `md` (768px) breakpoint — phones and small tablets portrait. */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}

/** True from `md` up to `lg` (768–1023px) — tablets. */
export function useIsTablet(): boolean {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
}

/** True below the `lg` (1024px) breakpoint — mobile + tablet combined. */
export function useIsCompact(): boolean {
  return useMediaQuery('(max-width: 1023px)');
}
