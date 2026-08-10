import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchDeal } from '../lib/api'
import TierBadge from '../components/TierBadge'
import ScoreGauge from '../components/ScoreGauge'
import { RiskPills, UpsidePills } from '../components/SignalPills'
import CompTable from '../components/CompTable'

export default function DealDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: deal, isLoading } = useQuery({
    queryKey: ['deal', Number(id)],
    queryFn: () => fetchDeal(Number(id)),
    enabled: !!id,
  })

  if (isLoading) return <div className="p-8 text-muted">Loading...</div>
  if (!deal) return <div className="p-8 text-muted">Deal not found</div>

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-surface rounded-lg p-4 border border-border">
        <h1 className="text-lg font-medium mb-2">{deal.parcel?.address || 'Unknown Address'}</h1>
        <div className="flex items-center gap-4">
          <TierBadge tier={deal.tier} />
          <ScoreGauge score={deal.score} />
          <span className="text-sm text-muted capitalize">{deal.deal_type} Deal</span>
          <span className="text-xs px-2 py-1 rounded bg-white/5 capitalize">{deal.status}</span>
        </div>
      </div>

      {/* AI Narrative */}
      <div className="bg-surface rounded-lg p-4 border border-border">
        <h2 className="text-xs text-muted uppercase tracking-wider mb-2">AI Analysis</h2>
        <p className="leading-relaxed">{deal.narrative}</p>
        <div className="mt-3 space-y-2">
          <RiskPills flags={deal.risk_flags} />
          <UpsidePills flags={deal.upside_flags} />
        </div>
      </div>

      {/* Metrics + Comps side by side */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-lg p-4 border border-border">
          <h2 className="text-xs text-muted uppercase tracking-wider mb-3">Key Metrics</h2>
          <dl className="space-y-2 text-sm">
            {[
              ['Acreage', deal.parcel?.acreage ? `${deal.parcel.acreage} ac` : '—'],
              ['Zoning', `${deal.parcel?.zoning_code || '—'} ${deal.parcel?.zoning_desc ? `— ${deal.parcel.zoning_desc}` : ''}`],
              ['County', deal.parcel?.county],
              ['Land Value', deal.parcel?.land_value ? `$${deal.parcel.land_value.toLocaleString()}` : '—'],
              ['Owner', deal.parcel?.owner_name || '—'],
              ['Owner Since', deal.parcel?.owner_since || '—'],
              ['Delinquent', deal.parcel?.is_delinquent ? `Yes — $${deal.parcel?.delinquency_amt?.toLocaleString() || '?'}` : 'No'],
            ].map(([label, value]) => (
              <div key={label as string} className="flex justify-between">
                <dt className="text-muted">{label}</dt>
                <dd className="font-mono text-right">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="bg-surface rounded-lg p-4 border border-border">
          <h2 className="text-xs text-muted uppercase tracking-wider mb-3">
            Comps ({deal.comps?.length || 0})
          </h2>
          <CompTable comps={deal.comps || []} />
        </div>
      </div>

      {/* Submarket */}
      {deal.submarket_stats && (
        <div className="bg-surface rounded-lg p-4 border border-border">
          <h2 className="text-xs text-muted uppercase tracking-wider mb-2">Submarket</h2>
          <div className="text-sm font-medium mb-2">{deal.submarket_stats.name}</div>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted text-xs block">Vacancy</span>
              <span className="font-mono">{deal.submarket_stats.vacancy_rate ? `${(deal.submarket_stats.vacancy_rate * 100).toFixed(1)}%` : '—'}</span>
            </div>
            <div>
              <span className="text-muted text-xs block">Avg NNN</span>
              <span className="font-mono">${deal.submarket_stats.avg_asking_rent_nnn?.toFixed(2) || '—'}</span>
            </div>
            <div>
              <span className="text-muted text-xs block">Trend 12mo</span>
              <span className="font-mono">{deal.submarket_stats.rent_trend_12mo ? `${(deal.submarket_stats.rent_trend_12mo * 100).toFixed(1)}%` : '—'}</span>
            </div>
            <div>
              <span className="text-muted text-xs block">Heat</span>
              <span className="font-mono">{deal.submarket_stats.heat_score || '—'}/5</span>
            </div>
          </div>
        </div>
      )}

      {/* Notes */}
      <div className="bg-surface rounded-lg p-4 border border-border">
        <h2 className="text-xs text-muted uppercase tracking-wider mb-2">Notes</h2>
        {deal.notes?.length ? (
          <div className="space-y-3">
            {deal.notes.map((n: any) => (
              <div key={n.id} className="text-sm">
                <span className="text-muted text-xs">{n.author} &middot; {n.created_at?.split('T')[0]}</span>
                <p>{n.note}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No notes yet</p>
        )}
      </div>
    </div>
  )
}
