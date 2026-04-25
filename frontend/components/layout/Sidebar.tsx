'use client'

import { useAuthStore } from '@/store/auth'
import {
    ArrowLeftRight,
    BarChart3,
    ChevronRight,
    CreditCard,
    FileText,
    LayoutDashboard,
    LogOut,
    Package,
    PackageCheck,
    Receipt,
    ShoppingCart,
    Truck,
    Users,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface NavItem {
  label:      string
  href:       string
  icon:       React.ElementType
  permission: string
  badge?:     string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV: NavGroup[] = [
  {
    label: '',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, permission: 'view_sales' },
    ],
  },
  {
    label: 'Pembelian',
    items: [
      { label: 'Purchase Order',    href: '/purchase/orders',   icon: ShoppingCart,  permission: 'view_purchase' },
      { label: 'Terima Barang',     href: '/purchase/receipts', icon: PackageCheck,  permission: 'view_purchase' },
    ],
  },
  {
    label: 'Penjualan',
    items: [
      { label: 'Sales Order',   href: '/sales/orders',      icon: FileText,  permission: 'view_sales' },
      { label: 'Surat Jalan',   href: '/sales/surat-jalan', icon: Truck,     permission: 'view_sales' },
      { label: 'Invoice',       href: '/sales/invoices',    icon: Receipt,   permission: 'view_invoices' },
      { label: 'Pembayaran',    href: '/sales/payments',    icon: CreditCard, permission: 'manage_payments' },
    ],
  },
  {
    label: 'Inventori',
    items: [
      { label: 'Produk',          href: '/inventory/products',  icon: Package,        permission: 'view_inventory' },
      { label: 'Pergerakan Stok', href: '/inventory/movements', icon: ArrowLeftRight, permission: 'view_inventory' },
    ],
  },
  {
    label: 'Pengaturan',
    items: [
      { label: 'Pengguna', href: '/settings/users', icon: Users, permission: 'manage_users' },
    ],
  },
]

export function Sidebar() {
  const pathname     = usePathname()
  const user         = useAuthStore(s => s.user)
  const logout       = useAuthStore(s => s.logout)
  const hasPermission = useAuthStore(s => s.hasPermission)

  const initials = user?.fullName
    .split(' ')
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase() ?? '?'

  const roleLabel: Record<string, string> = {
    super_admin: 'Super Admin',
    owner:       'Owner',
    admin:       'Admin',
    sales:       'Sales',
    warehouse:   'Gudang',
    finance:     'Finance',
  }

  return (
    <aside
      className="fixed inset-y-0 left-0 w-[220px] flex flex-col z-30 overflow-hidden"
      style={{ background: 'hsl(var(--sidebar-bg))' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 flex-shrink-0"
           style={{ borderBottom: '1px solid hsl(var(--sidebar-border))' }}>
        <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center flex-shrink-0">
          <BarChart3 className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-white font-semibold text-sm tracking-tight">Arthasee</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV.map((group) => {
          const visibleItems = group.items.filter(item => hasPermission(item.permission))
          if (visibleItems.length === 0) return null

          return (
            <div key={group.label} className="mb-4">
              {group.label && (
                <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest"
                   style={{ color: 'hsl(var(--sidebar-fg) / 0.4)' }}>
                  {group.label}
                </p>
              )}
              {visibleItems.map(item => {
                const Icon    = item.icon
                const isActive = pathname === item.href ||
                                 (item.href !== '/dashboard' && pathname.startsWith(item.href))
                return (
                  <Link key={item.href} href={item.href}>
                    <div className={`sidebar-item ${isActive ? 'active' : ''}`}>
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      <span className="flex-1 text-sm">{item.label}</span>
                      {item.badge && (
                        <span className="text-[10px] bg-brand-500/20 text-brand-400 px-1.5 py-0.5 rounded-full">
                          {item.badge}
                        </span>
                      )}
                      {isActive && <ChevronRight className="w-3 h-3 opacity-50" />}
                    </div>
                  </Link>
                )
              })}
            </div>
          )
        })}
      </nav>

      {/* User section */}
      <div className="flex-shrink-0 p-2"
           style={{ borderTop: '1px solid hsl(var(--sidebar-border))' }}>
        <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg"
             style={{ background: 'hsl(var(--sidebar-hover))' }}>
          {/* Avatar */}
          <div className="w-7 h-7 rounded-full bg-brand-500/20 flex items-center justify-center flex-shrink-0">
            <span className="text-[11px] font-semibold text-brand-400">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white truncate">{user?.fullName}</p>
            <p className="text-[10px]" style={{ color: 'hsl(var(--sidebar-fg))' }}>
              {roleLabel[user?.role ?? ''] ?? user?.role}
            </p>
          </div>
          <button
            onClick={logout}
            title="Keluar"
            className="flex-shrink-0 text-ink-500 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}
