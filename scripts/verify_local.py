"""Repeatable local validation. No model key is required or used."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.run import hashes  # noqa: E402


def main():
    out = ROOT / "results/local"
    out.mkdir(parents=True, exist_ok=True)
    commands = [
        ("pytest", [sys.executable, "-m", "pytest", "-q", "--junitxml=results/local/tests.xml"]),
        ("doctor", [sys.executable, "app.py", "doctor"]),
        ("security_replay", [sys.executable, "-m", "evals.security", "--mode", "replay"]),
        ("compile", [sys.executable, "-m", "compileall", "-q", "finder", "evals", "scripts", "tests", "app.py", "mcp_server.py"]),
    ]
    results = []
    for label, command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
        (out / (label + ".txt")).write_text(result.stdout + result.stderr, encoding="utf-8")
        results.append({"check": label, "exit_code": result.returncode})
        print(label + ": " + ("PASS" if result.returncode == 0 else "FAIL"), flush=True)
        if result.returncode:
            print(result.stdout + result.stderr)
            break
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "mode": "local_contracts_no_llm",
              "passed": len(results) == len(commands) and all(r["exit_code"] == 0 for r in results),
              "checks": results, "hashes": hashes()}
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
