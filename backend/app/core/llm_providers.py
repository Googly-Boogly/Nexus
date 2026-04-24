from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class LLMMessage:
    role: str
    content: str | list
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "gpt-5-nano": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}

AGENT_PROVIDER_MAP: dict[str, str] = {
    "incident_response": "openai",
    "infrastructure_provisioning": "openai",
    "compliance_scan": "openai",
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = COST_PER_1K_TOKENS.get(model, {"input": 0.003, "output": 0.015})
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000


class LLMProvider(ABC):

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 2048,
        model: str | None = None,
    ) -> LLMResponse:
        ...


class AnthropicProvider(LLMProvider):

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 2048,
        model: str | None = None,
    ) -> LLMResponse:
        if settings.DEMO_MODE or not self.api_key:
            return LLMResponse(
                content="[DEMO MODE — set ANTHROPIC_API_KEY to enable real LLM]",
                stop_reason="end_turn",
                model=model or settings.ANTHROPIC_MODEL,
            )

        client = self._get_client()
        msgs = []
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                blocks: list = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]})
                msgs.append({"role": "assistant", "content": blocks})
            else:
                msgs.append({"role": m.role, "content": m.content})
        kwargs: dict = dict(
            model=model or settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=msgs,
        )
        if tools:
            kwargs["tools"] = tools

        response = await client.messages.create(**kwargs)
        tool_calls = []
        text_parts = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({"name": block.name, "id": block.id, "input": block.input})
            elif block.type == "text":
                text_parts.append(block.text)

        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )


class OpenAIProvider(LLMProvider):

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 2048,
        model: str | None = None,
    ) -> LLMResponse:
        if settings.DEMO_MODE or not self.api_key:
            return LLMResponse(
                content="[DEMO MODE — set OPENAI_API_KEY to enable real LLM]",
                stop_reason="stop",
                model=model or settings.OPENAI_MODEL,
            )

        import json as _json
        client = self._get_client()
        msgs: list = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                msgs.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["name"], "arguments": _json.dumps(tc["input"])}}
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == "user" and isinstance(m.content, list):
                for block in m.content:
                    if block.get("type") == "tool_result":
                        msgs.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block.get("content", "")),
                        })
            else:
                msgs.append({"role": m.role, "content": m.content})

        kwargs: dict = dict(
            model=model or settings.OPENAI_MODEL,
            max_completion_tokens=max_tokens,
            messages=msgs,
        )
        if tools:
            oai_tools = []
            for t in tools:
                oai_tools.append({"type": "function", "function": t})
            kwargs["tools"] = oai_tools

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message
        tool_calls = []
        if msg.tool_calls:
            import json
            for tc in msg.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "id": tc.id,
                    "input": json.loads(tc.function.arguments or "{}"),
                })

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "stop",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model,
        )


class LLMRouter:

    def __init__(self):
        self._anthropic = AnthropicProvider()
        self._openai = OpenAIProvider()

    def _provider_for_agent(self, agent_type: str, preferred: str | None = None) -> LLMProvider:
        if preferred == "anthropic":
            return self._anthropic
        if preferred == "openai":
            return self._openai
        mapped = AGENT_PROVIDER_MAP.get(agent_type, settings.PRIMARY_LLM_PROVIDER)
        return self._anthropic if mapped == "anthropic" else self._openai

    async def complete_with_failover(
        self,
        agent_type: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 2048,
        preferred_provider: str | None = None,
    ) -> LLMResponse:
        primary = self._provider_for_agent(agent_type, preferred_provider)
        fallback = self._openai if isinstance(primary, AnthropicProvider) else self._anthropic

        try:
            return await primary.complete(system, messages, tools, max_tokens)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "500" in err or "rate" in err:
                return await fallback.complete(system, messages, tools, max_tokens)
            raise
