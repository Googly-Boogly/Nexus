# Security Architecture

## Overview

Security is implemented as multiple independent layers that each have a single responsibility. They operate in sequence inside `BaseAgent.run()` and at the API routing level.

```
core/
├── security.py       JWT creation/verification, bcrypt hashing, clearance helpers
├── audit.py          Async audit log writer + EventType constants
├── governance.py     PII detection/redaction, forbidden command check, rate limiting
├── sandbox.py        Tool allowlists per agent type
├── prompt_defense.py Multi-layer prompt injection defense
├── llm_providers.py  LLM abstraction + routing + failover
└── opa_client.py     OPA HTTP client + local RBAC fallback
```

---

## Authentication (`core/security.py`)

JWT HS256 signed with `SECRET_KEY`. Two token types:
- **Access token** — 30-minute TTL, `"type": "access"` claim
- **Refresh token** — 7-day TTL, `"type": "refresh"` claim

JWT payload: `{"sub": username, "role": role, "clearance": clearance, "user_id": uuid_str, "exp": ..., "type": ...}`

Password hashing: `passlib[bcrypt]` with `bcrypt==4.0.1` pinned to avoid API breakage.

### Login lockout
5 failed attempts → account locked for 15 minutes (`locked_until` column on `User`). The lockout check is against the current UTC time, not a session flag, so it survives server restarts.

### DEMO_MODE auth
When `DEMO_MODE=True`, `get_current_user()` skips the DB lookup and builds a `User` object directly from the JWT claims (`_synthetic_user(payload)`). This allows the entire security pipeline to run without a real database.

### Clearance hierarchy
`CLEARANCE_HIERARCHY = ["public", "internal", "confidential"]`

`clearance_level(s)` returns the integer index. `accessible_levels(clearance)` returns all levels at or below the user's clearance.

---

## Authorization (`core/opa_client.py`)

Authorization is a two-phase check:

**Phase 1 — OPA call** (production): async HTTP POST to `http://opa:8181/v1/data/nexus/authz/allow` with:
```json
{
  "input": {
    "user": {"role": "operator", "clearance": "internal"},
    "action": "execute:incident_response",
    "resource": {"classification": "internal"}
  }
}
```

**Phase 2 — local RBAC fallback**: if OPA is unreachable or returns an error, `local_rbac_check()` is used. The local permissions dict is the source of truth for both modes.

### Role permissions

| Role | Permitted actions |
|---|---|
| `admin` | All execute, audit, admin, approvals, knowledge actions |
| `operator` | `execute:incident_response`, `execute:compliance_scan`, `audit:view_own`, `admin:system_metrics`, `knowledge:search` |
| `viewer` | `audit:view_own`, `knowledge:search` |

**Note**: OPA's `authz.rego` has a divergence — it maps `execute:provisioning` while the Python fallback uses `execute:infrastructure_provisioning`. The Python fallback and `base_agent.py` are authoritative; OPA policies should be updated to match.

### Tool authorization (`check_tool_allowed`)
Separate OPA endpoint `nexus/agents/tool_allowed`. Falls back to `AGENT_ALLOWED_TOOLS` dict in `sandbox.py`.

---

## Prompt Defense (`core/prompt_defense.py`)

Six layers applied in sequence:

### 1. Static pattern check
11 regex patterns covering:
- `\n ignore previous instructions` style injections
- System/assistant/user tag injections (`<system>`, `[INST]`)
- Role-play jailbreaks (`pretend you are`, `act as if`)
- Known jailbreak keywords (DAN, STAN, DUDE, AIM)
- Instruction extraction attempts (`reveal your system prompt`)

### 2. Jailbreak phrase check
26 exact phrases matched case-insensitively in the static check.

### 3. LLM classifier
`claude-haiku-4-5-20251001` classifies the input. Returns JSON:
```json
{"is_safe": true, "threat_type": null, "confidence": 0.0, "reasoning": ""}
```
Input is blocked if `is_safe=false` OR if the combined threat score ≥ 0.6.

Combined score = max of (static threat score, LLM confidence if unsafe). Static score = 1.0 if any static pattern matches.

### 4. Tool result inspection
Each tool response is checked against the same injection patterns before being appended to the LLM context. Blocked results are replaced with a sanitized error string.

### 5. Constitutional check (post-output)
After the LLM produces its final output, `constitutional_check()` uses Haiku to verify compliance:
```json
{"compliant": true, "violations": [], "severity": "none"}
```
The output is blocked if `compliant=false`.

### 6. RAG query sanitization
`RAGDefenseLayer.sanitize_query()` additionally strips HTML tags and code blocks from the query string.

---

## Governance Layer (`core/governance.py`)

### PII detection and redaction
Five pattern types: SSN (`\b\d{3}-\d{2}-\d{4}\b`), credit card numbers, AWS access keys (`AKIA[A-Z0-9]{16}`), PEM private keys, and password literals. Detected PII is replaced with `[SSN_REDACTED]`, `[CREDIT_CARD_REDACTED]`, etc. A `PII_DETECTED` audit event is written with the types found.

### Forbidden command detection
Nine regex patterns for destructive operations: `rm -rf`, `DROP TABLE`, naked `DELETE FROM`, `eval(`, `exec(`, `os.system(`, `subprocess.*`, `__import__(`, Windows format commands.

### Rate limiting
Redis sliding window: 30 requests per user per 60-second window. Key: `ratelimit:{user_id}`. On `DEMO_MODE` or Redis unavailable, the check passes silently.

### Input length
`check_length()` enforces `MAX_INPUT_LENGTH` (default 2000 characters).

---

## Sandbox (`core/sandbox.py`)

Hard-coded allowlist per agent type:

```python
AGENT_ALLOWED_TOOLS = {
    "incident_response": {
        "check_system_status", "query_application_logs", "restart_service",
        "isolate_host", "escalate_ticket", "notify_on_call", "query_knowledge_base"
    },
    "infrastructure_provisioning": {
        "create_virtual_machine", "deploy_container", "resize_resource",
        "check_quota", "tag_resource", "decommission_resource", "query_knowledge_base"
    },
    "compliance_scan": {
        "scan_vulnerabilities", "check_patch_status", "audit_access_rights",
        "list_open_ports", "check_encryption_status", "generate_compliance_report",
        "query_knowledge_base"
    },
}
```

`filter_tools()` strips any tools not in the allowlist from the list passed to the LLM, preventing the model from even seeing unapproved tool signatures.

`check_tool()` validates at call-time — a `SandboxViolationError` is raised if the LLM somehow calls a tool not in its allowlist (e.g. via a prompt injection that altered the tool name).

---

## Audit Logging (`core/audit.py`)

Every security-relevant event is written to `audit_log` via `log_event()`. The function is `async` and uses `session.flush()` (not `session.commit()`) so the log entry is part of the same database transaction as any side effects.

### Event types

| EventType constant | When written |
|---|---|
| `LOGIN_SUCCESS` / `LOGIN_FAILED` / `LOGIN_LOCKED` | Auth attempts |
| `TOKEN_REFRESH` | Token refresh |
| `TASK_SUBMITTED` / `TASK_COMPLETED` / `TASK_FAILED` | Agent pipeline |
| `APPROVAL_REQUESTED` / `APPROVAL_GRANTED` / `APPROVAL_DENIED` | Approval flow |
| `RAG_RETRIEVAL` / `RAG_QUARANTINE` / `RAG_POISONING_SUSPECTED` / `RAG_INDIRECT_INJECTION` | RAG defense events |
| `KNOWLEDGE_INGESTED` / `KNOWLEDGE_DELETED` | Knowledge base mutations |
| `PROMPT_INJECTION_BLOCKED` / `JAILBREAK_BLOCKED` / `CONSTITUTIONAL_VIOLATION` | Defense activations |
| `PII_DETECTED` | PII redaction |
| `RATE_LIMITED` | Rate limit exceeded |
| `CLEARANCE_DENIED` | Authorization failures |
| `USER_CREATED` / `USER_UPDATED` | User management |

### Row-Level Security
The `audit_log` table has PostgreSQL RLS enabled:
```sql
CREATE POLICY user_audit_isolation ON audit_log AS PERMISSIVE FOR SELECT
USING (user_id::text = current_setting('app.current_user_id', true))
```
Non-admin API reads filter by `user_id = user.id` at the application layer; RLS provides a defence-in-depth guarantee at the database level.

---

## LLM Security (`core/llm_providers.py`)

`LLMRouter.complete_with_failover()` routes to the per-agent preferred provider and falls back to the other provider on HTTP 429 or 500 errors. This prevents a single provider outage from blocking all agent execution.

Cost tracking uses a static `COST_PER_1K_TOKENS` lookup. Costs are recorded on the `Task` row and in the `TASK_COMPLETED` audit event.
