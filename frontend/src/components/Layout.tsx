import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { Approval } from '../types'
import { MOCK_APPROVALS } from '../mocks/data'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: '◈' },
  { to: '/tasks', label: 'Task Runner', icon: '▶' },
  { to: '/audit', label: 'Audit Log', icon: '◎' },
  { to: '/security', label: 'Security Feed', icon: '⬡' },
  { to: '/knowledge', label: 'Knowledge Base', icon: '◉' },
  { to: '/approvals', label: 'Approvals', icon: '◷', adminOnly: false },
  { to: '/users', label: 'Users', icon: '◈', adminOnly: true },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, isDemoMode } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const pendingApprovals: Approval[] = isDemoMode
    ? MOCK_APPROVALS.filter((a) => a.status === 'pending')
    : []

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleNav = NAV.filter((n) => !n.adminOnly || user?.role === 'admin')

  return (
    <div className="flex h-screen bg-base overflow-hidden">
      <div className="scan-line" />

      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-56' : 'w-14'} flex-shrink-0 bg-card border-r border-border
          flex flex-col transition-all duration-200 overflow-hidden`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-border h-14">
          <span className="text-cyan font-mono text-lg font-bold flex-shrink-0">⬡</span>
          {sidebarOpen && (
            <span className="text-cyan font-mono font-bold text-sm glow-cyan">NEXUS</span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto text-text-muted hover:text-text-primary transition-colors"
          >
            {sidebarOpen ? '◁' : '▷'}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm font-mono transition-colors relative
                ${isActive
                  ? 'text-cyan bg-cyan/5 border-r-2 border-cyan'
                  : 'text-text-secondary hover:text-text-primary hover:bg-card-hover'
                }`
              }
            >
              <span className="flex-shrink-0 text-base">{item.icon}</span>
              {sidebarOpen && (
                <span className="flex items-center gap-2">
                  {item.label}
                  {item.label === 'Approvals' && pendingApprovals.length > 0 && (
                    <span className="bg-amber text-base text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">
                      {pendingApprovals.length}
                    </span>
                  )}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-border px-4 py-3">
          {sidebarOpen ? (
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-text-primary text-xs font-mono truncate">{user?.username}</p>
                <p className="text-text-muted text-xs capitalize">{user?.role}</p>
              </div>
              <button onClick={handleLogout} className="text-text-muted hover:text-red text-xs font-mono ml-2">
                EXIT
              </button>
            </div>
          ) : (
            <button onClick={handleLogout} className="text-text-muted hover:text-red text-sm w-full text-center">
              ×
            </button>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {isDemoMode && (
          <div className="bg-amber/10 border-b border-amber/20 px-6 py-1.5 text-amber text-xs font-mono text-center">
            DEMO MODE — using mock data, no API calls required
          </div>
        )}
        <div className="p-6 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
