import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPipeline, updateDeal } from '../lib/api'
import { useFilterStore } from '../store/filters'
import TierBadge from '../components/TierBadge'

const COLUMNS = ['new', 'researching', 'underwriting', 'active', 'pass']

export default function Pipeline() {
  const queryClient = useQueryClient()
  const setSelectedDealId = useFilterStore((s) => s.setSelectedDealId)

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: fetchPipeline,
  })

  const moveMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => updateDeal(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pipeline'] }),
  })

  if (isLoading) return <div className="p-8 text-muted">Loading pipeline...</div>

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h1 className="text-sm font-medium">Pipeline</h1>
      </div>

      <div className="flex-1 flex gap-3 p-3 overflow-x-auto">
        {COLUMNS.map((col) => {
          const deals = data?.[col] || []
          return (
            <div key={col} className="w-72 shrink-0 flex flex-col">
              <div className="flex items-center justify-between mb-2 px-1">
                <h2 className="text-xs text-muted uppercase tracking-wider capitalize">{col}</h2>
                <span className="text-xs text-muted bg-white/5 px-1.5 rounded">{deals.length}</span>
              </div>

              <div
                className="flex-1 bg-bg rounded-lg border border-border p-2 space-y-2 overflow-y-auto"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  const id = Number(e.dataTransfer.getData('dealId'))
                  if (id) moveMutation.mutate({ id, status: col })
                }}
              >
                {deals.map((deal: any) => (
                  <div
                    key={deal.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData('dealId', String(deal.id))}
                    onClick={() => setSelectedDealId(deal.id)}
                    className="bg-surface border border-border rounded-lg p-3 cursor-pointer hover:border-primary/30 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <TierBadge tier={deal.tier} />
                      <span className="font-mono text-sm font-bold">{deal.score}</span>
                      <span className="text-xs text-muted ml-auto">
                        {deal.deal_type === 'land' ? '🏗' : '🏭'}
                      </span>
                    </div>
                    <div className="text-xs truncate">{deal.parcel?.address || 'Unknown'}</div>
                    <div className="text-xs text-muted mt-1">
                      {deal.parcel?.acreage?.toFixed(1)} ac &middot; ${(deal.parcel?.land_value / 1000)?.toFixed(0)}k &middot; {deal.parcel?.county}
                    </div>
                    {deal.parcel?.is_delinquent && (
                      <span className="text-[10px] text-red mt-1 inline-block">Delinquent</span>
                    )}
                  </div>
                ))}
                {!deals.length && (
                  <p className="text-xs text-muted text-center py-4">No deals</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
