from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

API = "https://openrouter.ai/api/v1"


class ProviderError(RuntimeError):
    pass


@dataclass
class Completion:
    message: dict
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    model: str
    cost_source: str = "provider"


async def free_tool_models() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(API + "/models")
            if response.status_code != 200:
                raise ProviderError(f"Model metadata unavailable (HTTP {response.status_code}). No model selected.")
            data = response.json().get("data", [])
    except httpx.HTTPError:
        raise ProviderError("Cannot retrieve current model metadata. Check the network; no model selected.") from None
    except (ValueError, AttributeError):
        raise ProviderError("Invalid model metadata response. No model selected.") from None
    result = []
    for item in data:
        try:
            pricing = item["pricing"]
            if "prompt" not in pricing or "completion" not in pricing:
                continue
            relevant = [Decimal(str(pricing.get(key, "0"))) for key in
                        ("prompt", "completion", "request", "internal_reasoning", "input_cache_read", "input_cache_write")]
            # Router aliases can change the underlying model between trials; exclude them.
            if all(x == 0 for x in relevant) and "tools" in item.get("supported_parameters", []) and not item["id"].startswith("openrouter/"):
                result.append(item)
        except (KeyError, TypeError, InvalidOperation):
            continue
    return sorted(result, key=lambda x: x["id"])


class OpenRouter:
    """Single, concrete, verified-free model. No silent fallback, paid calls or retries."""
    def __init__(self, key: str | None = None, model: str | None = None):
        self.key = key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model or os.environ.get("OPENROUTER_MODEL", "")
        if not self.key:
            raise ProviderError("OPENROUTER_API_KEY is missing. Set it locally in .env; never commit or share it.")
        if not self.model:
            raise ProviderError("OPENROUTER_MODEL is missing. Run `uv run python app.py models` and select a concrete free tool model.")

    async def __aenter__(self):
        available = {x["id"]: x for x in await free_tool_models()}
        if self.model not in available:
            raise ProviderError("Configured model is not currently listed as a concrete free tool-calling model. Re-select explicitly; no paid fallback.")
        self.metadata = available[self.model]
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15), follow_redirects=False)
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def complete(self, messages: list[dict], tools: list[dict], max_tokens: int = 900) -> Completion:
        try:
            response = await self.client.post(API + "/chat/completions",
                headers={"Authorization": "Bearer " + self.key, "X-Title": "Internship Finder synthetic capstone"},
                json={"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto",
                      "temperature": 0, "max_tokens": max_tokens, "stream": False,
                      "provider": {"require_parameters": True, "max_price": {"prompt": 0, "completion": 0}}})
        except httpx.HTTPError:
            raise ProviderError("Provider connection/timeout error. Request stopped; no retry or fallback.") from None
        if response.status_code != 200:
            # Never log provider response bodies, headers or credentials.
            raise ProviderError(f"Provider HTTP {response.status_code}. Request stopped; no retry or fallback.")
        try:
            body = response.json()
            message = body["choices"][0]["message"]
            usage = body["usage"]
            prompt_tokens, completion_tokens = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
            if min(prompt_tokens, completion_tokens) < 0:
                raise ValueError("negative usage")
            cost = float(usage["cost"]) if usage.get("cost") is not None else 0.0
            if cost < 0 or not math.isfinite(cost):
                raise ValueError("negative cost")
            if not isinstance(message, dict) or (message.get("tool_calls") is not None and not isinstance(message["tool_calls"], list)):
                raise ValueError("invalid message")
            return Completion(message=message, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                              cost_usd=cost, model=body.get("model", self.model),
                              cost_source="provider" if usage.get("cost") is not None else "verified_zero_price_estimate")
        except (KeyError, IndexError, ValueError, TypeError):
            raise ProviderError("Provider returned missing/malformed message or usage. Stopping; no invented metrics.") from None


class ReplayProvider:
    """DETERMINISTIC TEST DOUBLE ONLY. It does not process language or measure LLM quality."""
    model = "offline-scripted-test-double"

    def __init__(self, messages: list[dict]):
        self.script = iter(messages)

    async def complete(self, messages, tools, max_tokens=900):
        return Completion(next(self.script), 0, 0, 0.0, self.model, "offline_no_model")


def scripted_call(name: str, arguments: dict, call_id: str = "call_test"):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": call_id, "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)}}]}


def scripted_final(answer: str, ids: list[str] | None = None, missing: list[str] | None = None):
    return {"role": "assistant", "content": json.dumps({"answer": answer, "opportunity_ids": ids or [], "needs_info": missing or []})}
