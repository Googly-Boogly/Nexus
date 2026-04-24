import type { Task, AuditLog, Approval, KnowledgeDocument, KnowledgeStats, User } from '../types'

export const MOCK_USERS: User[] = [
  {
    id: 'u1', username: 'admin', email: 'admin@nexuscorp.com',
    role: 'admin', data_clearance: 'restricted', is_active: true,
    created_at: '2024-01-01T00:00:00Z', last_login: '2024-01-15T14:00:00Z',
  },
  {
    id: 'u2', username: 'operator1', email: 'operator1@nexuscorp.com',
    role: 'operator', data_clearance: 'confidential', is_active: true,
    created_at: '2024-01-02T00:00:00Z', last_login: '2024-01-15T09:30:00Z',
  },
  {
    id: 'u3', username: 'viewer1', email: 'viewer1@nexuscorp.com',
    role: 'viewer', data_clearance: 'internal', is_active: true,
    created_at: '2024-01-03T00:00:00Z', last_login: '2024-01-14T16:45:00Z',
  },
]

export const MOCK_TASKS: Task[] = [
  {
    id: 't1', title: 'Production API Gateway Down', description: 'API gateway returning 502 errors',
    task_type: 'incident_response', status: 'completed', priority: 'P1',
    created_by: 'operator1', requires_approval: false, approved_by: null,
    celery_task_id: 'cel-001', rag_sources: [
      { chunk_id: 'c1', document_title: 'Incident Response Runbook', document_category: 'runbooks',
        text_preview: 'Step 1: Acknowledge and assess scope...', score: 0.92, source_paths: ['pgvector', 'qdrant_dense'] },
      { chunk_id: 'c2', document_title: 'Escalation Matrix', document_category: 'general',
        text_preview: 'P1 escalation: T+0 L1 acknowledges...', score: 0.87, source_paths: ['pgvector'] },
    ],
    result: 'Incident INC-20240115-001 created. Root cause: nginx upstream timeout. Restarted api-gateway-prod-[1-4]. Service restored at 14:47 UTC. MTTR: 15 minutes.',
    error_message: null, created_at: '2024-01-15T14:32:00Z', updated_at: '2024-01-15T14:47:00Z', completed_at: '2024-01-15T14:47:00Z',
  },
  {
    id: 't2', title: 'Deploy Payment Service v2.4.1', description: 'Blue-green deployment to production ECS',
    task_type: 'infrastructure_provisioning', status: 'pending_approval', priority: 'P2',
    created_by: 'operator1', requires_approval: true, approved_by: null,
    celery_task_id: null, rag_sources: null,
    result: null, error_message: null,
    created_at: '2024-01-15T10:00:00Z', updated_at: '2024-01-15T10:00:00Z', completed_at: null,
  },
  {
    id: 't3', title: 'SOC 2 Pre-Audit Vulnerability Scan', description: 'Full scan before external audit',
    task_type: 'compliance_scan', status: 'running', priority: 'P2',
    created_by: 'admin', requires_approval: false, approved_by: null,
    celery_task_id: 'cel-003', rag_sources: null,
    result: null, error_message: null,
    created_at: '2024-01-15T11:00:00Z', updated_at: '2024-01-15T11:23:00Z', completed_at: null,
  },
  {
    id: 't4', title: 'Provision ML Training Cluster', description: '4x g4dn.xlarge for data science team',
    task_type: 'infrastructure_provisioning', status: 'completed', priority: 'P3',
    created_by: 'operator1', requires_approval: false, approved_by: null,
    celery_task_id: 'cel-004', rag_sources: [
      { chunk_id: 'c3', document_title: 'Provisioning Standards', document_category: 'infrastructure',
        text_preview: 'EC2 naming convention: {env}-{service}-{role}...', score: 0.89, source_paths: ['qdrant_dense', 'qdrant_sparse'] },
    ],
    result: 'Provisioned 4x g4dn.xlarge (ml-train-gpu-[01-04]) in us-east-1a. AMI: ami-0c55b159cbfafe1f0. Volumes: 500GB gp3. Tags applied.',
    error_message: null, created_at: '2024-01-14T09:00:00Z', updated_at: '2024-01-14T09:12:00Z', completed_at: '2024-01-14T09:12:00Z',
  },
  {
    id: 't5', title: 'Quarterly Access Rights Audit', description: 'Review IAM roles and dormant accounts',
    task_type: 'compliance_scan', status: 'failed', priority: 'P2',
    created_by: 'admin', requires_approval: false, approved_by: null,
    celery_task_id: 'cel-005', rag_sources: null,
    result: null, error_message: 'AWS credential error: insufficient permissions to list IAM roles.',
    created_at: '2024-01-13T14:00:00Z', updated_at: '2024-01-13T14:05:00Z', completed_at: null,
  },
]

export const MOCK_AUDIT_LOGS: AuditLog[] = [
  { id: 'a1', user_id: 'u1', username: 'admin', action: 'login', resource_type: 'auth', resource_id: null, details: {}, ip_address: '10.0.1.5', success: true, created_at: '2024-01-15T14:00:00Z' },
  { id: 'a2', user_id: 'u2', username: 'operator1', action: 'task_created', resource_type: 'task', resource_id: 't1', details: { task_type: 'incident_response', priority: 'P1' }, ip_address: '10.0.1.8', success: true, created_at: '2024-01-15T14:32:00Z' },
  { id: 'a3', user_id: 'u2', username: 'operator1', action: 'rag_retrieval', resource_type: 'knowledge', resource_id: 't1', details: { chunks_retrieved: 5, top_score: 0.92, sources: ['pgvector', 'qdrant'] }, ip_address: '10.0.1.8', success: true, created_at: '2024-01-15T14:32:05Z' },
  { id: 'a4', user_id: 'u1', username: 'admin', action: 'task_created', resource_type: 'task', resource_id: 't3', details: { task_type: 'compliance_scan', priority: 'P2' }, ip_address: '10.0.1.5', success: true, created_at: '2024-01-15T11:00:00Z' },
  { id: 'a5', user_id: 'u2', username: 'operator1', action: 'task_created', resource_type: 'task', resource_id: 't2', details: { task_type: 'infrastructure_provisioning', requires_approval: true }, ip_address: '10.0.1.8', success: true, created_at: '2024-01-15T10:00:00Z' },
  { id: 'a6', user_id: 'u3', username: 'viewer1', action: 'knowledge_search', resource_type: 'knowledge', resource_id: null, details: { query: 'P1 escalation steps', results: 5 }, ip_address: '10.0.2.3', success: true, created_at: '2024-01-15T09:45:00Z' },
  { id: 'a7', user_id: 'u2', username: 'operator1', action: 'login_failed', resource_type: 'auth', resource_id: null, details: { reason: 'invalid_password', attempt: 1 }, ip_address: '10.0.1.8', success: false, created_at: '2024-01-15T09:00:00Z' },
  { id: 'a8', user_id: 'u1', username: 'admin', action: 'document_ingested', resource_type: 'knowledge', resource_id: 'doc-12', details: { title: 'IT Glossary', chunks: 23 }, ip_address: '10.0.1.5', success: true, created_at: '2024-01-14T08:00:00Z' },
]

export const MOCK_APPROVALS: Approval[] = [
  {
    id: 'ap1', task_id: 't2',
    requested_by: 'u2', reviewed_by: null,
    agent_type: 'infrastructure_provisioning', priority: 'high',
    input_preview: 'Deploy Payment Service v2.4.1 to production — requires rolling restart of 12 instances.',
    status: 'pending', review_notes: null, expires_at: null,
    created_at: '2024-01-15T10:00:00Z', reviewed_at: null,
  },
]

export const MOCK_DOCUMENTS: KnowledgeDocument[] = [
  { id: 'd1', title: 'Incident Response Runbook', category: 'runbooks', source_path: 'runbooks/incident_response_runbook.md', clearance_level: 'internal', chunk_count: 18, token_count: 2340, created_at: '2024-01-14T08:00:00Z' },
  { id: 'd2', title: 'High CPU Runbook', category: 'runbooks', source_path: 'runbooks/high_cpu_runbook.md', clearance_level: 'internal', chunk_count: 12, token_count: 1560, created_at: '2024-01-14T08:01:00Z' },
  { id: 'd3', title: 'Database Failover Runbook', category: 'runbooks', source_path: 'runbooks/database_failover_runbook.md', clearance_level: 'internal', chunk_count: 14, token_count: 1820, created_at: '2024-01-14T08:02:00Z' },
  { id: 'd4', title: 'SOC 2 Policies', category: 'compliance', source_path: 'compliance/soc2_policies.md', clearance_level: 'confidential', chunk_count: 22, token_count: 2860, created_at: '2024-01-14T08:03:00Z' },
  { id: 'd5', title: 'NIST Controls', category: 'compliance', source_path: 'compliance/nist_controls.md', clearance_level: 'confidential', chunk_count: 19, token_count: 2470, created_at: '2024-01-14T08:04:00Z' },
  { id: 'd6', title: 'Provisioning Standards', category: 'infrastructure', source_path: 'infrastructure/provisioning_standards.md', clearance_level: 'internal', chunk_count: 16, token_count: 2080, created_at: '2024-01-14T08:05:00Z' },
  { id: 'd7', title: 'Escalation Matrix', category: 'general', source_path: 'general/escalation_matrix.md', clearance_level: 'public', chunk_count: 10, token_count: 1300, created_at: '2024-01-14T08:06:00Z' },
  { id: 'd8', title: 'On-Call Procedures', category: 'general', source_path: 'general/on_call_procedures.md', clearance_level: 'internal', chunk_count: 11, token_count: 1430, created_at: '2024-01-14T08:07:00Z' },
]

export const MOCK_STATS: KnowledgeStats = {
  total_documents: 18,
  total_chunks: 234,
  documents_by_category: { runbooks: 5, compliance: 5, infrastructure: 5, general: 3 },
  pgvector_indexed: 234,
  qdrant_indexed: 234,
}
