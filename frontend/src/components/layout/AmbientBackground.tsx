'use client';

// =============================================================================
// AmbientBackground — client wrapper that mounts the WebGL fluid atmosphere.
//
// Responsibilities (kept out of the shader itself so it stays a dumb renderer):
//   • Watch the `data-ambient` tier on <html> (set by AmbientController) and
//     map it to shader params — one system, per-route intensity only.
//   • Watch `prefers-reduced-motion`; when reduced, speed → 0 so the atmosphere
//     freezes mid-flow rather than disappearing.
//   • Guard for WebGL support. If unavailable, render nothing and let the CSS
//     gradient base (.cx-ambient in globals.css) show through unchanged.
//   • Dynamically import the R3F canvas so three.js stays out of the server
//     bundle and only loads on the client after mount.
//
// The deep espresso base gradient + readability scrim remain pure CSS in
// globals.css and sit under / over this canvas respectively.
// =============================================================================

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import type { AmbientParams } from './AmbientCanvas';
import type { AmbientTier } from './AmbientController';

const AmbientCanvas = dynamic(() => import('./AmbientCanvas'), { ssr: false });

// Per-tier shader parameters. Every tier flows (speed > 0) except when reduced
// motion is on. Landing is the most expressive; app restrained but alive; calm
// / quiet quieter still. Warm palette + saturation are shared; only intensity,
// speed and morph amount change.
// warp = reach multiplier; the shader's base reach (~1.55-1.9) already
// matches the measured screen-diagonal falloff at warp=1. speed scales the
// breathing/drift cycle (0 = frozen for reduced motion).
const TIER_PARAMS: Record<AmbientTier, AmbientParams> = {
  landing: { opacity: 1.0,  sat: 1.0,  speed: 1.0, warp: 1.08 },
  app:     { opacity: 0.72, sat: 0.9,  speed: 0.8, warp: 1.0 },
  calm:    { opacity: 0.5,  sat: 0.78, speed: 0.6, warp: 0.94 },
  quiet:   { opacity: 0.32, sat: 0.66, speed: 0.45, warp: 0.88 },
};

function readTier(): AmbientTier {
  if (typeof document === 'undefined') return 'app';
  const t = document.documentElement.getAttribute('data-ambient');
  if (t === 'landing' || t === 'app' || t === 'calm' || t === 'quiet') return t;
  return 'app';
}

function hasWebGL(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const c = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext('webgl') || c.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

export function AmbientBackground() {
  const [supported, setSupported] = useState(false);
  const [tier, setTier] = useState<AmbientTier>('app');
  const [reduced, setReduced] = useState(false);

  // WebGL capability check (client only).
  useEffect(() => {
    setSupported(hasWebGL());
  }, []);

  // Track prefers-reduced-motion.
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  // Track the data-ambient tier: AmbientController mutates the attribute on
  // <html>, so observe it rather than re-deriving the route here.
  useEffect(() => {
    setTier(readTier());
    const obs = new MutationObserver(() => setTier(readTier()));
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-ambient'],
    });
    return () => obs.disconnect();
  }, []);

  if (!supported) return null; // CSS gradient base remains visible

  const base = TIER_PARAMS[tier];
  const params: AmbientParams = reduced ? { ...base, speed: 0 } : base;

  return <AmbientCanvas params={params} />;
}
