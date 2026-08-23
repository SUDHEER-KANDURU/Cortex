'use client';

/**
 * Tabs — Radix UI tabs with Framer Motion sliding indicator + content transition.
 *
 * Motion behaviour:
 *  - Active tab: layoutId="tab-pill" slides the background pill with spring physics
 *  - TabsContent: AnimatePresence fades + translates on switch (tabContent variant)
 *  - prefers-reduced-motion: instant switch, no layout animation
 */

import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils/cn';
import { SPRING, tabContent } from '@/lib/utils/motion';

// ── Tabs Root ──────────────────────────────────────────────────────────────

const Tabs = TabsPrimitive.Root;

// ── TabsList ───────────────────────────────────────────────────────────────

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'relative inline-flex h-10 items-center justify-center gap-1',
      'rounded-[var(--radius-md)] p-1',
      'bg-[var(--surface)] border border-[var(--border)]',
      'text-[var(--text-muted)]',
      className
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

// ── TabsTrigger ────────────────────────────────────────────────────────────
// Uses layoutId for the spring-animated active pill.

interface TabsTriggerProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> {
  /** layoutId prefix — use the same prefix across all triggers in a TabsList */
  layoutGroupId?: string;
  /** Radix sets this attribute at runtime for the active/inactive state */
  'data-state'?: 'active' | 'inactive';
}

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  TabsTriggerProps
>(({ className, children, layoutGroupId = 'tab-pill', 'data-state': dataState, ...props }, ref) => {
  const prefersReduced = useReducedMotion();
  const isActive = dataState === 'active';

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      data-state={dataState}
      className={cn(
        'relative inline-flex items-center justify-center whitespace-nowrap',
        'rounded-[var(--radius-sm)] px-3 py-1.5',
        'text-sm font-medium z-10',
        'ring-offset-background',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1',
        'disabled:pointer-events-none disabled:opacity-45',
        // Text colour — active handled by data-state below
        'text-[var(--text-muted)]',
        'data-[state=active]:text-[var(--text)]',
        // Hover (inactive only)
        'hover:text-[var(--text)]',
        'transition-colors duration-150',
        className
      )}
      {...props}
    >
      {/* Spring-animated active pill — lives BEHIND the label */}
      {isActive && !prefersReduced && (
        <motion.span
          layoutId={layoutGroupId}
          className={cn(
            'absolute inset-0 rounded-[var(--radius-sm)]',
            'bg-[var(--card)] border border-[var(--border)]',
            'shadow-[var(--shadow-sm)]',
          )}
          transition={SPRING.gentle}
          style={{ zIndex: -1 }}
          aria-hidden
        />
      )}
      {/* CSS fallback active state for reduced-motion */}
      {isActive && prefersReduced && (
        <span
          className={cn(
            'absolute inset-0 rounded-[var(--radius-sm)]',
            'bg-[var(--card)] border border-[var(--border)]',
            'shadow-[var(--shadow-sm)]',
          )}
          style={{ zIndex: -1 }}
          aria-hidden
        />
      )}
      {children}
    </TabsPrimitive.Trigger>
  );
});
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

// ── TabsContent ────────────────────────────────────────────────────────────
// Wraps Radix content in AnimatePresence for enter/exit transitions.

interface TabsContentProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content> {
  /** Pass the current value of the parent Tabs so AnimatePresence can key correctly */
  activeValue?: string;
}

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  TabsContentProps
>(({ className, children, value, activeValue, ...props }, ref) => {
  const prefersReduced = useReducedMotion();
  const isActive = activeValue === value;

  return (
    <TabsPrimitive.Content
      ref={ref}
      value={value}
      forceMount
      className={cn(
        'mt-3',
        'ring-offset-background',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2',
        // Hide inactive tabs — AnimatePresence handles the animated hide/show
        !isActive && 'hidden',
        className
      )}
      {...props}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isActive && (
          <motion.div
            key={value}
            variants={prefersReduced ? undefined : tabContent}
            initial={prefersReduced ? false : 'hidden'}
            animate="visible"
            exit={prefersReduced ? undefined : 'exit'}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </TabsPrimitive.Content>
  );
});
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
