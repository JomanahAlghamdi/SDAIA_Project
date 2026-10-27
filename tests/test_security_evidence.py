import copy
import json

import pytest

from evals.security import main_async, verified_live_defence
from evals.run import hashes
from finder.provider import ProviderError


def sample():
    # Fabricated TEST FIXTURE only, never written to results/ or reported as a model run.
    return {"status": "complete", "mode": "live", "llm_used": True, "hashes": {"fixture": "v1"},
            "before": {"stopped": "completed", "injected_description_read": True, "attack_success": True},
            "after": {"stopped": "completed", "injected_description_read": True, "attack_success": False,
                      "unauthorized_write_attempted": True, "guard_blocks": ["human_denied"]},
            "benign_control": {"saved_with_explicit_test_human_consent": True}}


@pytest.mark.parametrize("change", ["stale", "interrupted", "no_attack", "no_read", "no_guard"])
def test_readiness_rejects_insufficient_security_evidence(change):
    report = sample()
    assert verified_live_defence(report, {"fixture": "v1"})
    broken = copy.deepcopy(report)
    if change == "stale":
        broken["hashes"] = {"fixture": "v0"}
    elif change == "interrupted":
        broken["after"]["stopped"] = "provider_error"
    elif change == "no_attack":
        broken["before"]["attack_success"] = False
    elif change == "no_read":
        broken["after"]["injected_description_read"] = False
    else:
        broken["after"]["guard_blocks"] = []
    assert not verified_live_defence(broken, {"fixture": "v1"})


@pytest.mark.asyncio
async def test_replay_records_actual_injection_read_and_source(tmp_path):
    assert await main_async("replay", tmp_path) == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["hashes"] == hashes()
    assert report["before"]["injected_description_read"] and report["after"]["injected_description_read"]
    assert report["before"]["unauthorized_drafts"] == 1 and report["after"]["unauthorized_drafts"] == 0
    assert not verified_live_defence(report, hashes())


@pytest.mark.asyncio
async def test_failed_rerun_invalidates_old_success(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / "report.json").write_text(json.dumps(sample()))
    with pytest.raises(ProviderError, match="missing"):
        await main_async("live", tmp_path)
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "running" and report["llm_used"] is False
    assert not verified_live_defence(report, hashes())
