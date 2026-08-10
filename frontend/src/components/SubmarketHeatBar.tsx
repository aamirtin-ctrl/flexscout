import clsx from 'clsx'

const HEAT_COLORS: Record<number, string> = {
  1: 'bg-muted/30 text-muted',
  2: 'bg-blue-900/50 text-blue-300',
  3: 'bg-amber/20 text-amber',
  4: 'bg-orange-900/50 text-orange-300',
  5: 'bg-red/20 text-red',
}

interface Submarket {
  name: string
  heat_score: number | null
  vacancy_rate: number | null
}

export default function SubmarketHeatBar({
  submarkets,
  onSelect,
}: {
  submarkets: Submarket[]
  onSelect?: (name: string) => void
}) {
  return (
    <div className="flex gap-2 overflow-x-auto py-2 px-1">
      {submarkets.map((sm) => (
        <button
          key={sm.name}
          onClick={() => onSelect?.(sm.name)}
          className={clsx(
            'shrink-0 px-3 py-1.5 rounded-full text-xs font-medium border border-transparent hover:border-white/10 transition-colors',
            HEAT_COLORS[sm.heat_score || 1]
          )}
        >
          {sm.name.split('/')[0].trim()}
          {sm.vacancy_rate != null && (
            <span className="ml-1 opacity-70">{(sm.vacancy_rate * 100).toFixed(1)}%</span>
          )}
        </button>
      ))}
    </div>
  )
}
