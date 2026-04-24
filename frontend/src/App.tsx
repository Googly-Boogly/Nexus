import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import TaskRunner from './pages/TaskRunner'
import AuditExplorer from './pages/AuditExplorer'
import SecurityFeed from './pages/SecurityFeed'
import KnowledgeBase from './pages/KnowledgeBase'
import Approvals from './pages/Approvals'
import UserManagement from './pages/UserManagement'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="text-cyan font-mono animate-pulse">NEXUS LOADING...</div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={<RequireAuth><Dashboard /></RequireAuth>}
      />
      <Route
        path="/tasks"
        element={<RequireAuth><TaskRunner /></RequireAuth>}
      />
      <Route
        path="/audit"
        element={<RequireAuth><AuditExplorer /></RequireAuth>}
      />
      <Route
        path="/security"
        element={<RequireAuth><SecurityFeed /></RequireAuth>}
      />
      <Route
        path="/knowledge"
        element={<RequireAuth><KnowledgeBase /></RequireAuth>}
      />
      <Route
        path="/approvals"
        element={<RequireAuth><Approvals /></RequireAuth>}
      />
      <Route
        path="/users"
        element={<RequireAuth><UserManagement /></RequireAuth>}
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
