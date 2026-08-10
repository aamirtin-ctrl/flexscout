import { useQuery, useMutation } from '@tanstack/react-query'
import { fetchAgentStatus, triggerAgent } from '../lib/api'
import { Play, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

const STATUS_ICON: Record<string, any> = {
  success: <CheckCircle size={14} className="text-green" />,
  partial: <AlertTriangle size={14} className="text-amber" />,
  failed: <XCircle size={14} className="text-red" />,
}

export default function SettingsPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['agent-status'],
    queryFn: fetchAgentStatus,
  })

  const triggerMut = useMutation({
    mutationFn: (name: string) => triggerAgent(name),
    onSuccess: () => setTimeout(() => refetch(), 2000),
  })

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-sm font-medium">Agent Status</h1>

      {isLoading ? (
        <div className="text-muted">Loading...</div>
      ) : (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted border-b border-border">
                <th className="text-left px-4 py-2">Agent</th>
                <th className="text-left px-4 py-2">Last Run</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Fetched</th>
                <th className="text-right px-4 py-2">Upserted</th>
                <th className="text-right px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(data?.agents || []).map((agent: any) => (
                <tr key={agent.name} className="border-b border-border/30 hover:bg-white/5">
                  <td className="px-4 py-2 font-mono text-xs">{agent.name}</td>
                  <td className="px-4 py-2 text-muted text-xs">
                    {agent.last_run ? new Date(agent.last_run).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1">
                      {STATUS_ICON[agent.status] || <span className="text-muted">—</span>}
                      <span className="text-xs capitalize">{agent.status || '—'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">{agent.records_fetched ?? '—'}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs">{agent.records_upserted ?? '—'}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => triggerMut.mutate(agent.name)}
                      className="text-primary hover:text-primary/80 p-1"
                      title="Trigger run"
                    >
                      <Play size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!data?.agents?.length && !isLoading && (
        <p className="text-sm text-muted">No agent runs recorded yet. Trigger an agent to start.</p>
      )}
    </div>
  )
}
