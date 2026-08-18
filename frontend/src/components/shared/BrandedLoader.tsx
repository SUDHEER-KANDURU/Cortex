// =============================================================================
// BrandedLoader — Cortex unified loading system
//
// THE single source for every loading state in the application.
// No Loader2. No animate-spin. No LoadingSpinner. Only the Cortex logo.
//
// Exports:
//   BrandedLoader         – core animated card (logo + message + progress bar)
//   InlineLoader          – compact centred loader for panels and sections
//   FullScreenLoader      – full-viewport overlay with fade in/out
//   PageLoader            – Next.js route loading.tsx replacement
//   TransitionOverlay     – page-transition overlay (Landing → Dashboard, etc.)
//   SlowRequestIndicator  – auto-shows after 400 ms if a request is still in-flight
//   CortexSkeleton        – generic skeleton block that matches layout exactly
//   ButtonSpinner         – tiny inline Cortex logo for loading buttons
//
// Usage:
//   <FullScreenLoader visible={loading} stage="building_graph" />
//   <InlineLoader stage="generating_artifact" />
//   <TransitionOverlay visible={navigating} />
//   <SlowRequestIndicator isLoading={isFetching} />
//   <CortexSkeleton width="100%" height={160} />
//   <ButtonSpinner />   ← inside a button while isSubmitting
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
  | 'loading'
  | 'route_change'
  | 'submitting'
  | 'thinking'
  | 'transition'
  | 'computing_insights'
  | 'slow_request';

const STAGE_MESSAGES: Record<LoadingStage, string> = {
  connecting:          'Connecting to GitHub…',
  downloading:         'Downloading Repository…',
  reading_files:       'Reading Files…',
  parsing:             'Parsing Source Code…',
  detecting_languages: 'Detecting Languages…',
  building_graph:      'Building Knowledge Graph…',
  analyzing_deps:      'Analyzing Dependencies…',
  generating_artifact: 'Generating Artifact…',
  rendering_diagram:   'Rendering Diagram…',
  finalizing:          'Finalizing Results…',
  loading:             'Loading…',
  route_change:        'Navigating…',
  submitting:          'Submitting Repository…',
  thinking:            'Understanding Repository…',
  transition:          'Opening Cortex…',
  computing_insights:  'Computing Engineering Insights…',
  slow_request:        'Waiting for Response…',
};

// ── Rotating transition messages ──────────────────────────────────────────────

const TRANSITION_MESSAGES = [
  'Opening Cortex…',
  'Loading Workspace…',
  'Preparing Dashboard…',
  'Building Knowledge Graph…',
  'Understanding Repository…',
  'Reasoning About Code…',
  'Optimizing Experience…',
  'Almost Ready…',
];

// ── Indeterminate progress bar ────────────────────────────────────────────────

function IndeterminateBar() {
  return (
    <div
      style={{
        position: 'relative', width: '100%', height: 2,
        borderRadius: 9999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
      }}
      role="progressbar" aria-label="Loading" aria-valuemin={0} aria-valuemax={100}
    >
      <div style={{
        position: 'absolute', top: 0, left: 0, height: '100%', width: '40%',
        borderRadius: 9999,
        background: 'linear-gradient(90deg, transparent 0%, var(--primary,#00E5A8) 50%, transparent 100%)',
        animation: 'cortex-bar-sweep 1.8s cubic-bezier(0.4,0,0.2,1) infinite',
      }} />
    </div>
  );
}

// ── Determinate progress bar ──────────────────────────────────────────────────

function DeterminateBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div
      style={{
        position: 'relative', width: '100%', height: 2,
        borderRadius: 9999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
      }}
      role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
    >
      <div style={{
        height: '100%', width: `${pct}%`, borderRadius: 9999,
        background: 'linear-gradient(90deg, var(--primary,#00E5A8), var(--accent,#6C7CFF))',
        transition: 'width 0.5s cubic-bezier(0.16,1,0.3,1)',
        boxShadow: '0 0 8px rgba(0,229,168,0.4)',
      }} />
    </div>
  );
}

// ── BrandedLoader (card) ──────────────────────────────────────────────────────

export interface BrandedLoaderProps {
  stage?: LoadingStage;
  message?: string;
  progress?: number;
  className?: string;
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
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20,
        padding: '36px 32px',
        borderRadius: 'var(--radius-xl, 26px)',
        background: 'var(--glass-card, rgba(14,18,28,0.88))',
        border: '1px solid var(--border, rgba(255,255,255,0.07))',
        boxShadow: 'var(--shadow-xl), var(--edge-top), var(--edge-inner)',
        backdropFilter: 'blur(32px) saturate(200%)',
        WebkitBackdropFilter: 'blur(32px) saturate(200%)',
        minWidth: 260, maxWidth: 360,
      }}
    >
      <AnimatedCortexLogo size={logoSize} />
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <span style={{
          fontFamily: 'var(--font-display, Syne, sans-serif)',
          fontSize: 15, fontWeight: 700, letterSpacing: '-0.03em',
          color: 'var(--text, #F0F4FF)',
        }}>
          Cortex
        </span>
        <span style={{
          fontFamily: 'var(--font-mono, "JetBrains Mono", monospace)',
          fontSize: 11, letterSpacing: '0.07em',
          color: 'var(--text-muted, #6E7A90)', textTransform: 'uppercase',
        }}>
          {displayMessage}
        </span>
      </div>
      <div style={{ width: '100%' }}>
        {progress !== undefined ? <DeterminateBar value={progress} /> : <IndeterminateBar />}
      </div>
    </div>
  );
}

// ── FullScreenLoader ──────────────────────────────────────────────────────────

export interface FullScreenLoaderProps {
  visible: boolean;
  stage?: LoadingStage;
  message?: string;
  progress?: number;
}

export function FullScreenLoader({ visible, stage = 'loading', message, progress }: FullScreenLoaderProps) {
  const [mounted, setMounted] = useState(visible);
  const [opacity, setOpacity] = useState(visible ? 1 : 0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (visible) {
      setMounted(true);
      requestAnimationFrame(() => requestAnimationFrame(() => setOpacity(1)));
    } else {
      setOpacity(0);
      timerRef.current = setTimeout(() => setMounted(false), 350);
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [visible]);

  if (!mounted) return null;

  return (
    <div
      aria-live="polite" aria-busy={visible}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg, #060810)',
        opacity, transition: 'opacity 300ms ease', willChange: 'opacity',
      }}
    >
      <BrandedLoader stage={stage} message={message} progress={progress} />
    </div>
  );
}

// ── InlineLoader ──────────────────────────────────────────────────────────────

export interface InlineLoaderProps {
  stage?: LoadingStage;
  message?: string;
  progress?: number;
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
      aria-live="polite" aria-busy={true}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 14, padding: '24px 16px',
      }}
    >
      <AnimatedCortexLogo size={size} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', alignItems: 'center' }}>
        <span style={{
          fontFamily: 'var(--font-mono, "JetBrains Mono", monospace)',
          fontSize: 11, letterSpacing: '0.07em',
          color: 'var(--text-muted, #6E7A90)', textTransform: 'uppercase',
        }}>
          {displayMessage}
        </span>
        <div style={{ width: 180 }}>
          {progress !== undefined ? <DeterminateBar value={progress} /> : <IndeterminateBar />}
        </div>
      </div>
    </div>
  );
}

// ── PageLoader ────────────────────────────────────────────────────────────────

export function PageLoader() {
  return (
    <div
      aria-live="polite" aria-busy={true}
      style={{
        minHeight: '100vh',
        background: 'var(--bg, #060810)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <BrandedLoader stage="loading" logoSize={52} />
    </div>
  );
}

// ── TransitionOverlay ─────────────────────────────────────────────────────────
// Premium page-transition overlay. Use for:
//   - Landing → Dashboard (Open App click)
//   - Any route change that requires data loading
//   - Long navigation sequences

export interface TransitionOverlayProps {
  visible: boolean;
  message?: string;
}

export function TransitionOverlay({ visible, message }: TransitionOverlayProps) {
  const [mounted, setMounted] = useState(visible);
  const [opacity, setOpacity] = useState(visible ? 1 : 0);
  const [msgIndex, setMsgIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cycleRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (visible) {
      setMounted(true);
      setMsgIndex(0);
      requestAnimationFrame(() => requestAnimationFrame(() => setOpacity(1)));
      cycleRef.current = setInterval(() => {
        setMsgIndex(i => (i + 1) % TRANSITION_MESSAGES.length);
      }, 1800);
    } else {
      setOpacity(0);
      timerRef.current = setTimeout(() => setMounted(false), 350);
      if (cycleRef.current) clearInterval(cycleRef.current);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (cycleRef.current) clearInterval(cycleRef.current);
    };
  }, [visible]);

  if (!mounted) return null;

  const displayMsg = message ?? TRANSITION_MESSAGES[msgIndex];

  return (
    <div
      aria-live="assertive" aria-busy={visible} aria-label={displayMsg}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg, #060810)',
        opacity, transition: 'opacity 300ms ease', willChange: 'opacity',
      }}
    >
      <BrandedLoader stage="transition" message={displayMsg} logoSize={52} />
    </div>
  );
}

// ── SlowRequestIndicator ──────────────────────────────────────────────────────
// Renders nothing until the request has been in-flight longer than `delay` ms.
// Prevents the flash of a loader for fast requests (<400ms).

export interface SlowRequestIndicatorProps {
  isLoading: boolean;
  delay?: number;
  stage?: LoadingStage;
  message?: string;
  size?: number;
}

export function SlowRequestIndicator({
  isLoading,
  delay = 400,
  stage = 'slow_request',
  message,
  size = 24,
}: SlowRequestIndicatorProps) {
  const [show, setShow] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isLoading) {
      timerRef.current = setTimeout(() => setShow(true), delay);
    } else {
      if (timerRef.current) clearTimeout(timerRef.current);
      setShow(false);
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [isLoading, delay]);

  if (!show) return null;
  return <InlineLoader stage={stage} message={message} size={size} />;
}

// ── CortexSkeleton ────────────────────────────────────────────────────────────
// A layout-preserving skeleton block. Use where data will arrive shortly
// and you want zero layout shift when it does.

export interface CortexSkeletonProps {
  width?: number | string;
  height?: number | string;
  borderRadius?: number | string;
  className?: string;
  style?: React.CSSProperties;
}

export function CortexSkeleton({
  width = '100%',
  height = 20,
  borderRadius = 8,
  className,
  style,
}: CortexSkeletonProps) {
  return (
    <div
      className={className}
      aria-hidden="true"
      style={{
        width,
        height,
        borderRadius,
        background: 'rgba(255,255,255,0.05)',
        backgroundImage:
          'linear-gradient(90deg, rgba(255,255,255,0.0) 0%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.0) 100%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.7s ease-in-out infinite',
        flexShrink: 0,
        ...style,
      }}
    />
  );
}

// ── ButtonSpinner ─────────────────────────────────────────────────────────────
// A tiny Cortex logo for use inside buttons while isSubmitting/isLoading.
// Replaces Loader2 and animate-spin everywhere.

export interface ButtonSpinnerProps {
  size?: number;
}

export function ButtonSpinner({ size = 14 }: ButtonSpinnerProps) {
  return (
    <span
      aria-hidden="true"
      style={{ display: 'inline-flex', flexShrink: 0, lineHeight: 0 }}
    >
      <AnimatedCortexLogo size={size} />
    </span>
  );
}
