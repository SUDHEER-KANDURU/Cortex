/**
 * Auth API service — all authentication-related API calls.
 */

import { apiClient } from './client';

// ── Types ───────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  organization?: string;
  role?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
}

export interface RegisterResponse {
  id: string;
  name: string;
  email: string;
  is_verified: boolean;
  message: string;
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
  organization?: string | null;
  role?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
}

export interface UpdateProfilePayload {
  name?: string;
  organization?: string;
  role?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
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

export async function verifyEmail(code: string): Promise<UserResponse> {
  const { data } = await apiClient.post<UserResponse>('/auth/verify-email', { code });
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

export async function resetPassword(code: string, password: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/reset-password', { code, password });
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

export async function updateProfile(payload: UpdateProfilePayload): Promise<UserResponse> {
  const { data } = await apiClient.put<UserResponse>('/auth/me', payload);
  return data;
}

export async function requestPasswordChange(): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/change-password/request', {});
  return data;
}

export async function confirmPasswordChange(code: string, newPassword: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/change-password/confirm', {
    code,
    new_password: newPassword,
  });
  return data;
}

export async function deleteAccount(): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>('/auth/me');
  return data;
}
