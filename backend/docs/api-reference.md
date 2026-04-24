# API Reference

Base URL: `http://localhost:8000`

All endpoints (except `/health` and `/auth/login`) require `Authorization: Bearer <access_token>`.

---

## Health

### `GET /health`
Returns service status. No authentication required.

```json
{"status": "healthy", "service": "nexus-api", "version": "1.0.0"}
```

---

## Auth — `/auth`

### `POST /auth/login`
Form-encoded or JSON credentials. Returns JWT pair.

**Request**
```json
{"username": "admin", "password": "secret"}
```

**Response**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

**Error codes**
- `401` — wrong credentials
- `423` — account locked (5 failed attempts → 15-minute lockout)

---

### `POST /auth/refresh`
Exchange a refresh token for a new token pair.

**Request** `{"refresh_token": "<jwt>"}`

---

### `GET /auth/me`
Returns the current user object.

---

### `GET /auth/users` *(admin only)*
Lists all users.

---

### `POST /auth/users` *(admin only)*
Creates a user.

**Request**
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "secret",
  "role": "operator",
  "data_clearance": "internal"
}
```

---

### `PATCH /auth/users/{user_id}` *(admin only)*
Updates role, clearance, or active status.

```json
{"role": "operator", "data_clearance": "confidential", "is_active": true}
```

---

## Tasks — `/tasks`

### `POST /tasks`
Submit a task to an agent. High/critical priority tasks are held for approval.

**Request**
```json
{
  "agent_type": "incident_response",
  "priority": "medium",
  "input_text": "API gateway is returning 503 errors",
  "preferred_provider": "anthropic"
}
```

`agent_type` must be one of: `incident_response`, `infrastructure_provisioning`, `compliance_scan`.

`priority` values: `low`, `medium`, `high`, `critical`. Tasks with `high` or `critical` priority are set to `awaiting_approval` and not dispatched until approved.

**Response** — `TaskOut` schema (see Data Models).

---

### `GET /tasks`
Lists tasks. Admins see all; other roles see their own.

---

### `GET /tasks/{task_id}`
Get a single task. Non-admins can only fetch their own tasks.

---

### `WebSocket /tasks/ws/{task_id}?token=<access_token>`
Streams task execution events as newline-delimited JSON.

**Event format**
```json
{"event": "started", "data": {"agent_type": "incident_response"}, "timestamp": "..."}
{"event": "tool_call", "data": {"tool": "check_system_status", "input": {...}}, "timestamp": "..."}
{"event": "rag_retrieval", "data": {"sources": [...], "stats": {...}}, "timestamp": "..."}
{"event": "completed", "data": {"result": "...", "tokens": 1240}, "timestamp": "..."}
```

Event types: `started`, `tool_call`, `tool_result`, `rag_retrieval`, `completed`, `failed`.

Connection auto-closes on `completed`/`failed` or after 300 seconds.

---

## Audit — `/audit`

### `GET /audit`
Returns audit log entries. Admins see all events; other roles see only their own.

**Query params**: `event_type`, `limit` (default 50), `offset`

---

### `GET /audit/{log_id}`
Get a single audit log entry.

---

## Approvals — `/approvals`

### `GET /approvals`
Lists approvals. Admins see all; others see their own. Optional `?status=pending`.

### `GET /approvals/{approval_id}`
Get a single approval.

### `POST /approvals/{approval_id}/review` *(admin only)*
Approve or deny a pending request.

**Request**
```json
{"action": "approve", "notes": "Reviewed and approved for production"}
```

On `approve`: the associated task is re-queued and dispatched to Celery immediately.

---

## Knowledge — `/knowledge`

### `POST /knowledge/ingest` *(admin only)*
Ingest a document. Accepts `multipart/form-data`.

**Fields**: `file` (text file), `title`, `category` (`runbook` | `compliance` | `infrastructure` | `general`), `classification` (`public` | `internal` | `confidential`)

The document is chunked, embedded, stored in pgvector (via SQLAlchemy) and Qdrant simultaneously. Returns chunk and token counts.

---

### `GET /knowledge/documents`
List documents visible to the user's clearance level.

**Query params**: `category`, `limit`, `offset`, `title_contains`

---

### `GET /knowledge/documents/{doc_id}`
Get a document with its first 5 chunk previews (300 chars each).

---

### `DELETE /knowledge/documents/{doc_id}` *(admin only)*
Soft-deletes a document (`is_active = False`) and removes its Qdrant points.

---

### `POST /knowledge/search`
Hybrid RAG search. Returns fused and reranked results with source path attribution.

**Request**
```json
{"query": "How do I escalate a P1 incident?", "category": "runbook", "top_n": 8}
```

**Response** — `SearchResponse` with `results` (array of `SearchResultOut`) and `retrieval_stats`.

Returns empty in `DEMO_MODE`.

---

### `GET /knowledge/stats` *(admin or operator)*
Returns document/chunk/token counts, breakdown by category and classification, and Qdrant collection info.

---

### `GET /knowledge/compare-paths` *(admin only)*
Debug endpoint. Runs the same query through all three retrieval paths independently and returns a side-by-side comparison with RRF fusion.

**Query params**: `query`

Returns `pgvector_only`, `qdrant_only`, `both`, and `fused_top5` arrays.

---

## Common Response Schemas

### TaskOut
```json
{
  "id": "uuid",
  "agent_type": "incident_response",
  "priority": "medium",
  "status": "completed",
  "input_text": "...",
  "result": "...",
  "error_message": null,
  "celery_task_id": "abc123",
  "llm_provider": "claude-sonnet-4-6",
  "tokens_used": 1842,
  "cost_usd": 0.0031,
  "rag_chunks_retrieved": 4,
  "rag_sources": [{"title": "...", "category": "...", "score": 0.91}],
  "approval_required": false,
  "duration_ms": 3420,
  "created_at": "...",
  "updated_at": "..."
}
```

### SearchResultOut
```json
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "title": "Incident Response Runbook",
  "category": "runbook",
  "classification": "internal",
  "chunk_index": 3,
  "token_count": 487,
  "text": "...",
  "cross_score": 0.87,
  "rrf_score": 0.0312,
  "pgvector_rank": 1,
  "qdrant_dense_rank": 2,
  "qdrant_sparse_rank": null,
  "source_paths": ["pgvector", "qdrant_dense"]
}
```

### AuditLogOut
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "event_type": "task_submitted",
  "resource_type": "task",
  "resource_id": "uuid",
  "threat_score": 0.0,
  "details": {},
  "created_at": "..."
}
```
