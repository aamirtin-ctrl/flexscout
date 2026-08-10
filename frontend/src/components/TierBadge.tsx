import clsx from 'clsx'

const COLORS: Record<string, string> = {
  A: 'bg-green/20 text-green border-green/30',
  B: 'bg-primary/20 text-primary border-primary/30',
  C: 'bg-amber/20 text-amber border-amber/30',
  Pass: 'bg-muted/20 text-muted border-muted/30',
}

export default function TierBadge({ tier }: { tier: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center w-7 h-7 rounded font-mono text-xs font-bold border',
        COLORS[tier] || COLORS.Pass
      )}
    >
      {tier}
    </span>
  )
}
