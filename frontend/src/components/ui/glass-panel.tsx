import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// GlassPanel — the canonical glass surface for the Cortex design system.
//
// Use this for: cards, sidebars, modals, dropdowns, floating panels.
// All glass surfaces in the app should use this component or the
// .glass-panel CSS class, which mirrors the same values.
//
// Variants:
//   default  — standard glass (dark: 72% opacity dark, light: 72% white)
//   elevated — stronger shadow + slightly more opaque surface
//   subtle   — lighter background, used for nested glass surfaces
// =============================================================================

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'subtle';
  radius?: 'sm' | 'md' | 'lg' | 'xl';
  noBorder?: boolean;
}

const GlassPanel = React.forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, variant = 'default', radius = 'lg', noBorder = false, ...props }, ref) => {
    const radiusMap = {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
      lg: 'var(--radius-lg)',
      xl: 'var(--radius-xl)',
    } as const;

    const variantStyles: Record<string, React.CSSProperties> = {
      default: {
        background: 'var(--glass)',
        backdropFilter: 'blur(18px) saturate(160%)',
        WebkitBackdropFilter: 'blur(18px) saturate(160%)',
        boxShadow: 'var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.06)',
      },
      elevated: {
        background: 'var(--glass)',
        backdropFilter: 'blur(32px) saturate(200%)',
        WebkitBackdropFilter: 'blur(32px) saturate(200%)',
        boxShadow: 'var(--shadow-xl), inset 0 1px 0 rgba(255,255,255,0.09)',
      },
      subtle: {
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(8px) saturate(130%)',
        WebkitBackdropFilter: 'blur(8px) saturate(130%)',
        boxShadow: 'var(--shadow-sm)',
      },
    };

    return (
      <div
        ref={ref}
        style={{
          ...variantStyles[variant],
          borderRadius: radiusMap[radius],
          border: noBorder ? 'none' : '1px solid var(--border)',
        }}
        className={cn('overflow-hidden', className)}
        {...props}
      />
    );
  }
);
GlassPanel.displayName = 'GlassPanel';

export { GlassPanel };
