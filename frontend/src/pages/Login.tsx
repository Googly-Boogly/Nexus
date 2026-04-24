import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button, Input, Spinner } from '../components/ui'

export default function Login() {
  const { login, loginDemo, user } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/dashboard')
  }, [user, navigate])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  const handleDemo = (role: 'admin' | 'operator' | 'viewer') => {
    loginDemo(role)
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-base flex items-center justify-center px-4">
      <div className="scan-line" />
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-cyan text-4xl mb-3 glow-cyan">⬡</div>
          <h1 className="text-2xl font-mono font-bold text-cyan glow-cyan">NEXUS</h1>
          <p className="text-text-muted text-sm mt-1 font-mono">Enterprise IT Automation Platform</p>
        </div>

        {/* Form */}
        <div className="bg-card border border-border rounded-lg p-6 corner-bracket">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-text-secondary text-xs font-mono mb-1">USERNAME</label>
              <Input
                value={username}
                onChange={setUsername}
                placeholder="username"
                type="text"
              />
            </div>
            <div>
              <label className="block text-text-secondary text-xs font-mono mb-1">PASSWORD</label>
              <Input
                value={password}
                onChange={setPassword}
                placeholder="••••••••"
                type="password"
              />
            </div>
            {error && (
              <p className="text-red text-xs font-mono">{error}</p>
            )}
            <Button type="submit" disabled={loading || !username || !password} className="w-full">
              {loading ? <Spinner size="sm" /> : 'AUTHENTICATE'}
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-border">
            <p className="text-text-muted text-xs font-mono text-center mb-3">DEMO ACCESS</p>
            <div className="grid grid-cols-3 gap-2">
              {(['admin', 'operator', 'viewer'] as const).map((role) => (
                <button
                  key={role}
                  onClick={() => handleDemo(role)}
                  className="py-1.5 text-xs font-mono rounded border border-border text-text-secondary
                    hover:border-cyan/40 hover:text-cyan transition-colors capitalize"
                >
                  {role.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-text-muted text-xs font-mono text-center mt-4">
          v1.0.0 · NEXUS Corp · {new Date().getFullYear()}
        </p>
      </div>
    </div>
  )
}
