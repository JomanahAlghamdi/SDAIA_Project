from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import platform
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from finder.agent import Agent
from finder.catalog import Catalog, ROOT, load_student
from finder.harness import Harness, Trace
from finder.mcp_client import CatalogBridge
from finder.models import Student
from finder.provider import OpenRouter, ProviderError
from finder.storage import DraftStore
from evals.graders import grade


def load_tasks(path: Path):
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(tasks) < 15 or len({x["id"] for x in tasks}) != len(tasks):
        raise ValueError("At least 15 unique task IDs are required")
    if any(not x["turns"] or not x.get("expect") for x in tasks):
        raise ValueError("Each task needs turns and golden assertions")
    return tasks


def hashes():
    paths = [ROOT / "tasks.jsonl", ROOT / "data/opportunities.json", ROOT / "data/students.json",
             ROOT / "prompts/system.md", ROOT / "prompts/config_b.txt", ROOT / "uv.lock",
             ROOT / "pyproject.toml", ROOT / "app.py", ROOT / "mcp_server.py"]
    for directory in ("finder", "evals", "scripts", "tests"):
        paths += sorted((ROOT / directory).glob("*.py"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


async def evaluate(args):
    tasks = load_tasks(args.tasks)
    args.out.mkdir(parents=True, exist_ok=True)
    # Each invocation creates a new directory. Never silently overwrites or mixes releases.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = args.out / (stamp + "-" + str(time.time_ns())[-6:])
    out.mkdir()
    manifest = {"status": "not_started", "mode": "live_openrouter", "configurations": args.config,
                "task_count": len(tasks), "trials": args.trials, "python": platform.python_version(),
                "hashes": hashes(), "rows": 0, "cache": "no application response cache", "approval": "explicit per-task simulated human decisions; isolated synthetic DB"}
    def write_manifest():
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_manifest()
    rows = []
    try:
        async with OpenRouter() as provider:
            manifest.update(status="running", requested_model=provider.model)
            write_manifest()
            # Interleave A/B within each task/trial to reduce order/time confounds.
            async with CatalogBridge(date(2026, 10, 27)) as bridge:
                for trial in range(args.trials):
                    for task in tasks:
                        for config in args.config:
                            started = time.monotonic()
                            with tempfile.TemporaryDirectory(prefix="if-eval-") as tmp:
                                store = DraftStore(Path(tmp) / "test.sqlite")
                                try:
                                    raw = load_student(task["student"]).model_dump(mode="json")
                                    raw.update(task.get("profile_overrides", {}))
                                    approved = set(task.get("approved_opportunity_ids", []))
                                    trace = Trace(out / "traces" / f"{task['id']}-{config}-{trial}.jsonl")
                                    harness = Harness(Student.model_validate(raw), Catalog(), bridge, store,
                                        approve=lambda preview: preview["opportunity_id"] in approved,
                                        today=date.fromisoformat(task["as_of"]), trace=trace)
                                    agent = Agent(harness, provider, config)
                                    runs = []
                                    for prompt in task["turns"]:
                                        runs.append(await agent.run(prompt))
                                        if runs[-1].stopped != "completed":
                                            break
                                    checks = grade(task, runs, harness)
                                    failures = [c["grader"] for c in checks if not c["passed"]]
                                    row = {"config": config, "task_id": task["id"], "category": task["category"],
                                           "trial": trial + 1, "passed": not failures, "failed_graders": ";".join(failures),
                                           "stopped": runs[-1].stopped if runs else "not_run",
                                           "requests": sum(r.requests for r in runs),
                                           "tokens": sum(r.prompt_tokens + r.completion_tokens for r in runs),
                                           "cost_usd": sum(r.cost_usd for r in runs),
                                           "seconds": round(time.monotonic() - started, 3),
                                           "effective_models": ";".join(sorted({m for r in runs for m in r.models}))}
                                    rows.append(row)
                                    with (out / f"eval_{config}.csv").open("a", newline="", encoding="utf-8") as f:
                                        writer = csv.DictWriter(f, fieldnames=list(row))
                                        if f.tell() == 0:
                                            writer.writeheader()
                                        writer.writerow(row)
                                    (out / "traces" / f"{task['id']}-{config}-{trial}-transcript.json").write_text(
                                        json.dumps({"graders": checks, "turns": [r.transcript for r in runs]}, ensure_ascii=False, indent=2), encoding="utf-8")
                                    manifest["rows"] = len(rows)
                                    write_manifest()
                                    print(f"{config} trial={trial + 1} {task['id']}: {'PASS' if row['passed'] else 'FAIL ' + row['failed_graders']}", flush=True)
                                    if row["stopped"] == "provider_error":
                                        raise ProviderError("Provider failure during evaluation. Partial results retained; rerun explicitly when service/quota recovers.")
                                finally:
                                    store.close()
            manifest["status"] = "complete"
    except ProviderError as exc:
        manifest["status"] = "blocked" if not rows else "incomplete"
        manifest["reason"] = str(exc)
        write_manifest()
        print(f"Evaluation {manifest['status']}: {exc}\nManifest: {out / 'manifest.json'}", file=sys.stderr)
        return 2
    write_manifest()
    summarize(rows, out, args.trials)
    print("Actual live results:", out)
    return 0


def summarize(rows, out, trials):
    configs = sorted({r["config"] for r in rows})
    lines = ["# Actual live evaluation results", "", f"Trials per task/config: {trials}. No application response cache.", "",
             "| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |",
             "|---|---:|---:|---:|---:|"]
    errors = {}
    for config in configs:
        group = [r for r in rows if r["config"] == config]
        ids = {r["task_id"] for r in group}
        all_pass = sum(all(r["passed"] for r in group if r["task_id"] == task_id) for task_id in ids)
        n = len(group)
        lines.append(f"| {config} | {sum(r['passed'] for r in group)/n:.1%} | {all_pass/len(ids):.1%} | {sum(r['requests'] for r in group)/n:.2f} | {sum(r['tokens'] for r in group)/n:.1f} |")
        for r in group:
            for failure in filter(None, r["failed_graders"].split(";")):
                errors[(config, failure)] = errors.get((config, failure), 0) + 1
    lines += ["", "## Error analysis", "", "These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.", "",
              "| Config | Failed assertion | Count |", "|---|---|---:|"]
    lines += [f"| {c} | {reason} | {count} |" for (c, reason), count in sorted(errors.items())]
    if set(configs) == {"A", "B"}:
        lines += ["", "## Tasks that changed between configurations", "", "| Task | A observed pass rate | B observed pass rate |", "|---|---:|---:|"]
        for task_id in sorted({r["task_id"] for r in rows}):
            rates = {c: sum(r["passed"] for r in rows if r["task_id"] == task_id and r["config"] == c) / trials for c in configs}
            if rates["A"] != rates["B"]:
                lines.append(f"| {task_id} | {rates['A']:.1%} | {rates['B']:.1%} |")
    lines += ["", "With k=1, pass^k equals one-trial performance and does not establish repeated reliability.",
              "No statistical significance claim is made. Examine regressions as well as improvements."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=ROOT / "tasks.jsonl")
    parser.add_argument("--config", nargs="+", choices=["A", "B"], default=["A", "B"])
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", type=Path, default=ROOT / "results/live")
    args = parser.parse_args()
    if args.trials < 1 or len(set(args.config)) != len(args.config):
        parser.error("Trials must be positive and configurations unique")
    return asyncio.run(evaluate(args))


if __name__ == "__main__":
    raise SystemExit(main())
