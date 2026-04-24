from app.config import settings

AGENT_ALLOWED_TOOLS: dict[str, set[str]] = {
    "incident_response": {
        "check_system_status",
        "query_application_logs",
        "restart_service",
        "isolate_host",
        "escalate_ticket",
        "notify_on_call",
        "query_knowledge_base",
    },
    "infrastructure_provisioning": {
        "create_virtual_machine",
        "deploy_container",
        "resize_resource",
        "check_quota",
        "tag_resource",
        "decommission_resource",
        "query_knowledge_base",
    },
    "compliance_scan": {
        "scan_vulnerabilities",
        "check_patch_status",
        "audit_access_rights",
        "list_open_ports",
        "check_encryption_status",
        "generate_compliance_report",
        "query_knowledge_base",
    },
}


class SandboxViolationError(Exception):
    pass


class SandboxLayer:

    def check_tool(self, agent_type: str, tool_name: str) -> None:
        allowed = AGENT_ALLOWED_TOOLS.get(agent_type, set())
        if tool_name not in allowed:
            raise SandboxViolationError(
                f"Tool '{tool_name}' not permitted for agent '{agent_type}'. "
                f"Allowed: {sorted(allowed)}"
            )

    def filter_tools(self, agent_type: str, tools: list[dict]) -> tuple[list[dict], list[str]]:
        allowed = AGENT_ALLOWED_TOOLS.get(agent_type, set())
        filtered = []
        dropped = []
        for tool in tools:
            name = tool.get("name", "")
            if name in allowed:
                filtered.append(tool)
            else:
                dropped.append(name)
        return filtered, dropped

    def get_allowed_tools(self, agent_type: str) -> set[str]:
        return AGENT_ALLOWED_TOOLS.get(agent_type, set())
