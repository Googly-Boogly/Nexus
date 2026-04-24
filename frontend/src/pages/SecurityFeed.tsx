import { useState } from 'react'
import { Card, SectionHeader, Badge } from '../components/ui'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

interface SecurityEvent {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  message: string
  source: string
  timestamp: string
  mitigated: boolean
}

const MOCK_EVENTS: SecurityEvent[] = [
  { id: 'se1', severity: 'high', category: 'brute_force', message: '847 failed auth attempts from 185.220.x.x (Tor exit)', source: 'SIEM', timestamp: '2024-01-15T14:45:00Z', mitigated: true },
  { id: 'se2', severity: 'medium', category: 'anomalous_access', message: 'User svc-monitoring accessed 430 S3 objects in 2 minutes', source: 'CloudTrail', timestamp: '2024-01-15T13:12:00Z', mitigated: false },
  { id: 'se3', severity: 'critical', category: 'vulnerability', message: 'CVE-2024-0001 (CVSS 9.8) detected on web-prod-04 — unpatched OpenSSL 3.0.2', source: 'Vulnerability Scanner', timestamp: '2024-01-15T11:30:00Z', mitigated: false },
  { id: 'se4', severity: 'info', category: 'policy', message: 'New IAM policy attached: s3-readonly to role data-analyst-prod', source: 'CloudTrail', timestamp: '2024-01-15T10:05:00Z', mitigated: true },
  { id: 'se5', severity: 'high', category: 'data_exfiltration', message: 'Unusual outbound data transfer: 2.3GB to 198.51.100.0/24', source: 'Network Monitor', timestamp: '2024-01-15T09:50:00Z', mitigated: false },
  { id: 'se6', severity: 'medium', category: 'config_drift', message: '2 S3 buckets missing encryption — non-compliant with policy', source: 'Config Scanner', timestamp: '2024-01-15T08:00:00Z', mitigated: false },
  { id: 'se7', severity: 'low', category: 'certificate', message: 'TLS certificate for api.nexuscorp.com expires in 14 days', source: 'Certificate Monitor', timestamp: '2024-01-15T06:00:00Z', mitigated: false },
  { id: 'se8', severity: 'info', category: 'auth', message: 'Admin user logged in from new IP: 10.0.2.50', source: 'Auth Service', timestamp: '2024-01-15T14:00:00Z', mitigated: true },
]

const SEVERITY_TREND = [
  { day: 'Mon', critical: 1, high: 3, medium: 7 },
  { day: 'Tue', critical: 0, high: 2, medium: 5 },
  { day: 'Wed', critical: 2, high: 4, medium: 9 },
  { day: 'Thu', critical: 1, high: 5, medium: 6 },
  { day: 'Fri', critical: 0, high: 3, medium: 8 },
  { day: 'Sat', critical: 0, high: 1, medium: 3 },
  { day: 'Sun', critical: 1, high: 2, medium: 4 },
]

const SEV_COLOR: Record<SecurityEvent['severity'], string> = {
  critical: '#ff4444',
  high: '#ff8844',
  medium: '#ffaa00',
  low: '#7a9cbf',
  info: '#4a6a8a',
}

const SEV_VARIANT: Record<SecurityEvent['severity'], 'danger' | 'warning' | 'info' | 'muted' | 'default'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'warning',
  low: 'muted',
  info: 'default',
}

export default function SecurityFeed() {
  const [severityFilter, setSeverityFilter] = useState<string>('all')

  const filtered = MOCK_EVENTS.filter(
    (e) => severityFilter === 'all' || e.severity === severityFilter
  )

  const counts = {
    critical: MOCK_EVENTS.filter((e) => e.severity === 'critical' && !e.mitigated).length,
    high: MOCK_EVENTS.filter((e) => e.severity === 'high' && !e.mitigated).length,
    open: MOCK_EVENTS.filter((e) => !e.mitigated).length,
    mitigated: MOCK_EVENTS.filter((e) => e.mitigated).length,
  }

  return (
    <div>
      <SectionHeader title="⬡ SECURITY FEED" subtitle="Real-time security events from SIEM, CloudTrail, and scanners" />

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Card className="text-center border-red/30">
          <div className="text-2xl font-mono font-bold text-red">{counts.critical}</div>
          <div className="text-text-muted text-xs mt-1">Critical Open</div>
        </Card>
        <Card className="text-center border-amber/30">
          <div className="text-2xl font-mono font-bold text-amber">{counts.high}</div>
          <div className="text-text-muted text-xs mt-1">High Open</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-mono font-bold text-text-primary">{counts.open}</div>
          <div className="text-text-muted text-xs mt-1">Total Open</div>
        </Card>
        <Card className="text-center border-green/30">
          <div className="text-2xl font-mono font-bold text-green">{counts.mitigated}</div>
          <div className="text-text-muted text-xs mt-1">Mitigated</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="lg:col-span-2">
          <h2 className="text-text-secondary text-xs font-mono mb-4">SEVERITY TREND (7D)</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={SEVERITY_TREND}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4a" />
              <XAxis dataKey="day" tick={{ fill: '#4a6a8a', fontSize: 10 }} />
              <YAxis tick={{ fill: '#4a6a8a', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#0c1524', border: '1px solid #1a2d4a', borderRadius: 4 }}
                itemStyle={{ fontSize: 11 }}
              />
              <Bar dataKey="critical" fill="#ff4444" radius={[2, 2, 0, 0]} />
              <Bar dataKey="high" fill="#ff8844" radius={[2, 2, 0, 0]} />
              <Bar dataKey="medium" fill="#ffaa00" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h2 className="text-text-secondary text-xs font-mono mb-4">FILTER BY SEVERITY</h2>
          <div className="space-y-2">
            {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-colors
                  ${severityFilter === s ? 'bg-cyan/10 text-cyan border border-cyan/30' : 'text-text-secondary hover:text-text-primary hover:bg-card-hover border border-transparent'}`}
              >
                {s === 'all' ? 'ALL EVENTS' : s.toUpperCase()}
                {s !== 'all' && (
                  <span className="ml-2 opacity-60">
                    ({MOCK_EVENTS.filter((e) => e.severity === s).length})
                  </span>
                )}
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* Events list */}
      <Card className="p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-text-secondary text-xs font-mono">
            EVENTS — {filtered.length} SHOWN
          </h2>
        </div>
        <div className="divide-y divide-border/50">
          {filtered.map((event) => (
            <div key={event.id} className={`px-4 py-3 ${!event.mitigated ? 'hover:bg-card-hover' : 'opacity-60'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div
                    className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                    style={{ background: SEV_COLOR[event.severity] }}
                  />
                  <div className="min-w-0">
                    <p className="text-text-primary text-sm">{event.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={SEV_VARIANT[event.severity]}>{event.severity.toUpperCase()}</Badge>
                      <span className="text-text-muted text-xs font-mono">{event.category}</span>
                      <span className="text-text-muted text-xs">·</span>
                      <span className="text-text-muted text-xs">{event.source}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {event.mitigated && <Badge variant="success">MITIGATED</Badge>}
                  <span className="text-text-muted text-xs font-mono">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
