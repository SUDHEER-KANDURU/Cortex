/**
 * Token storage — secure client-side token management.
 *
 * Tokens stored in localStorage for persistence across tabs/refreshes.
 * A cookie flag is also set so Next.js middleware can check auth state.
 * In production with sensitive data, httpOnly cookies would be preferred.
 */

const ACCESS_TOKEN_KEY = 'cortex_access_token';
const REFRESH_TOKEN_KEY = 'cortex_refresh_token';
const AUTH_COOKIE_NAME = 'cortex_authenticated';

function setAuthCookie(authenticated: boolean): void {
  if (typeof document === 'undefined') return;
  if (authenticated) {
    // Set a simple flag cookie (not httpOnly — accessible to middleware)
    document.cookie = `${AUTH_COOKIE_NAME}=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
  } else {
    document.cookie = `${AUTH_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  setAuthCookie(true);
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  setAuthCookie(false);
}

export function hasTokens(): boolean {
  return !!getAccessToken();
}
