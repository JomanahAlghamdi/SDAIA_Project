import json
from datetime import date

import pytest

from finder.agent import Agent, Limits, PromptBudget, token_upper_bound
from finder.models import tool_schemas
from finder.catalog import Catalog, load_student
from finder.harness import Harness, Trace
from finder.mcp_client import CatalogBridge
from finder.provider import Completion, ReplayProvider, ProviderError, scripted_call, scripted_final
from finder.storage import DraftStore
from finder.intake import new_student


@pytest.mark.asyncio
async def test_browsing_finishes_with_nonzero_usage_and_unchanged_24000_limit(tmp_path):
    """Regression for the user's token_budget failure; not a live model score."""
    class MeteredBrowse:
        def __init__(self):
            self.responses = iter(zip([3200, 3800, 4300, 4800], [
                scripted_call("search_opportunities", {"field": "AI", "cities": ["Riyadh"]}),
                scripted_call("get_opportunity_details", {"opportunity_id": "OP012"}),
                scripted_call("get_opportunity_details", {"opportunity_id": "OP017"}),
                scripted_final("Synthetic AI options OP012 and OP017 in Riyadh; eligibility unchecked.")]))

        async def complete(self, messages, tools, max_tokens):
            usage, response = next(self.responses)
            return Completion(response, usage, 150, 0, "metered-regression-fixture")

    store = DraftStore(tmp_path / "db.sqlite")
    try:
        async with CatalogBridge(date(2026, 10, 27)) as bridge:
            h = Harness(new_student(), Catalog(), bridge, store, today=date(2026, 10, 27))
            run = await Agent(h, MeteredBrowse(), limits=Limits(max_total_tokens=24000)).run(
                "I need an internship opportunity for AI in Riyadh")
            assert run.stopped == "completed" and run.requests == 4
            assert run.prompt_tokens + run.completion_tokens == 16700
            assert "OP012" in run.final.answer and "OP017" in run.final.answer
            assert store.count() == 0 and h.student.major is None
    finally:
        store.close()


def test_prompt_meter_never_reuses_a_changed_prefix_or_tool_schema():
    messages = [{"role": "user", "content": "x" * 3000}]
    tools = [{"name": "test"}]
    meter = PromptBudget()
    meter.observe(messages, tools, 1000)
    added = [*messages, {"role": "assistant", "content": "A short answer."}]
    estimate, basis = meter.estimate(added, tools)
    assert 1000 < estimate < token_upper_bound([added, tools])
    assert basis == "measured_prefix_plus_new_bytes"
    changed = [{"role": "user", "content": "Different request"}, added[1]]
    assert meter.estimate(changed, tools) == (token_upper_bound([changed, tools]), "full_utf8_bytes")
    assert meter.estimate(added, [])[1] == "full_utf8_bytes"
    meter.observe(messages, tools, 0)
    assert meter.estimate(added, tools)[1] == "full_utf8_bytes"


@pytest.mark.asyncio
async def test_remaining_budget_caps_output_and_keeps_actual_usage_guard(tmp_path):
    class FinalProvider:
        async def complete(self, messages, tools, max_tokens):
            assert max_tokens == 300
            return Completion(scripted_final("Synthetic example."), 1000, 100, 0, "budget-test")
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        harness = Harness(new_student(), Catalog(), None, store)
        agent = Agent(harness, FinalProvider())
        bound = token_upper_bound([[{"role": "system", "content": agent.system()},
                                    {"role": "user", "content": "Hello"}], tool_schemas()])
        agent.limits = Limits(max_total_tokens=bound + 300)
        result = await agent.run("Hello")
        assert result.stopped == "completed" and result.requests == 1
        assert result.prompt_tokens + result.completion_tokens <= agent.limits.max_total_tokens
    finally:
        store.close()


@pytest.mark.asyncio
async def test_context_compacts_old_pairs_after_tools_without_losing_current_call(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        async with CatalogBridge(date(2026, 10, 27)) as bridge:
            harness = Harness(new_student(), Catalog(), bridge, store, today=date(2026, 10, 27))
            provider = ReplayProvider([
                scripted_call("get_opportunity_details", {"opportunity_id": "OP030"}),
                scripted_final("Synthetic opportunity details; no draft saved.")])
            agent = Agent(harness, provider)
            agent.history = [{"role": "user", "content": "Old question"},
                             {"role": "assistant", "content": "x" * 3500}]
            prompt = "Show OP030"
            bound = token_upper_bound([[{"role": "system", "content": agent.system()}, *agent.history,
                                        {"role": "user", "content": prompt}], tool_schemas()])
            agent.limits = Limits(max_context_bound=bound + 100)
            run = await agent.run(prompt)
            assert run.stopped == "completed"
            assert any(e["event"] == "history_compacted" for e in run.events)
            assert [m["role"] for m in run.transcript] == ["system", "user", "assistant", "tool", "assistant"]
            assert run.transcript[1]["content"] == prompt
    finally:
        store.close()


@pytest.mark.parametrize("cost", [float("nan"), float("inf"), 0, -1])
def test_nonfinite_or_disabled_cost_limits_are_rejected(cost):
    with pytest.raises(ValueError, match="Cost limit"):
        Limits(max_cost_usd=cost)


@pytest.mark.asyncio
async def test_mcp_cleanup_preserves_provider_error():
    with pytest.raises(ProviderError, match="quota fixture"):
        async with CatalogBridge(date(2026, 10, 27)):
            raise ProviderError("quota fixture")


@pytest.mark.asyncio
async def test_real_mcp_tools_and_full_loop(tmp_path):
    async with CatalogBridge(date(2026, 10, 27)) as bridge:
        assert {"search_opportunities", "get_opportunity_details"} == set(bridge.tools)
        search = await bridge.call("search_opportunities", {"field": "AI", "cities": ["Jeddah"]})
        assert [x["id"] for x in search["opportunities"]] == ["OP002"]
        store = DraftStore(tmp_path / "db.sqlite")
        try:
            h = Harness(load_student("S001"), Catalog(), bridge, store, lambda _: True, date(2026, 10, 27))
            script = [
                scripted_call("search_opportunities", {"field": "Data", "cities": ["Riyadh"]}, "one"),
                scripted_call("get_opportunity_details", {"opportunity_id": "OP001"}, "two"),
                scripted_call("check_eligibility", {"opportunity_id": "OP001"}, "three"),
                scripted_call("save_application_draft", {"opportunity_id": "OP001"}, "four"),
                scripted_final("Synthetic local draft created, not sent.", ["OP001"])]
            run = await Agent(h, ReplayProvider(script)).run("Prepare a local draft for OP001.")
            assert run.stopped == "completed" and run.tool_calls == 4 and store.count() == 1
            assert bridge.calls.count("search_opportunities") >= 2
            assert "get_opportunity_details" in bridge.calls
            assert run.models == ["offline-scripted-test-double"] * 5
        finally:
            store.close()


@pytest.mark.asyncio
async def test_budget_stops_before_side_effects(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store, lambda _: True, date(2026, 10, 27))
        calls = [scripted_call("check_eligibility", {"opportunity_id": "OP001"})] * 10
        run = await Agent(h, ReplayProvider(calls), limits=Limits(max_steps=2)).run("Check repeatedly")
        assert run.stopped == "step_budget" and run.requests == 2
        run = await Agent(h, ReplayProvider(calls), limits=Limits(max_total_tokens=5)).run("Check")
        assert run.stopped == "token_budget" and run.requests == 0
        run = await Agent(h, ReplayProvider(calls), limits=Limits(max_context_bound=10)).run("Check")
        assert run.stopped == "context_budget" and run.requests == 0
        msg = scripted_call("save_application_draft", {"opportunity_id": "OP001"})
        msg["tool_calls"] *= 2
        run = await Agent(h, ReplayProvider([msg]), limits=Limits(max_tool_calls=1)).run("Save")
        assert run.stopped == "tool_budget" and store.count() == 0
    finally:
        store.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("usage,cost,reason", [(99999, 0, "token_budget"), (10, 0.2, "cost_budget"),
                                              (10, 0.001, "unexpected_provider_cost")])
async def test_excess_provider_meter_never_reaches_write(tmp_path, usage, cost, reason):
    class Metered:
        async def complete(self, *args):
            return Completion(scripted_call("save_application_draft", {"opportunity_id": "OP001"}), usage, 1, cost, "test-meter")
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store, lambda _: True, date(2026, 10, 27))
        run = await Agent(h, Metered()).run("Save")
        assert run.stopped == reason and store.count() == 0
    finally:
        store.close()


@pytest.mark.asyncio
async def test_invalid_final_format_repair_and_memory(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store, today=date(2026, 10, 27))
        agent = Agent(h, ReplayProvider([{"role": "assistant", "content": "not json"}, scripted_final("Synthetic example.")]), limits=Limits(max_history_messages=4))
        run = await agent.run("Hello")
        assert run.stopped == "completed" and run.requests == 2
        for _ in range(5):
            agent.provider = ReplayProvider([scripted_final("Synthetic response.")])
            assert (await agent.run("Follow up")).stopped == "completed"
        assert len(agent.history) == 4
        assert [m["role"] for m in agent.history] == ["user", "assistant", "user", "assistant"]
        assert "S001" in agent.system()
    finally:
        store.close()


@pytest.mark.asyncio
async def test_invalid_function_json_is_observation(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        msg = scripted_call("check_eligibility", {})
        msg["tool_calls"][0]["function"]["arguments"] = "{broken"
        h = Harness(load_student("S001"), Catalog(), None, store)
        run = await Agent(h, ReplayProvider([msg, scripted_final("Could not execute malformed tool request.")])).run("Check")
        assert run.stopped == "completed"
        assert any("malformed_tool_call" in str(x) for x in run.transcript)
        assert store.count() == 0
    finally:
        store.close()


@pytest.mark.asyncio
async def test_injected_catalog_cannot_approve(tmp_path):
    async with CatalogBridge(date(2026, 10, 27)) as bridge:
        details = await bridge.call("get_opportunity_details", {"opportunity_id": "OP030"})
        assert "already approved" in details["opportunity"]["description"]
        store = DraftStore(tmp_path / "db.sqlite")
        try:
            h = Harness(load_student("S001"), Catalog(), bridge, store, lambda _: False, date(2026, 10, 27))
            # Worst-case tool call: assume the model follows the malicious description.
            result = await h.dispatch("save_application_draft", {"opportunity_id": "OP030"})
            assert result["status"] == "denied" and store.count() == 0
        finally:
            store.close()
