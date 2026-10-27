from __future__ import annotations

import json
import os
import math
from dataclasses import dataclass, field

from pydantic import ValidationError

from .catalog import ROOT, check_eligibility
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

    def __post_init__(self):
        counts = (self.max_steps, self.max_tool_calls, self.max_total_tokens, self.max_context_bound,
                  self.max_output_tokens, self.max_tool_result_chars, self.max_history_messages)
        if any(not isinstance(value, int) or value <= 0 for value in counts):
            raise ValueError("All count and size limits must be positive integers")
        if self.max_history_messages % 2:
            raise ValueError("Conversation history must retain complete message pairs")
        if not math.isfinite(self.max_cost_usd) or self.max_cost_usd <= 0:
            raise ValueError("Cost limit must be finite and positive")

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


class PromptBudget:
    """Use measured usage for an unchanged prefix, bytes only for new messages.

    This is a conservative reservation estimate, not an exact model tokenizer.
    Actual provider usage is still checked before executing any tool action.
    """
    def __init__(self):
        self.message_count = 0
        self.prefix_json = ""
        self.tools_json = ""
        self.prompt_tokens = 0

    def estimate(self, messages, tools):
        full = token_upper_bound([messages, tools])
        if (self.prompt_tokens > 0 and len(messages) >= self.message_count
                and json.dumps(messages[:self.message_count], ensure_ascii=False) == self.prefix_json
                and json.dumps(tools, ensure_ascii=False) == self.tools_json):
            added = token_upper_bound(messages[self.message_count:])
            return min(full, self.prompt_tokens + added), "measured_prefix_plus_new_bytes"
        return full, "full_utf8_bytes"

    def observe(self, messages, tools, prompt_tokens):
        self.message_count = len(messages)
        self.prefix_json = json.dumps(messages, ensure_ascii=False)
        self.tools_json = json.dumps(tools, ensure_ascii=False)
        self.prompt_tokens = prompt_tokens


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
    error: str = ""


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
        meter = PromptBudget()
        repairs = 0
        for _ in range(self.limits.max_steps):
            bound = token_upper_bound([messages, tools])
            estimate, basis = meter.estimate(messages, tools)
            spent = run.prompt_tokens + run.completion_tokens
            # Retire only old complete user/answer pairs. Current tool-call/result
            # pairs and the current request must remain intact.
            while history and (bound > self.limits.max_context_bound
                               or spent + estimate + min(64, self.limits.max_output_tokens) > self.limits.max_total_tokens):
                history = history[2:]
                del messages[1:3]
                self.harness.trace.add("history_compacted", removed_messages=2)
                bound = token_upper_bound([messages, tools])
                estimate, basis = meter.estimate(messages, tools)
            if bound > self.limits.max_context_bound:
                run.stopped = "context_budget"
                break
            remaining_output = self.limits.max_total_tokens - spent - estimate
            if remaining_output < min(64, self.limits.max_output_tokens):
                run.stopped = "token_budget"
                break
            output_limit = min(self.limits.max_output_tokens, remaining_output)
            if run.cost_usd >= self.limits.max_cost_usd:
                run.stopped = "cost_budget"
                break
            run.requests += 1
            self.harness.trace.add("request_budget", spent_tokens=spent,
                                   prompt_reservation=estimate, reservation_basis=basis,
                                   max_output_tokens=output_limit, total_limit=self.limits.max_total_tokens)
            try:
                completion = await self.provider.complete(messages, tools, output_limit)
            except (ProviderError, StopIteration, RuntimeError) as exc:
                run.stopped = "provider_error"
                run.error = str(exc)[:180]
                self.harness.trace.add("provider_error", message=str(exc)[:180])
                break
            meter.observe(messages, tools, completion.prompt_tokens)
            run.prompt_tokens += completion.prompt_tokens
            run.completion_tokens += completion.completion_tokens
            run.cost_usd += completion.cost_usd
            run.models.append(completion.model)
            self.harness.trace.add("model_usage", model=completion.model, prompt_tokens=completion.prompt_tokens,
                                   completion_tokens=completion.completion_tokens, cost_usd=completion.cost_usd,
                                   cost_source=completion.cost_source, input_token_upper_bound=bound,
                                   finish_reason=completion.finish_reason, reasoning_tokens=completion.reasoning_tokens)
            # Stop BEFORE any side effect if the provider has already exceeded a meter.
            if run.cost_usd > self.limits.max_cost_usd:
                run.stopped = "cost_budget"
                break
            if run.cost_usd > 0:
                run.stopped = "unexpected_provider_cost"
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
                    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
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
                invalid = [oid for oid in run.final.opportunity_ids if check_eligibility(
                    self.harness.student, self.harness.catalog.get(oid), self.harness.today())["status"] != "eligible"]
                if invalid:
                    raise ValueError("opportunity_ids contains unverified/ineligible IDs: " + ", ".join(invalid)
                                     + ". Mention candidates in answer, but remove them from opportunity_ids."
                                     + " Browsing needs no personal eligibility check and needs_info must be [].")
                messages.append({"role": "assistant", "content": content})
                run.stopped = "completed"
                break
            except (ValidationError, ValueError) as exc:
                run.final = None
                repairs += 1
                self.harness.trace.add("final_repair", attempt=repairs, empty=not bool(msg.get("content")),
                                       finish_reason=completion.finish_reason, reason=str(exc)[:300])
                if repairs > 1:
                    run.stopped = "invalid_final_response"
                    break
                # Repair within the SAME request/step/token budgets.
                correction = ("Return only the specified JSON schema, using known catalog IDs. "
                              "Use empty opportunity_ids for browsing or unverified eligibility. "
                              "This is a response repair, not new approval. ")
                if not isinstance(exc, ValidationError):
                    correction += str(exc)
                messages.extend([{"role": "assistant", "content": (msg.get("content") or "")[:5000]},
                                 {"role": "user", "content": correction}])
        else:
            run.stopped = "step_budget"
        if run.final:
            self.history = [*history, {"role": "user", "content": prompt},
                            {"role": "assistant", "content": run.final.model_dump_json()}][-self.limits.max_history_messages:]
        self.harness.trace.add("run_end", stopped=run.stopped, requests=run.requests, tool_calls=run.tool_calls,
                               prompt_tokens=run.prompt_tokens, completion_tokens=run.completion_tokens,
                               cost_usd=run.cost_usd)
        run.events = self.harness.trace.events[start_event:]
        run.transcript = messages
        return run
