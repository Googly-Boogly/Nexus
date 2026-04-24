import { useState, useEffect } from 'react'
import { Card, SectionHeader, Badge, Input, Select } from '../components/ui'
import { getAuditLogs } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { MOCK_AUDIT_LOGS } from '../mocks/data'
import type { AuditLog } from '../types'

const ACTION_COLORS: Record<string, 'success' | 'danger' | 'info' | 'warning' | 'muted'> = {
  login: 'success',
  login_success: 'success',
  login_failed: 'danger',
  login_locked: 'danger',
  task_created: 'info',
  task_submitted: 'info',
  rag_retrieval: 'success',
  document_ingested: 'info',
  knowledge_search: 'muted',
  approval_granted: 'success',
  approval_denied: 'danger',
}

function ActionBadge({ action, success }: { action: string; success?: boolean }) {
  if (success === false) return <Badge variant="danger">{action}</Badge>
  const v = ACTION_COLORS[action] ?? 'muted'
  return <Badge variant={v}>{action}</Badge>
}

export default function AuditExplorer() {
  const { isDemoMode } = useAuth()
  const [logs, setLogs] = useState<AuditLog[]>(isDemoMode ? MOCK_AUDIT_LOGS : [])
  const [search, setSearch] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [selected, setSelected] = useState<AuditLog | null>(null)

  useEffect(() => {
    if (isDemoMode) return
    getAuditLogs({ limit: 100 }).then((r) => setLogs(r.data)).catch(() => {})
  }, [isDemoMode])

  const allActions = Array.from(new Set(logs.map((l) => l.event_type ?? l.action ?? '')))
  const actionOptions = [
    { value: 'all', label: 'All Actions' },
    ...allActions.filter(Boolean).map((a) => ({ value: a, label: a })),
  ]

  const filtered = logs.filter((log) => {
    const action = log.event_type ?? log.action ?? ''
    const username = log.username ?? log.user_id ?? ''
    const resource = log.resource_type ?? ''
    const matchSearch =
      !search ||
      username.includes(search) ||
      action.includes(search) ||
      resource.includes(search)
    const matchAction = actionFilter === 'all' || action === actionFilter
    return matchSearch && matchAction
  })

  return (
    <div>
      <SectionHeader title="◎ AUDIT EXPLORER" subtitle="Immutable audit log with RLS enforcement" />

      <div className="flex gap-3 mb-4">
        <Input value={search} onChange={setSearch} placeholder="Search by user, action, resource..." className="max-w-sm" />
        <Select value={actionFilter} onChange={setActionFilter} options={actionOptions} className="w-48" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-text-muted text-xs font-mono border-b border-border bg-base/50">
                    <th className="text-left px-4 py-3">TIME</th>
                    <th className="text-left px-4 py-3">USER</th>
                    <th className="text-left px-4 py-3">ACTION</th>
                    <th className="text-left px-4 py-3">RESOURCE</th>
                    <th className="text-left px-4 py-3">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-text-muted text-xs font-mono">
                        No audit events yet.
                      </td>
                    </tr>
                  )}
                  {filtered.map((log) => {
                    const action = log.event_type ?? log.action ?? 'unknown'
                    const username = log.username ?? log.user_id ?? '—'
                    const isSuccess = log.success ?? (log.status !== 'blocked' && log.status !== 'failed')
                    return (
                      <tr
                        key={log.id}
                        onClick={() => setSelected(log === selected ? null : log)}
                        className={`border-b border-border/50 cursor-pointer transition-colors
                          ${selected?.id === log.id ? 'bg-cyan/5' : 'hover:bg-card-hover'}`}
                      >
                        <td className="px-4 py-2 text-text-muted text-xs font-mono whitespace-nowrap">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-2 text-text-primary text-xs font-mono">{username}</td>
                        <td className="px-4 py-2">
                          <ActionBadge action={action} success={isSuccess} />
                        </td>
                        <td className="px-4 py-2 text-text-secondary text-xs">{log.resource_type ?? '—'}</td>
                        <td className="px-4 py-2 text-text-muted text-xs font-mono">{log.ip_address ?? '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div>
          {selected ? (
            <Card>
              <h2 className="text-text-secondary text-xs font-mono mb-4">EVENT DETAIL</h2>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-text-muted font-mono">ID</span>
                  <p className="text-text-primary font-mono mt-0.5 break-all">{selected.id}</p>
                </div>
                <div>
                  <span className="text-text-muted font-mono">TIMESTAMP</span>
                  <p className="text-text-primary font-mono mt-0.5">
                    {new Date(selected.created_at).toISOString()}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted font-mono">USER</span>
                  <p className="text-text-primary font-mono mt-0.5">
                    {selected.username ?? selected.user_id ?? '—'}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted font-mono">ACTION</span>
                  <div className="mt-0.5">
                    <ActionBadge
                      action={selected.event_type ?? selected.action ?? 'unknown'}
                      success={selected.success ?? (selected.status !== 'blocked')}
                    />
                  </div>
                </div>
                <div>
                  <span className="text-text-muted font-mono">RESOURCE</span>
                  <p className="text-text-primary font-mono mt-0.5">
                    {selected.resource_type ?? '—'}{selected.resource_id ? ` / ${selected.resource_id}` : ''}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted font-mono">IP ADDRESS</span>
                  <p className="text-cyan font-mono mt-0.5">{selected.ip_address ?? '—'}</p>
                </div>
                {selected.message && (
                  <div>
                    <span className="text-text-muted font-mono">MESSAGE</span>
                    <p className="text-text-secondary font-mono mt-0.5">{selected.message}</p>
                  </div>
                )}
                {Object.keys(selected.details).length > 0 && (() => {
                  const { decision_tree, ...rest } = selected.details as Record<string, unknown>
                  const steps = decision_tree as Array<Record<string, unknown>> | undefined
                  return (
                    <>
                      {Object.keys(rest).length > 0 && (
                        <div>
                          <span className="text-text-muted font-mono">DETAILS</span>
                          <pre className="bg-base rounded p-2 text-text-secondary font-mono text-xs mt-0.5 overflow-auto max-h-40">
                            {JSON.stringify(rest, null, 2)}
                          </pre>
                        </div>
                      )}
                      {steps && steps.length > 0 && (
                        <div>
                          <span className="text-text-muted font-mono">AGENT DECISION TREE</span>
                          <div className="mt-1 space-y-1">
                            {steps.map((s, i) => {
                              const stepName = String(s.step ?? '')
                              const isLlm = stepName.startsWith('llm_iteration')
                              const toolCalls = s.tool_calls as Array<Record<string, unknown>> | undefined
                              return (
                                <div key={i} className="bg-base border border-border/60 rounded p-2 text-xs">
                                  <div className="flex items-center gap-2">
                                    <span className={`font-mono font-bold ${
                                      s.status === 'passed' || s.status === 'completed' ? 'text-green' :
                                      isLlm ? 'text-cyan' : 'text-amber'
                                    }`}>
                                      {isLlm ? '↻' : s.status === 'passed' || s.status === 'completed' ? '✓' : '→'}
                                    </span>
                                    <span className="text-text-primary font-mono">{stepName}</span>
                                    {s.model != null && <span className="text-text-muted">· {String(s.model)}</span>}
                                    {s.status != null && !isLlm && (
                                      <span className="text-text-muted ml-auto">{String(s.status)}</span>
                                    )}
                                  </div>
                                  {(s.combined_score !== undefined || s.threat_score !== undefined) && (
                                    <p className="text-text-muted pl-4 mt-0.5">
                                      threat score: {String(s.combined_score ?? s.threat_score)}
                                    </p>
                                  )}
                                  {s.chunks_retrieved !== undefined && (
                                    <p className="text-text-muted pl-4 mt-0.5">
                                      {String(s.chunks_retrieved)} chunks retrieved
                                      {(s.sources as unknown[])?.length ? ` — ${(s.sources as Array<Record<string,unknown>>).map(x => x.title).join(', ')}` : ''}
                                    </p>
                                  )}
                                  {s.response_preview != null && (
                                    <p className="text-text-secondary pl-4 mt-0.5 italic whitespace-pre-wrap">
                                      {String(s.response_preview)}
                                    </p>
                                  )}
                                  {isLlm && (
                                    <p className="text-text-muted pl-4 mt-0.5">
                                      {String(s.input_tokens ?? 0)} in · {String(s.output_tokens ?? 0)} out · stop: {String(s.stop_reason ?? '')}
                                    </p>
                                  )}
                                  {toolCalls && toolCalls.map((tc, j) => (
                                    <div key={j} className="pl-4 mt-1 border-l border-cyan/30">
                                      <p className="text-cyan font-mono">→ {String(tc.tool)}({JSON.stringify(tc.input).slice(0, 120)})</p>
                                      <p className={`font-mono mt-0.5 ${tc.blocked ? 'text-red' : 'text-green'}`}>
                                        {tc.blocked ? '  [BLOCKED]' : `  ${String(tc.result_preview)}`}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </>
                  )
                })()}
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12">
              <p className="text-text-muted text-xs font-mono">Select an event to inspect</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
