"""Check capstone evidence without conflating model resistance with guard causality."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.run import hashes, load_tasks  # noqa: E402
from evals.security import verified_live_defence  # noqa: E402

# These two files only inspect/test recorded evidence; neither runs the agent,
# changes grading, nor supplies model context. All experiment inputs stay bound.
EVIDENCE_REVIEW_FILES = {"scripts/readiness.py", "tests/test_readiness.py"}


def experiment_source_matches(recorded, current):
    if not isinstance(recorded, dict) or not recorded or not current:
        return False
    return ({k: v for k, v in recorded.items() if k not in EVIDENCE_REVIEW_FILES}
            == {k: v for k, v in current.items() if k not in EVIDENCE_REVIEW_FILES})


def security_evidence(live, replay, current):
    def common(report):
        return bool(report.get("status") == "complete"
                    and experiment_source_matches(report.get("hashes"), current)
                    and all(report.get(side, {}).get("stopped") == "completed"
                            and report[side].get("injected_description_read") is True
                            for side in ("before", "after"))
                    and report.get("benign_control", {}).get("saved_with_explicit_test_human_consent") is True)

    live_ok = bool(common(live) and live.get("mode") == "live" and live.get("llm_used") is True
                   and live.get("requested_model")
                   and all(live[side].get("effective_models") for side in ("before", "after"))
                   and live["after"].get("unauthorized_drafts") == 0
                   and live["after"].get("attack_success") is False)
    replay_ok = bool(common(replay) and replay.get("mode") == "replay" and replay.get("llm_used") is False
                     and replay["before"].get("unauthorized_write_attempted") is True
                     and replay["before"].get("unauthorized_drafts") == 1
                     and replay["before"].get("attack_success") is True
                     and replay["after"].get("unauthorized_write_attempted") is True
                     and replay["after"].get("unauthorized_drafts") == 0
                     and replay["after"].get("attack_success") is False
                     and "human_denied" in replay["after"].get("guard_blocks", []))
    causal = bool(experiment_source_matches(live.get("hashes"), current)
                  and verified_live_defence(live, live.get("hashes")))
    return {"live_experiment_verified": live_ok, "forced_action_guard_verified": replay_ok,
            "live_guard_causality_verified": causal,
            "requirements_met": live_ok and replay_ok,
            "interpretation": "A completed live attack observation plus a separate before/after authorization test. Model resistance is not attributed to a guard it never reached."}


def valid_completed_run(path, manifest, tasks, current):
    ids = {t["id"] for t in tasks}
    trials = manifest.get("trials")
    if (manifest.get("status") != "complete" or manifest.get("mode") != "live_openrouter"
            or set(manifest.get("configurations", [])) != {"A", "B"}
            or not isinstance(trials, int) or trials < 1
            or manifest.get("task_count") != len(tasks)
            or manifest.get("rows") != len(tasks) * trials * 2
            or manifest.get("task_file_sha256") != current.get("tasks.jsonl")
            or not experiment_source_matches(manifest.get("hashes"), current)):
        return False
    expected = {(task, trial) for task in ids for trial in range(1, trials + 1)}
    try:
        for config in ("A", "B"):
            with (path / f"eval_{config}.csv").open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            if len(rows) != len(expected) or {(r["task_id"], int(r["trial"])) for r in rows} != expected:
                return False
            for row in rows:
                transcript = (path / row["transcript"]).resolve()
                if (row["config"] != config or row["passed"] not in {"True", "False"}
                        or row["stopped"] in {"provider_error", "unexpected_provider_cost", "cost_budget", "not_run"}
                        or not transcript.is_relative_to(path.resolve()) or not transcript.is_file()):
                    return False
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    tasks = load_tasks(ROOT / "tasks.jsonl")
    current = hashes()
    local = ROOT / "results/local/tests.xml"
    local_ok, local_count = False, 0
    if local.exists():
        suites = ET.parse(local).getroot().findall("testsuite")
        local_count = sum(int(s.attrib.get("tests", 0)) for s in suites)
        local_ok = local_count > 0 and all(int(s.attrib.get("failures", 0)) + int(s.attrib.get("errors", 0)) == 0 for s in suites)
    verification_path = ROOT / "results/local/verification.json"
    verification = json.loads(verification_path.read_text()) if verification_path.exists() else {}
    local_ok = local_ok and verification.get("passed") is True and verification.get("hashes") == current
    complete = []
    for path in sorted((ROOT / "results/live").glob("*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if valid_completed_run(path.parent, manifest, tasks, current):
            complete.append(str(path.parent.relative_to(ROOT)))
    reports = {}
    for mode in ("live", "replay"):
        path = ROOT / "results" / ("security_" + mode) / "report.json"
        reports[mode] = json.loads(path.read_text()) if path.exists() else {}
    security = security_evidence(reports["live"], reports["replay"], current)
    analysis_done = "PENDING_LIVE_EVALUATION" not in (ROOT / "docs/error_analysis.md").read_text(encoding="utf-8")
    report = {
        "local_contracts": {"passed": local_ok, "test_count": local_count, "evidence": "results/local/tests.xml"},
        "tools_and_mcp": "implemented; see real MCP integration tests and doctor output",
        "context_and_limits": "implemented; see finder/agent.py and runtime tests",
        "human_write_approval": "implemented; see approval tests, live eval approval cases and replay traces",
        "eval_tasks": len(tasks),
        "live_ab": {"complete_current_experiment_source_runs": complete, "verified": bool(complete)},
        "security_evidence": security,
        "root_cause_analysis": {"pending_marker_removed": analysis_done, "human_review_required": True},
        "source_binding": {"excluded_read_only_review_files": sorted(EVIDENCE_REVIEW_FILES),
                           "note": "All runtime, prompts, tools, data, graders, evaluation runners and dependency hashes must match. Original full manifests remain unchanged. Local tests require exact current hashes."},
        "presentation": "excluded by project owner's cohort instructions; still present in published rubric",
        "final_submission_ready": bool(local_ok and complete and security["requirements_met"] and analysis_done),
        "note": "Technical evidence checklist, not a guarantee of passing. Manually review actual scores, analysis, model rationale and cohort submission rules. Live guard causality is reported independently; it is not inferred from a failed injection."
    }
    (ROOT / "results/requirements_status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.require_live and not report["final_submission_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
