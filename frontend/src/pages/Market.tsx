import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchMarketOverview, fetchNationalMarkets } from '../lib/api'

const HEAT_BG: Record<number, string> = {
  1: 'bg-muted/10',
  2: 'bg-blue-900/20',
  3: 'bg-amber/10',
  4: 'bg-orange-900/20',
  5: 'bg-red/10',
}

export default function Market() {
  const [tab, setTab] = useState<'dfw' | 'national'>('dfw')

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-1 border-b border-border">
        <TabBtn active={tab === 'dfw'} onClick={() => setTab('dfw')}>DFW Submarkets</TabBtn>
        <TabBtn active={tab === 'national'} onClick={() => setTab('national')}>National Markets</TabBtn>
      </div>

      {tab === 'dfw' ? <DFWView /> : <NationalView />}
    </div>
  )
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: any
}) {
  return (
    <button
      onClick={onClick}
      className={`text-sm px-4 py-2 border-b-2 -mb-px ${
        active ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-text'
      }`}
    >
      {children}
    </button>
  )
}

function DFWView() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['market-overview'],
    queryFn: fetchMarketOverview,
  })

  if (isLoading) return <div className="pt-8 text-muted">Loading DFW data...</div>

  return (
    <>
      <div className="bg-surface rounded-lg p-4 border border-border">
        <h1 className="text-sm font-medium mb-3">DFW Market Snapshot</h1>
        <div className="grid grid-cols-4 gap-4">
          <Kpi label="Vacancy Rate" value={overview?.overall_vacancy_rate != null ? `${(overview.overall_vacancy_rate * 100).toFixed(1)}%` : '—'} />
          <Kpi label="Avg NNN Rent" value={`$${overview?.avg_asking_rent_nnn?.toFixed(2) || '—'}`} />
          <Kpi
            label="Rent Trend (12mo)"
            value={
              overview?.rent_trend_12mo
                ? `${overview.rent_trend_12mo > 0 ? '+' : ''}${(overview.rent_trend_12mo * 100).toFixed(1)}%`
                : '—'
            }
          />
          <Kpi label="Active Listings" value={overview?.active_listing_count || 0} />
        </div>
        {overview?.as_of && (
          <p className="text-xs text-muted mt-3">As of {overview.as_of}</p>
        )}
      </div>

      <div>
        <h2 className="text-xs text-muted uppercase tracking-wider mb-3 mt-6">Submarkets</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {(overview?.submarkets || []).map((sm: any) => (
            <div
              key={sm.name}
              className={`rounded-lg p-4 border border-border ${HEAT_BG[sm.heat_score || 1]}`}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-medium truncate pr-2">{sm.name}</h3>
                <span className="text-xs font-mono shrink-0">
                  {'█'.repeat(sm.heat_score || 0)}{'░'.repeat(5 - (sm.heat_score || 0))} {sm.heat_score}/5
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted">Vacancy</span>
                  <div className="font-mono">
                    {sm.vacancy_rate != null ? `${(sm.vacancy_rate * 100).toFixed(1)}%` : '—'}
                  </div>
                </div>
                <div>
                  <span className="text-muted">Avg Rent</span>
                  <div className="font-mono">
                    ${sm.avg_asking_rent_nnn?.toFixed(2) || '—'}
                  </div>
                </div>
                <div className="col-span-2">
                  <span className="text-muted">Rent Trend</span>
                  <div className="font-mono">
                    {sm.rent_trend_12mo != null
                      ? `${sm.rent_trend_12mo > 0 ? '▲' : '▼'} ${(sm.rent_trend_12mo * 100).toFixed(1)}% YoY`
                      : '—'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {!overview?.submarkets?.length && (
        <p className="text-sm text-muted text-center py-8">
          No submarket data yet. Run the MarketTrendAgent to populate.
        </p>
      )}
    </>
  )
}

function NationalView() {
  const [maxVac, setMaxVac] = useState<number | ''>(4) // percent
  const [marketType, setMarketType] = useState('emerging')
  const [maxLand, setMaxLand] = useState<number | ''>('')
  const [sortBy, setSortBy] = useState('vacancy')

  const params: Record<string, any> = { sort_by: sortBy }
  if (typeof maxVac === 'number') params.max_vacancy_rate = maxVac / 100
  if (marketType !== 'all') params.market_type = marketType
  if (typeof maxLand === 'number') params.max_land_price_per_sqft = maxLand

  const { data, isLoading } = useQuery({
    queryKey: ['national-markets', params],
    queryFn: () => fetchNationalMarkets(params),
  })

  const markets: any[] = data?.markets || []

  return (
    <div className="space-y-4">
      <div className="bg-surface border border-border rounded-lg p-4 grid grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-muted block mb-1">Max vacancy rate (%)</label>
          <input
            type="number"
            value={maxVac}
            onChange={(e) => setMaxVac(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Market type</label>
          <select
            value={marketType}
            onChange={(e) => setMarketType(e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
          >
            <option value="all">All</option>
            <option value="emerging">Emerging</option>
            <option value="primary">Primary</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Max land cost ($/sqft)</label>
          <input
            type="number"
            value={maxLand}
            onChange={(e) => setMaxLand(e.target.value === '' ? '' : Number(e.target.value))}
            placeholder="10"
            className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Sort by</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
          >
            <option value="vacancy">Vacancy (low → high)</option>
            <option value="rent">Rent (high → low)</option>
            <option value="land_cost">Land $/sqft (low → high)</option>
            <option value="metro">Metro name</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-muted text-sm">Loading national markets…</p>}

      {!isLoading && markets.length === 0 && (
        <div className="bg-surface border border-border rounded-lg p-8 text-center">
          <p className="text-sm text-muted">
            No national market data matches your filters.
          </p>
          <p className="text-xs text-muted mt-2">
            Go to the <b>Alerts</b> page and click <b>Refresh National Data</b> to pull the latest
            CommercialEdge / CBRE industrial report.
          </p>
        </div>
      )}

      {markets.length > 0 && (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-bg/50">
              <tr className="text-xs text-muted uppercase tracking-wider">
                <th className="text-left py-2 px-3">Metro</th>
                <th className="text-left py-2 px-3">State</th>
                <th className="text-left py-2 px-3">Type</th>
                <th className="text-right py-2 px-3">Vacancy</th>
                <th className="text-right py-2 px-3">Avg Rent NNN</th>
                <th className="text-right py-2 px-3">Land $/sqft</th>
                <th className="text-left py-2 px-3">Source</th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => (
                <tr key={m.id} className="border-t border-border hover:bg-white/5">
                  <td className="py-2 px-3 font-medium">{m.metro}</td>
                  <td className="py-2 px-3 text-muted">{m.state || '—'}</td>
                  <td className="py-2 px-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        m.market_type === 'emerging' ? 'bg-green/10 text-green' : 'bg-muted/10 text-muted'
                      }`}
                    >
                      {m.market_type || '—'}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {m.vacancy_rate != null ? `${(m.vacancy_rate * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {m.avg_asking_rent_nnn != null ? `$${m.avg_asking_rent_nnn.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {m.avg_land_price_per_sqft != null ? `$${m.avg_land_price_per_sqft.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 px-3 text-xs text-muted">
                    {m.source_url ? (
                      <a href={m.source_url} target="_blank" rel="noopener" className="hover:text-primary">
                        {m.source}
                      </a>
                    ) : (
                      m.source
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Kpi({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <span className="text-xs text-muted block">{label}</span>
      <span className="text-2xl font-mono font-bold">{value}</span>
    </div>
  )
}
