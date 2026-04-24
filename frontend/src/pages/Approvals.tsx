import { useState, useEffect } from 'react'
import { Card, SectionHeader, Button, Badge, PriorityBadge, Textarea, EmptyState, Spinner } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { MOCK_APPROVALS } from '../mocks/data'
import { getApprovals, reviewApproval } from '../api/client'
import type { Approval } from '../types'

export default function Approvals() {
  const { isDemoMode, user } = useAuth()
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(!isDemoMode)
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [processing, setProcessing] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isDemoMode) {
      setApprovals(MOCK_APPROVALS as unknown as Approval[])
      return
    }
    setLoading(true)
    getApprovals()
      .then((r) => setApprovals(r.data))
      .catch(() => setError('Failed to load approvals'))
      .finally(() => setLoading(false))
  }, [isDemoMode])

  const pending = approvals.filter((a) => a.status === 'pending')
  const resolved = approvals.filter((a) => a.status !== 'pending')

  const handle = async (id: string, action: 'approve' | 'deny') => {
    if (user?.role !== 'admin') return
    setProcessing(id)
    setError('')
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 600))
        setApprovals((prev) =>
          prev.map((a) =>
            a.id === id
              ? { ...a, status: action === 'approve' ? 'approved' : 'denied',
                  reviewed_by: user?.username ?? '', reviewed_at: new Date().toISOString(),
                  review_notes: notes[id] ?? null }
              : a
          )
        )
      } else {
        const res = await reviewApproval(id, action, notes[id])
        setApprovals((prev) => prev.map((a) => (a.id === id ? res.data : a)))
      }
    } catch {
      setError(`Failed to ${action} request`)
    } finally {
      setProcessing(null)
    }
  }

  const agentLabel = (type: string) =>
    type === 'incident_response' ? 'Incident Response'
    : type === 'infrastructure_provisioning' ? 'Infrastructure Provisioning'
    : type === 'compliance_scan' ? 'Compliance Scan'
    : type

  return (
    <div>
      <SectionHeader
        title="◷ APPROVALS"
        subtitle={`${pending.length} pending approval${pending.length !== 1 ? 's' : ''}`}
      />

      {error && <p className="text-red text-xs font-mono mb-4">{error}</p>}

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner size="md" />
        </div>
      )}

      {!loading && pending.length === 0 && <EmptyState message="No pending approvals" />}

      {pending.length > 0 && (
        <div className="space-y-4 mb-8">
          <h2 className="text-text-secondary text-xs font-mono">PENDING ({pending.length})</h2>
          {pending.map((approval) => (
            <Card key={approval.id} className="border-amber/20">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="warning">AWAITING APPROVAL</Badge>
                    <PriorityBadge priority={approval.priority} />
                    <span className="text-text-muted text-xs font-mono">{agentLabel(approval.agent_type)}</span>
                  </div>
                  <p className="text-text-secondary text-sm mt-1">
                    Requested by <span className="text-cyan font-mono">{approval.requested_by.slice(0, 8)}…</span>{' '}
                    at {new Date(approval.created_at).toLocaleString()}
                  </p>
                  {approval.input_preview && (
                    <p className="text-text-muted text-xs mt-2 max-w-lg font-mono bg-base rounded p-2 border border-border/60">
                      {approval.input_preview}
                    </p>
                  )}
                </div>
              </div>

              {user?.role === 'admin' && (
                <div className="mt-4 space-y-3 border-t border-border pt-4">
                  <Textarea
                    value={notes[approval.id] ?? ''}
                    onChange={(v) => setNotes((prev) => ({ ...prev, [approval.id]: v }))}
                    placeholder="Optional review notes..."
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      onClick={() => handle(approval.id, 'approve')}
                      disabled={processing === approval.id}
                    >
                      {processing === approval.id ? <Spinner size="sm" /> : 'APPROVE'}
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => handle(approval.id, 'deny')}
                      disabled={processing === approval.id}
                    >
                      DENY
                    </Button>
                  </div>
                </div>
              )}

              {user?.role !== 'admin' && (
                <p className="text-text-muted text-xs font-mono mt-3">
                  Only admins can approve or deny requests.
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

      {resolved.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-text-secondary text-xs font-mono">RESOLVED ({resolved.length})</h2>
          {resolved.map((approval) => (
            <Card key={approval.id} className="opacity-70">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <PriorityBadge priority={approval.priority} />
                    <span className="text-text-primary text-sm font-mono">{agentLabel(approval.agent_type)}</span>
                  </div>
                  <p className="text-text-muted text-xs mt-0.5">
                    {approval.reviewed_by
                      ? `Reviewed by ${approval.reviewed_by.slice(0, 8)}… · `
                      : ''}
                    {approval.reviewed_at ? new Date(approval.reviewed_at).toLocaleString() : ''}
                  </p>
                  {approval.review_notes && (
                    <p className="text-text-secondary text-xs mt-1 italic">"{approval.review_notes}"</p>
                  )}
                </div>
                <Badge variant={approval.status === 'approved' ? 'success' : 'danger'}>
                  {approval.status.toUpperCase()}
                </Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
