/**
 * Auth API service — all authentication-related API calls.
 */

import { apiClient } from './client';

// ── Types ───────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  id: string;
  name: string;
  email: string;
  is_verified: boolean;
  verification_token: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  is_verified: boolean;
  is_active: boolean;
}

export interface MessageResponse {
  message: string;
  token?: string | null;
}

// ── API Functions ───────────────────────────────────────────────────────────

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  const { data } = await apiClient.post<RegisterResponse>('/auth/register', payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', payload);
  return data;
}

export async function verifyEmail(token: string): Promise<UserResponse> {
  const { data } = await apiClient.post<UserResponse>('/auth/verify-email', { token });
  return data;
}

export async function resendVerification(email: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/resend-verification', { email });
  return data;
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/forgot-password', { email });
  return data;
}

export async function resetPassword(token: string, password: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/reset-password', { token, password });
  return data;
}

export async function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>('/auth/me');
  return data;
}
