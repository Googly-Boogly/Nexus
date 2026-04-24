import React from 'react'
import type { TaskStatus, TaskPriority } from '../types'

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${className}`}>
      {children}
    </div>
  )
}

export function Badge({
  children,
  variant = 'default',
}: {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'muted'
}) {
  const colors = {
    default: 'bg-border text-text-secondary',
    success: 'bg-green/10 text-green border border-green/30',
    warning: 'bg-amber/10 text-amber border border-amber/30',
    danger: 'bg-red/10 text-red border border-red/30',
    info: 'bg-cyan/10 text-cyan border border-cyan/30',
    muted: 'bg-card text-text-muted border border-border',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono ${colors[variant]}`}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: TaskStatus | string }) {
  const map: Record<TaskStatus, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'muted' | 'default' }> = {
    completed: { label: 'COMPLETED', variant: 'success' },
    running: { label: 'RUNNING', variant: 'info' },
    pending: { label: 'PENDING', variant: 'muted' },
    queued: { label: 'QUEUED', variant: 'muted' },
    failed: { label: 'FAILED', variant: 'danger' },
    pending_approval: { label: 'AWAITING APPROVAL', variant: 'warning' },
    approved: { label: 'APPROVED', variant: 'success' },
    rejected: { label: 'REJECTED', variant: 'danger' },
  }
  const entry = (map as Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'muted' | 'default' }>)[status]
  const { label, variant } = entry ?? { label: status.toUpperCase(), variant: 'default' as const }
  return <Badge variant={variant}>{label}</Badge>
}

export function PriorityBadge({ priority }: { priority: TaskPriority | string }) {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'muted'> = {
    P1: 'danger', P2: 'warning', P3: 'info', P4: 'muted',
    critical: 'danger', high: 'warning', medium: 'info', low: 'muted',
  }
  return <Badge variant={map[priority] ?? 'muted'}>{priority}</Badge>
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  type = 'button',
  className = '',
}: {
  children: React.ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  type?: 'button' | 'submit'
  className?: string
}) {
  const base = 'inline-flex items-center justify-center font-mono transition-all rounded focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed'
  const sizes = { sm: 'px-3 py-1 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  const variants = {
    primary: 'bg-cyan/10 text-cyan border border-cyan/30 hover:bg-cyan/20 hover:border-cyan/60',
    secondary: 'bg-card text-text-secondary border border-border hover:border-cyan/30 hover:text-text-primary',
    danger: 'bg-red/10 text-red border border-red/30 hover:bg-red/20',
    ghost: 'text-text-secondary hover:text-text-primary hover:bg-card',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

export function Input({
  value,
  onChange,
  placeholder,
  type = 'text',
  className = '',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
  className?: string
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`bg-base border border-border rounded px-3 py-2 text-text-primary font-mono text-sm
        placeholder-text-muted focus:outline-none focus:border-cyan/50 w-full ${className}`}
    />
  )
}

export function Select({
  value,
  onChange,
  options,
  className = '',
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  className?: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`bg-base border border-border rounded px-3 py-2 text-text-primary font-mono text-sm
        focus:outline-none focus:border-cyan/50 ${className}`}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

export function Textarea({
  value,
  onChange,
  placeholder,
  rows = 4,
  className = '',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  rows?: number
  className?: string
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className={`bg-base border border-border rounded px-3 py-2 text-text-primary font-mono text-sm
        placeholder-text-muted focus:outline-none focus:border-cyan/50 w-full resize-none ${className}`}
    />
  )
}

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return (
    <div className={`${sizes[size]} border-2 border-border border-t-cyan rounded-full animate-spin`} />
  )
}

export function Terminal({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-base border border-border rounded font-mono text-sm overflow-auto ${className}`}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
        <div className="w-2 h-2 rounded-full bg-red/60" />
        <div className="w-2 h-2 rounded-full bg-amber/60" />
        <div className="w-2 h-2 rounded-full bg-green/60" />
        <span className="text-text-muted text-xs ml-2">terminal</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}

export function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-xl font-mono text-cyan glow-cyan">{title}</h1>
      {subtitle && <p className="text-text-secondary text-sm mt-1">{subtitle}</p>}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-text-muted">
      <div className="text-4xl mb-3">◻</div>
      <p className="font-mono text-sm">{message}</p>
    </div>
  )
}
