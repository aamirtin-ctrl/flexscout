import { useQuery } from '@tanstack/react-query'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { ArrowUpDown } from 'lucide-react'
import { fetchDeals } from '../lib/api'
import { useFilterStore } from '../store/filters'
import TierBadge from '../components/TierBadge'
import ScoreGauge from '../components/ScoreGauge'

interface DealRow {
  id: number
  deal_type: string
  score: number
  tier: string
  narrative: string
  status: string
  comp_count: number
  created_at: string
  parcel: {
    address: string
    acreage: number | null
    zoning_code: string | null
    land_value: number | null
    county: string
    is_delinquent: boolean
  }
}

const col = createColumnHelper<DealRow>()

const columns = [
  col.accessor('tier', {
    header: 'Tier',
    cell: (info) => <TierBadge tier={info.getValue()} />,
    size: 60,
  }),
  col.accessor('score', {
    header: 'Score',
    cell: (info) => <ScoreGauge score={info.getValue()} size="sm" />,
    size: 120,
  }),
  col.accessor('deal_type', {
    header: 'Type',
    cell: (info) => (
      <span className="text-xs">{info.getValue() === 'land' ? '🏗 Land' : '🏭 Flip'}</span>
    ),
    size: 80,
  }),
  col.accessor('parcel.address', {
    header: 'Address',
    cell: (info) => <span className="truncate block max-w-[200px]">{info.getValue() || '—'}</span>,
  }),
  col.accessor('parcel.county', {
    header: 'County',
    cell: (info) => <span className="capitalize text-xs">{info.getValue()}</span>,
    size: 80,
  }),
  col.accessor('parcel.land_value', {
    header: 'Price',
    cell: (info) => {
      const v = info.getValue()
      return <span className="font-mono text-xs">{v ? `$${(v / 1000).toFixed(0)}k` : '—'}</span>
    },
    size: 80,
  }),
  col.accessor('parcel.acreage', {
    header: 'Size',
    cell: (info) => {
      const v = info.getValue()
      return <span className="font-mono text-xs">{v ? `${v.toFixed(1)} ac` : '—'}</span>
    },
    size: 80,
  }),
  col.accessor('parcel.zoning_code', {
    header: 'Zoning',
    cell: (info) => <span className="text-xs font-mono">{info.getValue() || '—'}</span>,
    size: 70,
  }),
  col.accessor('parcel.is_delinquent', {
    header: 'Signals',
    cell: (info) =>
      info.getValue() ? (
        <span className="text-xs px-1.5 py-0.5 rounded bg-red/10 text-red">Delinquent</span>
      ) : null,
    size: 100,
  }),
  col.accessor('comp_count', {
    header: 'Comps',
    cell: (info) => <span className="text-xs font-mono">{info.getValue()}</span>,
    size: 60,
  }),
  col.accessor('status', {
    header: 'Status',
    cell: (info) => (
      <span className="text-xs capitalize px-2 py-0.5 rounded bg-white/5">{info.getValue()}</span>
    ),
    size: 100,
  }),
]

export default function DealList() {
  const params = useFilterStore((s) => s.getQueryParams())
  const setSelectedDealId = useFilterStore((s) => s.setSelectedDealId)
  const maxLandPricePerSqft = useFilterStore((s) => s.maxLandPricePerSqft)
  const setMaxLandPricePerSqft = useFilterStore((s) => s.setMaxLandPricePerSqft)
  const minScore = useFilterStore((s) => s.minScore)
  const setMinScore = useFilterStore((s) => s.setMinScore)
  const county = useFilterStore((s) => s.county)
  const setCounty = useFilterStore((s) => s.setCounty)
  const [sorting, setSorting] = useState<SortingState>([{ id: 'score', desc: true }])
  const [page, setPage] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ['deals-list', params, page],
    queryFn: () => fetchDeals({ ...params, limit: 50, offset: page * 50 }),
  })

  const table = useReactTable({
    data: data?.deals || [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border gap-4 flex-wrap">
        <h1 className="text-sm font-medium">
          Deals <span className="text-muted">({data?.total || 0})</span>
        </h1>

        <div className="flex items-center gap-3 text-xs">
          <label className="flex items-center gap-1.5">
            <span className="text-muted">County</span>
            <select
              value={county}
              onChange={(e) => setCounty(e.target.value)}
              className="bg-bg border border-border rounded px-2 py-1 text-xs"
            >
              <option value="all">All</option>
              <option value="dallas">Dallas</option>
              <option value="tarrant">Tarrant</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <span className="text-muted">Min score</span>
            <input
              type="number"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value) || 0)}
              className="w-16 bg-bg border border-border rounded px-2 py-1 text-xs"
            />
          </label>
          <label className="flex items-center gap-1.5">
            <span className="text-muted">Max land $/sqft</span>
            <input
              type="number"
              step="1"
              value={maxLandPricePerSqft ?? ''}
              onChange={(e) =>
                setMaxLandPricePerSqft(e.target.value === '' ? null : Number(e.target.value))
              }
              placeholder="e.g. 10"
              className="w-20 bg-bg border border-border rounded px-2 py-1 text-xs"
            />
          </label>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-2 py-1 text-xs text-muted hover:text-text disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-xs text-muted py-1">Page {page + 1}</span>
          <button
            onClick={() => data?.has_more && setPage(page + 1)}
            disabled={!data?.has_more}
            className="px-2 py-1 text-xs text-muted hover:text-text disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-muted">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface z-10">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="text-left text-xs text-muted font-normal px-3 py-2 border-b border-border cursor-pointer select-none hover:text-text"
                      style={{ width: header.getSize() }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        <ArrowUpDown size={10} className="opacity-40" />
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-border/30 hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => setSelectedDealId(row.original.id)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
