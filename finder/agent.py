from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from pydantic import ValidationError

from .catalog import ROOT
from .harness import Harness
from .models import FinalAnswer, tool_schemas
from .provider import ProviderError


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Limits:
    max_steps: int = 8
    max_tool_calls: int = 20
    max_total_tokens: int = 24000
    max_cost_usd: float = 0.05
    max_context_bound: int = 16000
    max_output_tokens: int = 900
    max_tool_result_chars: int = 4000
    max_history_messages: int = 12

    @classmethod
    def environment(cls):
        obj = cls(max_steps=int(os.getenv("IF_MAX_STEPS", "8")),
                  max_tool_calls=int(os.getenv("IF_MAX_TOOL_CALLS", "20")),
                  max_total_tokens=int(os.getenv("IF_MAX_REQUEST_TOKENS", "24000")),
                  max_cost_usd=float(os.getenv("IF_MAX_COST_USD", "0.05")))
        if min(obj.max_steps, obj.max_tool_calls, obj.max_total_tokens, obj.max_cost_usd) <= 0:
            raise ValueError("All runtime budgets must be positive")
        return obj


def token_upper_bound(value) -> int:
    # Conservative UTF-8 byte bound + framing allowance, NOT a measured tokenizer count.
    # Provider usage is reported separately. This intentionally overestimates Arabic.
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8")) + 512


@dataclass
class Run:
    final: FinalAnswer | None = None
    stopped: str = ""
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0
    tool_calls: int = 0
    models: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    transcript: list[dict] = field(default_factory=list)


class Agent:
    def __init__(self, harness: Harness, provider, config="B", limits: Limits | None = None):
        if config not in {"A", "B"}:
            raise ValueError("Config must be A or B")
        self.harness, self.provider, self.config = harness, provider, config
        self.limits = limits or Limits.environment()
        self.history: list[dict] = []

    def system(self):
        spec = (ROOT / "prompts/system.md").read_text(encoding="utf-8")
        if self.config == "B":
            spec += "\n" + (ROOT / "prompts/config_b.txt").read_text(encoding="utf-8")
        state = {"student": self.harness.student.model_dump(mode="json"),
                 "as_of": self.harness.today().isoformat(),
                 "last_search_filters": self.harness.last_search}
        return spec + "\nHOST SESSION STATE (approval is never stored here):\n" + json.dumps(state, ensure_ascii=False)

    async def run(self, prompt: str) -> Run:
        run = Run()
        start_event = len(self.harness.trace.events)
        self.harness.begin_turn()
        if not prompt.strip() or len(prompt) > 4000:
            run.stopped = "input_limit"
            return run
        # Only complete user/final-answer pairs persist; never orphan tool result messages.
        self.history = self.history[-self.limits.max_history_messages:]
        history = list(self.history)
        tools = tool_schemas()
        messages = [{"role": "system", "content": self.system()}, *history, {"role": "user", "content": prompt}]
        while history and token_upper_bound([messages, tools]) > self.limits.max_context_bound:
            history = history[2:]
            messages = [messages[0], *history, {"role": "user", "content": prompt}]
        self.harness.trace.add("run_start", config=self.config, profile_id=self.harness.student.id,
                               history_kept=len(history), history_removed=len(self.history) - len(history))
        for _ in range(self.limits.max_steps):
            bound = token_upper_bound([messages, tools])
            if bound > self.limits.max_context_bound:
                run.stopped = "context_budget"
                break
            if run.prompt_tokens + run.completion_tokens + bound + self.limits.max_output_tokens > self.limits.max_total_tokens:
                run.stopped = "token_budget"
                break
            if run.cost_usd >= self.limits.max_cost_usd:
                run.stopped = "cost_budget"
                break
            run.requests += 1
            try:
                completion = await self.provider.complete(messages, tools, self.limits.max_output_tokens)
            except (ProviderError, StopIteration, RuntimeError) as exc:
                run.stopped = "provider_error"
                self.harness.trace.add("provider_error", message=str(exc)[:180])
                break
            run.prompt_tokens += completion.prompt_tokens
            run.completion_tokens += completion.completion_tokens
            run.cost_usd += completion.cost_usd
            run.models.append(completion.model)
            self.harness.trace.add("model_usage", model=completion.model, prompt_tokens=completion.prompt_tokens,
                                   completion_tokens=completion.completion_tokens, cost_usd=completion.cost_usd,
                                   cost_source=completion.cost_source, input_token_upper_bound=bound)
            # Stop BEFORE any side effect if the provider has already exceeded a meter.
            if run.cost_usd > self.limits.max_cost_usd:
                run.stopped = "cost_budget"
                break
            if run.prompt_tokens + run.completion_tokens > self.limits.max_total_tokens:
                run.stopped = "token_budget"
                break
            msg = completion.message
            calls = msg.get("tool_calls") or []
            if calls:
                if len(calls) + run.tool_calls > self.limits.max_tool_calls:
                    run.stopped = "tool_budget"
                    break
                cleaned = {"role": "assistant", "content": msg.get("content"), "tool_calls": calls}
                messages.append(cleaned)
                for call in calls:
                    run.tool_calls += 1
                    if not isinstance(call, dict):
                        run.stopped = "malformed_provider_message"
                        break
                    try:
                        fn = call["function"]
                        arguments = json.loads(fn["arguments"])
                        result = await self.harness.dispatch(fn["name"], arguments)
                    except (KeyError, TypeError, json.JSONDecodeError):
                        result = {"error": "malformed_tool_call"}
                    text = json.dumps(result, ensure_ascii=False)
                    if len(text) > self.limits.max_tool_result_chars:
                        text = json.dumps({"truncated": True, "excerpt": text[:self.limits.max_tool_result_chars],
                                           "instruction": "Ask for a smaller page or a specific ID."}, ensure_ascii=False)
                        self.harness.trace.add("context_result_capped", tool=call.get("function", {}).get("name"))
                    messages.append({"role": "tool", "tool_call_id": call.get("id", "invalid"), "content": text})
                if run.stopped:
                    break
                continue
            try:
                content = msg.get("content") or ""
                run.final = FinalAnswer.model_validate_json(content)
                if any(oid not in self.harness.catalog.items for oid in run.final.opportunity_ids):
                    raise ValueError("Unknown opportunity IDs in final answer")
                messages.append({"role": "assistant", "content": content})
                run.stopped = "completed"
                break
            except (ValidationError, ValueError):
                run.final = None
                # Repair within the SAME request/step/token budgets.
                messages.extend([{"role": "assistant", "content": (msg.get("content") or "")[:5000]},
                                 {"role": "user", "content": "Return only the specified JSON schema, using known catalog IDs. This is a formatting repair, not new approval."}])
        else:
            run.stopped = "step_budget"
        if run.final:
            self.history = [*history, {"role": "user", "content": prompt},
                            {"role": "assistant", "content": run.final.model_dump_json()}][-self.limits.max_history_messages:]
        self.harness.trace.add("run_end", stopped=run.stopped, requests=run.requests, tool_calls=run.tool_calls)
        run.events = self.harness.trace.events[start_event:]
        run.transcript = messages
        return run
