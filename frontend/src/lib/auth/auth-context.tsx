'use client';

/**
 * AuthProvider — React context for authentication state.
 *
 * Provides:
 * - user object (null if not logged in)
 * - isLoading (true while checking auth on mount)
 * - login / logout / register helpers
 * - Token management via interceptors
 */

import React, { createContext, useContext, useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import * as authApi from '@/lib/api/auth';
import { setTokens, clearTokens, getRefreshToken, hasTokens } from './token-storage';
import { installAuthInterceptors } from './auth-interceptor';
import { sessionCache } from '@/lib/cache';

// ── Types ───────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  is_verified: boolean;
  is_active: boolean;
  organization?: string | null;
  role?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: authApi.RegisterPayload) => Promise<authApi.RegisterResponse>;
  updateUser: (user: AuthUser) => void;
  logout: () => void;
  deleteAccount: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Install interceptors once at module level
let interceptorsInstalled = false;

// ── Provider ────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Install interceptors on first render
  useEffect(() => {
    if (!interceptorsInstalled) {
      installAuthInterceptors();
      interceptorsInstalled = true;
    }
  }, []);

  // Check for existing session on mount.
  //
  // On app boot (including right after the backend restarts) the stored
  // access token may already have expired — a 60-minute lifetime is easily
  // outlived by an idle tab. When that happens `getMe()` returns 401. We must
  // try to mint a fresh pair from the still-valid refresh token BEFORE giving
  // up; only clear tokens and force a re-login if the refresh itself fails.
  // Previously any getMe() error cleared tokens outright, which is what made
  // users get bounced to /login after a restart even though they never logged
  // out.
  const refreshUser = useCallback(async () => {
    if (!hasTokens()) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    // A single outer try/finally guarantees isLoading is ALWAYS cleared, no
    // matter which path we take. Previously the happy path (`getMe` succeeds)
    // returned early and skipped the finally, so isLoading stayed true forever
    // and every route that gates on it (login/landing/dashboard) got stuck on
    // the loading logo after the first navigation.
    try {
      try {
        const me = await authApi.getMe();
        setUser(me);
        return;
      } catch {
        // Access token likely expired — fall through to an explicit refresh.
      }

      const refresh = getRefreshToken();
      if (!refresh) {
        throw new Error('No refresh token');
      }
      const tokens = await authApi.refreshTokens(refresh);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await authApi.getMe();
      setUser(me);
    } catch {
      // Refresh token is missing/expired/invalid — this is a genuine
      // "session is over" case, so clear and require a fresh login.
      setUser(null);
      clearTokens();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    // Drop any cached data from a previously logged-in account so one user
    // never sees another user's jobs/conversations from the in-memory cache.
    sessionCache.clear();
    const tokens = await authApi.login({ email, password });
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await authApi.getMe();
    setUser(me);
  }, []);

  const register = useCallback(async (payload: authApi.RegisterPayload) => {
    const result = await authApi.register(payload);
    return result;
  }, []);

  const updateUser = useCallback((updatedUser: AuthUser) => {
    setUser(updatedUser);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    sessionCache.clear();
    setUser(null);
    router.push('/login');
  }, [router]);

  const deleteAccount = useCallback(async () => {
    await authApi.deleteAccount();
    clearTokens();
    sessionCache.clear();
    setUser(null);
    router.push('/login');
  }, [router]);

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    updateUser,
    logout,
    deleteAccount,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
