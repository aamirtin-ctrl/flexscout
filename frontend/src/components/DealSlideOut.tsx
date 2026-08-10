import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, MapPin, Send } from 'lucide-react'
import { useState } from 'react'
import { fetchDeal, updateDeal, addDealNote } from '../lib/api'
import { useFilterStore } from '../store/filters'
import TierBadge from './TierBadge'
import ScoreGauge from './ScoreGauge'
import { RiskPills, UpsidePills } from './SignalPills'
import CompTable from './CompTable'

const STATUSES = ['new', 'researching', 'underwriting', 'active', 'pass']

export default function DealSlideOut({ dealId }: { dealId: number }) {
  const setSelectedDealId = useFilterStore((s) => s.setSelectedDealId)
  const queryClient = useQueryClient()
  const [noteText, setNoteText] = useState('')

  const { data: deal, isLoading } = useQuery({
    queryKey: ['deal', dealId],
    queryFn: () => fetchDeal(dealId),
  })

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateDeal(dealId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deal', dealId] }),
  })

  const noteMutation = useMutation({
    mutationFn: () => addDealNote(dealId, { note: noteText, author: 'User' }),
    onSuccess: () => {
      setNoteText('')
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] })
    },
  })

  if (isLoading) {
    return (
      <div className="fixed right-0 top-0 h-full w-[480px] bg-surface border-l border-border z-50 flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  if (!deal) return null

  return (
    <div className="fixed right-0 top-0 h-full w-[480px] bg-surface border-l border-border z-50 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-surface border-b border-border p-4 z-10">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <MapPin size={14} className="text-muted" />
              <span className="text-sm font-medium">{deal.parcel?.address || 'Unknown'}</span>
            </div>
            <div className="flex items-center gap-3">
              <TierBadge tier={deal.tier} />
              <ScoreGauge score={deal.score} />
              <span className="text-xs text-muted capitalize">{deal.deal_type} Deal</span>
            </div>
          </div>
          <button onClick={() => setSelectedDealId(null)} className="text-muted hover:text-text p-1">
            <X size={18} />
          </button>
        </div>

        {/* Status selector */}
        <div className="flex gap-1 mt-3">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => statusMutation.mutate(s)}
              className={`px-2 py-1 rounded text-xs capitalize transition-colors ${
                deal.status === s
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'text-muted hover:text-text hover:bg-white/5'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* AI Narrative */}
        <section className="bg-bg rounded-lg p-3 border border-border">
          <h3 className="text-xs text-muted uppercase tracking-wider mb-2">AI Analysis</h3>
          <p className="text-sm leading-relaxed">{deal.narrative}</p>
          <div className="mt-3 space-y-2">
            <RiskPills flags={deal.risk_flags} />
            <UpsidePills flags={deal.upside_flags} />
          </div>
        </section>

        {/* Key Metrics */}
        <section className="bg-bg rounded-lg p-3 border border-border">
          <h3 className="text-xs text-muted uppercase tracking-wider mb-2">Key Metrics</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {[
              ['Acreage', deal.parcel?.acreage ? `${deal.parcel.acreage} ac` : '—'],
              ['Zoning', deal.parcel?.zoning_code || '—'],
              ['County', deal.parcel?.county || '—'],
              ['Land Value', deal.parcel?.land_value ? `$${(deal.parcel.land_value / 1000).toFixed(0)}k` : '—'],
              ['Owner Since', deal.parcel?.owner_since || '—'],
              ['Delinquent', deal.parcel?.is_delinquent ? `Yes ${deal.parcel.delinquency_amt ? '$' + deal.parcel.delinquency_amt.toLocaleString() : ''}` : 'No'],
            ].map(([label, value]) => (
              <div key={label}>
                <span className="text-muted text-xs">{label}</span>
                <div className="font-mono">{value}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Comps */}
        <section className="bg-bg rounded-lg p-3 border border-border">
          <h3 className="text-xs text-muted uppercase tracking-wider mb-2">
            Comparable Sales ({deal.comps?.length || 0})
          </h3>
          <CompTable comps={deal.comps || []} />
        </section>

        {/* Submarket */}
        {deal.submarket_stats && (
          <section className="bg-bg rounded-lg p-3 border border-border">
            <h3 className="text-xs text-muted uppercase tracking-wider mb-2">Submarket</h3>
            <div className="text-sm font-medium mb-2">{deal.submarket_stats.name}</div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <span className="text-muted text-xs">Vacancy</span>
                <div className="font-mono">
                  {deal.submarket_stats.vacancy_rate
                    ? `${(deal.submarket_stats.vacancy_rate * 100).toFixed(1)}%`
                    : '—'}
                </div>
              </div>
              <div>
                <span className="text-muted text-xs">Avg Rent NNN</span>
                <div className="font-mono">
                  {deal.submarket_stats.avg_asking_rent_nnn
                    ? `$${deal.submarket_stats.avg_asking_rent_nnn.toFixed(2)}`
                    : '—'}
                </div>
              </div>
              <div>
                <span className="text-muted text-xs">Rent Trend</span>
                <div className="font-mono">
                  {deal.submarket_stats.rent_trend_12mo
                    ? `${(deal.submarket_stats.rent_trend_12mo * 100).toFixed(1)}%`
                    : '—'}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Notes */}
        <section className="bg-bg rounded-lg p-3 border border-border">
          <h3 className="text-xs text-muted uppercase tracking-wider mb-2">Notes</h3>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && noteText && noteMutation.mutate()}
              placeholder="Add a note..."
              className="flex-1 bg-surface border border-border rounded px-3 py-1.5 text-sm outline-none focus:border-primary/50"
            />
            <button
              onClick={() => noteText && noteMutation.mutate()}
              className="p-2 text-primary hover:bg-primary/10 rounded"
            >
              <Send size={14} />
            </button>
          </div>
          <div className="space-y-2">
            {deal.notes?.map((n: any) => (
              <div key={n.id} className="text-sm">
                <span className="text-muted text-xs">
                  {n.author || 'Anonymous'} &middot; {n.created_at?.split('T')[0]}
                </span>
                <p>{n.note}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
