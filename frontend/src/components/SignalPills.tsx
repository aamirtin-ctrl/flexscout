import { AlertTriangle, TrendingUp } from 'lucide-react'

export function RiskPills({ flags }: { flags: string[] }) {
  if (!flags.length) return null
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((f) => (
        <span key={f} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-red/10 text-red border border-red/20">
          <AlertTriangle size={10} /> {f.replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  )
}

export function UpsidePills({ flags }: { flags: string[] }) {
  if (!flags.length) return null
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((f) => (
        <span key={f} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-green/10 text-green border border-green/20">
          <TrendingUp size={10} /> {f.replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  )
}
