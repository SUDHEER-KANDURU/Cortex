// =============================================================================
// Cortex Session Cache
//
// Lightweight in-memory cache for API responses. Lives for the browser session.
// Avoids duplicate requests when the user navigates back to a previously
// visited job, artifact list, or insights report.
//
// Design:
//   - Simple Map<key, {data, timestamp}>
//   - TTL per entry type (jobs list short, completed artifacts forever)
//   - Manual invalidation by key prefix
//   - No persistence (session only — stale analysis should never be shown)
//   - No dependencies
//
// Usage:
//   const cached = sessionCache.get<T>(key);
//   if (cached) return cached;
//   const data = await fetchFn();
//   sessionCache.set(key, data, ttl);
// =============================================================================

interface CacheEntry<T> {
  data: T;
  ts: number;   // Date.now() at write time
  ttl: number;  // ms — 0 = never expires within session
}

class SessionCache {
  private readonly store = new Map<string, CacheEntry<unknown>>();

  get<T>(key: string): T | null {
    const entry = this.store.get(key) as CacheEntry<T> | undefined;
    if (!entry) return null;
    if (entry.ttl > 0 && Date.now() - entry.ts > entry.ttl) {
      this.store.delete(key);
      return null;
    }
    return entry.data;
  }

  set<T>(key: string, data: T, ttl = 0): void {
    this.store.set(key, { data, ts: Date.now(), ttl });
  }

  /** Invalidate all keys that start with the given prefix. */
  invalidatePrefix(prefix: string): void {
    for (const key of this.store.keys()) {
      if (key.startsWith(prefix)) this.store.delete(key);
    }
  }

  has(key: string): boolean {
    return this.get(key) !== null;
  }

  clear(): void {
    this.store.clear();
  }
}

// Singleton — shared across all hooks in the same browser tab
export const sessionCache = new SessionCache();

// ── TTL constants ─────────────────────────────────────────────────────────────

export const TTL = {
  /** Jobs list refreshes every 10s — it changes as jobs complete */
  JOBS_LIST:        10_000,
  /** A single job's status: 0 = don't cache (polled live) */
  JOB_STATUS:       0,
  /** Artifacts for a completed job never change — cache indefinitely */
  ARTIFACTS:        0,
  /** Insights for a completed job never change */
  INSIGHTS:         0,
  /** Graph data for a completed job never changes */
  GRAPH:            0,
} as const;

// ── Cache key helpers ─────────────────────────────────────────────────────────

export const cacheKey = {
  jobsList:  ()           => 'jobs:list',
  job:       (id: string) => `job:${id}`,
  artifacts: (id: string) => `artifacts:${id}`,
  insights:  (id: string) => `insights:${id}`,
  graph:     (id: string) => `graph:${id}`,
} as const;
