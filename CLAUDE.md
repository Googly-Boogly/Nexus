# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All `make` targets run from `nexus/`:

```bash
make dev            # docker compose up --build (all 7 services)
make migrate        # alembic upgrade head
make seed           # 3 demo users + 60 tasks
make seed-knowledge # ingest 18 sample .md docs into pgvector + Qdrant
make test           # pytest inside Docker
make clean          # docker compose down -v
```

**Running tests locally** (without Docker — uses SQLite, no external services needed):

```bash
# From repo root — activate the .venv first
source .venv/bin/activate
python -m pytest nexus/backend/tests/ -v
python -m pytest nexus/backend/tests/test_rag.py::test_chunker_splits_long_doc -v  # single test
```

**Frontend typecheck** (requires Node via nvm):

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh"
cd nexus/frontend && npm install && npm run typecheck
```

## Architecture Overview

### Services (docker-compose)

| Service | Image / Build | Port |
|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | internal |
| `redis` | `redis:7-alpine` | internal |
| `qdrant` | `qdrant/qdrant` | 6333 (UI at `/dashboard`) |
| `opa` | `openpolicyagent/opa` | 8181 (internal) |
| `api` | `backend/Dockerfile` | 8000 |
| `worker` | same image, Celery | internal |
| `frontend` | `frontend/Dockerfile` (nginx) | 3000 |

`nexus_internal` network is isolated; only `api` and `frontend` are on `nexus_public`.

### Backend (`backend/app/`)

**Request flow for a task submission:**

1. `POST /tasks/` → `api/routes/tasks.py` dispatches Celery task (skipped in `DEMO_MODE`)
2. `workers/task_worker.py` runs `execute_agent_task`, publishes Redis pub/sub events
3. `GET /tasks/{id}/stream` WebSocket streams those events to the frontend

**Agent pipeline** (`agents/base_agent.py` — 12 steps, in order):
rate-limit → OPA authz → clearance check → audit log → static prompt defense → LLM classifier → input guardrails (PII, length) → approval gate → RAG retrieval → LLM agentic loop → constitutional check → output audit

Three concrete agents (`incident_agent.py`, `provisioning_agent.py`, `compliance_agent.py`) extend `BaseAgent`, implementing `get_tools()`, `get_system_prompt()`, and `execute_tool()`. The agentic loop is driven directly via Anthropic/OpenAI SDK — no LangChain AgentExecutor.

**Dual RAG pipeline** (`rag/`):

```
query
  ├─ pgvector HNSW cosine similarity  (pgvector_store.py)
  └─ Qdrant dense + sparse hybrid     (qdrant_store.py)
         ↓ asyncio.gather (concurrent)
     Reciprocal Rank Fusion k=60      (fusion.py)
         ↓
     CrossEncoder reranker            (reranker.py — cross-encoder/ms-marco-MiniLM-L-6-v2)
         ↓
     RAGDefenseLayer                  (rag_defense.py — relevance gate, classification filter)
```

`RAGPipeline` (`pipeline.py`) orchestrates ingest and retrieval. On ingest, every chunk is written to both pgvector (via SQLAlchemy ORM) and Qdrant simultaneously.

**Security layers** (`core/`):
- `prompt_defense.py` — static regex patterns + LLM classifier (haiku) + constitutional self-check on output
- `governance.py` — PII redaction (SSN/CC/AWS keys/private keys), forbidden command detection, Redis sliding-window rate limit
- `sandbox.py` — per-agent tool allowlists, blocks unapproved tool calls
- `opa_client.py` — async OPA HTTP call; falls back to local RBAC dict on error
- `llm_providers.py` — `LLMRouter` with per-agent provider routing and automatic failover

### Frontend (`frontend/src/`)

React 18 + TypeScript + Vite + Tailwind. All pages consume mock data when `isDemoMode` (set in `AuthContext` via `loginDemo()`). The three demo login buttons on `/login` skip the API entirely.

`useTaskStream.ts` — WebSocket hook with exponential backoff reconnect; extracts `rag_sources` from `rag_retrieval` events.

Seven routes: `/dashboard`, `/tasks`, `/audit`, `/security`, `/knowledge`, `/approvals`, `/users`.

## Key Implementation Constraints

**DEMO_MODE** (`settings.DEMO_MODE = True` by default):
- `EmbeddingProvider` returns deterministic hash-seeded unit vectors (no OpenAI call)
- `CrossEncoderReranker` sorts by rrf_score instead of loading the model
- `PGVectorStore` returns `[]` for all queries (skips pgvector ops)
- `BaseAgent.run()` returns a hardcoded demo string
- `get_current_user` synthesizes a `User` from JWT claims without a DB lookup
- Celery dispatch is skipped; a `demo-{task_id}` is written directly

**Cross-dialect SQLAlchemy models** (must work for both PostgreSQL and SQLite in tests):
- Use `Uuid` (from `sqlalchemy`), not `UUID` from `sqlalchemy.dialects.postgresql`
- Use `JSON`, not `JSONB`
- Use Python-side defaults (`default=uuid.uuid4`, `default=lambda: datetime.now(timezone.utc)`), not `server_default`

**pgvector on SQLite** — tests patch `pgvector.sqlalchemy.VECTOR = lambda dim=None: Text()` in `conftest.py`. `PGVectorStore` methods early-return `[]` when `"sqlite" in settings.DATABASE_URL` to avoid `.cosine_distance()` and `SET LOCAL` failures.

**OPA action names** — must be the exact strings `execute:incident_response`, `execute:infrastructure_provisioning`, `execute:compliance_scan`. The local RBAC dict in `opa_client.py` and the Rego policies must stay in sync.

**Qdrant collection config** — must use named vectors:
```python
vectors_config={"dense": VectorParams(size=1536, distance=Distance.COSINE)},
sparse_vectors_config={"sparse": SparseVectorParams(...)}
```

**pgvector HNSW** — HNSW index and GIN FTS index are created via `op.execute()` raw SQL in the Alembic migration (not via SQLAlchemy `Index` objects). Before each similarity search: `SET LOCAL hnsw.ef_search = :ef`.

## Testing

Tests use SQLite in-memory via `conftest.py`. The `session` fixture rolls back after each test. `DEMO_MODE=true` is set as an env var before imports so no real services are contacted.

Mock classes for unit tests (`MockEmbedder`, `MockReranker`, `MockPGVectorStore`, `MockQdrantStore`) are all defined in `conftest.py`.

Token fixtures: `admin_token` (role=admin, clearance=confidential), `operator_token` (operator/internal), `viewer_token` (viewer/public).
