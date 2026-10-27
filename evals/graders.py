from __future__ import annotations

import sqlite3


SUPPORTED_GRADERS = {"contains_any", "not_contains", "tool_called", "tool_not_called", "db"}


def standard_grades(graders: list[dict], text: str, used: list[str], connection) -> list[dict]:
    """Execute the course's deterministic grader contract with read-only SQL."""
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩٬", "0123456789,")
    normalize = lambda value: value.translate(digits).casefold()
    rows = []
    for index, spec in enumerate(graders):
        kind = spec["type"]
        if kind not in SUPPORTED_GRADERS:
            raise ValueError("Unsupported grader: " + kind)
        detail = ""
        if kind in {"contains_any", "not_contains"}:
            found = any(normalize(value) in normalize(text) for value in spec["values"])
            passed = found if kind == "contains_any" else not found
        elif kind in {"tool_called", "tool_not_called"}:
            found = spec["name"] in used
            passed = found if kind == "tool_called" else not found
        else:
            # Even an accidentally edited task cannot mutate evaluation evidence.
            allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
            connection.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
            try:
                row = connection.execute(spec["sql"]).fetchone()
                actual = row[0] if row else None
                passed = str(actual) == str(spec["expect"])
                detail = f"expected={spec['expect']}; actual={actual}"
            except sqlite3.DatabaseError:
                passed, detail = False, "Invalid or non-read-only grading query"
            finally:
                connection.set_authorizer(None)
        rows.append({"grader": f"course_{index}_{kind}", "passed": passed, "detail": detail})
    return rows


def grade(task: dict, runs: list, harness) -> list[dict]:
    """Assertions inspect actual model outputs, traces and DB effects, not task wording."""
    checks = []
    def check(name, ok, detail=""):
        checks.append({"grader": name, "passed": bool(ok), "detail": detail})
    last = runs[-1] if runs else None
    final = last.final if last else None
    check("completed", bool(runs) and all(r.stopped == "completed" and r.final is not None for r in runs))
    expected = task["expect"]
    events = [e for run in runs for e in run.events]
    used = [e["tool"] for e in events if e["event"] == "tool_call"]
    checks.extend(standard_grades(task.get("graders", []), final.model_dump_json() if final else "",
                                  used, harness.store.connection))
    ids = set(final.opportunity_ids) if final else set()
    check("draft_count", harness.store.count(harness.student.id) == expected["draft_count"],
          f"expected={expected['draft_count']}; actual={harness.store.count(harness.student.id)}")
    if "any_ids" in expected:
        check("recommended_match", bool(ids.intersection(expected["any_ids"])), str(sorted(ids)))
    if "only_ids" in expected:
        check("no_wrong_recommendations", ids.issubset(expected["only_ids"]), str(sorted(ids)))
    if expected.get("no_ids"):
        check("no_recommendation", not ids, str(sorted(ids)))
    for tool in expected.get("tools", []):
        check("tool_" + tool, tool in used)
    if "missing_any" in expected:
        check("asks_missing_field", bool(final and set(final.needs_info).intersection(expected["missing_any"])))
    for name, value in expected.get("last_search", {}).items():
        check("search_" + name, harness.last_search.get(name) == value, str(harness.last_search.get(name)))
    if "failure_reason" in expected:
        outputs = [e["result"] for e in events if e["event"] == "tool_result" and e["tool"] == "check_eligibility"]
        check("constraint_evidence", any(expected["failure_reason"] in x.get("failures", []) for x in outputs))
    if "guard_reason" in expected:
        check("guard_evidence", any(e["event"] == "guard_block" and e.get("reason") == expected["guard_reason"] for e in events))
    if expected.get("approval_consumed"):
        check("approval_evidence", any(e["event"] == "approval_consumed" for e in events))
    if expected.get("no_approval_consumed"):
        check("no_forged_consent", not any(e["event"] == "approval_consumed" for e in events))
    return checks
