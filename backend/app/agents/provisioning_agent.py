from __future__ import annotations

import random

from app.agents.base_agent import BaseAgent
from app.rag.pipeline import RAGContext

TOOLS = [
    {
        "name": "create_virtual_machine",
        "description": "Provision a new virtual machine",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "size": {"type": "string"},
                "region": {"type": "string"},
                "tags": {"type": "object"},
            },
            "required": ["name", "size", "region"],
        },
    },
    {
        "name": "deploy_container",
        "description": "Deploy a container to the ECS cluster",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {"type": "string"},
                "service": {"type": "string"},
                "replicas": {"type": "integer"},
            },
            "required": ["image", "service"],
        },
    },
    {
        "name": "resize_resource",
        "description": "Resize an existing resource",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "new_size": {"type": "string"},
            },
            "required": ["resource_id", "new_size"],
        },
    },
    {
        "name": "check_quota",
        "description": "Check current quota usage for a resource type",
        "input_schema": {
            "type": "object",
            "properties": {"resource_type": {"type": "string"}, "region": {"type": "string"}},
            "required": ["resource_type"],
        },
    },
    {
        "name": "tag_resource",
        "description": "Apply tags to a resource",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "tags": {"type": "object"},
            },
            "required": ["resource_id", "tags"],
        },
    },
    {
        "name": "decommission_resource",
        "description": "Safely decommission and remove a resource",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "snapshot_before": {"type": "boolean", "default": True},
            },
            "required": ["resource_id"],
        },
    },
    {
        "name": "query_knowledge_base",
        "description": "Search provisioning standards and infrastructure docs",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are NEXUS Infrastructure Provisioning Agent — expert in cloud resource management.

Your role:
- Provision, resize, tag, and decommission cloud resources per standards
- Always check quota before provisioning
- Apply mandatory tags: env, team, cost-center, owner, created-by, data-classification
- Follow naming convention: {env}-{service}-{region}-{index}
- No public IPs without WAF, no 0.0.0.0/0 ingress, always encrypt storage
- Cite provisioning standards and infrastructure docs in your responses
"""


class ProvisioningAgent(BaseAgent):
    agent_type = "infrastructure_provisioning"

    def get_tools(self) -> list[dict]:
        return TOOLS

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "create_virtual_machine":
            name = tool_input.get("name", "vm")
            size = tool_input.get("size", "medium")
            region = tool_input.get("region", "us-east-1a")
            instance_id = f"i-{random.randint(100000000, 999999999):09x}"
            return f"VM {name} ({size}) created in {region}: {instance_id}, status: running"

        if tool_name == "deploy_container":
            image = tool_input.get("image", "unknown")
            service = tool_input.get("service", "unknown")
            return f"Container {image} deployed to {service}: 3/3 tasks running, health: healthy"

        if tool_name == "resize_resource":
            resource_id = tool_input.get("resource_id", "unknown")
            new_size = tool_input.get("new_size", "unknown")
            return f"Resource {resource_id} resized to {new_size}: change applied, 2m downtime"

        if tool_name == "check_quota":
            resource_type = tool_input.get("resource_type", "unknown")
            used = random.randint(10, 80)
            limit = 100
            return f"{resource_type} quota: {used}/{limit} used ({100 - used} available)"

        if tool_name == "tag_resource":
            resource_id = tool_input.get("resource_id", "unknown")
            tags = tool_input.get("tags", {})
            return f"Tags applied to {resource_id}: {', '.join(f'{k}={v}' for k, v in tags.items())}"

        if tool_name == "decommission_resource":
            resource_id = tool_input.get("resource_id", "unknown")
            snap = f"snap-{random.randint(10000000, 99999999):08x}"
            return f"{resource_id} decommissioned: snapshot {snap} created, resource deleted, billing stops within 24h"

        if tool_name == "query_knowledge_base":
            return "Knowledge base query not available in tool execution context"

        return f"Unknown tool: {tool_name}"

    def _demo_response(self, input_text: str, rag_ctx: RAGContext) -> str:
        source_titles = [s.title for s in rag_ctx.sources[:3]] if rag_ctx.sources else []
        sources_str = ", ".join(source_titles) if source_titles else "Provisioning Standards"
        instance_id = f"i-{random.randint(100000000, 999999999):09x}"

        return f"""INFRASTRUCTURE PROVISIONING REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Retrieved context: {sources_str}
Applied: Naming convention, mandatory tags, security baseline

Actions taken:
  [1] check_quota(ec2, us-east-1) → 34/100 used (66 available)
  [2] create_virtual_machine(prod-app-use1-01, large, us-east-1a) → {instance_id}
  [3] tag_resource({instance_id}, env=prod, team=payments, cost-center=CC-4821) → applied
  [4] deploy_container(app:v2.4.1, prod-app-svc, replicas=3) → 3/3 healthy

Standards compliance: ✓ IMDSv2 enforced, no public IP, encryption enabled
Source: {source_titles[0] if source_titles else 'Provisioning Standards v3.1'}
Status: COMPLETE — all resources tagged and healthy."""
