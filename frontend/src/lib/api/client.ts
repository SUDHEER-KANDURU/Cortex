// =============================================================================
// Cortex API Client
// Axios instance configured to talk exclusively to the local FastAPI backend.
// =============================================================================

import axios, { AxiosError } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// ── Slow request tracking (>400ms) ───────────────────────────────────────────
// Components can subscribe to this to show the SlowRequestIndicator.

type SlowListener = (count: number) => void;
const _slowListeners = new Set<SlowListener>();
let _slowCount = 0;

export function onSlowRequest(fn: SlowListener) {
  _slowListeners.add(fn);
  return () => _slowListeners.delete(fn);
}

function notifySlowListeners() {
  _slowListeners.forEach(fn => fn(_slowCount));
}

// ── Request interceptor — start slow-request timer ───────────────────────────
apiClient.interceptors.request.use(config => {
  const timer = setTimeout(() => {
    _slowCount++;
    notifySlowListeners();
    // Store cleanup on config so response interceptor can clear it
    (config as Record<string, unknown>).__slowTimer = timer;
    (config as Record<string, unknown>).__wasSlow = true;
  }, 400);
  (config as Record<string, unknown>).__slowTimer = timer;
  return config;
});

// ── Response interceptor — clear timer, decrement slow count ─────────────────
apiClient.interceptors.response.use(
  response => {
    const cfg = response.config as Record<string, unknown>;
    if (cfg.__slowTimer) clearTimeout(cfg.__slowTimer as ReturnType<typeof setTimeout>);
    if (cfg.__wasSlow) { _slowCount = Math.max(0, _slowCount - 1); notifySlowListeners(); }
    return response;
  },
  (error: AxiosError<{ detail?: string }>) => {
    const cfg = (error.config ?? {}) as Record<string, unknown>;
    if (cfg.__slowTimer) clearTimeout(cfg.__slowTimer as ReturnType<typeof setTimeout>);
    if (cfg.__wasSlow) { _slowCount = Math.max(0, _slowCount - 1); notifySlowListeners(); }

    const status = error.response?.status ?? 0;
    const detail = error.response?.data?.detail;
    const message =
      detail ?? error.message ?? 'An unexpected error occurred. Is the Cortex backend running?';
    const normalized = new Error(message) as Error & { status: number };
    normalized.status = status;
    return Promise.reject(normalized);
  },
);
