'use client'

import { Sidebar } from '@/components/layout/Sidebar'
import { useAuthStore } from '@/store/auth'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router          = useRouter()
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  const hydrate         = useAuthStore(s => s.hydrate)
  const user            = useAuthStore(s => s.user)

  useEffect(() => {
    // Hydrate from token on mount
    if (isAuthenticated && !user) {
      hydrate()
    }
    // Redirect if not authenticated
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, user, hydrate, router])

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-50">
        <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface-50">
      <Sidebar />
      {/* Main content — offset by sidebar width */}
      <main className="ml-[220px] min-h-screen">
        <div className="p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  )
}
