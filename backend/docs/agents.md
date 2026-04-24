# Agent System

## Overview

Three specialist AI agents handle different categories of IT automation tasks. All share a common 12-step security pipeline defined in `BaseAgent`. The agentic loop is driven directly via the Anthropic and OpenAI SDKs — no LangChain AgentExecutor.

```
agents/
├── base_agent.py       BaseAgent — 12-step pipeline + agentic loop
├── orchestrator.py     get_agent(agent_type) — maps type string to class
├── incident_agent.py   IncidentAgent — SRE incident response
├── provisioning_agent.py  ProvisioningAgent — infrastructure provisioning
└── compliance_agent.py    ComplianceAgent — security and compliance scanning
```

---

## Agent Registry

`orchestrator.py` maintains a dict mapping the three valid `agent_type` strings to their classes:

| agent_type | Class | Default LLM |
|---|---|---|
| `incident_response` | `IncidentAgent` | Anthropic |
| `infrastructure_provisioning` | `ProvisioningAgent` | OpenAI |
| `compliance_scan` | `ComplianceAgent` | Anthropic |

Per-agent provider mapping is in `core/llm_providers.py:AGENT_PROVIDER_MAP`.

---

## 12-Step Pipeline (`BaseAgent.run`)

Every task executes these steps in order. Any step can return an `AgentResult` with `success=False` and `status="failed"` (or `"awaiting_approval"`), short-circuiting the remainder.

| Step | What happens | Returns error on |
|---|---|---|
| 1 | **Rate limit** — Redis sliding window, 30 req/min per user | `rate_limited` |
| 2 | **OPA authorization** — `execute:{agent_type}` action check | `unauthorized` |
| 3 | **Data classification** — user clearance vs agent classification | `clearance_denied` |
| 4 | **Audit log** — `TASK_SUBMITTED` event written | — |
| 5 | **Static prompt defense** — regex patterns + jailbreak phrases | `injection_detected` |
| 6 | **LLM classifier** — Haiku classifies the input (blocks if score ≥ 0.6) | `classified_unsafe` |
| 7 | **Input guardrails** — length check (≤2000 chars), PII redaction | `input_too_long` |
| 8 | **Approval gate** — `high`/`critical` priority without approval_id | `approval_required` |
| 9 | **RAG retrieval** — category-filtered hybrid search + defense layer | `injection_detected` |
| 10 | **LLM agentic loop** — up to 10 iterations, tool calls intercepted | — |
| 11 | **Constitutional check** — Haiku reviews the output for policy violations | `constitutional_violation` |
| 12 | **Output audit** — `TASK_COMPLETED` event with token/cost/provider data | — |

### Agentic loop detail (step 10)

```python
for _ in range(settings.MAX_AGENT_ITERATIONS):  # default 10
    response = await llm.complete_with_failover(...)

    if response.stop_reason in ("end_turn", "stop") and not response.tool_calls:
        break

    if response.tool_calls:
        for tc in response.tool_calls:
            sandbox.check_tool(agent_type, tc["name"])   # raises SandboxViolationError if not allowed
            result = await execute_tool(tc["name"], tc["input"])
            result = defense.check_tool_result(result)   # scan tool output for injection
        # append tool_result messages and continue
```

If the LLM attempts a tool not in the sandbox allowlist for this agent type, `SandboxViolationError` is raised and the task fails.

### DEMO_MODE shortcut

When `settings.DEMO_MODE = True`, step 10 is replaced entirely by `_demo_response()` — a hardcoded realistic-looking output string that references the retrieved RAG source titles. The 12-step security pipeline still runs in full.

---

## Incident Agent (`incident_agent.py`)

**Data classification**: `internal`  
**RAG category**: `runbook`

### Tools

| Tool | Purpose |
|---|---|
| `check_system_status` | CPU/mem health of a host |
| `query_application_logs` | Recent error logs for a service |
| `restart_service` | Restart a service on a host |
| `isolate_host` | Network-isolate a compromised host |
| `escalate_ticket` | Create PagerDuty ticket |
| `notify_on_call` | Post to incident channel |
| `query_knowledge_base` | Search runbooks (handled by LLM, not tool execution) |

All tool implementations in demo mode return randomised but realistic-looking output (random CPU %, random ticket IDs, random PIDs).

**System prompt directive**: Acknowledge P1 within 5 minutes, contain within 1 hour; for security incidents isolate first, then investigate, notify CISO within 15 minutes.

---

## Provisioning Agent (`provisioning_agent.py`)

**Data classification**: `internal`  
**RAG category**: `infrastructure`

### Tools

| Tool | Purpose |
|---|---|
| `create_virtual_machine` | Provision an EC2-style VM |
| `deploy_container` | Deploy to ECS/Kubernetes |
| `resize_resource` | Scale a resource up or down |
| `check_quota` | Verify resource quota availability |
| `tag_resource` | Apply metadata tags |
| `decommission_resource` | Terminate and remove a resource |
| `query_knowledge_base` | Search infrastructure standards |

---

## Compliance Agent (`compliance_agent.py`)

**Data classification**: `confidential` (requires higher clearance than the other two agents)  
**RAG category**: `compliance`

### Tools

| Tool | Purpose |
|---|---|
| `scan_vulnerabilities` | Run a CVE vulnerability scan |
| `check_patch_status` | List unpatched critical/high CVEs |
| `audit_access_rights` | Find dormant/over-privileged accounts |
| `list_open_ports` | Enumerate exposed ports |
| `check_encryption_status` | Verify encryption at rest/in transit |
| `generate_compliance_report` | Produce SOC 2/NIST/PCI report |
| `query_knowledge_base` | Search compliance policies |

---

## Security Controls on Agents

### Sandbox (`core/sandbox.py`)
`AGENT_ALLOWED_TOOLS` defines the exact set of permitted tool names per agent type. `SandboxLayer.filter_tools()` strips any tools returned by `get_tools()` that aren't in the allowlist before passing them to the LLM. `SandboxLayer.check_tool()` validates each tool call at execution time.

### Agent Classification (`core/opa_client.py` + OPA)
Each agent type has a required minimum clearance:
- `incident_response` → `internal`
- `infrastructure_provisioning` → `internal`  
- `compliance_scan` → `confidential`

Users with only `public` clearance cannot execute any agent.

### Tool Result Inspection
After each tool call, `PromptDefenseLayer.check_tool_result()` scans the returned string for injection patterns before appending it to the LLM message history. Blocked tool results are replaced with `"[Tool result blocked: injection detected]"` and an `RAG_INDIRECT_INJECTION` audit event is written.

---

## AgentResult Schema

```python
@dataclass
class AgentResult:
    success: bool
    output: str
    tokens_used: int       # total input + output tokens
    cost_usd: float        # estimated cost based on model pricing
    llm_provider: str      # e.g. "claude-sonnet-4-6"
    duration_ms: int       # wall-clock time for the full pipeline
    rag_sources: list      # [{"title", "category", "score"}]
    rag_stats: dict        # RetrievalStats as dict
    error: str | None      # error code if success=False
    status: str            # "completed" | "failed" | "awaiting_approval"
```
