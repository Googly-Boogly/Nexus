import { useState } from 'react'
import { Card, SectionHeader, Badge, Button, Select } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { MOCK_USERS } from '../mocks/data'
import type { User, UserRole, DataClearance } from '../types'

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'operator', label: 'Operator' },
  { value: 'viewer', label: 'Viewer' },
]

const CLEARANCE_OPTIONS = [
  { value: 'public', label: 'Public' },
  { value: 'internal', label: 'Internal' },
  { value: 'confidential', label: 'Confidential' },
  { value: 'restricted', label: 'Restricted' },
]

const CLEARANCE_VARIANT: Record<DataClearance, 'muted' | 'info' | 'warning' | 'danger'> = {
  public: 'muted',
  internal: 'info',
  confidential: 'warning',
  restricted: 'danger',
}

export default function UserManagement() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>(MOCK_USERS)
  const [editing, setEditing] = useState<string | null>(null)
  const [editRole, setEditRole] = useState<UserRole>('viewer')
  const [editClearance, setEditClearance] = useState<DataClearance>('public')

  if (currentUser?.role !== 'admin') {
    return (
      <div>
        <SectionHeader title="◈ USER MANAGEMENT" />
        <Card className="text-center py-16">
          <p className="text-red font-mono text-sm">ACCESS DENIED — Admin role required</p>
        </Card>
      </div>
    )
  }

  const startEdit = (u: User) => {
    setEditing(u.id)
    setEditRole(u.role)
    setEditClearance(u.data_clearance)
  }

  const saveEdit = (id: string) => {
    setUsers((prev) =>
      prev.map((u) => (u.id === id ? { ...u, role: editRole, data_clearance: editClearance } : u))
    )
    setEditing(null)
  }

  const toggleActive = (id: string) => {
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, is_active: !u.is_active } : u)))
  }

  return (
    <div>
      <SectionHeader
        title="◈ USER MANAGEMENT"
        subtitle={`${users.length} users · ${users.filter((u) => u.is_active).length} active`}
      />

      <div className="grid grid-cols-1 gap-4">
        {users.map((u) => (
          <Card key={u.id} className={`${!u.is_active ? 'opacity-50' : ''}`}>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4 min-w-0">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-mono text-sm font-bold flex-shrink-0
                  ${u.is_active ? 'bg-cyan/20 text-cyan' : 'bg-border text-text-muted'}`}>
                  {u.username[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary font-medium">{u.username}</span>
                    {u.id === currentUser?.id && (
                      <Badge variant="info">YOU</Badge>
                    )}
                  </div>
                  <p className="text-text-muted text-xs font-mono">{u.email}</p>
                </div>
              </div>

              {editing === u.id ? (
                <div className="flex items-center gap-2">
                  <Select
                    value={editRole}
                    onChange={(v) => setEditRole(v as UserRole)}
                    options={ROLE_OPTIONS}
                    className="w-32"
                  />
                  <Select
                    value={editClearance}
                    onChange={(v) => setEditClearance(v as DataClearance)}
                    options={CLEARANCE_OPTIONS}
                    className="w-36"
                  />
                  <Button size="sm" onClick={() => saveEdit(u.id)}>SAVE</Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>CANCEL</Button>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Badge variant="muted">{u.role}</Badge>
                  <Badge variant={CLEARANCE_VARIANT[u.data_clearance]}>{u.data_clearance}</Badge>
                  <div className="flex gap-2">
                    {u.id !== currentUser?.id && (
                      <>
                        <Button size="sm" variant="secondary" onClick={() => startEdit(u)}>EDIT</Button>
                        <Button
                          size="sm"
                          variant={u.is_active ? 'danger' : 'secondary'}
                          onClick={() => toggleActive(u.id)}
                        >
                          {u.is_active ? 'DISABLE' : 'ENABLE'}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-3 pt-3 border-t border-border/50 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div>
                <span className="text-text-muted font-mono">LAST LOGIN</span>
                <p className="text-text-secondary mt-0.5">
                  {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                </p>
              </div>
              <div>
                <span className="text-text-muted font-mono">CREATED</span>
                <p className="text-text-secondary mt-0.5">{new Date(u.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <span className="text-text-muted font-mono">STATUS</span>
                <p className={`mt-0.5 font-mono ${u.is_active ? 'text-green' : 'text-red'}`}>
                  {u.is_active ? 'ACTIVE' : 'DISABLED'}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
