// =============================================================================
// Cortex API Client
// Axios instance configured to talk exclusively to the local FastAPI backend.
// No external API calls — everything routes through http://localhost:8000.
// =============================================================================

import axios, { AxiosError } from 'axios';

// Base URL reads from Next.js env — falls back to localhost for dev
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10_000,
});

// Normalize all errors into { message: string, status: number }
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status ?? 0;
    const detail = error.response?.data?.detail;
    const message =
      detail ??
      error.message ??
      'An unexpected error occurred. Is the Cortex backend running?';
    const normalized = new Error(message) as Error & { status: number };
    normalized.status = status;
    return Promise.reject(normalized);
  }
);
