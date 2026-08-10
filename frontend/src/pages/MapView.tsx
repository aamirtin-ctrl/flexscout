import { useQuery } from '@tanstack/react-query'
import { useRef, useEffect } from 'react'
import mapboxgl from 'mapbox-gl'
import { fetchDeals } from '../lib/api'
import { useFilterStore } from '../store/filters'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

const TIER_COLORS: Record<string, string> = { A: '#10b981', B: '#3b82f6', C: '#f59e0b' }

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const params = useFilterStore((s) => s.getQueryParams())
  const setSelectedDealId = useFilterStore((s) => s.setSelectedDealId)
  const {
    dealType, tiers, minScore, county,
    maxLandPricePerSqft,
    setDealType, setTiers, setMinScore, setCounty,
    setMaxLandPricePerSqft,
  } = useFilterStore()

  const { data } = useQuery({
    queryKey: ['deals-map', params],
    queryFn: () => fetchDeals({ ...params, limit: 100 }),
  })

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return
    if (!mapboxgl.accessToken) return

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-96.85, 32.80],
      zoom: 10,
    })
    map.addControl(new mapboxgl.NavigationControl(), 'top-right')
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !data?.deals) return

    document.querySelectorAll('.map-deal-marker').forEach((el) => el.remove())

    data.deals.forEach((deal: any) => {
      if (!deal.parcel?.lat || !deal.parcel?.lng) return

      const color = TIER_COLORS[deal.tier] || '#64748b'
      const size = deal.deal_type === 'land'
        ? Math.max(8, Math.min(20, (deal.parcel.acreage || 1) * 5))
        : 12

      const el = document.createElement('div')
      el.className = 'map-deal-marker'
      el.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid ${color}60;cursor:pointer;`
      el.title = `${deal.tier} ${deal.score} — ${deal.parcel.address}`

      el.addEventListener('click', () => {
        setSelectedDealId(deal.id)
      })

      new mapboxgl.Marker(el).setLngLat([deal.parcel.lng, deal.parcel.lat]).addTo(map)
    })
  }, [data])

  return (
    <div className="h-full flex">
      {/* Filter sidebar */}
      <div className="w-56 bg-surface border-r border-border p-3 space-y-4 overflow-y-auto shrink-0">
        <h2 className="text-xs text-muted uppercase tracking-wider">Filters</h2>

        <div>
          <label className="text-xs text-muted block mb-1">Deal Type</label>
          <div className="flex gap-1">
            {['all', 'land', 'flip'].map((t) => (
              <button
                key={t}
                onClick={() => setDealType(t)}
                className={`px-2 py-1 rounded text-xs capitalize ${
                  dealType === t ? 'bg-primary/20 text-primary' : 'text-muted hover:text-text'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-muted block mb-1">Tier</label>
          <div className="flex gap-1">
            {['A', 'B', 'C'].map((t) => (
              <button
                key={t}
                onClick={() =>
                  setTiers(tiers.includes(t) ? tiers.filter((x) => x !== t) : [...tiers, t])
                }
                className={`px-2 py-1 rounded text-xs ${
                  tiers.includes(t) ? 'bg-primary/20 text-primary' : 'text-muted hover:text-text'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-muted block mb-1">Min Score: {minScore}</label>
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="text-xs text-muted block mb-1">County</label>
          <div className="flex gap-1 flex-wrap">
            {['all', 'dallas', 'tarrant'].map((c) => (
              <button
                key={c}
                onClick={() => setCounty(c)}
                className={`px-2 py-1 rounded text-xs capitalize ${
                  county === c ? 'bg-primary/20 text-primary' : 'text-muted hover:text-text'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-3 border-t border-border space-y-3">
          <h3 className="text-xs text-muted uppercase tracking-wider">Thresholds</h3>
          <div>
            <label className="text-xs text-muted block mb-1">
              Max land cost ($/sqft) {maxLandPricePerSqft != null && <span className="text-primary">{maxLandPricePerSqft}</span>}
            </label>
            <input
              type="number"
              step="1"
              value={maxLandPricePerSqft ?? ''}
              onChange={(e) =>
                setMaxLandPricePerSqft(e.target.value === '' ? null : Number(e.target.value))
              }
              placeholder="e.g. 10"
              className="w-full bg-bg border border-border rounded px-2 py-1 text-xs"
            />
          </div>
        </div>

        <div className="text-xs text-muted pt-2 border-t border-border">
          {data?.total || 0} deals on map
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <div ref={mapContainer} className="absolute inset-0" />
        {!mapboxgl.accessToken && (
          <div className="absolute inset-0 flex items-center justify-center bg-bg/80 text-muted">
            Set VITE_MAPBOX_TOKEN to enable map
          </div>
        )}
      </div>
    </div>
  )
}
