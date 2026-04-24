# OPA Authorization Policies

OPA (Open Policy Agent) runs at `http://opa:8181` and provides centralized authorization for the NEXUS platform. The backend calls OPA for every agent execution request and tool authorization check. If OPA is unreachable, the backend falls back to an equivalent local RBAC implementation in `core/opa_client.py`.

## Policy Files

```
opa/policies/
├── authz.rego             Role + clearance authorization
├── agent_permissions.rego Tool allowlists per agent type
└── data_classification.rego Agent data classification requirements
```

---

## `authz.rego` — Role and Clearance Authorization

**Package**: `nexus.authz`  
**Query endpoint**: `POST /v1/data/nexus/authz/allow`

```rego
package nexus.authz
import future.keywords.in

default allow = false

role_permissions := {
    "admin":    { "execute:incident_response", "execute:provisioning",
                  "execute:compliance_scan", "audit:view_all", "audit:view_own",
                  "admin:manage_users", "admin:system_metrics", "approvals:review",
                  "knowledge:upload", "knowledge:delete", "knowledge:search", "knowledge:admin" },
    "operator": { "execute:incident_response", "execute:compliance_scan",
                  "audit:view_own", "admin:system_metrics", "knowledge:search" },
    "viewer":   { "audit:view_own", "knowledge:search" }
}

clearance_level := { "public": 0, "internal": 1, "confidential": 2 }

allow {
    input.action in role_permissions[input.user.role]
    clearance_level[input.user.clearance] >= clearance_level[input.resource.classification]
}
```

### Input format
```json
{
  "input": {
    "user": { "role": "operator", "clearance": "internal" },
    "action": "execute:incident_response",
    "resource": { "classification": "internal" }
  }
}
```

### Response
```json
{ "result": true }
```

### Authorization rules
`allow` is `true` only when **both** conditions hold:
1. The action is in the role's permission set
2. The user's clearance level is >= the resource's classification level

Both conditions must pass. A high-clearance user still needs the action in their role's set. A role with the action but insufficient clearance is also denied.

### ⚠️ Known divergence
`authz.rego` uses `execute:provisioning` but `base_agent.py` generates `execute:infrastructure_provisioning`. The Python local RBAC fallback uses the full `execute:infrastructure_provisioning` string. The Rego file should be updated to match:

```rego
# Change this:
"execute:provisioning"
# To this:
"execute:infrastructure_provisioning"
```

Until fixed, operator/admin provisioning tasks will fail OPA but succeed via the local fallback.

---

## `agent_permissions.rego` — Tool Allowlists

**Package**: `nexus.agents`  
**Query endpoint**: `POST /v1/data/nexus/agents/tool_allowed`

```rego
package nexus.agents

allowed_tools := {
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
    }
}

tool_allowed { input.tool_name in allowed_tools[input.agent_type] }
```

### Input format
```json
{
  "input": {
    "agent_type": "incident_response",
    "tool_name": "restart_service"
  }
}
```

### Response
```json
{ "result": true }
```

These allowlists must remain in sync with `core/sandbox.py:AGENT_ALLOWED_TOOLS` — both are checked.

---

## `data_classification.rego` — Agent Classification Requirements

**Package**: `nexus.data`

Defines the minimum clearance level required to use each agent type:

```rego
package nexus.data

agent_classification := {
    "incident_response":           "internal",
    "infrastructure_provisioning": "internal",
    "compliance_scan":             "confidential"
}

access_allowed {
    required := agent_classification[input.agent_type]
    clearance_level[input.user.clearance] >= clearance_level[required]
}

clearance_level := { "public": 0, "internal": 1, "confidential": 2 }
```

### Agent classification summary

| Agent | Required clearance | Notes |
|---|---|---|
| `incident_response` | `internal` | Operations staff and above |
| `infrastructure_provisioning` | `internal` | Operations staff and above |
| `compliance_scan` | `confidential` | Restricted to senior staff; handles sensitive audit data |

A user with `public` clearance cannot execute any agent. A user with `internal` clearance can run incident and provisioning agents but not compliance scans.

This classification is also enforced independently in `BaseAgent.run()` via `GovernanceLayer.check_clearance()` (step 3 of the 12-step pipeline), providing defence in depth.

---

## Running OPA Locally

```bash
# OPA starts automatically with docker compose
# To check a policy decision manually:
curl -s -X POST http://localhost:8181/v1/data/nexus/authz/allow \
  -H 'Content-Type: application/json' \
  -d '{"input": {"user": {"role": "operator", "clearance": "internal"}, "action": "execute:incident_response", "resource": {"classification": "internal"}}}' \
  | jq .result

# Run OPA tests (if you add .rego test files)
docker compose run --rm opa test /policies -v
```

## Policy Update Workflow

OPA policies are mounted read-only into the container (`./opa/policies:/policies:ro`). To apply changes:

1. Edit the `.rego` files
2. `docker compose restart opa`

No migration needed — OPA loads policies from disk on startup.
