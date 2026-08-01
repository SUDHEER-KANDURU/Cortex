'use client';

// =============================================================================
// Select — Premium liquid glass dropdown
// Radix Select with full design system tokens
// Rounded 18px · Backdrop blur · Shadow · Animated open/close
// Keyboard accessible · WCAG AA contrast
// =============================================================================

import * as React from 'react';
import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

const Select = SelectPrimitive.Root;
const SelectGroup = SelectPrimitive.Group;
const SelectValue = SelectPrimitive.Value;

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      // Layout
      'flex h-10 w-full items-center justify-between gap-2 px-3 py-2',
      // Shape
      'rounded-[var(--radius-md)]',
      // Colors
      'bg-[rgba(255,255,255,0.05)] text-[var(--text)]',
      'border border-[var(--border)]',
      // Text
      'text-sm font-normal',
      // Placeholder
      '[&>span[data-placeholder]]:text-[var(--text-muted)]',
      // Focus
      'focus:outline-none focus:border-[var(--primary)]',
      'focus:shadow-[0_0_0_3px_var(--primary-dim)]',
      // Hover
      'hover:border-[var(--border-hover)] hover:bg-[rgba(255,255,255,0.07)]',
      // Transition
      'transition-all duration-200 ease-out',
      // Disabled
      'disabled:cursor-not-allowed disabled:opacity-45',
      // Line-clamp on content
      '[&>span]:line-clamp-1 [&>span]:text-left',
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 shrink-0 text-[var(--text-muted)] opacity-60 transition-transform duration-200 group-data-[state=open]:rotate-180" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

const SelectScrollUpButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollUpButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollUpButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollUpButton
    ref={ref}
    className={cn(
      'flex cursor-default items-center justify-center py-1.5',
      'text-[var(--text-muted)]',
      className
    )}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </SelectPrimitive.ScrollUpButton>
));
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName;

const SelectScrollDownButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollDownButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollDownButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollDownButton
    ref={ref}
    className={cn(
      'flex cursor-default items-center justify-center py-1.5',
      'text-[var(--text-muted)]',
      className
    )}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </SelectPrimitive.ScrollDownButton>
));
SelectScrollDownButton.displayName = SelectPrimitive.ScrollDownButton.displayName;

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        // Layout
        'relative z-50 min-w-[8rem] overflow-hidden',
        // Shape — premium 18px radius
        'rounded-[var(--radius-lg)]',
        // Glass surface
        'bg-[rgba(18,22,30,0.92)]',
        'border border-[var(--border)]',
        'backdrop-blur-[24px] saturate-150',
        // Shadow — elevated dropdown
        'shadow-[var(--shadow-xl),inset_0_1px_0_rgba(255,255,255,0.07)]',
        // Text
        'text-[var(--text)]',
        // Animations — open
        'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
        // Animations — close
        'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
        // Slide in from direction
        'data-[side=bottom]:slide-in-from-top-2',
        'data-[side=left]:slide-in-from-right-2',
        'data-[side=right]:slide-in-from-left-2',
        'data-[side=top]:slide-in-from-bottom-2',
        // Popper offset
        position === 'popper' && [
          'data-[side=bottom]:translate-y-1',
          'data-[side=left]:-translate-x-1',
          'data-[side=right]:translate-x-1',
          'data-[side=top]:-translate-y-1',
        ].join(' '),
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <SelectPrimitive.Viewport
        className={cn(
          'p-1.5',
          position === 'popper' &&
            'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]'
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectScrollDownButton />
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = SelectPrimitive.Content.displayName;

const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={cn(
      'px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest',
      'text-[var(--text-muted)]',
      className
    )}
    {...props}
  />
));
SelectLabel.displayName = SelectPrimitive.Label.displayName;

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      // Layout
      'relative flex w-full cursor-pointer select-none items-center',
      'rounded-[var(--radius-sm)] py-2 pl-9 pr-3',
      // Text
      'text-sm text-[var(--text-secondary)]',
      'outline-none',
      // Hover / focus
      'focus:bg-[rgba(255,255,255,0.07)] focus:text-[var(--text)]',
      'data-[highlighted]:bg-[rgba(255,255,255,0.07)] data-[highlighted]:text-[var(--text)]',
      // Selected
      'data-[state=checked]:text-[var(--primary)]',
      // Disabled
      'data-[disabled]:pointer-events-none data-[disabled]:opacity-40',
      // Transition
      'transition-colors duration-150',
      className
    )}
    {...props}
  >
    {/* Check indicator */}
    <span className="absolute left-3 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-3.5 w-3.5 text-[var(--primary)]" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;

const SelectSeparator = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={cn('-mx-1 my-1 h-px bg-[var(--border)]', className)}
    {...props}
  />
));
SelectSeparator.displayName = SelectPrimitive.Separator.displayName;

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
};
