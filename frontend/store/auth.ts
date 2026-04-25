/**
 * store/auth.ts
 * ==============
 * Zustand store for auth state.
 * Persists token to localStorage via getToken/setToken.
 *
 * Used by:
 *   - LoginPage   → calls login()
 *   - Sidebar     → reads user.fullName, user.role
 *   - Route guard → checks isAuthenticated
 *   - RBAC        → checks hasPermission()
 */

import { authApi, clearToken, getToken, setToken } from '@/lib/api'
import type { AuthUser, Role } from '@/types'
import { create } from 'zustand'

// ─── Permission map (mirrors backend) ────────────────────────────────────────

const PERMISSIONS: Record<string, Role[]> = {
  // Purchase
  view_purchase:    ['owner', 'admin', 'warehouse'],
  manage_purchase:  ['owner', 'admin', 'warehouse'],
  // Sales
  view_sales:       ['owner', 'admin', 'sales', 'finance'],
  manage_sales:     ['owner', 'admin', 'sales'],
  // Invoices
  view_invoices:    ['owner', 'admin', 'finance'],
  manage_invoices:  ['owner', 'admin', 'finance'],
  // Payments
  manage_payments:  ['owner', 'finance'],
  // Inventory
  view_inventory:   ['owner', 'admin', 'warehouse'],
  manage_inventory: ['owner', 'admin', 'warehouse'],
  // Users
  manage_users:     ['owner', 'admin'],
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface AuthState {
  user:            AuthUser | null
  token:           string | null
  isAuthenticated: boolean
  isLoading:       boolean

  login:       (email: string, password: string) => Promise<void>
  logout:      () => void
  hydrate:     () => Promise<void>
  hasPermission: (permission: string) => boolean
  canAccess:   (roles: Role[]) => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user:            null,
  token:           getToken(),
  isAuthenticated: !!getToken(),
  isLoading:       false,

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const res = await authApi.login(email, password)
      setToken(res.access_token)

      const user: AuthUser = {
        id:       res.user_id,
        email:    res.email,
        fullName: res.full_name,
        role:     res.role,
        tenantId: res.tenant_id,
      }

      set({ token: res.access_token, user, isAuthenticated: true, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw err
    }
  },

  logout: () => {
    clearToken()
    set({ token: null, user: null, isAuthenticated: false })
    window.location.href = '/login'
  },

  hydrate: async () => {
    const token = getToken()
    if (!token) {
      set({ isAuthenticated: false })
      return
    }
    try {
      const me = await authApi.me()
      set({
        user: {
          id:       me.id,
          email:    me.email,
          fullName: me.full_name,
          role:     me.role as Role,
          tenantId: me.tenant_id,
        },
        isAuthenticated: true,
      })
    } catch {
      clearToken()
      set({ token: null, user: null, isAuthenticated: false })
    }
  },

  hasPermission: (permission: string) => {
    const { user } = get()
    if (!user) return false
    if (user.role === 'super_admin') return true
    const allowed = PERMISSIONS[permission] ?? []
    return allowed.includes(user.role)
  },

  canAccess: (roles: Role[]) => {
    const { user } = get()
    if (!user) return false
    if (user.role === 'super_admin') return true
    return roles.includes(user.role)
  },
}))
