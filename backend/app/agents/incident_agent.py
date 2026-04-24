from __future__ import annotations

import random

from app.agents.base_agent import BaseAgent
from app.rag.pipeline import RAGContext

TOOLS = [
    {
        "name": "check_system_status",
        "description": "Check the health and status of a host or service",
        "input_schema": {
            "type": "object",
            "properties": {"host": {"type": "string", "description": "Hostname or service name"}},
            "required": ["host"],
        },
    },
    {
        "name": "query_application_logs",
        "description": "Query recent application logs for errors",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "minutes": {"type": "integer", "default": 15},
            },
            "required": ["service"],
        },
    },
    {
        "name": "restart_service",
        "description": "Restart a service on a host",
        "input_schema": {
            "type": "object",
            "properties": {"host": {"type": "string"}, "service": {"type": "string"}},
            "required": ["host", "service"],
        },
    },
    {
        "name": "isolate_host",
        "description": "Network-isolate a compromised host",
        "input_schema": {
            "type": "object",
            "properties": {"host": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["host"],
        },
    },
    {
        "name": "escalate_ticket",
        "description": "Escalate incident to on-call team",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["severity", "description"],
        },
    },
    {
        "name": "notify_on_call",
        "description": "Send notification to on-call channel",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "string"}, "message": {"type": "string"}},
            "required": ["channel"],
        },
    },
    {
        "name": "query_knowledge_base",
        "description": "Search the knowledge base for runbooks and procedures",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are NEXUS Incident Response Agent — an expert SRE AI for enterprise IT operations.

Your role:
- Diagnose and resolve production incidents following established runbooks
- Execute remediation steps methodically and safely
- Escalate appropriately based on severity classification (P1-P4)
- Cite the knowledge base sources you use in your response

Always follow P1 SLA: acknowledge within 5 minutes, contain within 1 hour.
For security incidents: isolate first, investigate second, notify CISO within 15 minutes.
"""


class IncidentAgent(BaseAgent):
    agent_type = "incident_response"

    def get_tools(self) -> list[dict]:
        return TOOLS

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "check_system_status":
            host = tool_input.get("host", "unknown")
            cpu = random.randint(70, 99)
            mem = random.randint(60, 95)
            return f"{host}: CPU {cpu}%, MEM {mem}%, {'CRITICAL' if cpu > 90 else 'WARNING'}"

        if tool_name == "query_application_logs":
            service = tool_input.get("service", "unknown")
            minutes = tool_input.get("minutes", 15)
            errors = random.randint(50, 500)
            return f"{service} ({minutes}m): {errors} ERRORs, OOM pattern detected, top error: OutOfMemoryError"

        if tool_name == "restart_service":
            host = tool_input.get("host", "unknown")
            service = tool_input.get("service", "unknown")
            pid = random.randint(10000, 60000)
            return f"Restarted {service} on {host}: PID {pid}, status healthy after 10s"

        if tool_name == "isolate_host":
            host = tool_input.get("host", "unknown")
            return f"{host} isolated: all network traffic blocked except management VLAN"

        if tool_name == "escalate_ticket":
            severity = tool_input.get("severity", "P2")
            ticket = f"INC-{random.randint(10000, 99999)}"
            return f"Ticket {ticket} created ({severity}): on-call team paged via PagerDuty"

        if tool_name == "notify_on_call":
            channel = tool_input.get("channel", "#incidents")
            return f"Notification delivered to {channel} at {__import__('datetime').datetime.utcnow().isoformat()}"

        if tool_name == "query_knowledge_base":
            return "Knowledge base query not available in tool execution context"

        return f"Unknown tool: {tool_name}"

    def _demo_response(self, input_text: str, rag_ctx: RAGContext) -> str:
        source_titles = [s.title for s in rag_ctx.sources[:3]] if rag_ctx.sources else []
        sources_str = ", ".join(source_titles) if source_titles else "General IT Runbooks"
        ticket = f"INC-{random.randint(50000, 99999)}"
        pid = random.randint(30000, 60000)

        return f"""INCIDENT RESPONSE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━
Retrieved context: {sources_str}
Following P1 runbook — SLA: 15-min acknowledgement, 1-hour containment

Actions taken:
  [1] check_system_status(app-server-03)         → CPU 94%, MEM 88%, CRITICAL
  [2] query_application_logs(payment-service,15m) → 412 ERRORs, OOM pattern
  [3] query_knowledge_base("OOM restart procedure") → runbook step 4.2 applied
  [4] restart_service(app-server-03,payment-svc)  → PID {pid}, healthy
  [5] escalate_ticket(P1, "payment OOM crash")    → {ticket}, on-call paged
  [6] notify_on_call("#incidents")                → delivered

Runbook compliance: ✓ All P1 steps followed per {source_titles[0] if source_titles else 'Incident Response Runbook v2.1'}
Status: RESOLVED — P1 open for RCA. Next review: 24h post-incident."""
