import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { Card, SectionHeader, StatusBadge, PriorityBadge } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { getTasks, getKnowledgeStats } from '../api/client'
import { MOCK_TASKS, MOCK_STATS } from '../mocks/data'
import type { Task, KnowledgeStats } from '../types'

const ACTIVITY_DATA = [
  { time: '00:00', tasks: 2 },
  { time: '03:00', tasks: 1 },
  { time: '06:00', tasks: 3 },
  { time: '09:00', tasks: 8 },
  { time: '12:00', tasks: 12 },
  { time: '15:00', tasks: 9 },
  { time: '18:00', tasks: 6 },
  { time: '21:00', tasks: 4 },
]

const STATUS_COLORS: Record<string, string> = {
  completed: '#00ff88',
  running: '#00d4ff',
  failed: '#ff4444',
  pending_approval: '#ffaa00',
  awaiting_approval: '#ffaa00',
  pending: '#4a6a8a',
  queued: '#4a6a8a',
}

export default function Dashboard() {
  const { user, isDemoMode } = useAuth()
  const [tasks, setTasks] = useState<Task[]>(isDemoMode ? MOCK_TASKS : [])
  const [stats, setStats] = useState<KnowledgeStats | null>(isDemoMode ? MOCK_STATS : null)

  useEffect(() => {
    if (isDemoMode) return
    getTasks().then((r) => setTasks(r.data)).catch(() => {})
    getKnowledgeStats().then((r) => setStats(r.data)).catch(() => {})
  }, [isDemoMode])

  const statusCounts = tasks.reduce<Record<string, number>>((acc, t) => {
    acc[t.status] = (acc[t.status] ?? 0) + 1
    return acc
  }, {})

  const pieData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }))

  const recentTasks = [...tasks]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5)

  const statCards = [
    { label: 'Total Tasks', value: tasks.length, color: 'text-cyan' },
    { label: 'Running', value: statusCounts['running'] ?? 0, color: 'text-cyan' },
    { label: 'Pending Approval', value: (statusCounts['awaiting_approval'] ?? 0) + (statusCounts['pending_approval'] ?? 0), color: 'text-amber' },
    { label: 'Failed', value: statusCounts['failed'] ?? 0, color: 'text-red' },
    { label: 'Knowledge Docs', value: stats?.total_documents ?? 0, color: 'text-green' },
    { label: 'RAG Chunks', value: stats?.total_chunks ?? 0, color: 'text-text-secondary' },
  ]

  return (
    <div>
      <SectionHeader
        title="◈ OPERATIONS DASHBOARD"
        subtitle={`Welcome back, ${user?.username} · ${user?.role?.toUpperCase()}`}
      />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {statCards.map((s) => (
          <Card key={s.label} className="text-center">
            <div className={`text-2xl font-mono font-bold ${s.color}`}>{s.value}</div>
            <div className="text-text-muted text-xs mt-1">{s.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <Card className="lg:col-span-2">
          <h2 className="text-text-secondary text-xs font-mono mb-4">TASK ACTIVITY (24H)</h2>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={ACTIVITY_DATA}>
              <defs>
                <linearGradient id="actGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4a" />
              <XAxis dataKey="time" tick={{ fill: '#4a6a8a', fontSize: 10 }} />
              <YAxis tick={{ fill: '#4a6a8a', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#0c1524', border: '1px solid #1a2d4a', borderRadius: 4 }}
                labelStyle={{ color: '#7a9cbf', fontSize: 11 }}
                itemStyle={{ color: '#00d4ff', fontSize: 11 }}
              />
              <Area type="monotone" dataKey="tasks" stroke="#00d4ff" strokeWidth={2} fill="url(#actGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h2 className="text-text-secondary text-xs font-mono mb-4">STATUS BREAKDOWN</h2>
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={30} outerRadius={50} dataKey="value" paddingAngle={3}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#4a6a8a'} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0c1524', border: '1px solid #1a2d4a', borderRadius: 4 }}
                itemStyle={{ color: '#e2e8f0', fontSize: 11 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1">
            {pieData.map((entry) => (
              <div key={entry.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: STATUS_COLORS[entry.name] ?? '#4a6a8a' }} />
                  <span className="text-text-secondary capitalize">{entry.name.replace('_', ' ')}</span>
                </div>
                <span className="text-text-primary font-mono">{entry.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="text-text-secondary text-xs font-mono mb-4">RECENT TASKS</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-muted text-xs font-mono border-b border-border">
                <th className="text-left pb-2 pr-4">TASK</th>
                <th className="text-left pb-2 pr-4">TYPE</th>
                <th className="text-left pb-2 pr-4">PRIORITY</th>
                <th className="text-left pb-2 pr-4">STATUS</th>
                <th className="text-left pb-2">UPDATED</th>
              </tr>
            </thead>
            <tbody>
              {recentTasks.map((task) => (
                <tr key={task.id} className="border-b border-border/50 hover:bg-card-hover transition-colors">
                  <td className="py-2 pr-4">
                    <span className="text-text-primary truncate block max-w-xs">
                      {task.title ?? task.input_text?.slice(0, 60) ?? '—'}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className="text-text-secondary text-xs font-mono">
                      {(task.task_type ?? task.agent_type ?? '').replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-2 pr-4"><PriorityBadge priority={task.priority} /></td>
                  <td className="py-2 pr-4"><StatusBadge status={task.status} /></td>
                  <td className="py-2 text-text-muted text-xs font-mono">
                    {new Date(task.updated_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {recentTasks.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-text-muted text-xs font-mono">
                    No tasks yet — submit one from the Task Runner.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
