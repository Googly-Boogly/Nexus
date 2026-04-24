import axios from 'axios'
import type {
  User, Task, AuditLog, Approval, KnowledgeDocument,
  KnowledgeSearchResult, KnowledgeStats, RagPathComparison, AuthTokens, TaskStatus
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const res = await axios.post('/api/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', res.data.access_token)
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`
          return api(error.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (username: string, password: string) =>
  api.post<AuthTokens>('/auth/login', { username, password })

export const getMe = () => api.get<User>('/auth/me')

// Tasks
const PRIORITY_MAP: Record<string, string> = {
  P1: 'critical', P2: 'high', P3: 'medium', P4: 'low',
}

export const createTask = (data: {
  title: string
  description: string
  task_type: string
  priority: string
}) => api.post<Task>('/tasks', {
  agent_type: data.task_type,
  input_text: data.title ? `${data.title}\n\n${data.description}` : data.description,
  priority: PRIORITY_MAP[data.priority] ?? data.priority,
})

export const getTasks = (params?: { status?: TaskStatus; page?: number; per_page?: number }) =>
  api.get<Task[]>('/tasks', { params })

export const getTask = (id: string) => api.get<Task>(`/tasks/${id}`)

// Audit
export const getAuditLogs = (params?: {
  event_type?: string
  user_id?: string
  limit?: number
  offset?: number
}) => api.get<AuditLog[]>('/audit', { params })

// Approvals
export const getApprovals = (status?: string) =>
  api.get<Approval[]>('/approvals', { params: status ? { status } : undefined })
export const reviewApproval = (id: string, action: 'approve' | 'deny', notes?: string) =>
  api.post<Approval>(`/approvals/${id}/review`, { action, notes })

// Users (admin)
export const getUsers = () => api.get<User[]>('/users/')
export const updateUserRole = (id: string, role: string, clearance: string) =>
  api.patch(`/users/${id}`, { role, data_clearance: clearance })
export const toggleUser = (id: string, active: boolean) =>
  api.patch(`/users/${id}`, { is_active: active })

// Knowledge
export const ingestDocument = (data: {
  title: string
  content: string
  category: string
  source_path: string
  clearance_level: string
}) => api.post('/knowledge/ingest', data)

export const getDocuments = (params?: { category?: string; page?: number }) =>
  api.get<{ documents: KnowledgeDocument[]; total: number }>('/knowledge/documents', { params })

export const deleteDocument = (id: string) => api.delete(`/knowledge/documents/${id}`)

export const searchKnowledge = (data: {
  query: string
  top_k?: number
  filters?: Record<string, string>
}) => api.post<KnowledgeSearchResult[]>('/knowledge/search', data)

export const getKnowledgeStats = () => api.get<KnowledgeStats>('/knowledge/stats')

export const compareRagPaths = (query: string, top_k = 5) =>
  api.get<RagPathComparison>('/knowledge/compare-paths', { params: { query, top_k } })

export default api
