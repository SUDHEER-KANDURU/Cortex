'use client';

/**
 * Modal — Radix Dialog with Framer Motion spring entrance.
 *
 * Motion behaviour:
 *  - Overlay: opacity fade (fast)
 *  - Content: scaleIn variant — springs open (scale 0.90→1 + blur clear + y:8→0)
 *  - Exit: fast scale out + fade (medium ease)
 *  - prefers-reduced-motion: Radix data-state CSS animations (fade only, no scale)
 *
 * Usage:
 *  <Modal open={open} onOpenChange={setOpen}>
 *    <ModalTrigger asChild><Button>Open</Button></ModalTrigger>
 *    <ModalContent>
 *      <ModalHeader><ModalTitle>Title</ModalTitle></ModalHeader>
 *      <ModalBody>…</ModalBody>
 *      <ModalFooter>…</ModalFooter>
 *    </ModalContent>
 *  </Modal>
 */

import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils/cn';
import { SPRING, DURATION, EASE } from '@/lib/utils/motion';

// ── Radix re-exports ───────────────────────────────────────────────────────

const Modal        = DialogPrimitive.Root;
const ModalTrigger = DialogPrimitive.Trigger;
const ModalPortal  = DialogPrimitive.Portal;
const ModalClose   = DialogPrimitive.Close;

// ── Motion variants ────────────────────────────────────────────────────────

const overlayVariants = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { duration: DURATION.medium, ease: EASE.easeOut } },
  exit:    { opacity: 0, transition: { duration: DURATION.fast,   ease: EASE.snap    } },
};

const contentVariants = {
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
};

// ── Animated overlay ───────────────────────────────────────────────────────

const ModalOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay> & {
    animate?: boolean;
  }
>(({ className, animate = true, ...props }, ref) => {
  const prefersReduced = useReducedMotion();

  if (prefersReduced || !animate) {
    return (
      <DialogPrimitive.Overlay
        ref={ref}
        className={cn(
          'fixed inset-0 z-50',
          'bg-black/60 backdrop-blur-[4px]',
          'data-[state=open]:animate-in   data-[state=open]:fade-in-0',
          'data-[state=closed]:animate-out data-[state=closed]:fade-out-0',
          className
        )}
        {...props}
      />
    );
  }

  return (
    <DialogPrimitive.Overlay
      ref={ref}
      asChild
      className={cn('fixed inset-0 z-50', className)}
      {...props}
    >
      <motion.div
        style={{ background: 'rgba(0,0,0,0.60)', backdropFilter: 'blur(4px)' }}
        variants={overlayVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
      />
    </DialogPrimitive.Overlay>
  );
});
ModalOverlay.displayName = DialogPrimitive.Overlay.displayName;

// ── Animated content ───────────────────────────────────────────────────────

interface ModalContentProps
  extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  showClose?: boolean;
  /** Disable Framer Motion — falls back to Radix CSS animations */
  noMotion?: boolean;
}

const ModalContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  ModalContentProps
>(({ className, children, showClose = true, noMotion = false, ...props }, ref) => {
  const prefersReduced = useReducedMotion();
  const useMotionAnimation = !noMotion && !prefersReduced;

  const closeButton = showClose && (
    <DialogPrimitive.Close
      className={cn(
        'absolute right-4 top-4 z-10',
        'inline-flex items-center justify-center w-7 h-7 rounded-[var(--radius-sm)]',
        'text-[var(--text-muted)]',
        'hover:bg-[rgba(255,255,255,0.08)] hover:text-[var(--text)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]',
        'disabled:pointer-events-none',
        'transition-colors duration-150',
      )}
      aria-label="Close"
    >
      <X className="w-4 h-4" />
    </DialogPrimitive.Close>
  );

  return (
    <ModalPortal>
      <ModalOverlay animate={useMotionAnimation} />

      {useMotionAnimation ? (
        <DialogPrimitive.Content ref={ref} asChild {...props}>
          <motion.div
            className={cn(
              'fixed left-[50%] top-[50%] z-50',
              'w-full max-w-lg -translate-x-1/2 -translate-y-1/2',
              'rounded-[var(--radius-lg)] border border-[var(--border)]',
              'bg-[var(--glass)] backdrop-blur-[24px] saturate-150',
              'shadow-[var(--shadow-xl),inset_0_1px_0_rgba(255,255,255,0.07)]',
              className
            )}
            variants={contentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {children}
            {closeButton}
          </motion.div>
        </DialogPrimitive.Content>
      ) : (
        <DialogPrimitive.Content
          ref={ref}
          className={cn(
            'fixed left-[50%] top-[50%] z-50',
            'w-full max-w-lg -translate-x-1/2 -translate-y-1/2',
            'rounded-[var(--radius-lg)] border border-[var(--border)]',
            'bg-[var(--glass)] backdrop-blur-[24px] saturate-150',
            'shadow-[var(--shadow-xl),inset_0_1px_0_rgba(255,255,255,0.07)]',
            // Radix CSS fallback
            'data-[state=open]:animate-in   data-[state=open]:fade-in-0   data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'duration-200',
            className
          )}
          {...props}
        >
          {children}
          {closeButton}
        </DialogPrimitive.Content>
      )}
    </ModalPortal>
  );
});
ModalContent.displayName = DialogPrimitive.Content.displayName;

// ── Sub-components ─────────────────────────────────────────────────────────

const ModalHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      'flex flex-col gap-1.5 px-6 pt-6 pb-4',
      'border-b border-[var(--border)]',
      className
    )}
    {...props}
  />
);
ModalHeader.displayName = 'ModalHeader';

const ModalFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      'flex items-center justify-end gap-3 px-6 py-4',
      'border-t border-[var(--border)]',
      className
    )}
    {...props}
  />
);
ModalFooter.displayName = 'ModalFooter';

const ModalTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn(
      'text-lg font-semibold leading-tight tracking-[-0.02em] text-[var(--text)]',
      className
    )}
    {...props}
  />
));
ModalTitle.displayName = DialogPrimitive.Title.displayName;

const ModalDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn('text-sm text-[var(--text-secondary)] leading-relaxed', className)}
    {...props}
  />
));
ModalDescription.displayName = DialogPrimitive.Description.displayName;

const ModalBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('px-6 py-4', className)} {...props} />
);
ModalBody.displayName = 'ModalBody';

export {
  Modal,
  ModalTrigger,
  ModalClose,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalTitle,
  ModalDescription,
  ModalBody,
};
