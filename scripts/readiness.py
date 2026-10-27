"""Report evidence honestly; never treats local tests as a live-model eval."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    tasks = load_tasks(ROOT / "tasks.jsonl")
    local = ROOT / "results/local/tests.xml"
    local_ok = False
    local_count = 0
    if local.exists():
        suites = ET.parse(local).getroot().findall("testsuite")
        local_count = sum(int(s.attrib.get("tests", 0)) for s in suites)
        local_ok = local_count > 0 and all(int(s.attrib.get("failures", 0)) + int(s.attrib.get("errors", 0)) == 0 for s in suites)
    verification_path = ROOT / "results/local/verification.json"
    verification = json.loads(verification_path.read_text()) if verification_path.exists() else {}
    local_ok = local_ok and verification.get("passed") is True and verification.get("hashes") == hashes()
    complete = []
    for path in sorted((ROOT / "results/live").glob("*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete" or manifest.get("mode") != "live_openrouter" or set(manifest.get("configurations", [])) != {"A", "B"}:
            continue
        if manifest.get("hashes") != hashes():
            continue
        valid = True
        for config in ("A", "B"):
            csv_path = path.parent / f"eval_{config}.csv"
            if not csv_path.exists():
                valid = False
                continue
            with csv_path.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            valid &= len(rows) == len(tasks) * manifest["trials"]
            valid &= {r["task_id"] for r in rows} == {t["id"] for t in tasks}
        if valid:
            complete.append(str(path.parent.relative_to(ROOT)))
    security_file = ROOT / "results/security_live/report.json"
    security = json.loads(security_file.read_text()) if security_file.exists() else {}
    security_ok = (security.get("llm_used") is True and security.get("before", {}).get("attack_success") is True
                   and security.get("after", {}).get("attack_success") is False
                   and security.get("after", {}).get("stopped") == "completed"
                   and security.get("benign_control", {}).get("saved_with_explicit_test_human_consent") is True)
    analysis_done = "PENDING_LIVE_EVALUATION" not in (ROOT / "docs/error_analysis.md").read_text(encoding="utf-8")
    report = {
        "local_contracts": {"passed": local_ok, "test_count": local_count, "evidence": "results/local/tests.xml"},
        "tools_and_mcp": "implemented; see real MCP integration tests and doctor output",
        "context_and_limits": "implemented; see finder/agent.py and runtime tests",
        "human_write_approval": "implemented; see approval tests and replay traces",
        "eval_tasks": len(tasks),
        "live_ab": {"complete_current_source_runs": complete, "verified": bool(complete)},
        "live_attack_before_after": {"verified": security_ok, "evidence": str(security_file.relative_to(ROOT)) if security_file.exists() else None},
        "root_cause_analysis": {"pending_marker_removed": analysis_done, "human_review_required": True},
        "presentation": "excluded by project owner's cohort instructions; still present in published rubric",
        "final_submission_ready": bool(local_ok and complete and security_ok and analysis_done),
        "note": "Readiness is an evidence checklist, not a guarantee of passing. Review model rationale, actual README scores, analysis and cohort submission rules manually."
    }
    (ROOT / "results/requirements_status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.require_live and not report["final_submission_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
