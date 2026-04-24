import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { User } from '../types'
import { login as apiLogin, getMe } from '../api/client'
import { MOCK_USERS } from '../mocks/data'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  loginDemo: (role: 'admin' | 'operator' | 'viewer') => void
  logout: () => void
  isDemoMode: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [isDemoMode, setIsDemoMode] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const demoUser = localStorage.getItem('demo_user')
    if (demoUser) {
      setUser(JSON.parse(demoUser))
      setIsDemoMode(true)
      setLoading(false)
    } else if (token) {
      getMe()
        .then((r) => setUser(r.data))
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password)
    localStorage.removeItem('demo_user')
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    const me = await getMe()
    setUser(me.data)
    setIsDemoMode(false)
  }, [])

  const loginDemo = useCallback((role: 'admin' | 'operator' | 'viewer') => {
    const u = MOCK_USERS.find((m) => m.role === role) ?? MOCK_USERS[0]
    localStorage.setItem('demo_user', JSON.stringify(u))
    setUser(u)
    setIsDemoMode(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.clear()
    setUser(null)
    setIsDemoMode(false)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, loginDemo, logout, isDemoMode }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
