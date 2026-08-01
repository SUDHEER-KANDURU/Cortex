// =============================================================================
// CortexLogo — The Cortex brand mark
//
// A tilted rounded square with the LayoutDashboard grid icon inside.
// This is the exact same logo mark used in the Header and Footer,
// extracted into a reusable primitive so the loader can animate it.
// =============================================================================

'use client';

import React from 'react';

export interface CortexLogoProps {
  /** px size of the bounding box */
  size?: number;
  /** Override icon color — defaults to the brand green */
  iconColor?: string;
  /** Override background color */
  bgColor?: string;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * The 4-square grid SVG that makes up the Cortex icon —
 * identical to lucide-react's LayoutDashboard but inlined so we
 * can size it precisely and keep the loader zero-dependency.
 */
function GridIcon({ size, color }: { size: number; color: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* LayoutDashboard paths */}
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

export function CortexLogo({
  size = 26,
  iconColor = '#00ff87',
  bgColor = 'rgba(255,255,255,0.10)',
  className,
  style,
}: CortexLogoProps) {
  const iconSize = Math.round(size * 0.46);
  const radius = Math.round(size * 0.31);

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        borderRadius: radius,
        background: bgColor,
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.15)',
        flexShrink: 0,
        ...style,
      }}
    >
      <GridIcon size={iconSize} color={iconColor} />
    </span>
  );
}
