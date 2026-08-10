interface Comp {
  address: string | null
  sale_date: string | null
  sale_price: number | null
  price_per_acre: number | null
  acreage: number | null
  distance_miles: number | null
}

export default function CompTable({ comps }: { comps: Comp[] }) {
  if (!comps.length) {
    return <p className="text-sm text-muted">No comparable sales found</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs border-b border-border">
            <th className="text-left py-2 px-2">Address</th>
            <th className="text-left py-2 px-2">Sale Date</th>
            <th className="text-right py-2 px-2">$/Acre</th>
            <th className="text-right py-2 px-2">Acres</th>
            <th className="text-right py-2 px-2">Distance</th>
          </tr>
        </thead>
        <tbody>
          {comps.map((c, i) => (
            <tr key={i} className="border-b border-border/50 hover:bg-white/5">
              <td className="py-2 px-2 truncate max-w-[200px]">{c.address || '—'}</td>
              <td className="py-2 px-2 text-muted">{c.sale_date || '—'}</td>
              <td className="py-2 px-2 text-right font-mono">
                {c.price_per_acre ? `$${(c.price_per_acre / 1000).toFixed(0)}k` : '—'}
              </td>
              <td className="py-2 px-2 text-right font-mono">{c.acreage?.toFixed(1) || '—'}</td>
              <td className="py-2 px-2 text-right font-mono text-muted">
                {c.distance_miles?.toFixed(1)} mi
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
