/**
 * Cortex Motion System — v2
 * ─────────────────────────────────────────────────────────────────
 * Single source of truth for all animation variants, spring configs,
 * duration tokens, easing curves, and utility helpers.
 *
 * Motion Hierarchy:
 *  Micro   120–180 ms  button press, icon hover, badge pop
 *  Fast    180–250 ms  tooltip, chip, nav hover states
 *  Medium  280–350 ms  card enter, tab slide, modal open
 *  Major   450–700 ms  page transitions, hero entrance
 *  Slow    800+ ms     section reveals, ambient blobs
 *
 * Principles:
 *  - Every animation is purposeful — it communicates state or guides attention
 *  - Spring physics for interactive elements; easing for choreographed sequences
 *  - prefers-reduced-motion honoured via reduceMotion() / useMotion() hook
 *  - Only safe properties: opacity, transform (translate/scale/rotate), filter
 *  - All timings map to the hierarchy above — no arbitrary values
 *
 * Usage:
 *  import { fadeUp, SPRING, staggerContainer } from '@/lib/utils/motion'
 *  const { rv } = useMotion()  // rv() collapses variants when reduced-motion
 */

import type { Variants, Transition } from 'framer-motion'

// ─────────────────────────────────────────────────────────────────────────────
// DURATION TOKENS (seconds)
// ─────────────────────────────────────────────────────────────────────────────
export const DURATION = {
  /** Micro: button press, icon hover — 120 ms */
  micro:  0.12,
  /** Fast: tooltip, badge, chip appear — 180 ms */
  fast:   0.18,
  /** Medium: card enter, tab slide, dropdown — 300 ms */
  medium: 0.30,
  /** Reveal: section entrance, whileInView stagger — 650 ms */
  reveal: 0.65,
  /** Major: page transitions, hero — 550 ms */
  major:  0.55,
  /** Slow: background blobs, ambient — 900 ms */
  slow:   0.90,
} as const

// ─────────────────────────────────────────────────────────────────────────────
// EASING CURVES
// ─────────────────────────────────────────────────────────────────────────────
export const EASE = {
  /** Apple-style — snappy, slightly springy exit */
  out:     [0.16, 1, 0.3, 1]         as [number, number, number, number],
  /** Smooth ease-in-out for ambient / background motion */
  inOut:   [0.45, 0.05, 0.55, 0.95]  as [number, number, number, number],
  /** Snappy snap-in for UI elements */
  snap:    [0.25, 0.46, 0.45, 0.94]  as [number, number, number, number],
  /** Standard ease-out */
  easeOut: [0.0, 0.0, 0.2, 1.0]      as [number, number, number, number],
  /** Anticipation: slight pull-back before release */
  back:    [0.34, 1.56, 0.64, 1]     as [number, number, number, number],
} as const

// ─────────────────────────────────────────────────────────────────────────────
// SPRING PRESETS
// ─────────────────────────────────────────────────────────────────────────────
export const SPRING = {
  /**
   * Snappy — buttons, magnetic pull, icon hover, small pop
   * Resolves in ~180 ms with zero overshoot
   */
  snappy: {
    type:      'spring',
    stiffness: 480,
    damping:   32,
    mass:      0.8,
  } as Transition,

  /**
   * Default — cards, panels, general UI entrance
   * Slightly more organic; resolves in ~260 ms
   */
  default: {
    type:      'spring',
    stiffness: 340,
    damping:   28,
    mass:      1,
  } as Transition,

  /**
   * Gentle — nav pill slide, tab indicator, drawer
   * Smooth and purposeful; resolves in ~350 ms
   */
  gentle: {
    type:      'spring',
    stiffness: 260,
    damping:   26,
    mass:      1,
  } as Transition,

  /**
   * Bouncy — checkmarks, success states, notification badge
   * Brief, satisfying overshoot
   */
  bouncy: {
    type:      'spring',
    stiffness: 500,
    damping:   20,
    mass:      0.6,
  } as Transition,

  /**
   * Elastic — magnetic return, card release
   * Larger overshoot for tactile release feeling
   */
  elastic: {
    type:      'spring',
    stiffness: 200,
    damping:   14,
    mass:      1,
  } as Transition,

  /**
   * Stiff — progress bar fill, counter tick
   * Near-instant with minimal ringing
   */
  stiff: {
    type:      'spring',
    stiffness: 600,
    damping:   40,
    mass:      0.7,
  } as Transition,
} as const

// ─────────────────────────────────────────────────────────────────────────────
// FRAMER MOTION VARIANTS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * fadeUp — section entrance reveal
 * Combines opacity, vertical translate, and blur for premium depth
 */
export const fadeUp: Variants = {
  hidden: {
    opacity: 0,
    y:       32,
    filter:  'blur(4px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.reveal,
      ease:     EASE.out,
    },
  },
}

/**
 * fadeIn — simple opacity only (overlays, indicators, secondary elements)
 */
export const fadeIn: Variants = {
  hidden:  { opacity: 0 },
  visible: {
    opacity:    1,
    transition: { duration: DURATION.medium, ease: EASE.easeOut },
  },
}

/**
 * fadeDown — items that drop in from above (notifications, toasts)
 */
export const fadeDown: Variants = {
  hidden:  { opacity: 0, y: -20, filter: 'blur(3px)' },
  visible: {
    opacity:    1,
    y:          0,
    filter:     'blur(0px)',
    transition: { duration: DURATION.medium, ease: EASE.out },
  },
}

/**
 * scaleIn — modals, popovers, context menus
 * Springs open, eases closed
 */
export const scaleIn: Variants = {
  hidden: {
    opacity: 0,
    scale:   0.90,
    y:       8,
    filter:  'blur(2px)',
  },
  visible: {
    opacity: 1,
    scale:   1,
    y:       0,
    filter:  'blur(0px)',
    transition: SPRING.snappy,
  },
  exit: {
    opacity: 0,
    scale:   0.95,
    y:       4,
    filter:  'blur(1px)',
    transition: { duration: DURATION.fast, ease: EASE.snap },
  },
}

/**
 * heroWord — hero headline word-by-word reveal
 * Uses custom index for staggered delays
 */
export const heroWord: Variants = {
  hidden: {
    opacity: 0,
    y:       18,
    filter:  'blur(20px)',
  },
  visible: (i: number) => ({
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: {
      duration: 0.75,
      delay:    i * 0.085,
      ease:     EASE.out,
    },
  }),
}

/**
 * heroLine — hero headline line-by-line reveal (for multi-line headings)
 */
export const heroLine: Variants = {
  hidden: {
    opacity: 0,
    y:       24,
    filter:  'blur(8px)',
    clipPath: 'inset(0 0 100% 0)',
  },
  visible: (i: number) => ({
    opacity:  1,
    y:        0,
    filter:   'blur(0px)',
    clipPath: 'inset(0 0 0% 0)',
    transition: {
      duration: 0.65,
      delay:    i * 0.12,
      ease:     EASE.out,
    },
  }),
}

/**
 * staggerContainer — orchestrates children with delay offsets
 * Pair with staggerChild for list animations
 */
export const staggerContainer: Variants = {
  hidden:  {},
  visible: {
    transition: {
      staggerChildren:  0.07,
      delayChildren:    0.1,
    },
  },
}

/**
 * staggerChild — pairs with staggerContainer
 */
export const staggerChild: Variants = {
  hidden: {
    opacity: 0,
    y:       20,
    filter:  'blur(2px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.reveal,
      ease:     EASE.out,
    },
  },
}

/**
 * staggerFast — tighter stagger for dense grids (cards, grid items)
 */
export const staggerFastContainer: Variants = {
  hidden:  {},
  visible: {
    transition: {
      staggerChildren: 0.05,
      delayChildren:   0.05,
    },
  },
}

export const staggerFastChild: Variants = {
  hidden: {
    opacity: 0,
    y:       16,
    scale:   0.96,
  },
  visible: {
    opacity: 1,
    y:       0,
    scale:   1,
    transition: {
      duration: DURATION.medium,
      ease:     EASE.out,
    },
  },
}

/**
 * cardHover — spring lift with subtle scale
 * Use on card wrapper with whileHover
 */
export const cardHover = {
  y:          -6,
  scale:      1.01,
  transition: SPRING.snappy,
}

/**
 * cardTap — compress on click
 */
export const cardTap = {
  scale:      0.98,
  transition: { duration: DURATION.micro },
}

/**
 * buttonHover — CTA lift
 */
export const buttonHover = {
  y:          -3,
  transition: SPRING.snappy,
}

/**
 * buttonTap — satisfying press down
 */
export const buttonTap = {
  scale:      0.96,
  y:          1,
  transition: { duration: DURATION.micro, ease: EASE.snap },
}

/**
 * iconHoverRotate — icon subtle rotate on hover (nav icons, etc.)
 */
export const iconHoverRotate = {
  rotate:     8,
  scale:      1.12,
  transition: SPRING.snappy,
}

/**
 * navUnderline — underline expand for nav links
 */
export const navUnderline: Variants = {
  rest:  { scaleX: 0, opacity: 0, originX: 0 },
  hover: {
    scaleX:     1,
    opacity:    1,
    transition: { duration: DURATION.medium, ease: EASE.out },
  },
}

/**
 * pageEnter — route transition
 * Used by the PageTransition wrapper component
 */
export const pageEnter: Variants = {
  hidden: {
    opacity: 0,
    y:       18,
    filter:  'blur(3px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.major,
      ease:     EASE.out,
    },
  },
  exit: {
    opacity: 0,
    y:       -12,
    filter:  'blur(2px)',
    transition: {
      duration: DURATION.medium,
      ease:     EASE.snap,
    },
  },
}

/**
 * panelSlideRight — right panel / sidebar enter
 */
export const panelSlideRight: Variants = {
  hidden: {
    opacity: 0,
    x:       40,
    filter:  'blur(4px)',
  },
  visible: {
    opacity: 1,
    x:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.major,
      delay:    0.1,
      ease:     EASE.out,
    },
  },
}

/**
 * panelSlideLeft — left panel / sidebar enter
 */
export const panelSlideLeft: Variants = {
  hidden: {
    opacity: 0,
    x:       -40,
    filter:  'blur(4px)',
  },
  visible: {
    opacity: 1,
    x:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.major,
      delay:    0.05,
      ease:     EASE.out,
    },
  },
}

/**
 * counterTick — counter value roll when number changes
 */
export const counterTick: Variants = {
  enter:  { opacity: 0, y: -10 },
  center: { opacity: 1, y:   0, transition: SPRING.snappy },
  exit:   { opacity: 0, y:  10, transition: { duration: DURATION.fast } },
}

/**
 * drawPath — SVG path draw-on (graph edges, connector lines)
 */
export const drawPath: Variants = {
  hidden:  { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity:    1,
    transition: { duration: 0.55, ease: EASE.out },
  },
}

/**
 * tabIndicator — active tab sliding indicator
 */
export const tabIndicator: Variants = {
  inactive: { opacity: 0, scaleX: 0 },
  active:   {
    opacity:    1,
    scaleX:     1,
    transition: SPRING.gentle,
  },
}

/**
 * tabContent — tab panel content switch (fade + micro translate)
 */
export const tabContent: Variants = {
  hidden: {
    opacity: 0,
    y:       8,
    filter:  'blur(1px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: {
      duration: DURATION.medium,
      ease:     EASE.out,
    },
  },
  exit: {
    opacity: 0,
    y:       -6,
    transition: {
      duration: DURATION.fast,
      ease:     EASE.snap,
    },
  },
}

/**
 * progressFill — progress bar fill animation
 * custom(pct) where pct is 0–1
 */
export const progressFill: Variants = {
  hidden:  { scaleX: 0, originX: 0 },
  visible: (pct: number) => ({
    scaleX:     pct,
    originX:    0,
    transition: {
      duration: DURATION.slow,
      ease:     EASE.out,
      ...SPRING.default,
    },
  }),
}

/**
 * notificationBadge — count badge pop in
 */
export const notificationBadge: Variants = {
  hidden:  { scale: 0,    opacity: 0 },
  visible: {
    scale:      1,
    opacity:    1,
    transition: SPRING.bouncy,
  },
  exit: {
    scale:      0,
    opacity:    0,
    transition: { duration: DURATION.fast, ease: EASE.snap },
  },
}

/**
 * graphNodeEntry — knowledge graph node fade + scale entrance
 * Orchestrate with staggerContainer for cascading reveal
 */
export const graphNode: Variants = {
  hidden: {
    opacity: 0,
    scale:   0.5,
    filter:  'blur(6px)',
  },
  visible: (i: number) => ({
    opacity:    1,
    scale:      1,
    filter:     'blur(0px)',
    transition: {
      ...SPRING.bouncy,
      delay: i * 0.04,
    },
  }),
}

// ─────────────────────────────────────────────────────────────────────────────
// CSS TRANSITION TOKENS
// Use in: style={{ transition: CSS_T.card }}
// ─────────────────────────────────────────────────────────────────────────────
export const CSS_T = {
  /** Button / CTA hover — fast spring-like */
  button:
    'transform 0.13s cubic-bezier(0.16,1,0.3,1), box-shadow 0.13s ease, filter 0.13s ease',

  /** Card hover lift + shadow */
  card:
    'transform 0.18s cubic-bezier(0.16,1,0.3,1), box-shadow 0.22s ease, border-color 0.18s ease',

  /** Nav underline expand */
  nav:
    'transform 0.3s cubic-bezier(0.16,1,0.3,1), opacity 0.25s ease',

  /** Color / background / border transitions */
  color:
    'color 0.2s ease, background 0.2s ease, border-color 0.2s ease',

  /** Panel / drawer open */
  panel:
    'opacity 0.55s cubic-bezier(0.16,1,0.3,1), transform 0.55s cubic-bezier(0.16,1,0.3,1)',

  /** Tab sliding indicator */
  tab:
    'transform 0.4s cubic-bezier(0.16,1,0.3,1), width 0.4s cubic-bezier(0.16,1,0.3,1)',

  /** Input focus ring */
  input:
    'border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease',

  /** Icon hover */
  icon:
    'transform 0.15s cubic-bezier(0.34,1.56,0.64,1), color 0.15s ease, filter 0.15s ease',
} as const

// ─────────────────────────────────────────────────────────────────────────────
// REDUCED MOTION HELPERS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * reduceMotion
 * Returns instant variants when reduced-motion is preferred.
 * All transforms, filters, and blurs are stripped; duration → 0.
 *
 * Usage: const variants = reduceMotion(prefersReducedMotion, fadeUp)
 */
export function reduceMotion(prefers: boolean, variants: Variants): Variants {
  if (!prefers) return variants
  return Object.fromEntries(
    Object.entries(variants).map(([key, val]) => [
      key,
      typeof val === 'object' && val !== null
        ? {
            // Keep layout properties, strip visual transitions
            ...(typeof val === 'object' ? val : {}),
            // Clear any motion properties to their "revealed" state
            opacity:   (val as Record<string, unknown>).opacity   !== undefined
              ? ((key === 'hidden' || key === 'enter') ? 0 : 1)
              : undefined,
            y:         0,
            x:         0,
            scale:     1,
            filter:    'blur(0px)',
            clipPath:  undefined,
            pathLength: (val as Record<string, unknown>).pathLength !== undefined ? 1 : undefined,
            transition: { duration: 0 },
          }
        : val,
    ])
  )
}

/**
 * instantTransition
 * Zero-duration transition object — use for disabling individual animations
 */
export const instantTransition: Transition = { duration: 0 }

/**
 * getSpring
 * Returns the right spring for the context; falls back to 'default'
 */
export function getSpring(
  type: keyof typeof SPRING = 'default',
  overrides?: Partial<Transition>
): Transition {
  return { ...SPRING[type], ...overrides }
}
