from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import EventType, log_event
from app.core.governance import GovernanceLayer, RateLimitExceeded, check_rate_limit
from app.core.llm_providers import LLMMessage, LLMRouter, estimate_cost
from app.core.opa_client import check_permission
from app.core.prompt_defense import PromptDefenseLayer
from app.core.sandbox import SandboxLayer
from app.rag.pipeline import RAGPipeline


@dataclass
class AgentResult:
    success: bool
    output: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    llm_provider: str = ""
    duration_ms: int = 0
    rag_sources: list = field(default_factory=list)
    rag_stats: dict = field(default_factory=dict)
    error: str | None = None
    status: str = "completed"


AGENT_CLASSIFICATIONS: dict[str, str] = {
    "incident_response": "internal",
    "infrastructure_provisioning": "internal",
    "compliance_scan": "confidential",
}

HIGH_PRIORITY_REQUIRING_APPROVAL = {"high", "critical"}


class BaseAgent(ABC):

    agent_type: str = "base"

    def __init__(self):
        self.defense = PromptDefenseLayer()
        self.sandbox = SandboxLayer()
        self.rag = RAGPipeline()
        self.llm = LLMRouter()
        self.governance = GovernanceLayer()

    @abstractmethod
    def get_tools(self) -> list[dict]:
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        ...

    @abstractmethod
    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        ...

    async def run(
        self,
        task_id: str,
        user_id: str,
        user_role: str,
        user_clearance: str,
        input_text: str,
        priority: str,
        session: AsyncSession,
        preferred_provider: str | None = None,
        approval_id: str | None = None,
        publish: Callable[[str, dict], None] | None = None,
    ) -> AgentResult:
        def emit(event_type: str, data: dict) -> None:
            if publish:
                try:
                    publish(event_type, data)
                except Exception:
                    pass
        t_start = time.monotonic()
        decision_tree: list[dict] = []

        # Step 1: Rate limit
        try:
            await check_rate_limit(user_id)
            decision_tree.append({"step": "rate_limit", "status": "passed"})
        except RateLimitExceeded:
            await log_event(session, EventType.RATE_LIMITED, user_id=user_id,
                            resource_type="task", resource_id=task_id)
            return AgentResult(False, "Rate limit exceeded", status="failed", error="rate_limited")

        # Step 2: OPA authorization
        required_action = f"execute:{self.agent_type}"
        agent_class = AGENT_CLASSIFICATIONS.get(self.agent_type, "internal")
        permitted = await check_permission(user_role, user_clearance, required_action, agent_class)
        if not permitted:
            await log_event(session, EventType.CLEARANCE_DENIED, user_id=user_id,
                            resource_type="agent", resource_id=self.agent_type)
            return AgentResult(False, "Access denied", status="failed", error="unauthorized")
        decision_tree.append({"step": "opa_authz", "status": "passed",
                               "action": required_action, "classification": agent_class})

        # Step 3: Data classification
        if not self.governance.check_clearance(user_clearance, agent_class):
            await log_event(session, EventType.CLEARANCE_DENIED, user_id=user_id)
            return AgentResult(False, "Insufficient clearance", status="failed", error="clearance_denied")
        decision_tree.append({"step": "clearance_check", "status": "passed",
                               "user_clearance": user_clearance, "required": agent_class})

        # Step 4: Log attempt
        await log_event(session, EventType.TASK_SUBMITTED, user_id=user_id,
                        resource_type="task", resource_id=task_id,
                        details={"agent_type": self.agent_type, "priority": priority})

        # Step 5: Static prompt defense
        static_result = self.defense.static_check(input_text)
        if not static_result.allowed:
            await log_event(session, EventType.PROMPT_INJECTION_BLOCKED, user_id=user_id,
                            threat_score=static_result.threat_score)
            return AgentResult(False, "Input blocked by security filter", status="failed",
                               error="injection_detected")
        decision_tree.append({"step": "static_defense", "status": "passed",
                               "threat_score": round(static_result.threat_score, 3)})

        # Step 6: LLM classifier
        llm_result = await self.defense.llm_classify(input_text)
        combined_score = self.defense.combine_scores([static_result, llm_result])
        if not llm_result.allowed or combined_score >= 0.6:
            await log_event(session, EventType.JAILBREAK_BLOCKED, user_id=user_id,
                            threat_score=combined_score)
            return AgentResult(False, "Input blocked by AI classifier", status="failed",
                               error="classified_unsafe")
        decision_tree.append({"step": "llm_classifier", "status": "passed",
                               "combined_score": round(combined_score, 3)})

        # Step 7: Input guardrail
        if not self.governance.check_length(input_text):
            return AgentResult(False, "Input too long", status="failed", error="input_too_long")

        pii_result = self.governance.redact_pii(input_text)
        if pii_result.redacted:
            input_text = pii_result.text
            await log_event(session, EventType.PII_DETECTED, user_id=user_id,
                            details={"types": pii_result.types_found})
        decision_tree.append({"step": "input_guardrail", "status": "passed",
                               "pii_redacted": pii_result.redacted,
                               "pii_types": pii_result.types_found if pii_result.redacted else []})

        # Step 8: Approval gate
        if priority in HIGH_PRIORITY_REQUIRING_APPROVAL and not approval_id:
            return AgentResult(False, "Approval required for high/critical tasks",
                               status="awaiting_approval", error="approval_required")
        decision_tree.append({"step": "approval_gate", "status": "passed",
                               "required": priority in HIGH_PRIORITY_REQUIRING_APPROVAL,
                               "approval_id": approval_id})

        # Step 9: RAG retrieval
        try:
            rag_ctx = await self.rag.retrieve_for_agent(input_text, self.agent_type, user_clearance, session)
        except ValueError as exc:
            await log_event(session, EventType.PROMPT_INJECTION_BLOCKED, user_id=user_id,
                            details={"stage": "rag_defense", "error": str(exc)})
            return AgentResult(False, "Input blocked by RAG defense", status="failed",
                               error="injection_detected")
        decision_tree.append({"step": "rag_retrieval", "status": "completed",
                               "chunks_retrieved": len(rag_ctx.sources),
                               "was_retrieved": rag_ctx.was_retrieved,
                               "sources": [{"title": s.title, "score": round(s.cross_score, 3)}
                                           for s in rag_ctx.sources[:5]]})

        # Step 10: LLM execution
        system = self.get_system_prompt()
        if rag_ctx.was_retrieved:
            system = f"{system}\n\n{rag_ctx.formatted_block}"

        allowed_tools, dropped = self.sandbox.filter_tools(self.agent_type, self.get_tools())

        if settings.DEMO_MODE:
            output = self._demo_response(input_text, rag_ctx)
            duration_ms = int((time.monotonic() - t_start) * 1000)
            await log_event(session, EventType.TASK_COMPLETED, user_id=user_id,
                            resource_type="task", resource_id=task_id,
                            details={"demo_mode": True, "rag_sources": len(rag_ctx.sources),
                                     "decision_tree": decision_tree})
            return AgentResult(
                success=True,
                output=output,
                tokens_used=0,
                cost_usd=0.0,
                llm_provider="demo",
                duration_ms=duration_ms,
                rag_sources=[{"title": s.title, "category": s.category, "score": s.cross_score}
                             for s in rag_ctx.sources],
                rag_stats=vars(rag_ctx.stats),
            )

        emit("agent_start", {"agent_type": self.agent_type, "input": input_text[:300]})

        messages = [LLMMessage(role="user", content=input_text)]
        total_input_tokens = 0
        total_output_tokens = 0
        model_used = ""
        output_parts = []

        for iteration in range(settings.MAX_AGENT_ITERATIONS):
            emit("llm_thinking", {"iteration": iteration + 1, "message": "Calling LLM..."})
            response = await self.llm.complete_with_failover(
                agent_type=self.agent_type,
                system=system,
                messages=messages,
                tools=allowed_tools if allowed_tools else None,
                preferred_provider=preferred_provider,
            )
            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens
            model_used = response.model

            iter_step: dict = {
                "step": f"llm_iteration_{iteration + 1}",
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "stop_reason": response.stop_reason,
            }

            if response.content:
                output_parts.append(response.content)
                iter_step["response_preview"] = response.content[:300]
                emit("llm_response", {"content": response.content, "model": response.model,
                                      "input_tokens": response.input_tokens,
                                      "output_tokens": response.output_tokens})

            if response.stop_reason in ("end_turn", "stop") and not response.tool_calls:
                decision_tree.append(iter_step)
                break

            if response.tool_calls:
                messages.append(LLMMessage(role="assistant", content=response.content or "", tool_calls=response.tool_calls))
                tool_result_blocks = []
                iter_step["tool_calls"] = []
                for tc in response.tool_calls:
                    emit("tool_call", {"tool": tc["name"], "input": tc["input"]})
                    self.sandbox.check_tool(self.agent_type, tc["name"])
                    tr = await self.execute_tool(tc["name"], tc["input"])
                    tr_defense = self.defense.check_tool_result(tr)
                    blocked = not tr_defense.allowed
                    if blocked:
                        tr = "[Tool result blocked: injection detected]"
                        await log_event(session, EventType.RAG_INDIRECT_INJECTION,
                                        user_id=user_id, details={"tool": tc["name"]})
                    emit("tool_result", {"tool": tc["name"], "result": tr[:500]})
                    tool_result_blocks.append({"tool_use_id": tc["id"], "content": tr})
                    iter_step["tool_calls"].append({
                        "tool": tc["name"],
                        "input": {k: str(v)[:80] for k, v in tc["input"].items()},
                        "result_preview": tr[:200],
                        "blocked": blocked,
                    })

                messages.append(LLMMessage(
                    role="user",
                    content=[{"type": "tool_result", **b} for b in tool_result_blocks],
                ))
                decision_tree.append(iter_step)
            else:
                decision_tree.append(iter_step)
                break

        final_output = "\n".join(output_parts) or "Task completed."

        # Step 11: Constitutional check
        const_result = await self.defense.constitutional_check(final_output)
        if not const_result.allowed:
            await log_event(session, EventType.CONSTITUTIONAL_VIOLATION, user_id=user_id,
                            threat_score=const_result.threat_score)
            return AgentResult(False, "Output blocked by constitutional check",
                               status="failed", error="constitutional_violation")
        decision_tree.append({"step": "constitutional_check", "status": "passed",
                               "threat_score": round(const_result.threat_score, 3)})

        # Step 12: Output audit
        cost = estimate_cost(model_used, total_input_tokens, total_output_tokens)
        duration_ms = int((time.monotonic() - t_start) * 1000)

        await log_event(session, EventType.TASK_COMPLETED, user_id=user_id,
                        resource_type="task", resource_id=task_id,
                        details={
                            "tokens": total_input_tokens + total_output_tokens,
                            "cost_usd": cost,
                            "provider": model_used,
                            "rag_sources": len(rag_ctx.sources),
                            "duration_ms": duration_ms,
                            "decision_tree": decision_tree,
                        })

        return AgentResult(
            success=True,
            output=final_output,
            tokens_used=total_input_tokens + total_output_tokens,
            cost_usd=cost,
            llm_provider=model_used,
            duration_ms=duration_ms,
            rag_sources=[{"title": s.title, "category": s.category, "score": s.cross_score}
                         for s in rag_ctx.sources],
            rag_stats=vars(rag_ctx.stats),
        )

    def _demo_response(self, input_text: str, rag_ctx) -> str:
        return f"[DEMO] {self.agent_type.upper()} processed: {input_text[:100]}..."
