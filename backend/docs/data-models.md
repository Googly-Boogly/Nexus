# Data Models

All models use SQLAlchemy 2.x ORM with `Mapped[]` type annotations. They are written to be cross-dialect (PostgreSQL + SQLite) — see constraints section at the bottom.

---

## User

**Table**: `users`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | Python-side default `uuid.uuid4` |
| `username` | `String(100)` UNIQUE | Used as JWT `sub` claim |
| `email` | `String(255)` UNIQUE | |
| `hashed_password` | `String(255)` | bcrypt |
| `role` | `String(50)` | `admin` \| `operator` \| `viewer` |
| `data_clearance` | `String(50)` | `public` \| `internal` \| `confidential` |
| `is_active` | `Boolean` | Default `True` |
| `failed_login_attempts` | `Integer` | Reset to 0 on successful login |
| `locked_until` | `DateTime(tz=True)` nullable | Set after 5 failed login attempts |
| `created_at` | `DateTime(tz=True)` | Python-side default |
| `updated_at` | `DateTime(tz=True)` | `onupdate=_now` |

**Relationships**: `tasks` (1:N), `audit_logs` (1:N), `knowledge_docs` (1:N, as uploader)

---

## Task

**Table**: `tasks`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | |
| `user_id` | `Uuid` FK → `users.id` | |
| `agent_type` | `String(100)` | `incident_response` \| `infrastructure_provisioning` \| `compliance_scan` |
| `priority` | `String(50)` | `low` \| `medium` \| `high` \| `critical` |
| `status` | `String(50)` | `pending` \| `queued` \| `running` \| `awaiting_approval` \| `completed` \| `failed` |
| `input_text` | `Text` | User's task description (after PII redaction) |
| `result` | `Text` nullable | Agent output on completion |
| `error_message` | `Text` nullable | Error description on failure |
| `celery_task_id` | `String(255)` nullable | Celery task UUID or `demo-{task_id}` |
| `llm_provider` | `String(100)` nullable | Model name, e.g. `claude-sonnet-4-6` |
| `tokens_used` | `Integer` | Total input + output tokens |
| `cost_usd` | `Float` | Estimated cost |
| `rag_chunks_retrieved` | `Integer` | Count of chunks passed to LLM |
| `rag_sources` | `JSON` | Array of `{title, category, score}` |
| `approval_required` | `Boolean` | Set for high/critical priority tasks |
| `approval_id` | `Uuid` FK → `approvals.id` nullable | Set when approval is created |
| `duration_ms` | `Integer` | Wall-clock time for agent execution |
| `created_at` / `updated_at` | `DateTime(tz=True)` | |

**Relationships**: `user` (N:1), `approval` (N:1 optional)

---

## Approval

**Table**: `approvals`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | |
| `task_id` | `Uuid` nullable | Points to the associated task |
| `requested_by` | `Uuid` FK → `users.id` | |
| `reviewed_by` | `Uuid` FK → `users.id` nullable | Set when admin reviews |
| `agent_type` | `String(100)` | Copied from the task |
| `priority` | `String(50)` | Copied from the task |
| `input_preview` | `Text` nullable | First portion of input for display |
| `status` | `String(50)` | `pending` \| `approved` \| `denied` |
| `review_notes` | `Text` nullable | Admin's notes |
| `expires_at` | `DateTime(tz=True)` nullable | Optional expiry |
| `created_at` / `reviewed_at` | `DateTime(tz=True)` | |

**Relationships**: `requester` (N:1 User), `reviewer` (N:1 User nullable)

---

## AuditLog

**Table**: `audit_log`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | |
| `user_id` | `Uuid` nullable FK → `users.id` | Nullable for system events |
| `event_type` | `String(100)` | See `EventType` constants in `core/audit.py` |
| `resource_type` | `String(100)` nullable | e.g. `task`, `knowledge`, `auth` |
| `resource_id` | `String(255)` nullable | UUID string of the affected resource |
| `action` | `String(255)` nullable | Human-readable action description |
| `status` | `String(50)` nullable | |
| `threat_score` | `Float` | 0.0–1.0 for defense events |
| `ip_address` | `String(45)` nullable | IPv4 or IPv6 |
| `user_agent` | `Text` nullable | |
| `details` | `JSON` | Arbitrary event-specific metadata |
| `message` | `Text` nullable | |
| `created_at` | `DateTime(tz=True)` | |

**RLS policy** (PostgreSQL only): `SELECT` is restricted to rows where `user_id = current_setting('app.current_user_id')`. The API layer enforces the same filter explicitly.

**Relationships**: `user` (N:1 optional)

---

## KnowledgeDocument

**Table**: `knowledge_documents`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | |
| `title` | `String(500)` | |
| `source_filename` | `String(1000)` | e.g. `incident_response_runbook.md` |
| `category` | `String(100)` | `runbook` \| `compliance` \| `infrastructure` \| `general` |
| `data_classification` | `String(50)` | `public` \| `internal` \| `confidential` |
| `chunk_count` | `Integer` | Number of chunks produced at ingest |
| `token_count` | `Integer` | Total token count across all chunks |
| `embedding_model` | `String(100)` | `text-embedding-3-small` |
| `uploaded_by` | `Uuid` FK → `users.id` | |
| `is_active` | `Boolean` | `False` after soft-delete |
| `poisoning_suspected` | `Boolean` | Set when ≥2 chunks quarantined at retrieval |
| `created_at` / `updated_at` | `DateTime(tz=True)` | |

**Relationships**: `chunks` (1:N cascade delete), `uploader` (N:1 User)

---

## KnowledgeChunk

**Table**: `knowledge_chunks`

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid` PK | Also used as pgvector row identifier |
| `document_id` | `Uuid` FK → `knowledge_documents.id` ON DELETE CASCADE | |
| `qdrant_point_id` | `Uuid` nullable | Qdrant point ID (may differ from chunk id) |
| `chunk_index` | `Integer` | 0-based position within the document |
| `text` | `Text` | Raw chunk text |
| `token_count` | `Integer` | tiktoken cl100k_base count |
| `start_char` / `end_char` | `Integer` | Character offsets in original document |
| `embedding` | `VECTOR(1536)` | pgvector column; patched to `Text` in tests |
| `chunk_metadata` | `JSON` | LangChain splitter metadata + `chunk_index` |
| `created_at` | `DateTime(tz=True)` | |

**Indexes**:
- `idx_chunk_document` on `document_id` (ORM index)
- HNSW index on `embedding` with `vector_cosine_ops`, `m=16`, `ef_construction=64` (migration raw SQL)
- GIN index on `to_tsvector('english', text)` (migration raw SQL)

**Relationships**: `document` (N:1 KnowledgeDocument)

---

## Cross-Dialect Constraints

These constraints must be preserved when adding or modifying models:

| ❌ Don't use | ✅ Use instead | Reason |
|---|---|---|
| `sqlalchemy.dialects.postgresql.UUID` | `sqlalchemy.Uuid` | SQLite compatibility |
| `sqlalchemy.dialects.postgresql.JSONB` | `sqlalchemy.JSON` | SQLite compatibility |
| `server_default=text("gen_random_uuid()")` | `default=uuid.uuid4` | SQLite has no `gen_random_uuid()` |
| `server_default=func.now()` | `default=lambda: datetime.now(timezone.utc)` | Avoids SQLite datetime format issues |
| `pgvector.sqlalchemy.VECTOR` | (keep for production; patched in tests) | Tests patch it to `Text` in conftest.py |
