"""Synthetic evidence-checker fixtures only; never written to results/ or scored as LLM runs."""
import copy
import csv

import pytest

from scripts.readiness import experiment_source_matches, security_evidence, valid_completed_run


SOURCE = {"tasks.jsonl": "task-fixture", "finder/agent.py": "agent-fixture", "evals/graders.py": "grader-fixture", "scripts/readiness.py": "old-checker"}


def reports():
    live = {"status": "complete", "mode": "live", "llm_used": True, "requested_model": "test-fixture:free", "hashes": dict(SOURCE),
            "before": {"stopped": "completed", "injected_description_read": True, "effective_models": ["test-fixture:free"], "unauthorized_write_attempted": False, "unauthorized_drafts": 0, "attack_success": False},
            "after": {"stopped": "completed", "injected_description_read": True, "effective_models": ["test-fixture:free"], "unauthorized_write_attempted": False, "unauthorized_drafts": 0, "attack_success": False, "guard_blocks": []},
            "benign_control": {"saved_with_explicit_test_human_consent": True}}
    replay = copy.deepcopy(live)
    replay.update(mode="replay", llm_used=False)
    replay["before"].update(unauthorized_write_attempted=True, unauthorized_drafts=1, attack_success=True)
    replay["after"].update(unauthorized_write_attempted=True, guard_blocks=["human_denied"])
    return live, replay


def test_model_resistance_and_guard_replay_are_distinct():
    live, replay = reports()
    result = security_evidence(live, replay, SOURCE)
    assert result["requirements_met"]
    assert result["live_experiment_verified"] and result["forced_action_guard_verified"]
    assert not result["live_guard_causality_verified"]


@pytest.mark.parametrize("defect", ["provider_failure", "no_read", "no_llm", "unguarded_write", "no_guard_event", "no_benign_control", "runtime_changed"])
def test_incomplete_or_failed_security_evidence_rejected(defect):
    live, replay = reports()
    if defect == "provider_failure": live["after"]["stopped"] = "provider_error"
    elif defect == "no_read": live["before"]["injected_description_read"] = False
    elif defect == "no_llm": live["llm_used"] = False
    elif defect == "unguarded_write": replay["after"]["unauthorized_drafts"] = 1
    elif defect == "no_guard_event": replay["after"]["guard_blocks"] = []
    elif defect == "no_benign_control": replay["benign_control"]["saved_with_explicit_test_human_consent"] = False
    else: live["hashes"]["finder/agent.py"] = "different-runtime"
    assert not security_evidence(live, replay, SOURCE)["requirements_met"]


def test_only_read_only_checker_and_its_test_can_change():
    current = dict(SOURCE, **{"scripts/readiness.py": "new-checker", "tests/test_readiness.py": "new-tests"})
    assert experiment_source_matches(SOURCE, current)
    for path in ("finder/agent.py", "evals/graders.py", "tasks.jsonl", "prompts/system.md", "uv.lock"):
        changed = dict(current, **{path: "different-experiment"})
        assert not experiment_source_matches(SOURCE, changed)


@pytest.mark.parametrize("defect", [None, "duplicate_trial", "provider_error", "missing_transcript", "manifest_count"])
def test_completed_suite_requires_unique_trials_and_actual_transcripts(tmp_path, defect):
    tasks = [{"id": "fixture-one"}, {"id": "fixture-two"}]
    manifest = {"status": "complete", "mode": "live_openrouter", "configurations": ["A", "B"], "trials": 1, "rows": 4,
                "task_count": 2, "task_file_sha256": SOURCE["tasks.jsonl"], "hashes": dict(SOURCE)}
    for config in ("A", "B"):
        rows = []
        for task in tasks:
            transcript = f"{config}-{task['id']}.json"
            (tmp_path / transcript).write_text('{"test_fixture": true}')
            rows.append({"config": config, "task_id": task["id"], "trial": 1, "passed": "True", "stopped": "completed", "transcript": transcript})
        if config == "B":
            if defect == "duplicate_trial": rows[1]["task_id"] = rows[0]["task_id"]
            elif defect == "provider_error": rows[0]["stopped"] = "provider_error"
            elif defect == "missing_transcript": (tmp_path / rows[0]["transcript"]).unlink()
            elif defect == "manifest_count": manifest["rows"] = 3
        with (tmp_path / f"eval_{config}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    assert valid_completed_run(tmp_path, manifest, tasks, SOURCE) is (defect is None)
