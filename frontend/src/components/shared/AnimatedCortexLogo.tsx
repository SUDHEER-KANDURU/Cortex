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
// Elegant brand-safe sequence: no red, yellow, orange, rainbow
const COLOR_STOPS = [
  { r: 0,   g: 229, b: 168 }, // #00E5A8 emerald (brand primary)
  { r: 0,   g: 210, b: 255 }, // #00D2FF cyan
  { r: 80,  g: 160, b: 255 }, // #50A0FF electric blue
  { r: 108, g: 124, b: 255 }, // #6C7CFF indigo (brand accent)
  { r: 160, g: 100, b: 255 }, // #A064FF violet
  { r: 80,  g: 200, b: 240 }, // #50C8F0 teal
  { r: 0,   g: 229, b: 168 }, // loop back to emerald
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

      // ── Glow intensity: gentle sine wave (0.15 → 0.35) ────────────
      const glowAlpha = 0.15 + 0.12 * Math.sin((elapsed / COLOR_CYCLE_MS) * Math.PI * 2);

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
        // Initial color before rAF starts
        filter: `drop-shadow(0 0 ${size * 0.25}px rgba(0,229,168,0.18))`,
      }}
      aria-hidden="true"
    >
      <CortexLogo
        size={size}
        iconColor="#00E5A8"
        bgColor="rgba(0,229,168,0.12)"
        style={{
          boxShadow: `inset 0 1px 0 rgba(255,255,255,0.15), 0 0 ${size * 0.3}px rgba(0,229,168,0.08)`,
        }}
      />
    </span>
  );
}
