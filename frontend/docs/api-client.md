# API Client

## Axios Instance (`src/api/client.ts`)

The default export is a configured Axios instance. All API functions are named exports from the same file.

```typescript
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})
```

### Request interceptor
Attaches `Authorization: Bearer <token>` from `localStorage.access_token` on every request.

### Response interceptor (401 auto-refresh)
On a 401 response:
1. Attempts to POST `/api/auth/refresh` with the stored `refresh_token`
2. If successful: stores the new `access_token` and retries the original request
3. If refresh fails: clears `localStorage` and redirects to `/login`

---

## API Functions

### Auth
```typescript
login(username, password)         // POST /auth/login → AuthTokens
getMe()                           // GET  /auth/me    → User
```

### Tasks
```typescript
createTask({ title, description, task_type, priority })  // POST /tasks → Task
getTasks(params?)                 // GET  /tasks → { tasks, total, page, per_page }
getTask(id)                       // GET  /tasks/{id} → Task
```

### Audit
```typescript
getAuditLogs(params?)             // GET  /audit → { logs, total }
```

Params: `action`, `user_id`, `page`, `per_page`, `start_time`, `end_time`

### Approvals
```typescript
getPendingApprovals()             // GET  /approvals/pending → Approval[]
approveTask(id, notes?)           // POST /approvals/{id}/approve
denyTask(id, notes?)              // POST /approvals/{id}/deny
```

### Users (admin only)
```typescript
getUsers()                        // GET  /users → User[]
updateUserRole(id, role, clearance)  // PATCH /users/{id}
toggleUser(id, active)            // PATCH /users/{id}
```

### Knowledge
```typescript
ingestDocument({ title, content, category, source_path, clearance_level })
                                  // POST /knowledge/ingest
getDocuments(params?)             // GET  /knowledge/documents → { documents, total }
deleteDocument(id)                // DELETE /knowledge/documents/{id}
searchKnowledge({ query, top_k?, filters? })
                                  // POST /knowledge/search → KnowledgeSearchResult[]
getKnowledgeStats()               // GET  /knowledge/stats → KnowledgeStats
compareRagPaths(query, top_k?)    // GET  /knowledge/compare-paths → RagPathComparison
```

---

## TypeScript Types (`src/types/index.ts`)

All API types are declared as interfaces:

```typescript
type UserRole = 'admin' | 'operator' | 'viewer'
type DataClearance = 'public' | 'internal' | 'confidential' | 'restricted'
type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' |
                  'pending_approval' | 'approved' | 'rejected'
type TaskPriority = 'P1' | 'P2' | 'P3' | 'P4'
type AgentType = 'incident_response' | 'infrastructure_provisioning' | 'compliance_scan'
```

Key interfaces: `User`, `Task`, `RagSource`, `AuditLog`, `Approval`, `KnowledgeDocument`, `KnowledgeSearchResult`, `KnowledgeStats`, `RagPathComparison`, `AuthTokens`, `TaskEvent`

### TaskEvent
Used by `useTaskStream` to type WebSocket messages:
```typescript
interface TaskEvent {
  type: 'status_update' | 'log' | 'tool_call' | 'tool_result' | 'rag_retrieval' | 'complete' | 'error'
  timestamp: string
  data: Record<string, unknown>
}
```
The `rag_retrieval` event's `data.sources` is cast to `RagSource[]` to populate the RAG sources panel.

---

## Mock Data (`src/mocks/data.ts`)

Provides static typed data for DEMO_MODE:

| Export | Type | Contents |
|---|---|---|
| `MOCK_USERS` | `User[]` | 3 users: admin (restricted), operator1 (confidential), viewer1 (internal) |
| `MOCK_TASKS` | `Task[]` | 5 tasks across all 3 agent types and various statuses |
| `MOCK_AUDIT_LOGS` | `AuditLog[]` | 8 events including login, task creation, rag_retrieval |
| `MOCK_APPROVALS` | `Approval[]` | 1 pending approval for a P2 infrastructure task |
| `MOCK_DOCUMENTS` | `KnowledgeDocument[]` | 8 documents across runbooks/compliance/infrastructure/general |
| `MOCK_STATS` | `KnowledgeStats` | 18 docs, 234 chunks, category breakdown |

`MOCK_TASKS[0]` (incident_response, completed) has `rag_sources` populated — used by `TaskRunner` to show the RAG panel in demo mode.
