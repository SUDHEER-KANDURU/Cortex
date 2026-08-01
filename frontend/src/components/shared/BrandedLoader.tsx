// =============================================================================
// BrandedLoader — Cortex signature loading system
//
// Exports:
//   BrandedLoader        – the core animated card (logo + message + progress)
//   FullScreenLoader     – full-viewport overlay with fade in/out
//   InlineLoader         – compact horizontal loader for panels/sections
//   PageLoader           – Next.js route loading replacement
//
// Usage:
//   <FullScreenLoader visible={isLoading} stage="building_graph" />
//   <InlineLoader message="Rendering diagram…" />
//   <BrandedLoader stage="generating_artifact" />
// =============================================================================

'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatedCortexLogo } from './AnimatedCortexLogo';

// ── Stage → Message map ───────────────────────────────────────────────────────

export type LoadingStage =
  | 'connecting'
  | 'downloading'
  | 'reading_files'
  | 'parsing'
  | 'detecting_languages'
  | 'building_graph'
  | 'analyzing_deps'
  | 'generating_artifact'
  | 'rendering_diagram'
  | 'finalizing'
  | 'loading'        // generic fallback
  | 'route_change';

const STAGE_MESSAGES: Record<LoadingStage, string> = {
  connecting:           'Connecting to GitHub…',
  downloading:          'Downloading Repository…',
  reading_files:        'Reading Files…',
  parsing:              'Parsing Source Code…',
  detecting_languages:  'Detecting Languages…',
  building_graph:       'Building Knowledge Graph…',
  analyzing_deps:       'Analyzing Dependencies…',
  generating_artifact:  'Generating Artifact…',
  rendering_diagram:    'Rendering Diagram…',
  finalizing:           'Finalizing Results…',
  loading:              'Loading…',
  route_change:         'Navigating…',
};

// ── Animated progress bar (indeterminate) ────────────────────────────────────

function IndeterminateBar() {
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 2,
        borderRadius: 9999,
        background: 'rgba(255,255,255,0.06)',
        overflow: 'hidden',
      }}
      role="progressbar"
      aria-label="Loading progress"
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: '100%',
          width: '40%',
          borderRadius: 9999,
          background: 'linear-gradient(90deg, transparent 0%, var(--primary,#00E5A8) 50%, transparent 100%)',
          animation: 'cortex-bar-sweep 1.8s cubic-bezier(0.4,0,0.2,1) infinite',
        }}
      />
    </div>
  );
}

// ── Determinate progress bar ─────────────────────────────────────────────────

interface DeterminateBarProps {
  value: number; // 0–100
}

function DeterminateBar({ value }: DeterminateBarProps) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 2,
        borderRadius: 9999,
        background: 'rgba(255,255,255,0.06)',
        overflow: 'hidden',
      }}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        style={{
          height: '100%',
          width: `${pct}%`,
          borderRadius: 9999,
          background: 'linear-gradient(90deg, var(--primary,#00E5A8), var(--accent,#6C7CFF))',
          transition: 'width 0.5s cubic-bezier(0.16,1,0.3,1)',
          boxShadow: '0 0 8px rgba(0,229,168,0.4)',
        }}
      />
    </div>
  );
}

// ── BrandedLoader (card) ─────────────────────────────────────────────────────

export interface BrandedLoaderProps {
  /** Loading stage that maps to a message */
  stage?: LoadingStage;
  /** Custom message — overrides stage message */
  message?: string;
  /** Optional determinate progress 0–100; omit for indeterminate */
  progress?: number;
  /** Extra class */
  className?: string;
  /** Logo size in px */
  logoSize?: number;
}

export function BrandedLoader({
  stage = 'loading',
  message,
  progress,
  className,
  logoSize = 56,
}: BrandedLoaderProps) {
  const displayMessage = message ?? STAGE_MESSAGES[stage];

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
        padding: '36px 32px',
        borderRadius: 'var(--radius-xl, 24px)',
        background: 'var(--card, #151922)',
        border: '1px solid var(--border, rgba(255,255,255,0.08))',
        boxShadow: 'var(--shadow-lg, 0 8px 32px rgba(0,0,0,0.6))',
        minWidth: 260,
        maxWidth: 360,
      }}
    >
      {/* Animated logo */}
      <AnimatedCortexLogo size={logoSize} />

      {/* Brand name + message */}
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <span style={{
          fontFamily: 'var(--font-display, Syne, sans-serif)',
          fontSize: 15,
          fontWeight: 700,
          letterSpacing: '-0.02em',
          color: 'var(--text, #fff)',
        }}>
          Cortex
        </span>
        <span style={{
          fontFamily: 'var(--font-mono, monospace)',
          fontSize: 11,
          letterSpacing: '0.06em',
          color: 'var(--text-muted, #7A8395)',
          textTransform: 'uppercase',
        }}>
          {displayMessage}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ width: '100%' }}>
        {progress !== undefined
          ? <DeterminateBar value={progress} />
          : <IndeterminateBar />
        }
      </div>
    </div>
  );
}

// ── FullScreenLoader ──────────────────────────────────────────────────────────

export interface FullScreenLoaderProps {
  /** When false the overlay fades out and unmounts after the transition */
  visible: boolean;
  stage?: LoadingStage;
  message?: string;
  progress?: number;
}

export function FullScreenLoader({
  visible,
  stage = 'loading',
  message,
  progress,
}: FullScreenLoaderProps) {
  const [mounted, setMounted]   = useState(visible);
  const [opacity, setOpacity]   = useState(visible ? 1 : 0);
  const timerRef                = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (visible) {
      setMounted(true);
      // Micro-delay so opacity transition fires after mount
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setOpacity(1));
      });
    } else {
      setOpacity(0);
      timerRef.current = setTimeout(() => setMounted(false), 350);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [visible]);

  if (!mounted) return null;

  return (
    <div
      aria-live="polite"
      aria-busy={visible}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg, #07090d)',
        opacity,
        transition: 'opacity 300ms ease',
        willChange: 'opacity',
      }}
    >
      <BrandedLoader stage={stage} message={message} progress={progress} />
    </div>
  );
}

// ── InlineLoader ─────────────────────────────────────────────────────────────

export interface InlineLoaderProps {
  stage?: LoadingStage;
  message?: string;
  progress?: number;
  /** px size of the logo */
  size?: number;
  className?: string;
}

export function InlineLoader({
  stage = 'loading',
  message,
  progress,
  size = 32,
  className,
}: InlineLoaderProps) {
  const displayMessage = message ?? STAGE_MESSAGES[stage];

  return (
    <div
      className={className}
      aria-live="polite"
      aria-busy={true}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 14,
        padding: '24px 16px',
      }}
    >
      <AnimatedCortexLogo size={size} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', alignItems: 'center' }}>
        <span style={{
          fontFamily: 'var(--font-mono, monospace)',
          fontSize: 11,
          letterSpacing: '0.06em',
          color: 'var(--text-muted, #7A8395)',
          textTransform: 'uppercase',
        }}>
          {displayMessage}
        </span>
        <div style={{ width: '180px' }}>
          {progress !== undefined
            ? <DeterminateBar value={progress} />
            : <IndeterminateBar />
          }
        </div>
      </div>
    </div>
  );
}

// ── PageLoader ────────────────────────────────────────────────────────────────
// Drop-in replacement for src/app/loading.tsx

export function PageLoader() {
  return (
    <div
      aria-live="polite"
      aria-busy={true}
      style={{
        minHeight: '100vh',
        background: 'var(--bg, #07090d)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <BrandedLoader stage="loading" logoSize={52} />
    </div>
  );
}
