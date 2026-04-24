export type UserRole = 'admin' | 'operator' | 'viewer'
export type DataClearance = 'public' | 'internal' | 'confidential' | 'restricted'
export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'pending_approval' | 'approved' | 'rejected'
export type TaskPriority = 'P1' | 'P2' | 'P3' | 'P4'
export type AgentType = 'incident_response' | 'infrastructure_provisioning' | 'compliance_scan'

export interface User {
  id: string
  username: string
  email: string
  role: UserRole
  data_clearance: DataClearance
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface Task {
  id: string
  // Backend fields (real API)
  agent_type?: string
  input_text?: string
  approval_required?: boolean
  llm_provider?: string | null
  tokens_used?: number
  cost_usd?: number
  rag_chunks_retrieved?: number
  duration_ms?: number
  // Mock/legacy fields
  title?: string
  description?: string
  task_type?: AgentType
  created_by?: string
  requires_approval?: boolean
  approved_by?: string | null
  celery_task_id?: string | null
  completed_at?: string | null
  // Common
  status: TaskStatus | string
  priority: TaskPriority | string
  result: string | null
  error_message: string | null
  rag_sources: RagSource[] | null
  created_at: string
  updated_at: string
}

export interface RagSource {
  chunk_id: string
  document_title: string
  document_category: string
  text_preview: string
  score: number
  source_paths: string[]
}

export interface AuditLog {
  id: string
  user_id: string | null
  // Backend fields
  event_type?: string
  status?: string | null
  threat_score?: number
  message?: string | null
  // Mock/legacy fields
  username?: string
  action?: string
  success?: boolean
  // Common
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown>
  ip_address: string | null
  created_at: string
}

export interface Approval {
  id: string
  task_id: string | null
  requested_by: string      // UUID
  reviewed_by: string | null  // UUID
  agent_type: string
  priority: string
  input_preview: string | null
  status: string
  review_notes: string | null
  expires_at: string | null
  created_at: string
  reviewed_at: string | null
}

export interface KnowledgeDocument {
  id: string
  title: string
  category: string
  source_path: string
  clearance_level: DataClearance
  chunk_count: number
  token_count: number
  created_at: string
}

export interface KnowledgeSearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  category: string
  text: string
  score: number
  rrf_score: number
  source_paths: string[]
  rerank_score: number | null
}

export interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  documents_by_category: Record<string, number>
  pgvector_indexed: number
  qdrant_indexed: number
}

export interface RagPathComparison {
  query: string
  pgvector_results: KnowledgeSearchResult[]
  qdrant_dense_results: KnowledgeSearchResult[]
  qdrant_sparse_results: KnowledgeSearchResult[]
  fused_results: KnowledgeSearchResult[]
  stats: {
    pgvector_latency_ms: number
    qdrant_latency_ms: number
    rerank_latency_ms: number
    total_latency_ms: number
  }
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface TaskEvent {
  type: string
  event?: string
  timestamp: string
  data: Record<string, unknown>
}
