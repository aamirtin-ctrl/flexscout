import { useQuery } from '@tanstack/react-query'
import { useRef, useEffect } from 'react'
import mapboxgl from 'mapbox-gl'
import { Activity, Star, TrendingUp, Building2 } from 'lucide-react'
import { fetchDeals, fetchMarketOverview } from '../lib/api'
import { useFilterStore } from '../store/filters'
import DealCard from '../components/DealCard'
import SubmarketHeatBar from '../components/SubmarketHeatBar'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

export default function CommandCenter() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const params = useFilterStore((s) => s.getQueryParams())

  const { data: dealsData } = useQuery({
    queryKey: ['deals', params],
    queryFn: () => fetchDeals({ ...params, limit: 25 }),
  })

  const { data: overview } = useQuery({
    queryKey: ['market-overview'],
    queryFn: fetchMarketOverview,
  })

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return
    if (!mapboxgl.accessToken) return

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-96.8, 32.78],
      zoom: 10,
    })
    map.addControl(new mapboxgl.NavigationControl(), 'top-right')
    mapRef.current = map

    return () => { map.remove(); mapRef.current = null }
  }, [])

  // Add deal markers
  useEffect(() => {
    const map = mapRef.current
    if (!map || !dealsData?.deals) return

    // Remove existing markers
    document.querySelectorAll('.deal-marker').forEach((el) => el.remove())

    dealsData.deals.forEach((deal: any) => {
      if (!deal.parcel?.lat || !deal.parcel?.lng) return

      const color = deal.tier === 'A' ? '#10b981' : deal.tier === 'B' ? '#3b82f6' : '#f59e0b'
      const el = document.createElement('div')
      el.className = 'deal-marker'
      el.style.cssText = `width:12px;height:12px;border-radius:50%;background:${color};border:2px solid ${color}40;cursor:pointer;`

      new mapboxgl.Marker(el).setLngLat([deal.parcel.lng, deal.parcel.lat]).addTo(map)
    })
  }, [dealsData])

  const deals = dealsData?.deals || []
  const kpis = [
    { icon: Activity, label: 'New Deals (7d)', value: dealsData?.total || 0 },
    { icon: Star, label: 'A-Tier Active', value: deals.filter((d: any) => d.tier === 'A').length },
    { icon: TrendingUp, label: 'Avg Score', value: deals.length ? Math.round(deals.reduce((a: number, d: any) => a + d.score, 0) / deals.length) : 0 },
    { icon: Building2, label: 'DFW Vacancy', value: overview?.overall_vacancy_rate ? `${(overview.overall_vacancy_rate * 100).toFixed(1)}%` : '—' },
  ]

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface">
        <div className="flex items-center gap-2">
          <span className="text-primary font-bold">FlexScout</span>
          <span className="text-muted text-xs">DFW Deal Intelligence</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          <span>New today: <span className="text-text">{deals.filter((d: any) => d.status === 'new').length}</span></span>
          <span>A-tier: <span className="text-green">{deals.filter((d: any) => d.tier === 'A').length}</span></span>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 gap-3 p-3 border-b border-border">
        {kpis.map(({ icon: Icon, label, value }) => (
          <div key={label} className="bg-surface rounded-lg p-3 border border-border">
            <div className="flex items-center gap-2 text-muted text-xs mb-1">
              <Icon size={14} /> {label}
            </div>
            <div className="text-xl font-mono font-bold">{value}</div>
          </div>
        ))}
      </div>

      {/* Split: Map + Deal Feed */}
      <div className="flex-1 flex overflow-hidden">
        {/* Map */}
        <div className="w-3/5 relative">
          <div ref={mapContainer} className="absolute inset-0" />
          {!mapboxgl.accessToken && (
            <div className="absolute inset-0 flex items-center justify-center bg-bg/80 text-muted text-sm">
              Set VITE_MAPBOX_TOKEN to enable map
            </div>
          )}
        </div>

        {/* Deal Feed */}
        <div className="w-2/5 border-l border-border overflow-y-auto p-3 space-y-2">
          <h2 className="text-xs text-muted uppercase tracking-wider mb-2">
            Top Deals ({deals.length})
          </h2>
          {deals.map((deal: any) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
          {!deals.length && <p className="text-sm text-muted">No deals found</p>}
        </div>
      </div>

      {/* Submarket Heat Bar */}
      {overview?.submarkets?.length > 0 && (
        <div className="border-t border-border px-3">
          <SubmarketHeatBar submarkets={overview.submarkets} />
        </div>
      )}
    </div>
  )
}
