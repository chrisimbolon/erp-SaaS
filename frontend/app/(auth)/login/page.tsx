'use client'

import { useAuthStore } from '@/store/auth'
import { BarChart3, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LoginPage() {
  const router   = useRouter()
  const login    = useAuthStore(s => s.login)
  const isLoading = useAuthStore(s => s.isLoading)

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [error, setError]       = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message ?? 'Login gagal. Coba lagi.')
    }
  }

  return (
    <div className="min-h-screen bg-surface-50 flex">

      {/* ── Left panel — brand ── */}
      <div className="hidden lg:flex lg:w-[420px] xl:w-[480px] flex-col justify-between p-10"
           style={{ background: 'hsl(var(--sidebar-bg))' }}>

        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <span className="text-white font-semibold tracking-tight">Arthasee</span>
        </div>

        {/* Tagline */}
        <div className="space-y-4">
          <p className="text-3xl font-semibold text-white leading-snug tracking-tight">
            Kelola bisnis Anda<br />dengan lebih jelas.
          </p>
          <p style={{ color: 'hsl(var(--sidebar-fg))' }} className="text-sm leading-relaxed">
            Pembelian, penjualan, dan inventori — semua terhubung, semua real-time.
          </p>
        </div>

        {/* Modules */}
        <div className="space-y-2">
          {['Pembelian & Penerimaan Barang', 'Penjualan & Surat Jalan', 'Inventori Real-time'].map(m => (
            <div key={m} className="flex items-center gap-2.5 text-sm"
                 style={{ color: 'hsl(var(--sidebar-fg))' }}>
              <div className="w-1.5 h-1.5 rounded-full bg-brand-400 flex-shrink-0" />
              {m}
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm animate-fade-in">

          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
              <BarChart3 className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-ink-900 tracking-tight">Arthasee</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-ink-900 tracking-tight mb-1.5">
              Selamat datang kembali
            </h1>
            <p className="text-sm text-ink-500">Masuk ke akun Anda untuk melanjutkan</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-ink-700" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="chris@kusuma-agro.co.id"
                required
                className="w-full h-10 px-3 rounded-lg border border-surface-200 bg-white
                           text-sm text-ink-900 placeholder:text-ink-300
                           focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500
                           transition-colors"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-ink-700" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full h-10 px-3 pr-10 rounded-lg border border-surface-200 bg-white
                             text-sm text-ink-900 placeholder:text-ink-300
                             focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500
                             transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600 transition-colors"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 animate-fade-in">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-10 bg-brand-500 hover:bg-brand-600 disabled:opacity-60
                         text-white text-sm font-medium rounded-lg
                         flex items-center justify-center gap-2
                         transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isLoading ? 'Memuat...' : 'Masuk'}
            </button>
          </form>

          {/* Dev hint */}
          <div className="mt-8 p-3 rounded-lg bg-surface-100 border border-surface-200">
            <p className="text-xs text-ink-500 font-medium mb-1.5">Akun development</p>
            {[
              ['chris@kusuma-agro.co.id', 'owner'],
              ['sales@kusuma-agro.co.id', 'sales'],
              ['finance@kusuma-agro.co.id', 'finance'],
            ].map(([email, role]) => (
              <button
                key={email}
                type="button"
                onClick={() => { setEmail(email); setPassword('KLA_Dev_2026!') }}
                className="block w-full text-left text-xs text-ink-500 hover:text-brand-600
                           py-0.5 transition-colors"
              >
                {email} <span className="text-ink-300">({role})</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
