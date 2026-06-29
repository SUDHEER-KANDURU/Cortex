// =============================================================================
// cn — className utility
// Merges Tailwind classes safely, resolving conflicts via tailwind-merge.
// Usage: cn('px-2 py-1', condition && 'bg-blue-500', 'text-white')
// =============================================================================

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
