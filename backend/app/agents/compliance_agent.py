from __future__ import annotations

import random

from app.agents.base_agent import BaseAgent
from app.rag.pipeline import RAGContext

TOOLS = [
    {
        "name": "scan_vulnerabilities",
        "description": "Run vulnerability scan on a target",
        "input_schema": {
            "type": "object",
            "properties": {"target": {"type": "string"}, "scan_type": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "check_patch_status",
        "description": "Check patch compliance status for hosts",
        "input_schema": {
            "type": "object",
            "properties": {"scope": {"type": "string"}, "severity": {"type": "string"}},
            "required": ["scope"],
        },
    },
    {
        "name": "audit_access_rights",
        "description": "Audit IAM users and service account permissions",
        "input_schema": {
            "type": "object",
            "properties": {"account": {"type": "string"}, "scope": {"type": "string"}},
            "required": ["account"],
        },
    },
    {
        "name": "list_open_ports",
        "description": "List open ports on a target system",
        "input_schema": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "check_encryption_status",
        "description": "Verify encryption at rest and in transit",
        "input_schema": {
            "type": "object",
            "properties": {"resource_type": {"type": "string"}, "scope": {"type": "string"}},
            "required": ["resource_type"],
        },
    },
    {
        "name": "generate_compliance_report",
        "description": "Generate a compliance report",
        "input_schema": {
            "type": "object",
            "properties": {
                "framework": {"type": "string"},
                "scope": {"type": "string"},
                "period": {"type": "string"},
            },
            "required": ["framework"],
        },
    },
    {
        "name": "query_knowledge_base",
        "description": "Search compliance policies and NIST controls",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are NEXUS Compliance Scan Agent — expert in security compliance and policy enforcement.

Your role:
- Conduct compliance assessments against SOC2, NIST SP 800-53, and internal policies
- Identify gaps, violations, and remediation requirements
- Cite specific policy sections and control IDs in findings
- Classify findings by severity: Critical, High, Medium, Low
- Generate actionable remediation guidance with SLA timelines
"""


class ComplianceAgent(BaseAgent):
    agent_type = "compliance_scan"

    def get_tools(self) -> list[dict]:
        return TOOLS

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "scan_vulnerabilities":
            target = tool_input.get("target", "unknown")
            critical = random.randint(0, 3)
            high = random.randint(1, 8)
            medium = random.randint(5, 20)
            return f"{target}: {critical} Critical, {high} High, {medium} Medium CVEs found"

        if tool_name == "check_patch_status":
            scope = tool_input.get("scope", "production")
            compliant = random.randint(70, 95)
            return f"{scope}: {compliant}% patch compliance. Critical: 48h SLA met for {compliant}% of hosts"

        if tool_name == "audit_access_rights":
            account = tool_input.get("account", "production")
            over_privileged = random.randint(2, 8)
            return f"{account}: {over_privileged} over-privileged IAM entities found. AdministratorAccess: 2 service accounts"

        if tool_name == "list_open_ports":
            target = tool_input.get("target", "unknown")
            ports = "22, 443, 8080"
            return f"{target} open ports: {ports}. Port 8080 unexpected — review firewall rule SG-prod-web-443"

        if tool_name == "check_encryption_status":
            resource_type = tool_input.get("resource_type", "unknown")
            encrypted = random.randint(85, 100)
            return f"{resource_type}: {encrypted}% encrypted. {100 - encrypted}% unencrypted — violates data classification policy"

        if tool_name == "generate_compliance_report":
            framework = tool_input.get("framework", "SOC2")
            report_id = f"RPT-{random.randint(10000, 99999)}"
            return f"{framework} report {report_id} generated: 94% control compliance, 3 findings requiring remediation"

        if tool_name == "query_knowledge_base":
            return "Knowledge base query not available in tool execution context"

        return f"Unknown tool: {tool_name}"

    def _demo_response(self, input_text: str, rag_ctx: RAGContext) -> str:
        source_titles = [s.title for s in rag_ctx.sources[:3]] if rag_ctx.sources else []
        sources_str = ", ".join(source_titles) if source_titles else "SOC2 Policies, NIST Controls"
        report_id = f"RPT-{random.randint(10000, 99999)}"

        return f"""COMPLIANCE SCAN REPORT
━━━━━━━━━━━━━━━━━━━━━━
Retrieved context: {sources_str}
Framework: SOC2 Type II / NIST SP 800-53 Rev 5

Scan Results:
  [1] audit_access_rights(production) → 3 over-privileged service accounts (AdministratorAccess)
  [2] check_patch_status(production, critical) → 87% compliant, 13 hosts outside 48h SLA
  [3] check_encryption_status(S3) → 3 buckets unencrypted (violates data classification policy)
  [4] scan_vulnerabilities(production) → 1 Critical CVE, 4 High CVEs pending patch
  [5] generate_compliance_report(SOC2) → {report_id}: 91% control compliance

Findings (by severity):
  CRITICAL: CVE-2024-1234 on db-server-01,02 — patch within 48h per patch management policy
  HIGH: 3 service accounts with AdministratorAccess — remediate per AC-6 Least Privilege
  MEDIUM: 13 hosts exceed patch SLA — escalate to platform team

Source: {source_titles[0] if source_titles else 'SOC2 Policies v2024.1'}
Status: Report {report_id} ready for auditors."""
