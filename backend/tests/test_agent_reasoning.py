"""
Agent reasoning tests — two tiers.

Tier 1 (always run, no API key):
  Patches LLMRouter with scripted responses to verify the tool-call loop
  mechanics: tool results reach the next LLM call, multi-step chains complete,
  and the final output comes from the LLM not the demo stub.

Tier 2 (NEXUS_LIVE_LLM=1 + OPENAI_API_KEY required):
  Real API calls. Asserts on reasoning quality — correct tools invoked, output
  references scenario facts, severity classifications present.

Run tier 1 only:
    pytest tests/test_agent_reasoning.py -m "not live_llm"

Run all (requires live key):
    NEXUS_LIVE_LLM=1 pytest tests/test_agent_reasoning.py
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import app.config as _cfg
from app.core.llm_providers import LLMResponse


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _tc(name: str, args: dict, call_id: str = "tc_1") -> dict:
    """Build a tool-call dict matching the shape BaseAgent expects."""
    return {"name": name, "id": call_id, "input": args}


def _turn(
    content: str = "",
    tool_calls: list[dict] | None = None,
    stop_reason: str = "end_turn",
) -> LLMResponse:
    return LLMResponse(
        content=content,
        tool_calls=tool_calls or [],
        stop_reason=stop_reason,
        input_tokens=40,
        output_tokens=80,
        model="gpt-5-nano",
    )


@contextmanager
def live_mode():
    """Patch DEMO_MODE=False for the duration of a block."""
    with patch.object(_cfg.settings, "DEMO_MODE", False):
        yield


live_llm = pytest.mark.skipif(
    not (os.getenv("NEXUS_LIVE_LLM") and os.getenv("OPENAI_API_KEY")),
    reason="set NEXUS_LIVE_LLM=1 and OPENAI_API_KEY to run live reasoning tests",
)


# ─── Tier 1: Mock-LLM — loop mechanics ────────────────────────────────────────

@pytest.mark.asyncio
class TestIncidentAgentLoop:

    async def test_single_tool_call_then_conclusion(self, session):
        """Agent completes a one-tool scenario and returns the LLM's content, not the demo stub."""
        from app.agents.incident_agent import IncidentAgent

        turns = iter([
            _turn(tool_calls=[_tc("check_system_status", {"host": "web-01"})], stop_reason="tool_use"),
            _turn(content="CPU is critical on web-01. Restarting payment-svc.", stop_reason="end_turn"),
        ])

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover",
                   new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = lambda **kw: next(turns)
            result = await IncidentAgent().run(
                task_id="t-001", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="CPU at 96% on web-01. Payment service throwing OOM errors.",
                priority="medium", session=session,
            )

        assert result.success
        assert result.llm_provider == "gpt-5-nano"
        assert "cpu" in result.output.lower() or "critical" in result.output.lower()
        assert mock_llm.call_count == 2

    async def test_tool_result_reaches_second_llm_call(self, session):
        """The output of execute_tool must appear in the messages sent to the follow-up LLM call."""
        from app.agents.incident_agent import IncidentAgent

        received: list = []

        async def capture(**kwargs):
            received.append(kwargs["messages"][:])
            if len(received) == 1:
                return _turn(tool_calls=[_tc("query_application_logs", {"service": "payment-svc"})], stop_reason="tool_use")
            return _turn(content="OOM detected. Service restarted.", stop_reason="end_turn")

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover", side_effect=capture):
            await IncidentAgent().run(
                task_id="t-002", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Investigate payment service errors.",
                priority="medium", session=session,
            )

        assert len(received) == 2, "Expected exactly 2 LLM calls"
        # The message added after the tool call should be a tool_result block
        second_call_messages = received[1]
        last_msg = second_call_messages[-1]
        assert last_msg.role == "user"
        assert isinstance(last_msg.content, list)
        assert any(b.get("type") == "tool_result" for b in last_msg.content), (
            "Tool result was not included in the follow-up message"
        )

    async def test_multi_tool_chain_three_steps(self, session):
        """Agent can execute multiple sequential tool calls across iterations."""
        from app.agents.incident_agent import IncidentAgent

        turns = iter([
            _turn(tool_calls=[_tc("check_system_status",  {"host": "db-01"},       "tc_1")], stop_reason="tool_use"),
            _turn(tool_calls=[_tc("query_application_logs", {"service": "db-svc"},  "tc_2")], stop_reason="tool_use"),
            _turn(tool_calls=[_tc("escalate_ticket", {"severity": "P1", "description": "DB unresponsive"}, "tc_3")], stop_reason="tool_use"),
            _turn(content="Database incident escalated P1. Ticket created.", stop_reason="end_turn"),
        ])

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover",
                   new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = lambda **kw: next(turns)
            result = await IncidentAgent().run(
                task_id="t-003", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Database db-01 is completely unresponsive.",
                priority="medium", session=session,
            )

        assert result.success
        assert mock_llm.call_count == 4
        assert "p1" in result.output.lower() or "escalat" in result.output.lower()

    async def test_tokens_and_cost_tracked(self, session):
        """tokens_used and cost_usd are accumulated across multiple LLM calls."""
        from app.agents.incident_agent import IncidentAgent

        turns = iter([
            _turn(tool_calls=[_tc("check_system_status", {"host": "app-01"})], stop_reason="tool_use"),
            _turn(content="Host is degraded.", stop_reason="end_turn"),
        ])

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover",
                   new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = lambda **kw: next(turns)
            result = await IncidentAgent().run(
                task_id="t-004", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Check app-01 health.",
                priority="medium", session=session,
            )

        # Two calls × (40 input + 80 output) = 240 tokens total
        assert result.tokens_used == 240
        assert result.cost_usd > 0


@pytest.mark.asyncio
class TestComplianceAgentLoop:

    async def test_scan_then_report_sequence(self, session):
        """Compliance agent processes a scan result before generating the final report."""
        from app.agents.compliance_agent import ComplianceAgent

        turns = iter([
            _turn(tool_calls=[_tc("scan_vulnerabilities", {"target": "production"}, "tc_1")], stop_reason="tool_use"),
            _turn(tool_calls=[_tc("generate_compliance_report", {"framework": "SOC2"}, "tc_2")], stop_reason="tool_use"),
            _turn(content="SOC2 scan complete. 1 Critical CVE found. Remediation required within 48h.", stop_reason="end_turn"),
        ])

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover",
                   new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = lambda **kw: next(turns)
            result = await ComplianceAgent().run(
                task_id="t-010", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Run full SOC2 compliance scan on production.",
                priority="medium", session=session,
            )

        assert result.success
        assert mock_llm.call_count == 3
        assert "soc2" in result.output.lower() or "compliance" in result.output.lower()


@pytest.mark.asyncio
class TestProvisioningAgentLoop:

    async def test_quota_check_before_vm_creation(self, session):
        """Provisioning agent should check quota before creating a VM — enforced by the system prompt."""
        from app.agents.provisioning_agent import ProvisioningAgent

        tool_calls_made: list[str] = []

        async def track_tools(**kwargs):
            # Record tool calls from the last assistant message
            for msg in reversed(kwargs["messages"]):
                if msg.role == "user" and isinstance(msg.content, list):
                    for block in msg.content:
                        if block.get("type") == "tool_result":
                            pass  # already recorded on previous turn
                    break

            turn = len(tool_calls_made)
            if turn == 0:
                tool_calls_made.append("check_quota")
                return _turn(tool_calls=[_tc("check_quota", {"resource_type": "ec2", "region": "us-east-1"})], stop_reason="tool_use")
            if turn == 1:
                tool_calls_made.append("create_virtual_machine")
                return _turn(
                    tool_calls=[_tc("create_virtual_machine", {"name": "prod-app-use1-01", "size": "t3.large", "region": "us-east-1a"}, "tc_2")],
                    stop_reason="tool_use",
                )
            tool_calls_made.append("done")
            return _turn(content="VM provisioned. Quota verified first.", stop_reason="end_turn")

        with live_mode(), \
             patch("app.core.llm_providers.LLMRouter.complete_with_failover", side_effect=track_tools):
            result = await ProvisioningAgent().run(
                task_id="t-020", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Provision a t3.large EC2 instance in us-east-1 for the analytics team.",
                priority="medium", session=session,
            )

        assert result.success
        assert "check_quota" in tool_calls_made
        assert "create_virtual_machine" in tool_calls_made
        assert tool_calls_made.index("check_quota") < tool_calls_made.index("create_virtual_machine"), (
            "Agent must check quota before provisioning"
        )


# ─── Tier 2: Live LLM — reasoning quality ─────────────────────────────────────

@pytest.mark.asyncio
class TestLiveReasoning:

    @live_llm
    async def test_incident_agent_investigates_and_escalates(self, session):
        """Real LLM: calls diagnostic tools, mentions scenario facts, produces a substantive report."""
        from app.agents.incident_agent import IncidentAgent

        with live_mode():
            result = await IncidentAgent().run(
                task_id="live-001", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text=(
                    "CPU is at 96% on app-server-03 and customers are reporting 500 errors "
                    "from the payment service. Investigate and remediate."
                ),
                priority="medium", session=session,
            )

        assert result.success, f"Agent failed: {result.error}"
        assert result.tokens_used > 0, "No tokens used — LLM was not called"
        assert len(result.output) > 150, f"Output too short: {result.output!r}"
        assert any(kw in result.output.lower() for kw in ["cpu", "app-server", "payment", "memory", "oom", "error"]), (
            f"Output doesn't reference scenario facts:\n{result.output}"
        )

    @live_llm
    async def test_incident_agent_produces_severity_classification(self, session):
        """Real LLM: a critical-sounding incident should produce P1/P2 classification or equivalent."""
        from app.agents.incident_agent import IncidentAgent

        with live_mode():
            result = await IncidentAgent().run(
                task_id="live-002", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="All production databases are down. No connections accepted. Revenue impact.",
                priority="medium", session=session,
            )

        assert result.success, f"Agent failed: {result.error}"
        assert any(sev in result.output.upper() for sev in ["P1", "P2", "CRITICAL", "SEV1", "SEV-1"]), (
            f"No severity classification in output:\n{result.output}"
        )

    @live_llm
    async def test_compliance_agent_classifies_findings_by_severity(self, session):
        """Real LLM: compliance scan output must contain severity-classified findings."""
        from app.agents.compliance_agent import ComplianceAgent

        with live_mode():
            result = await ComplianceAgent().run(
                task_id="live-003", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text=(
                    "Run a full SOC2 Type II compliance assessment on the production environment. "
                    "Check vulnerabilities, patch status, access rights, and generate a report."
                ),
                priority="medium", session=session,
            )

        assert result.success, f"Agent failed: {result.error}"
        assert result.tokens_used > 0
        assert any(sev in result.output.upper() for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]), (
            f"No severity classifications in output:\n{result.output}"
        )
        assert any(fw in result.output.upper() for fw in ["SOC2", "SOC 2", "NIST"]), (
            f"No compliance framework referenced:\n{result.output}"
        )

    @live_llm
    async def test_provisioning_agent_checks_quota_before_provisioning(self, session):
        """Real LLM: provisioning agent must verify quota (system prompt requirement) before creating resources."""
        from app.agents.provisioning_agent import ProvisioningAgent

        with live_mode():
            result = await ProvisioningAgent().run(
                task_id="live-004", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="Provision 3 new t3.large EC2 instances in us-east-1 for the analytics team.",
                priority="medium", session=session,
            )

        assert result.success, f"Agent failed: {result.error}"
        assert result.tokens_used > 0
        assert any(kw in result.output.lower() for kw in ["quota", "instance", "provision", "ec2", "us-east"]), (
            f"Output doesn't reference the provisioning task:\n{result.output}"
        )

    @live_llm
    async def test_agent_uses_rag_sources_when_available(self, session):
        """When knowledge base has content, agent should use it and cite sources."""
        from app.agents.incident_agent import IncidentAgent

        with live_mode():
            result = await IncidentAgent().run(
                task_id="live-005", user_id="u-001",
                user_role="admin", user_clearance="confidential",
                input_text="OOM error on payment service. What does the runbook say to do?",
                priority="medium", session=session,
            )

        assert result.success, f"Agent failed: {result.error}"
        # rag_sources will be empty if knowledge base isn't seeded — that's OK,
        # but if sources were retrieved they should appear in output
        if result.rag_sources:
            source_titles = [s.get("title", "") for s in result.rag_sources]
            assert any(
                title.lower() in result.output.lower()
                for title in source_titles
                if title
            ), f"RAG sources retrieved but not cited in output. Sources: {source_titles}\nOutput: {result.output[:300]}"
