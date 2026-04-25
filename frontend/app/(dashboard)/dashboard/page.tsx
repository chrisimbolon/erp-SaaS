'use client'

import { formatDate, formatRupiah, inventoryApi, salesApi } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import type { Product, SalesOrder } from '@/types'
import {
    AlertTriangle,
    Clock, FileText, Loader2,
    Package,
    TrendingUp
} from 'lucide-react'
import { useEffect, useState } from 'react'

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  label, value, icon: Icon, trend, color,
}: {
  label:  string
  value:  string
  icon:   React.ElementType
  trend?: string
  color:  string
}) {
  return (
    <div className="stat-card bg-white rounded-xl border border-surface-200 p-5">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-ink-500 uppercase tracking-wide">{label}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-2xl font-semibold text-ink-900 tracking-tight mb-1">{value}</p>
      {trend && <p className="text-xs text-ink-400">{trend}</p>}
    </div>
  )
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft:              'bg-surface-100 text-ink-500',
    confirmed:          'bg-blue-50 text-blue-700',
    fulfilled:          'bg-green-50 text-green-700',
    cancelled:          'bg-red-50 text-red-500',
    partially_received: 'bg-yellow-50 text-yellow-700',
    fully_received:     'bg-green-50 text-green-700',
    sent:               'bg-blue-50 text-blue-700',
    paid:               'bg-green-50 text-green-700',
    overdue:            'bg-red-50 text-red-600',
  }
  const labels: Record<string, string> = {
    draft:              'Draft',
    confirmed:          'Konfirmasi',
    fulfilled:          'Dikirim',
    cancelled:          'Batal',
    partially_received: 'Parsial',
    fully_received:     'Diterima',
    sent:               'Terkirim',
    paid:               'Lunas',
    overdue:            'Jatuh Tempo',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? 'bg-surface-100 text-ink-500'}`}>
      {labels[status] ?? status}
    </span>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const user = useAuthStore(s => s.user)
  const hasPermission = useAuthStore(s => s.hasPermission)

  const [orders,   setOrders]   = useState<SalesOrder[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [o, p] = await Promise.all([
          hasPermission('view_sales')     ? salesApi.getOrders()       : Promise.resolve([]),
          hasPermission('view_inventory') ? inventoryApi.getProducts() : Promise.resolve([]),
        ])
        setOrders(o)
        setProducts(p)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const pendingOrders  = orders.filter(o => o.status === 'confirmed')
  const lowStockItems  = products.filter(p => parseFloat(p.current_stock) <= parseFloat(p.minimum_stock))
  const totalStockValue = products.reduce((sum, p) =>
    sum + parseFloat(p.current_stock) * parseFloat(p.cost_price), 0
  )

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Selamat pagi' :
                   now.getHours() < 17 ? 'Selamat siang' : 'Selamat sore'

  return (
    <div className="max-w-6xl mx-auto">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-ink-900 tracking-tight">
          {greeting}, {user?.fullName.split(' ')[0]} 👋
        </h1>
        <p className="text-sm text-ink-500 mt-1">
          {now.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
        </div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Sales Order Pending"
              value={String(pendingOrders.length)}
              icon={Clock}
              trend="Menunggu pengiriman"
              color="bg-blue-50 text-blue-600"
            />
            <StatCard
              label="Stok Rendah"
              value={String(lowStockItems.length)}
              icon={AlertTriangle}
              trend={lowStockItems.length > 0 ? 'Perlu restock segera' : 'Semua stok aman'}
              color={lowStockItems.length > 0 ? 'bg-yellow-50 text-yellow-600' : 'bg-green-50 text-green-600'}
            />
            <StatCard
              label="Total Produk"
              value={String(products.length)}
              icon={Package}
              trend="Produk aktif"
              color="bg-purple-50 text-purple-600"
            />
            <StatCard
              label="Nilai Persediaan"
              value={formatRupiah(totalStockValue)}
              icon={TrendingUp}
              trend="Harga pokok"
              color="bg-brand-50 text-brand-600"
            />
          </div>

          <div className="grid lg:grid-cols-2 gap-6">

            {/* Pending Sales Orders */}
            {hasPermission('view_sales') && (
              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="px-5 py-4 border-b border-surface-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-ink-400" />
                    <h2 className="text-sm font-semibold text-ink-900">Sales Order Tertunda</h2>
                  </div>
                  <span className="text-xs text-ink-400">{pendingOrders.length} order</span>
                </div>
                <div className="divide-y divide-surface-100">
                  {pendingOrders.length === 0 ? (
                    <div className="px-5 py-8 text-center">
                      <p className="text-sm text-ink-400">Tidak ada order tertunda</p>
                    </div>
                  ) : (
                    pendingOrders.slice(0, 5).map(order => (
                      <div key={order.id} className="px-5 py-3.5 flex items-center justify-between hover:bg-surface-50 transition-colors">
                        <div>
                          <p className="text-sm font-medium text-ink-900">{order.order_number}</p>
                          <p className="text-xs text-ink-400 mt-0.5">{formatDate(order.order_date)}</p>
                        </div>
                        <StatusBadge status={order.status} />
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Low stock products */}
            {hasPermission('view_inventory') && (
              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="px-5 py-4 border-b border-surface-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-500" />
                    <h2 className="text-sm font-semibold text-ink-900">Stok Rendah</h2>
                  </div>
                  <span className="text-xs text-ink-400">{lowStockItems.length} produk</span>
                </div>
                <div className="divide-y divide-surface-100">
                  {lowStockItems.length === 0 ? (
                    <div className="px-5 py-8 text-center">
                      <p className="text-sm text-ink-400">Semua stok dalam kondisi aman ✓</p>
                    </div>
                  ) : (
                    lowStockItems.slice(0, 5).map(p => (
                      <div key={p.id} className="px-5 py-3.5 flex items-center justify-between hover:bg-surface-50 transition-colors">
                        <div>
                          <p className="text-sm font-medium text-ink-900">{p.name}</p>
                          <p className="text-xs text-ink-400 mt-0.5">{p.sku}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-red-600">
                            {p.current_stock} {p.unit}
                          </p>
                          <p className="text-xs text-ink-400">min {p.minimum_stock}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
