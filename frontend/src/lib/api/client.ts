// =============================================================================
// Cortex API Client
// Axios instance configured to talk exclusively to the local FastAPI backend.
// No external API calls — everything routes through http://localhost:8000.
// =============================================================================

import axios from 'axios';

// Base URL reads from Next.js env — falls back to localhost for dev
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
});

// Log errors in development only — no console.log in production
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Cortex API Error]', error.response?.data ?? error.message);
    }
    return Promise.reject(error);
  }
);
