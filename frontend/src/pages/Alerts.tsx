import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Bell, Plus, Trash2, Play, Zap, TrendingDown, DollarSign, Landmark } from 'lucide-react'
import {
  fetchSubscribers,
  createSubscriber,
  deleteSubscriber,
  previewDigest,
  fetchDigests,
  fetchDigest,
  triggerAgent,
  Subscriber,
  SubscriberFilters,
} from '../lib/api'

type NewSub = {
  name: string
  email: string
  filters: SubscriberFilters
}

const BLANK: NewSub = {
  name: '',
  email: '',
  filters: {
    min_lease_rate_nnn: null,
    min_new_build_rent_nnn: null,
    max_land_price_per_sqft: null,
    max_vacancy_rate: null,
    market_type: null,
    min_deal_score: 70,
    county: null,
  },
}

// Quick-start presets the user described: flex lease >$13, new rent >$16, land <$10, emerging < 4% vacancy
const PRESETS: { id: string; label: string; icon: any; filters: SubscriberFilters }[] = [
  {
    id: 'flex_lease_13',
    label: 'Flex lease rates ≥ $13/sqft',
    icon: DollarSign,
    filters: { min_lease_rate_nnn: 13 },
  },
  {
    id: 'flex_lease_14',
    label: 'Flex lease rates ≥ $14/sqft',
    icon: DollarSign,
    filters: { min_lease_rate_nnn: 14 },
  },
  {
    id: 'new_flex_16',
    label: 'New-build flex rent ≥ $16/sqft',
    icon: Zap,
    filters: { min_new_build_rent_nnn: 16 },
  },
  {
    id: 'land_10',
    label: 'Land cost ≤ $10/sqft',
    icon: Landmark,
    filters: { max_land_price_per_sqft: 10 },
  },
  {
    id: 'emerging_4',
    label: 'Emerging US markets (vacancy < 4%)',
    icon: TrendingDown,
    filters: { max_vacancy_rate: 0.04, market_type: 'emerging' },
  },
  {
    id: 'dfw_deals',
    label: 'DFW deals (score ≥ 70)',
    icon: Bell,
    filters: { county: 'dallas', min_deal_score: 70 },
  },
]

export default function Alerts() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<NewSub>(BLANK)
  const [openDigestId, setOpenDigestId] = useState<number | null>(null)

  const { data: subs } = useQuery({
    queryKey: ['subscribers'],
    queryFn: () => fetchSubscribers(),
  })

  const { data: digests } = useQuery({
    queryKey: ['digests'],
    queryFn: () => fetchDigests({ limit: 20 }),
  })

  const { data: openDigest } = useQuery({
    queryKey: ['digest', openDigestId],
    queryFn: () => fetchDigest(openDigestId as number),
    enabled: openDigestId != null,
  })

  const createMut = useMutation({
    mutationFn: () =>
      createSubscriber({
        name: form.name,
        email: form.email || undefined,
        filters: stripNulls(form.filters),
        delivery: 'digest',
        frequency: '2x_weekly',
        active: true,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscribers'] })
      setForm(BLANK)
      setShowCreate(false)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteSubscriber(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscribers'] }),
  })

  const previewMut = useMutation({
    mutationFn: (id: number) => previewDigest(id),
  })

  const runDigestNow = useMutation({
    mutationFn: () => triggerAgent('market_digest'),
    onSuccess: () =>
      setTimeout(() => qc.invalidateQueries({ queryKey: ['digests'] }), 1500),
  })

  const refreshMarketsNow = useMutation({
    mutationFn: () => triggerAgent('national_market'),
  })

  function togglePreset(p: (typeof PRESETS)[number]) {
    setForm((f) => ({ ...f, filters: { ...f.filters, ...p.filters } }))
  }

  function setFilter<K extends keyof SubscriberFilters>(k: K, v: SubscriberFilters[K]) {
    setForm((f) => ({ ...f, filters: { ...f.filters, [k]: v } }))
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-medium flex items-center gap-2">
            <Bell size={18} /> Market Alerts & Digests
          </h1>
          <p className="text-xs text-muted mt-1">
            Subscribers get a digest every Monday &amp; Thursday matching their filter thresholds.
            SMS delivery is disabled — digests are viewable in-app.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refreshMarketsNow.mutate()}
            className="text-xs px-3 py-2 border border-border rounded hover:bg-white/5"
            disabled={refreshMarketsNow.isPending}
          >
            {refreshMarketsNow.isPending ? 'Refreshing…' : 'Refresh National Data'}
          </button>
          <button
            onClick={() => runDigestNow.mutate()}
            className="text-xs px-3 py-2 border border-border rounded hover:bg-white/5"
            disabled={runDigestNow.isPending}
          >
            {runDigestNow.isPending ? 'Running…' : 'Run Digest Now'}
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-xs px-3 py-2 bg-primary text-white rounded flex items-center gap-1"
          >
            <Plus size={14} /> New Subscriber
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Name (e.g. 'Aamir — DFW + Emerging')"
              className="bg-bg border border-border rounded px-3 py-2 text-sm outline-none focus:border-primary/50"
            />
            <input
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="Email (optional)"
              className="bg-bg border border-border rounded px-3 py-2 text-sm outline-none focus:border-primary/50"
            />
          </div>

          <div>
            <p className="text-xs text-muted uppercase tracking-wider mb-2">Quick presets</p>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => {
                const Icon = p.icon
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePreset(p)}
                    className="text-xs px-3 py-1.5 border border-border rounded-full hover:border-primary/50 hover:bg-primary/5 flex items-center gap-1.5"
                  >
                    <Icon size={12} /> {p.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <NumInput
              label="Min flex lease rate ($/sqft NNN)"
              value={form.filters.min_lease_rate_nnn}
              onChange={(v) => setFilter('min_lease_rate_nnn', v)}
              placeholder="13"
            />
            <NumInput
              label="Min NEW flex rent ($/sqft NNN)"
              value={form.filters.min_new_build_rent_nnn}
              onChange={(v) => setFilter('min_new_build_rent_nnn', v)}
              placeholder="16"
            />
            <NumInput
              label="Max land cost ($/sqft)"
              value={form.filters.max_land_price_per_sqft}
              onChange={(v) => setFilter('max_land_price_per_sqft', v)}
              placeholder="10"
            />
            <NumInput
              label="Max vacancy rate (%)"
              value={
                form.filters.max_vacancy_rate != null
                  ? form.filters.max_vacancy_rate * 100
                  : null
              }
              onChange={(v) => setFilter('max_vacancy_rate', v != null ? v / 100 : null)}
              placeholder="4"
            />
            <div>
              <label className="text-xs text-muted block mb-1">Market type</label>
              <select
                value={form.filters.market_type || ''}
                onChange={(e) => setFilter('market_type', e.target.value || null)}
                className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
              >
                <option value="">Any</option>
                <option value="emerging">Emerging (US)</option>
                <option value="primary">Primary</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">DFW county</label>
              <select
                value={form.filters.county || ''}
                onChange={(e) => setFilter('county', e.target.value || null)}
                className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
              >
                <option value="">Any</option>
                <option value="dallas">Dallas</option>
                <option value="tarrant">Tarrant</option>
              </select>
            </div>
            <NumInput
              label="Min deal score"
              value={form.filters.min_deal_score ?? null}
              onChange={(v) => setFilter('min_deal_score', v != null ? Math.round(v) : null)}
              placeholder="70"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => form.name && createMut.mutate()}
              disabled={!form.name || createMut.isPending}
              className="px-4 py-2 bg-primary text-white rounded text-sm disabled:opacity-50"
            >
              {createMut.isPending ? 'Saving…' : 'Save Subscriber'}
            </button>
            <button
              onClick={() => {
                setForm(BLANK)
                setShowCreate(false)
              }}
              className="px-4 py-2 border border-border rounded text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Subscribers list */}
      <section>
        <h2 className="text-xs text-muted uppercase tracking-wider mb-2">Subscribers</h2>
        <div className="space-y-2">
          {(subs?.subscribers || []).map((s) => (
            <SubscriberRow
              key={s.id}
              sub={s}
              onDelete={() => deleteMut.mutate(s.id)}
              onPreview={async () => {
                const r = await previewMut.mutateAsync(s.id)
                // Re-use digest modal UI by synthesising a digest-like object
                alert(
                  `Preview: ${r.match_count} matches\n\n` +
                    `Emerging markets: ${r.payload.emerging_markets.length}\n` +
                    `Listings: ${r.payload.matching_listings.length}\n` +
                    `DFW deals: ${r.payload.matching_deals.length}`,
                )
              }}
            />
          ))}
          {!subs?.subscribers?.length && (
            <p className="text-sm text-muted text-center py-8">
              No subscribers yet. Click <b>New Subscriber</b> above to configure alert filters.
            </p>
          )}
        </div>
      </section>

      {/* Digest history */}
      <section>
        <h2 className="text-xs text-muted uppercase tracking-wider mb-2">Recent Digests</h2>
        <div className="space-y-1">
          {(digests?.digests || []).map((d: any) => (
            <button
              key={d.id}
              onClick={() => setOpenDigestId(d.id)}
              className="w-full text-left bg-surface border border-border rounded p-3 hover:border-primary/40 flex items-center justify-between"
            >
              <div>
                <div className="text-sm">{d.subscriber_name || '(deleted subscriber)'}</div>
                <div className="text-xs text-muted">
                  {d.period_start} → {d.period_end} &middot; generated{' '}
                  {d.generated_at ? new Date(d.generated_at).toLocaleString() : ''}
                </div>
              </div>
              <span className="text-xs font-mono bg-primary/10 text-primary px-2 py-0.5 rounded">
                {d.match_count} matches
              </span>
            </button>
          ))}
          {!digests?.digests?.length && (
            <p className="text-sm text-muted text-center py-8">
              No digests yet. Digests fire Mon + Thu at 9am UTC or click <b>Run Digest Now</b>.
            </p>
          )}
        </div>
      </section>

      {/* Digest detail modal */}
      {openDigestId != null && openDigest && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
          onClick={() => setOpenDigestId(null)}
        >
          <div
            className="bg-bg border border-border rounded-lg max-w-4xl w-full max-h-[85vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <DigestDetail digest={openDigest} />
            <div className="p-4 border-t border-border flex justify-end">
              <button
                onClick={() => setOpenDigestId(null)}
                className="text-xs px-3 py-1.5 border border-border rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SubscriberRow({
  sub,
  onDelete,
  onPreview,
}: {
  sub: Subscriber
  onDelete: () => void
  onPreview: () => void
}) {
  const f = sub.filters || {}
  const chips: string[] = []
  if (f.min_lease_rate_nnn != null) chips.push(`lease ≥ $${f.min_lease_rate_nnn}`)
  if (f.min_new_build_rent_nnn != null) chips.push(`new-build rent ≥ $${f.min_new_build_rent_nnn}`)
  if (f.max_land_price_per_sqft != null) chips.push(`land ≤ $${f.max_land_price_per_sqft}/sqft`)
  if (f.max_vacancy_rate != null) chips.push(`vacancy < ${(f.max_vacancy_rate * 100).toFixed(1)}%`)
  if (f.market_type) chips.push(f.market_type)
  if (f.county) chips.push(f.county)
  if (f.min_deal_score) chips.push(`score ≥ ${f.min_deal_score}`)

  return (
    <div className="bg-surface border border-border rounded-lg p-3 flex items-center justify-between gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{sub.name}</span>
          {sub.email && <span className="text-xs text-muted">{sub.email}</span>}
          {!sub.active && <span className="text-xs text-red px-1.5 py-0.5 bg-red/10 rounded">inactive</span>}
        </div>
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {chips.length ? (
            chips.map((c, i) => (
              <span
                key={i}
                className="text-xs bg-bg border border-border rounded-full px-2 py-0.5"
              >
                {c}
              </span>
            ))
          ) : (
            <span className="text-xs text-muted">No filter thresholds set</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={onPreview}
          title="Preview what this digest would contain right now"
          className="p-1.5 text-muted hover:text-primary"
        >
          <Play size={14} />
        </button>
        <button
          onClick={onDelete}
          title="Delete subscriber"
          className="p-1.5 text-muted hover:text-red"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

function DigestDetail({ digest }: { digest: any }) {
  const p = digest.payload || {}
  return (
    <div className="p-5 space-y-5">
      <div>
        <h3 className="text-sm font-medium">
          Digest for {digest.subscriber_name || '(deleted subscriber)'}
        </h3>
        <p className="text-xs text-muted">
          Generated {new Date(digest.generated_at).toLocaleString()} &middot; window{' '}
          {digest.period_start} → {digest.period_end} &middot; {digest.match_count} total matches
        </p>
      </div>

      <DigestSection title={`Emerging markets (${(p.emerging_markets || []).length})`}>
        {(p.emerging_markets || []).map((m: any, i: number) => (
          <tr key={i} className="border-t border-border">
            <td className="py-1.5 pr-3">{m.metro}{m.state ? `, ${m.state}` : ''}</td>
            <td className="py-1.5 pr-3 font-mono">
              {m.vacancy_rate != null ? `${(m.vacancy_rate * 100).toFixed(1)}%` : '—'}
            </td>
            <td className="py-1.5 pr-3 font-mono">
              {m.avg_asking_rent_nnn != null ? `$${m.avg_asking_rent_nnn.toFixed(2)}` : '—'}
            </td>
            <td className="py-1.5 pr-3 font-mono">
              {m.avg_land_price_per_sqft != null ? `$${m.avg_land_price_per_sqft.toFixed(2)}` : '—'}
            </td>
            <td className="py-1.5 pr-3 text-muted text-xs">{m.source}</td>
          </tr>
        ))}
      </DigestSection>

      <DigestSection title={`Matching listings (${(p.matching_listings || []).length})`}>
        {(p.matching_listings || []).map((l: any, i: number) => (
          <tr key={i} className="border-t border-border">
            <td className="py-1.5 pr-3">{l.address}</td>
            <td className="py-1.5 pr-3">{l.metro}</td>
            <td className="py-1.5 pr-3 font-mono">
              {l.lease_rate_nnn != null ? `$${l.lease_rate_nnn}` : '—'}
              {l.is_new_construction && <span className="ml-1 text-primary">NEW</span>}
            </td>
            <td className="py-1.5 pr-3 font-mono">
              {l.land_price_per_sqft != null ? `$${l.land_price_per_sqft}/sqft land` : '—'}
            </td>
            <td className="py-1.5 pr-3">{l.sqft?.toLocaleString()}</td>
          </tr>
        ))}
      </DigestSection>

      <DigestSection title={`DFW deals (${(p.matching_deals || []).length})`}>
        {(p.matching_deals || []).map((d: any, i: number) => (
          <tr key={i} className="border-t border-border">
            <td className="py-1.5 pr-3 font-mono">{d.tier}</td>
            <td className="py-1.5 pr-3 font-mono">{d.score}</td>
            <td className="py-1.5 pr-3">{d.address}</td>
            <td className="py-1.5 pr-3">{d.county}</td>
            <td className="py-1.5 pr-3 font-mono">{d.acreage?.toFixed(1)} ac</td>
          </tr>
        ))}
      </DigestSection>
    </div>
  )
}

function DigestSection({ title, children }: { title: string; children: any }) {
  const rows = Array.isArray(children) ? children : [children]
  return (
    <div>
      <h4 className="text-xs text-muted uppercase tracking-wider mb-2">{title}</h4>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">No matches.</p>
      ) : (
        <table className="w-full text-sm">
          <tbody>{children}</tbody>
        </table>
      )}
    </div>
  )
}

function NumInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: number | null | undefined
  onChange: (v: number | null) => void
  placeholder?: string
}) {
  return (
    <div>
      <label className="text-xs text-muted block mb-1">{label}</label>
      <input
        type="number"
        step="any"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        placeholder={placeholder}
        className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
      />
    </div>
  )
}

function stripNulls<T extends Record<string, any>>(o: T): T {
  const out: any = {}
  for (const k in o) if (o[k] != null && o[k] !== '') out[k] = o[k]
  return out
}
