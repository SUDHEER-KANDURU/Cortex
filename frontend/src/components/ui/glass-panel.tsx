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
        background: 'var(--glass-card)',
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
        boxShadow: 'var(--shadow-lg), var(--edge-top)',
      },
      elevated: {
        background: 'var(--glass-modal)',
        backdropFilter: 'blur(32px) saturate(180%)',
        WebkitBackdropFilter: 'blur(32px) saturate(180%)',
        boxShadow: 'var(--shadow-xl), var(--edge-top-bright)',
      },
      subtle: {
        // Token-driven: light = near-white, dark = near-black
        background: 'var(--surface)',
        backdropFilter: 'blur(8px) saturate(140%)',
        WebkitBackdropFilter: 'blur(8px) saturate(140%)',
        boxShadow: 'var(--shadow-sm), var(--edge-top)',
      },
      nav: {
        background: 'var(--glass-nav)',
        backdropFilter: 'blur(44px) saturate(200%)',
        WebkitBackdropFilter: 'blur(44px) saturate(200%)',
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
