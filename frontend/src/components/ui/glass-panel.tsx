import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// GlassPanel — Premium layered glass surface
//
// Variants:
//   default  — standard glass card with specular top edge
//   elevated — stronger shadow + more opaque, for floating overlays/modals
//   subtle   — lighter tint for nested surfaces
//   nav      — maximum blur, pill-shaped, for floating navbars
//
// Radius: sm | md | lg | xl | full
// =============================================================================

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'subtle' | 'nav';
  radius?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  noBorder?: boolean;
}

const GlassPanel = React.forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, variant = 'default', radius = 'lg', noBorder = false, style, ...props }, ref) => {
    const radiusMap = {
      sm:   'var(--radius-sm)',
      md:   'var(--radius-md)',
      lg:   'var(--radius-lg)',
      xl:   'var(--radius-xl)',
      full: 'var(--radius-full)',
    } as const;

    const variantStyles: Record<string, React.CSSProperties> = {
      default: {
        background: 'var(--glass-card, rgba(14,18,28,0.82))',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        boxShadow: 'var(--shadow-lg), var(--edge-top), var(--edge-inner)',
      },
      elevated: {
        background: 'var(--glass-modal, rgba(11,15,24,0.94))',
        backdropFilter: 'blur(36px) saturate(210%)',
        WebkitBackdropFilter: 'blur(36px) saturate(210%)',
        boxShadow: 'var(--shadow-xl), var(--edge-top-bright), var(--edge-inner)',
      },
      subtle: {
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(8px) saturate(140%)',
        WebkitBackdropFilter: 'blur(8px) saturate(140%)',
        boxShadow: 'var(--shadow-sm), var(--edge-top)',
      },
      nav: {
        background: 'var(--glass-nav, rgba(10,13,22,0.72))',
        backdropFilter: 'blur(44px) saturate(220%)',
        WebkitBackdropFilter: 'blur(44px) saturate(220%)',
        boxShadow: 'var(--shadow-nav)',
      },
    };

    return (
      <div
        ref={ref}
        style={{
          ...variantStyles[variant],
          borderRadius: radiusMap[radius],
          border: noBorder ? 'none' : '1px solid var(--border)',
          ...style,
        }}
        className={cn('overflow-hidden', className)}
        {...props}
      />
    );
  }
);
GlassPanel.displayName = 'GlassPanel';

export { GlassPanel };
