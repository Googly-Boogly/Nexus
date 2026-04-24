# Backend Architecture

## Overview

The backend is a FastAPI async application running under Uvicorn. It has two process types:

- **api** — handles HTTP requests and WebSocket streams
- **worker** — executes agent tasks asynchronously via Celery

Both processes share the same Docker image built from `backend/Dockerfile`.

## Module Layout

```
backend/app/
├── main.py              # FastAPI app, CORS, middleware, lifespan startup
├── config.py            # Pydantic Settings v2 — all configuration from environment
├── database.py          # Async SQLAlchemy engine, session factory, get_db dependency
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic v2 request/response schemas
├── core/                # Cross-cutting concerns (auth, security, governance, LLM routing)
├── rag/                 # Dual-database RAG pipeline
├── agents/              # AI agent implementations
├── api/routes/          # FastAPI routers (one file per resource)
└── workers/             # Celery worker and task definitions
```

## Request Lifecycle

### Synchronous endpoints (auth, knowledge, audit, approvals)
```
HTTP request
  → RequestIDMiddleware (injects X-Request-ID)
  → SecurityHeadersMiddleware (adds security headers)
  → Router handler
      → get_current_user (JWT decode → DB lookup; or synthetic user in DEMO_MODE)
      → Business logic
      → SQLAlchemy async session (auto-committed or explicitly committed)
  → Response
```

### Task submission (`POST /tasks`)
```
POST /tasks
  → submit_task()
      → Create Task row (status=queued or awaiting_approval)
      → If not approval_required:
            DEMO_MODE  → set celery_task_id=demo-{id}, status=running
            Production → execute_agent_task.delay(...) → Celery queue
      → session.commit()
  → 200 TaskOut

(background, Celery worker)
execute_agent_task
  → orchestrator.get_agent(agent_type)
  → agent.run(...)       ← 12-step pipeline, see agents.md
  → Update Task row
  → Publish completion event to Redis pub/sub
```

### WebSocket task stream (`/tasks/ws/{task_id}`)
```
Frontend opens WS with ?token=<access_token>
  → Verify JWT
  → Subscribe to Redis channel task:{task_id}:events
  → Forward each message to WebSocket client
  → Auto-close on "completed" or "failed" event, or 5-minute timeout
```

## Database

PostgreSQL (production) via `asyncpg`. SQLite via `aiosqlite` in tests.

The SQLAlchemy engine conditionally sets `pool_size`/`max_overflow` only for non-SQLite URLs — SQLite's `StaticPool` does not accept these parameters.

Alembic manages schema migrations. The initial migration (`001_initial_schema.py`) creates the `vector` and `pg_trgm` extensions, all tables, the HNSW index on `knowledge_chunks.embedding`, a GIN index for full-text search, and the `audit_log` RLS policy — all via `op.execute()` raw SQL.

## Configuration

`app/config.py` exposes a single `settings` singleton. All values are read from environment variables (or `.env` file). Key flags:

| Setting | Default | Effect when True |
|---|---|---|
| `DEMO_MODE` | `True` | Bypasses external services (LLM, Redis, Qdrant, pgvector ops), synthetic JWT users |
| `APP_ENV` | `development` | Enables SQLAlchemy echo |
| `PRIMARY_LLM_PROVIDER` | `anthropic` | Fallback when no per-agent mapping |

## Startup (lifespan)

On startup (`main.py:lifespan`):
1. `QdrantStore.create_collection_if_not_exists()` — idempotent Qdrant collection setup with named `dense` + `sparse` vectors
2. `CrossEncoderReranker.get()` — warms the cross-encoder model (skipped in `DEMO_MODE`)

## Middleware

| Middleware | Purpose |
|---|---|
| `CORSMiddleware` | Allows `http://localhost:3000` and `http://frontend:80` |
| `SecurityHeadersMiddleware` | Adds `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security` |
| `RequestIDMiddleware` | Injects `X-Request-ID` UUID into every request and response |

## Network Isolation

`nexus_internal` is a Docker bridge network with `internal: true` — no external connectivity. PostgreSQL, Redis, Qdrant, and OPA are only reachable from within this network. Only the `api` and `frontend` services are also attached to `nexus_public`.
