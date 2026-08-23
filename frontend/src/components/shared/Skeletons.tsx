// =============================================================================
// Cortex Glass Skeletons
//
// Skeleton placeholders that match the exact layout of each panel.
// Uses the Liquid Glass design language — frosted shimmer, rounded glass.
// Zero layout shift when real data arrives.
//
// Respects prefers-reduced-motion: disables shimmer animation.
// =============================================================================

import React from 'react';

// ── Base shimmer block ────────────────────────────────────────────────────────

function Shimmer({
  width = '100%',
  height = 16,
  radius = 8,
  style,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      aria-hidden="true"
      style={{
        width,
        height,
        borderRadius: radius,
        background: 'var(--surface)',
        backgroundImage:
          'linear-gradient(90deg, transparent 0%, var(--border) 50%, transparent 100%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.7s ease-in-out infinite',
        flexShrink: 0,
        ...style,
      }}
    />
  );
}

// ── Job row skeleton ──────────────────────────────────────────────────────────

function JobRowSkeleton() {
  return (
    <div style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
      <Shimmer width={6} height={6} radius="50%" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 5 }}>
        <Shimmer width="55%" height={13} radius={6} />
        <Shimmer width="38%" height={10} radius={5} />
      </div>
      <Shimmer width={52} height={20} radius={10} />
    </div>
  );
}

// ── Sidebar jobs skeleton — shown while the jobs list loads ──────────────────

export function SidebarJobsSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {Array.from({ length: count }).map((_, i) => (
        <JobRowSkeleton key={i} />
      ))}
    </div>
  );
}

// ── Artifact panel skeleton ───────────────────────────────────────────────────

export function ArtifactSkeleton() {
  return (
    <div style={{
      borderRadius: 'var(--radius-lg)', overflow: 'hidden',
      background: 'var(--surface)',
      border: '1px solid var(--border)',
    }}>
      {/* Header strip */}
      <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Shimmer width={80} height={22} radius={100} />
        <Shimmer width={160} height={12} radius={6} />
      </div>
      {/* Content area */}
      <div style={{ padding: '20px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Shimmer width="100%" height={14} radius={6} />
        <Shimmer width="92%"  height={14} radius={6} />
        <Shimmer width="78%"  height={14} radius={6} />
        <Shimmer width="88%"  height={14} radius={6} />
        <Shimmer width="60%"  height={14} radius={6} />
        <div style={{ marginTop: 8 }} />
        <Shimmer width="100%" height={14} radius={6} />
        <Shimmer width="85%"  height={14} radius={6} />
        <Shimmer width="70%"  height={14} radius={6} />
      </div>
    </div>
  );
}

// ── Insights skeleton ─────────────────────────────────────────────────────────

function ScoreRingSkeleton() {
  return (
    <div style={{
      width: 120, height: 120, borderRadius: '50%', flexShrink: 0,
      background: 'var(--surface)',
      backgroundImage: 'linear-gradient(90deg, transparent 0%, var(--border) 50%, transparent 100%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.7s ease-in-out infinite',
    }} />
  );
}

export function InsightsSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header card */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20,
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: '20px 24px',
      }}>
        <ScoreRingSkeleton />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Shimmer width="40%" height={18} radius={7} />
          <Shimmer width="28%" height={12} radius={6} />
          <Shimmer width="55%" height={24} radius={12} />
        </div>
      </div>
      {/* Stats strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(100px,1fr))', gap: 10 }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
            <Shimmer width="60%" height={20} radius={6} />
            <Shimmer width="80%" height={10} radius={5} />
          </div>
        ))}
      </div>
      {/* Dimension cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: 10 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Shimmer width={24} height={24} radius={6} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 5 }}>
                <Shimmer width="60%" height={12} radius={5} />
                <Shimmer width="100%" height={4} radius={2} />
              </div>
            </div>
            <Shimmer width="80%" height={11} radius={5} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Graph skeleton ────────────────────────────────────────────────────────────

export function GraphSkeleton() {
  return (
    <div style={{
      height: 600, width: '100%',
      borderRadius: 12, border: '1px solid var(--border)',
      background: 'var(--surface)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Shimmer wash */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'linear-gradient(90deg, transparent 0%, var(--border) 50%, transparent 100%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 2s ease-in-out infinite',
      }} />
      {/* Fake node dots scattered around */}
      {[
        { top: '20%', left: '18%' }, { top: '35%', left: '42%' },
        { top: '55%', left: '25%' }, { top: '25%', left: '65%' },
        { top: '60%', left: '58%' }, { top: '75%', left: '38%' },
        { top: '15%', left: '80%' }, { top: '50%', left: '80%' },
      ].map((pos, i) => (
        <div key={i} style={{
          position: 'absolute', ...pos,
          width: 80, height: 34, borderRadius: 8,
          background: 'var(--surface)',
          border: '1px solid var(--border)',
        }} />
      ))}
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Building Knowledge Graph…
        </p>
      </div>
    </div>
  );
}

// ── Dashboard main panel skeleton ─────────────────────────────────────────────
// Shown on the right panel while the selected job's data loads

export function PanelSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: 24 }}>
      <ArtifactSkeleton />
    </div>
  );
}
