import httpx

from app.config import settings
from app.core.security import clearance_level

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "execute:incident_response", "execute:infrastructure_provisioning", "execute:compliance_scan",
        "audit:view_all", "audit:view_own", "admin:manage_users", "admin:system_metrics",
        "approvals:review", "knowledge:upload", "knowledge:delete", "knowledge:search",
        "knowledge:admin",
    },
    "operator": {
        "execute:incident_response", "execute:infrastructure_provisioning", "execute:compliance_scan",
        "audit:view_own", "admin:system_metrics", "knowledge:search",
    },
    "viewer": {
        "audit:view_own", "knowledge:search",
    },
}


def local_rbac_check(role: str, action: str, user_clearance: str, resource_classification: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    if action not in perms:
        return False
    return clearance_level(user_clearance) >= clearance_level(resource_classification)


async def check_permission(
    user_role: str,
    user_clearance: str,
    action: str,
    resource_classification: str = "public",
) -> bool:
    if settings.DEMO_MODE:
        return local_rbac_check(user_role, action, user_clearance, resource_classification)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(
                f"{settings.OPA_URL}/v1/data/nexus/authz/allow",
                json={
                    "input": {
                        "user": {"role": user_role, "clearance": user_clearance},
                        "action": action,
                        "resource": {"classification": resource_classification},
                    }
                },
            )
            resp.raise_for_status()
            return resp.json().get("result", False)
    except Exception:
        return local_rbac_check(user_role, action, user_clearance, resource_classification)


async def check_tool_allowed(agent_type: str, tool_name: str) -> bool:
    if settings.DEMO_MODE:
        from app.core.sandbox import AGENT_ALLOWED_TOOLS
        return tool_name in AGENT_ALLOWED_TOOLS.get(agent_type, set())

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(
                f"{settings.OPA_URL}/v1/data/nexus/agents/tool_allowed",
                json={"input": {"agent_type": agent_type, "tool_name": tool_name}},
            )
            resp.raise_for_status()
            return resp.json().get("result", False)
    except Exception:
        from app.core.sandbox import AGENT_ALLOWED_TOOLS
        return tool_name in AGENT_ALLOWED_TOOLS.get(agent_type, set())
