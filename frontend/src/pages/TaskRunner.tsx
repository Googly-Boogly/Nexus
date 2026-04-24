import React, { useState, useEffect } from 'react'
import {
  Card, SectionHeader, Button, Input, Textarea, Select,
  StatusBadge, PriorityBadge, Terminal, Spinner, Badge,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useTaskStream } from '../hooks/useTaskStream'
import { MOCK_TASKS } from '../mocks/data'
import type { Task, AgentType, TaskPriority } from '../types'
import { createTask, getTasks } from '../api/client'

const AGENT_OPTIONS = [
  { value: 'incident_response', label: 'Incident Response' },
  { value: 'infrastructure_provisioning', label: 'Infrastructure Provisioning' },
  { value: 'compliance_scan', label: 'Compliance Scan' },
]

const PRIORITY_OPTIONS = [
  { value: 'P1', label: 'P1 — Critical' },
  { value: 'P2', label: 'P2 — High' },
  { value: 'P3', label: 'P3 — Medium' },
  { value: 'P4', label: 'P4 — Low' },
]

const DEMO_OUTPUTS: Record<AgentType, string> = {
  incident_response: `[NEXUS INCIDENT AGENT v1.0]

Task: Resolving production incident
RAG Knowledge Retrieved: Incident Response Runbook (score: 0.92), Escalation Matrix (score: 0.87)

→ check_system_status(host="api-gateway-prod-1")
  Result: CPU 94%, nginx upstream error rate 100%, 3500 connections active

→ query_application_logs(service="api-gateway", minutes=15, level="ERROR")
  Result: [2024-01-15 14:31:52] UPSTREAM_TIMEOUT: backend pool exhausted (pool_size=50/50)
  Result: [2024-01-15 14:31:55] HEALTH_CHECK_FAIL: /health returned 503 in 5001ms

→ query_knowledge_base(query="nginx upstream timeout remediation steps")
  Result: Per 'Incident Response Runbook': Increase upstream pool or restart upstream services

→ restart_service(service="api-gateway", hosts=["api-gateway-prod-1","api-gateway-prod-2"])
  Result: Restarted. Health checks passing. Error rate: 0%

→ escalate_ticket(priority="P1", summary="API gateway upstream pool exhaustion")
  Result: Ticket INC-20240115-001 created

INCIDENT RESOLVED
MTTR: 15 minutes
Root cause: nginx upstream worker pool exhausted due to slow backend DB queries
Action items: Tune pool_size (50→200), investigate slow query at PID 14823`,

  infrastructure_provisioning: `[NEXUS PROVISIONING AGENT v1.0]

Task: Provisioning infrastructure resources
RAG Knowledge Retrieved: Provisioning Standards (score: 0.89), Network Topology (score: 0.82)

→ check_quota(region="us-east-1", resource_type="ec2")
  Result: vCPU limit: 384, used: 128, available: 256 ✓

→ query_knowledge_base(query="EC2 naming convention and tagging requirements")
  Result: Per 'Provisioning Standards': Format {env}-{service}-{seq:02d}, mandatory tags: env, team, cost-center

→ create_virtual_machine(
    instance_type="t3.medium",
    name="prod-webapp-07",
    vpc="main-prod",
    subnet="private-us-east-1a"
  )
  Result: Instance i-0abc123def456gh07 launched, IP: 10.0.1.107

→ tag_resource(resource_id="i-0abc123def456gh07", tags={env: prod, team: platform, cost-center: INFRA-2024})
  Result: Tags applied ✓

PROVISIONING COMPLETE
Instance: prod-webapp-07 (i-0abc123def456gh07)
Region: us-east-1a | VPC: main-prod | IP: 10.0.1.107`,

  compliance_scan: `[NEXUS COMPLIANCE AGENT v1.0]

Task: Running compliance scan
RAG Knowledge Retrieved: SOC 2 Policies (score: 0.94), NIST Controls (score: 0.88), Patch Management Policy (score: 0.85)

→ scan_vulnerabilities(scope="production", severity_threshold="medium")
  Result: 3 Critical, 7 High, 24 Medium found

→ check_patch_status(severity=["critical","high"])
  Result: 3 systems unpatched: web-prod-04 (CVE-2023-44487), db-replica-02 (CVE-2023-5678), cache-01 (CVE-2023-4911)

→ audit_access_rights(check_dormant=true, threshold_days=90)
  Result: 2 dormant accounts found: svc-old-deploy (inactive 127d), backup-user-legacy (inactive 203d)

→ check_encryption_status(resources=["s3","rds","ebs"])
  Result: 2 S3 buckets unencrypted: logs-archive-2021, dev-uploads-temp

→ generate_compliance_report(framework="SOC2", findings=true)
  Result: Report generated: SOC2-scan-20240115.pdf

SCAN COMPLETE — 2 Critical findings require immediate remediation
Per 'SOC 2 Policies': Patch SLA for Critical CVEs is 48 hours
Recommended: Emergency change request for 3 unpatched systems`,
}

export default function TaskRunner() {
  const { isDemoMode } = useAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [agentType, setAgentType] = useState<AgentType>('incident_response')
  const [priority, setPriority] = useState<TaskPriority>('P3')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [recentTasks, setRecentTasks] = useState<Task[]>([])
  const [demoOutput, setDemoOutput] = useState<string[]>([])
  const [demoRunning, setDemoRunning] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  const { events, ragSources, connected } = useTaskStream(
    !isDemoMode && activeTask ? activeTask.id : null
  )

  const fetchRecentTasks = () => {
    if (!isDemoMode) {
      getTasks().then((r) => setRecentTasks(r.data.slice(0, 5))).catch(() => {})
    }
  }

  useEffect(() => { fetchRecentTasks() }, [isDemoMode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title || !description) return
    setSubmitting(true)

    if (isDemoMode) {
      setDemoOutput([])
      setDemoRunning(true)
      const output = DEMO_OUTPUTS[agentType]
      const lines = output.split('\n')
      let i = 0
      const interval = setInterval(() => {
        if (i < lines.length) {
          setDemoOutput((prev) => [...prev, lines[i]])
          i++
        } else {
          clearInterval(interval)
          setDemoRunning(false)
        }
      }, 60)
      setSubmitting(false)
      return
    }

    setSubmitError('')
    try {
      const res = await createTask({ title, description, task_type: agentType, priority })
      setActiveTask(res.data)
      fetchRecentTasks()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSubmitError(msg ?? 'Failed to submit task. Check console for details.')
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  const ragSourcesToShow = isDemoMode
    ? MOCK_TASKS.find((t) => t.task_type === agentType)?.rag_sources ?? []
    : ragSources

  return (
    <div>
      <SectionHeader title="▶ TASK RUNNER" subtitle="Submit tasks to specialist AI agents" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Submit form */}
        <div className="space-y-4">
          <Card>
            <h2 className="text-text-secondary text-xs font-mono mb-4">NEW TASK</h2>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="text-text-muted text-xs font-mono mb-1 block">TITLE</label>
                <Input value={title} onChange={setTitle} placeholder="e.g. Production API Gateway Down" />
              </div>
              <div>
                <label className="text-text-muted text-xs font-mono mb-1 block">DESCRIPTION</label>
                <Textarea
                  value={description}
                  onChange={setDescription}
                  placeholder="Describe the task in detail..."
                  rows={4}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-text-muted text-xs font-mono mb-1 block">AGENT TYPE</label>
                  <Select
                    value={agentType}
                    onChange={(v) => setAgentType(v as AgentType)}
                    options={AGENT_OPTIONS}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-text-muted text-xs font-mono mb-1 block">PRIORITY</label>
                  <Select
                    value={priority}
                    onChange={(v) => setPriority(v as TaskPriority)}
                    options={PRIORITY_OPTIONS}
                    className="w-full"
                  />
                </div>
              </div>
              {submitError && (
                <p className="text-red text-xs font-mono">{submitError}</p>
              )}
              {isDemoMode && (
                <p className="text-amber text-xs font-mono">⚠ Demo mode active — tasks won't hit the backend. Log out and log in with real credentials.</p>
              )}
              <Button type="submit" disabled={submitting || !title || !description} className="w-full">
                {submitting ? <Spinner size="sm" /> : 'EXECUTE TASK'}
              </Button>
            </form>
          </Card>

          {/* Task history */}
          <Card>
            <h2 className="text-text-secondary text-xs font-mono mb-3">RECENT TASKS</h2>
            <div className="space-y-2">
              {(isDemoMode ? MOCK_TASKS.slice(0, 5) : recentTasks).map((task) => (
                <button
                  key={task.id}
                  onClick={() => setSelectedTask(task === selectedTask ? null : task)}
                  className="w-full text-left p-2 rounded border border-border hover:border-cyan/30
                    hover:bg-card-hover transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-text-primary text-sm truncate">{task.title}</span>
                    <div className="flex gap-1 flex-shrink-0">
                      <PriorityBadge priority={task.priority} />
                      <StatusBadge status={task.status} />
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Output panel */}
        <div className="space-y-4">
          <Terminal className="min-h-64 max-h-80">
            {demoOutput.length > 0 ? (
              demoOutput.map((line, i) => (
                <div
                  key={i}
                  className={`leading-relaxed ${
                    line.startsWith('→') ? 'text-cyan' :
                    line.startsWith('  Result:') ? 'text-green pl-4' :
                    line.startsWith('[NEXUS') ? 'text-amber font-bold' :
                    line.startsWith('INCIDENT') || line.startsWith('PROVISIONING') || line.startsWith('SCAN') ? 'text-green font-bold' :
                    line.startsWith('RAG Knowledge') ? 'text-text-secondary italic' :
                    'text-text-primary'
                  }`}
                >
                  {line || '\u00a0'}
                </div>
              ))
            ) : !isDemoMode && events.length > 0 ? (
              events.map((e, i) => {
                const d = e.data
                if (e.type === 'agent_start') return (
                  <div key={i} className="text-amber font-bold">[{(d.agent_type as string)?.toUpperCase()} AGENT] Starting task...</div>
                )
                if (e.type === 'llm_thinking') return (
                  <div key={i} className="text-text-muted text-xs">↻ Iteration {d.iteration as number} — calling LLM...</div>
                )
                if (e.type === 'llm_response') return (
                  <div key={i} className="text-text-primary leading-relaxed whitespace-pre-wrap">{d.content as string}</div>
                )
                if (e.type === 'tool_call') return (
                  <div key={i} className="text-cyan">→ {d.tool as string}({JSON.stringify(d.input).slice(0, 200)})</div>
                )
                if (e.type === 'tool_result') return (
                  <div key={i} className="text-green pl-4">  Result: {(d.result as string)?.slice(0, 300)}</div>
                )
                if (e.type === 'rag_retrieval') return (
                  <div key={i} className="text-text-secondary italic text-xs">◉ RAG: {d.chunks_retrieved as number} chunks retrieved</div>
                )
                if (e.type === 'completed') return (
                  <div key={i} className="text-green font-bold">✓ TASK COMPLETED ({d.duration_ms as number}ms · {d.tokens_used as number} tokens)</div>
                )
                if (e.type === 'failed') return (
                  <div key={i} className="text-red font-bold">✗ TASK FAILED: {d.error as string}</div>
                )
                if (e.type === 'started') return (
                  <div key={i} className="text-text-muted text-xs">Agent pipeline started</div>
                )
                return null
              })
            ) : (
              <div className="text-text-muted">
                {demoRunning ? (
                  <span className="text-cyan animate-pulse">Running agent...</span>
                ) : (
                  'Submit a task to see agent output here.'
                )}
                {!isDemoMode && connected && <span className="text-green ml-2">● CONNECTED</span>}
              </div>
            )}
          </Terminal>

          {/* RAG sources */}
          {ragSourcesToShow.length > 0 && (
            <Card>
              <h2 className="text-text-secondary text-xs font-mono mb-3">
                ◉ RAG KNOWLEDGE SOURCES
              </h2>
              <div className="space-y-2">
                {ragSourcesToShow.map((src) => (
                  <div key={src.chunk_id} className="p-2 rounded bg-base border border-border/60">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-cyan text-xs font-mono">{src.document_title}</span>
                      <span className="text-green text-xs font-mono">{(src.score * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-text-secondary text-xs leading-relaxed">{src.text_preview}</p>
                    <div className="flex gap-1 mt-1">
                      {src.source_paths.map((p) => (
                        <Badge key={p} variant={p === 'pgvector' ? 'info' : 'success'}>
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Selected task detail */}
          {selectedTask && (
            <Card>
              <h2 className="text-text-secondary text-xs font-mono mb-3">TASK DETAIL</h2>
              <p className="text-text-primary text-sm font-medium mb-2">{selectedTask.title}</p>
              {selectedTask.result && (
                <pre className="text-green text-xs font-mono whitespace-pre-wrap leading-relaxed">
                  {selectedTask.result}
                </pre>
              )}
              {selectedTask.error_message && (
                <p className="text-red text-xs font-mono">{selectedTask.error_message}</p>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
