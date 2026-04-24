# Pages Reference

## Login (`/login`)

Entry point for all users. No auth required.

**Real login**: POSTs `username`/`password` to `/api/auth/login`, stores `access_token` and `refresh_token` in localStorage, fetches `/api/auth/me` to populate the user context.

**Demo login**: Three buttons (ADMIN / OPERATOR / VIEWER) call `loginDemo(role)`. The corresponding user from `MOCK_USERS` is stored in `localStorage.demo_user`. No network call is made.

Redirects to `/dashboard` if already authenticated (checked via `useEffect`).

---

## Dashboard (`/dashboard`)

Operational overview. All data comes from `MOCK_TASKS` and `MOCK_STATS` (demo) or would come from API calls in production.

**Stat cards** (6): Total Tasks, Running, Pending Approval, Failed, Knowledge Docs, RAG Chunks.

**Activity chart**: AreaChart (Recharts) — 8 time-of-day buckets over 24 hours. Static mock data.

**Status breakdown**: PieChart with inner radius (donut style). Segments generated from live `MOCK_TASKS` status distribution.

**Recent tasks table**: 5 most recently updated tasks with type, priority badge, status badge, and timestamp.

---

## Task Runner (`/tasks`)

The primary operational interface.

### Submission form
- Agent type selector (incident_response / infrastructure_provisioning / compliance_scan)
- Priority selector (P1–P4)
- Title and description text fields
- Submit button calls `POST /api/tasks` (real) or triggers demo animation (demo)

### Demo output
Hardcoded realistic output for each agent type in `DEMO_OUTPUTS` dict. Plays back line by line at 60ms intervals using `setInterval`, with colour-coding:
- `→` prefixed lines: cyan (tool call)
- `  Result:` lines: green, indented
- `[NEXUS` header: amber, bold
- `INCIDENT RESOLVED` / `SCAN COMPLETE` etc.: green, bold
- `RAG Knowledge Retrieved:` lines: secondary, italic

### Live output (non-demo)
`useTaskStream(activeTask.id)` streams events. Each event is rendered as `[event.type] {JSON.stringify(data)}`.

### RAG sources panel
Appears when sources are available (from WebSocket `rag_retrieval` event in real mode, or from `MOCK_TASKS[task.rag_sources]` in demo). Each source shows:
- Document title (cyan)
- Score as percentage (green)
- Text preview
- Source path badges: pgvector=info, qdrant_dense=success, qdrant_sparse=warning

### Recent tasks list
5 items from `MOCK_TASKS`. Clicking a task expands a detail panel showing `result` or `error_message`.

---

## Audit Explorer (`/audit`)

Filterable audit log with event detail panel.

**Filters**: text search (username, action, resource_type) and action-type dropdown (built from unique values in the log).

**Table**: time, user, action badge (colour-coded by action type), resource type, IP address.

**Detail panel**: Clicking a row shows full event details including timestamp (ISO format), user + user_id, action badge, resource path, IP, and the `details` JSON rendered in a `<pre>` block.

In demo mode all data comes from `MOCK_AUDIT_LOGS` (8 events). In production, calls `GET /api/audit`.

---

## Security Feed (`/security`)

SIEM-style security event feed. All data is static mock (`MOCK_EVENTS` defined locally in the file — not from `mocks/data.ts`).

**Summary cards**: Critical Open, High Open, Total Open, Mitigated counts.

**Severity trend chart**: BarChart with 7-day history, stacked bars for critical/high/medium.

**Filter panel**: Buttons for All/Critical/High/Medium/Low/Info with event count per severity.

**Events list**: Each event shows a severity dot, message, severity badge, category, source, timestamp, and MITIGATED badge for resolved events. Mitigated events are faded to 60% opacity.

---

## Knowledge Base (`/knowledge`)

Three-tab interface for the RAG knowledge pipeline.

### SEARCH tab
- Query input + SEARCH button
- In demo: 600ms artificial delay, then shows `MOCK_SEARCH_RESULTS` (3 results)
- In production: calls `POST /api/knowledge/search`
- Each result card shows: document title, category, score %, rerank score, text, RRF score, source path badges

### DOCUMENTS tab
- Category filter dropdown
- Grid of document cards showing: title, category badge, chunk count, token count, clearance badge (colour by level)
- Data from `MOCK_DOCUMENTS` (demo) or `GET /api/knowledge/documents` (production)

### PATH COMPARE tab
Visualises the three retrieval paths independently, then shows fused results.
- In demo: 800ms delay, then builds a `RagPathComparison` from `MOCK_SEARCH_RESULTS` filtered by path
- In production: calls `GET /api/knowledge/compare-paths?query=...`
- Latency breakdown card: pgvector / Qdrant / Reranker / Total in ms
- Three-column path results: pgvector (cyan), Qdrant Dense (green), Qdrant Sparse/BM25 (amber)
- Fused + reranked results with RRF score, rerank score, and source path badges

---

## Approvals (`/approvals`)

Approval queue for high/critical priority tasks.

**Pending section**: Each card shows task title, priority badge, requester, timestamp, task description (from `MOCK_TASKS`). Admin-only: review notes textarea + APPROVE (primary) / DENY (danger) buttons with 600ms mock delay in demo.

**Resolved section**: Historical approvals with reviewer, review time, notes, and approved/denied badge. Faded to 70%.

Non-admin users see the pending items but no action buttons — just a message that admin access is required.

State is managed locally with `useState`. In demo mode, approving/denying updates the local `approvals` array in place.

---

## User Management (`/users`)

Admin-only page. Redirects to an ACCESS DENIED card for non-admin users (check is in-component, not at the router level).

**User cards**: Avatar initials, username (with YOU badge for current user), email, role badge, clearance badge, last login, created date, active status.

**Inline editing**: EDIT button opens role and clearance Select dropdowns inline. SAVE commits; CANCEL discards. The user's own card has no EDIT/DISABLE buttons.

**Disable/Enable toggle**: Flips `is_active` locally in demo; would call `PATCH /api/auth/users/{id}` in production.

All state is managed with `useState` on `MOCK_USERS` in demo mode.
