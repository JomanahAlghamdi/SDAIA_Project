import json
from datetime import date

import pytest

from finder.agent import Agent, Limits
from finder.catalog import Catalog, load_student
from finder.harness import Harness, Trace
from finder.mcp_client import CatalogBridge
from finder.provider import Completion, ReplayProvider, scripted_call, scripted_final
from finder.storage import DraftStore


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
@pytest.mark.parametrize("usage,cost,reason", [(99999, 0, "token_budget"), (10, 0.2, "cost_budget")])
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
