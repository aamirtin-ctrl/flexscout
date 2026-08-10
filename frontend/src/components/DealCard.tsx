import { Building2, MapPin } from 'lucide-react'
import TierBadge from './TierBadge'
import ScoreGauge from './ScoreGauge'
import { useFilterStore } from '../store/filters'

interface Deal {
  id: number
  deal_type: string
  score: number
  tier: string
  narrative: string
  status: string
  parcel: {
    address: string
    acreage: number | null
    zoning_code: string | null
    county: string
  }
}

export default function DealCard({ deal }: { deal: Deal }) {
  const setSelectedDealId = useFilterStore((s) => s.setSelectedDealId)

  return (
    <div
      className="p-3 bg-surface border border-border rounded-lg cursor-pointer hover:border-primary/40 transition-colors"
      onClick={() => setSelectedDealId(deal.id)}
    >
      <div className="flex items-start gap-3">
        <TierBadge tier={deal.tier} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <ScoreGauge score={deal.score} size="sm" />
            <span className="text-xs text-muted">
              {deal.deal_type === 'land' ? '🏗' : '🏭'} {deal.deal_type}
            </span>
          </div>
          <div className="flex items-center gap-1 text-sm truncate">
            <MapPin size={12} className="text-muted shrink-0" />
            <span className="truncate">{deal.parcel?.address || 'Unknown'}</span>
          </div>
          <p className="text-xs text-muted mt-1 line-clamp-2">{deal.narrative}</p>
        </div>
      </div>
    </div>
  )
}
