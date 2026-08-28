/**
 * Next.js Middleware — Route protection for Cortex.
 *
 * - Protected routes (/dashboard, /graph, /jobs) require an access token.
 * - Auth routes (/login, /signup, etc.) redirect to /dashboard if already authenticated.
 * - Public routes (/, /verify-email, /reset-password) are always accessible.
 *
 * Note: This is a lightweight client-cookie/localStorage check via cookie.
 * Since localStorage is not accessible in middleware, we rely on a thin
 * approach: the AuthProvider handles the real token validation client-side.
 * This middleware uses a cookie-based hint set by the auth interceptor.
 *
 * For this implementation, we check for the token in cookies. The auth
 * context will also set a simple cookie flag when tokens are stored.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = ['/dashboard', '/graph', '/jobs'];

// Routes only for unauthenticated users
const AUTH_ROUTES = ['/login', '/signup', '/forgot-password'];

// Always accessible regardless of auth state
// Public routes: /, /verify-email, /reset-password (no redirect logic needed)

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for auth cookie (set by frontend when tokens are stored)
  const authCookie = request.cookies.get('cortex_authenticated');
  const isAuthenticated = authCookie?.value === '1';

  // Protected routes — redirect to login if not authenticated
  const isProtectedRoute = PROTECTED_ROUTES.some(route =>
    pathname === route || pathname.startsWith(`${route}/`)
  );

  if (isProtectedRoute && !isAuthenticated) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Auth routes — redirect to dashboard if already authenticated
  const isAuthRoute = AUTH_ROUTES.some(route => pathname === route);

  if (isAuthRoute && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Match all routes except static files, api routes, and _next
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|api).*)',
  ],
};
