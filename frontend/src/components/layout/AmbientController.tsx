'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

export type AmbientTier = 'landing' | 'app' | 'calm' | 'quiet';

// -----------------------------------------------------------------------------
// AmbientController owns the `data-ambient` attribute on <html>, which selects
// the background intensity tier in globals.css. One source of truth so the
// whole app shares a single atmospheric system rather than a bespoke effect
// per screen.
//
// Tier is resolved as: highest-priority active OVERRIDE (pushed by screens via
// useAmbientTier) else the ROUTE default. Overrides are ref-counted on a stack
// so nested requests (a dialog opening on a calm tab) restore correctly.
// -----------------------------------------------------------------------------

// Priority: higher wins when multiple overrides are active at once.
const TIER_PRIORITY: Record<AmbientTier, number> = {
  landing: 0,
  app: 1,
  calm: 2,
  quiet: 3,
};

// Active overrides, most-recent last. Kept module-level so multiple mounted
// screens/dialogs coordinate through one shared stack.
const overrides: AmbientTier[] = [];
let routeTier: AmbientTier = 'app';

function resolveTier(): AmbientTier {
  let winner = routeTier;
  for (const t of overrides) {
    if (TIER_PRIORITY[t] > TIER_PRIORITY[winner]) winner = t;
  }
  return winner;
}

function apply() {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-ambient', resolveTier());
}

/** Map a pathname to its base tier. Landing gets the expressive atmosphere;
 *  the app shell and everything under it defaults to restrained. */
function tierForPath(pathname: string | null): AmbientTier {
  if (!pathname) return 'app';
  if (pathname === '/') return 'landing';
  // Marketing / legal pages share the landing atmosphere.
  if (
    pathname.startsWith('/privacy') ||
    pathname.startsWith('/terms')
  ) {
    return 'landing';
  }
  // Auth screens are simple and centered — keep them calm and readable.
  if (
    pathname.startsWith('/login') ||
    pathname.startsWith('/signup') ||
    pathname.startsWith('/forgot-password') ||
    pathname.startsWith('/reset-password') ||
    pathname.startsWith('/verify-email')
  ) {
    return 'calm';
  }
  // Dashboard, jobs, graph and any other app route → restrained.
  return 'app';
}

/**
 * Mount once near the app root. Keeps `data-ambient` in sync with the route.
 */
export function AmbientController() {
  const pathname = usePathname();

  useEffect(() => {
    routeTier = tierForPath(pathname);
    apply();
  }, [pathname]);

  return null;
}

/** Imperatively push an override tier. Returns a disposer that removes it. */
export function pushAmbientTier(tier: AmbientTier): () => void {
  overrides.push(tier);
  apply();
  let disposed = false;
  return () => {
    if (disposed) return;
    disposed = true;
    const i = overrides.lastIndexOf(tier);
    if (i !== -1) overrides.splice(i, 1);
    apply();
  };
}

/**
 * Request an ambient tier for as long as the calling component is mounted
 * (and `active` is true). On unmount / deactivation the previous tier is
 * restored automatically. Use `calm` for data-dense views (Insights,
 * Artifacts, Graph, Navigate, Chat) and `quiet` while a dialog is open.
 */
export function useAmbientTier(tier: AmbientTier, active = true) {
  useEffect(() => {
    if (!active) return;
    const dispose = pushAmbientTier(tier);
    return dispose;
  }, [tier, active]);
}
