import clsx from 'clsx'

export default function ScoreGauge({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) {
  const color =
    score >= 80 ? 'bg-green' : score >= 60 ? 'bg-primary' : score >= 40 ? 'bg-amber' : 'bg-red'

  return (
    <div className="flex items-center gap-2">
      <span className={clsx('font-mono font-bold', size === 'sm' ? 'text-xs' : 'text-sm')}>
        {score}
      </span>
      <div className={clsx('rounded-full bg-white/10', size === 'sm' ? 'w-16 h-1.5' : 'w-24 h-2')}>
        <div className={clsx('rounded-full h-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}
