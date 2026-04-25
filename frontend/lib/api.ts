/**
 * lib/api.ts
 * ============
 * Typed fetch wrapper for the KLA/Arthasee backend.
 *
 * - Auto-injects Authorization header from localStorage
 * - Returns typed responses
 * - Throws ApiError on non-2xx
 * - Handles 401 → redirects to /login
 */

import type { ApiError, TokenResponse } from '@/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'arthasee_token'

// ─── Token management ─────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  // 401 → clear token and redirect to login
  if (res.status === 401) {
    clearToken()
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new Error('Sesi habis. Silakan login kembali.')
  }

  const data = await res.json()

  if (!res.ok) {
    const err = data as ApiError
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }

  return data as T
}

// ─── HTTP helpers ─────────────────────────────────────────────────────────────

export const api = {
  get: <T>(path: string) =>
    request<T>(path, { method: 'GET' }),

  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  put: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  delete: <T>(path: string) =>
    request<T>(path, { method: 'DELETE' }),
}

// ─── Auth endpoints ───────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/api/v1/auth/login', { email, password }),

  me: () =>
    api.get<{ id: number; email: string; full_name: string; role: string; tenant_id: number | null }>
    ('/api/v1/auth/me'),
}

// ─── Inventory endpoints ──────────────────────────────────────────────────────

export const inventoryApi = {
  getProducts: () =>
    api.get<any[]>('/api/v1/inventory/products'),

  getMovements: () =>
    api.get<any[]>('/api/v1/inventory/stock-movements'),
}

// ─── Purchase endpoints ───────────────────────────────────────────────────────

export const purchaseApi = {
  getOrders: () =>
    api.get<any[]>('/api/v1/purchase/orders'),
}

// ─── Sales endpoints ──────────────────────────────────────────────────────────

export const salesApi = {
  getOrders: () =>
    api.get<any[]>('/api/v1/sales/orders'),

  confirmOrder: (id: number) =>
    api.post<any>(`/api/v1/sales/orders/${id}/confirm`, {}),

  cancelOrder: (id: number) =>
    api.post<any>(`/api/v1/sales/orders/${id}/cancel`, {}),

  getInvoices: () =>
    api.get<any[]>('/api/v1/sales/invoices'),
}

// ─── Utils ────────────────────────────────────────────────────────────────────

export function formatRupiah(amount: string | number): string {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return new Intl.NumberFormat('id-ID', {
    style:    'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(n)
}

export function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('id-ID', {
    day:   '2-digit',
    month: 'short',
    year:  'numeric',
  }).format(new Date(dateStr))
}
