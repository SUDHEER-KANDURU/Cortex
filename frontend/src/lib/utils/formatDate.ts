// =============================================================================
// formatDate — Date formatting utilities
// Converts ISO 8601 strings from the backend into human-readable formats.
// =============================================================================

/**
 * Format an ISO 8601 date string into a short, readable format.
 * Example: "2024-06-01T12:34:56Z" → "Jun 1, 2024, 12:34 PM"
 */
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return 'Invalid date';
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format an ISO 8601 date string into a relative time description.
 * Example: "2 minutes ago", "3 hours ago", "yesterday"
 */
export function formatRelativeDate(isoString: string): string {
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return 'Invalid date';

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? 's' : ''} ago`;
  if (diffDay === 1) return 'yesterday';
  return `${diffDay} days ago`;
}

/**
 * Format duration between two ISO 8601 strings in a human-readable way.
 * Example: "1m 23s"
 */
export function formatDuration(startIso: string, endIso: string): string {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (isNaN(start) || isNaN(end)) return '—';

  const diffSec = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(diffSec / 60);
  const seconds = diffSec % 60;

  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}
