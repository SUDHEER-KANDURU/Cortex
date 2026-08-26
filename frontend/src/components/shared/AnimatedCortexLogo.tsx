// =============================================================================
// AnimatedCortexLogo — Rotating, color-shifting Cortex brand mark
//
// • Smooth continuous rotation (~2.5s per revolution)
// • Slow chromatic sweep through emerald → cyan → electric-blue → violet → indigo → teal
// • Subtle glow that pulses with the color cycle
// • GPU-accelerated: only uses transform + filter + opacity
// • Respects prefers-reduced-motion: stops rotation, keeps gentle opacity pulse
// =============================================================================

'use client';

import React, { useEffect, useRef } from 'react';
import { CortexLogo } from './CortexLogo';

export interface AnimatedCortexLogoProps {
  /** Overall size in px */
  size?: number;
  /** Extra class on the outer wrapper */
  className?: string;
}

// ── Color palette ─────────────────────────────────────────────────────────────
// Deep navy to steel-blue tones matching the new dark primary
const COLOR_STOPS = [
  { r: 30,  g: 42,  b: 56  }, // #1E2A38 deep navy (brand primary)
  { r: 42,  g: 62,  b: 84  }, // #2A3E54 navy-steel
  { r: 58,  g: 84,  b: 112 }, // #3A5470 mid steel-blue
  { r: 42,  g: 62,  b: 84  }, // #2A3E54 back to navy-steel
  { r: 30,  g: 42,  b: 56  }, // loop back
] as const;

// Total animation duration for one full color cycle (ms)
const COLOR_CYCLE_MS = 8000;
// Rotation duration per full revolution (ms)
const ROTATION_MS   = 2500;

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function getColor(progress: number): { r: number; g: number; b: number } {
  // progress: 0..1 along the full cycle
  const scaled = progress * (COLOR_STOPS.length - 1);
  const idx    = Math.floor(scaled);
  const t      = scaled - idx;
  const from   = COLOR_STOPS[Math.min(idx,     COLOR_STOPS.length - 1)];
  const to     = COLOR_STOPS[Math.min(idx + 1, COLOR_STOPS.length - 1)];
  return {
    r: Math.round(lerp(from.r, to.r, t)),
    g: Math.round(lerp(from.g, to.g, t)),
    b: Math.round(lerp(from.b, to.b, t)),
  };
}

export function AnimatedCortexLogo({ size = 48, className }: AnimatedCortexLogoProps) {
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const rafRef     = useRef<number>(0);
  const startRef   = useRef<number | null>(null);

  useEffect(() => {
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const el = wrapperRef.current;
    if (!el) return;

    if (prefersReduced) {
      // Gentle opacity pulse only — no rotation
      el.style.animation = 'cortex-reduced-pulse 3s ease-in-out infinite';
      return;
    }

    let active = true;

    function frame(ts: number) {
      if (!active || !el) return;

      if (startRef.current === null) startRef.current = ts;
      const elapsed = ts - startRef.current;

      // ── Rotation: linear, wraps every ROTATION_MS ─────────────────
      const rotationDeg = ((elapsed % ROTATION_MS) / ROTATION_MS) * 360;

      // ── Color: interpolates through COLOR_STOPS over COLOR_CYCLE_MS ─
      const colorProgress = (elapsed % COLOR_CYCLE_MS) / COLOR_CYCLE_MS;
      const { r, g, b }   = getColor(colorProgress);

      // ── Glow intensity: very gentle (0.08 → 0.18) ────────────────
      const glowAlpha = 0.08 + 0.07 * Math.sin((elapsed / COLOR_CYCLE_MS) * Math.PI * 2);

      el.style.transform  = `rotate(${rotationDeg}deg)`;
      el.style.filter     = `drop-shadow(0 0 ${size * 0.25}px rgba(${r},${g},${b},${glowAlpha.toFixed(3)}))`;
      el.style.setProperty('--logo-color', `rgb(${r},${g},${b})`);

      // Update inner logo color via CSS variable
      const inner = el.querySelector<HTMLElement>('[data-logo-icon]');
      if (inner) inner.style.color = `rgb(${r},${g},${b})`;

      // Update inner svg strokes
      const svg = el.querySelector<SVGElement>('svg');
      if (svg) svg.setAttribute('stroke', `rgb(${r},${g},${b})`);

      rafRef.current = requestAnimationFrame(frame);
    }

    rafRef.current = requestAnimationFrame(frame);

    return () => {
      active = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [size]);

  return (
    <span
      ref={wrapperRef}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        willChange: 'transform, filter',
        transformOrigin: 'center center',
        // Initial color before rAF starts — soft slate, no neon
        filter: `drop-shadow(0 0 ${size * 0.18}px rgba(107,143,174,0.15))`,
      }}
      aria-hidden="true"
    >
      <CortexLogo
        size={size}
        iconColor="var(--primary)"
        bgColor="var(--primary-dim)"
        style={{
          boxShadow: `var(--shadow-sm)`,
        }}
      />
    </span>
  );
}
