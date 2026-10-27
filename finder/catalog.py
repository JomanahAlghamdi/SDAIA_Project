from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import Opportunity, SearchArgs, Student

ROOT = Path(__file__).resolve().parents[1]


class Catalog:
    def __init__(self, path: Path | None = None):
        records = json.loads((path or ROOT / "data/opportunities.json").read_text(encoding="utf-8"))
        parsed = [Opportunity.model_validate(x) for x in records]
        self.items = {x.id: x for x in parsed}
        if len(self.items) != len(parsed):
            raise ValueError("Duplicate opportunity IDs")

    def get(self, opportunity_id: str) -> Opportunity:
        if opportunity_id not in self.items:
            raise ValueError("Unknown opportunity ID")
        return self.items[opportunity_id]

    def search(self, criteria: SearchArgs, today: date) -> dict:
        results = []
        for item in self.items.values():
            if item.status != "open" or item.deadline < today or item.start_date < today:
                continue
            if criteria.field and item.field != criteria.field:
                continue
            if criteria.cities and item.city not in criteria.cities:
                continue
            if criteria.kind and item.kind != criteria.kind:
                continue
            if criteria.mode and item.mode != criteria.mode:
                continue
            if criteria.duration_months and item.duration_months != criteria.duration_months:
                continue
            results.append(item)
        results.sort(key=lambda x: (x.deadline, x.id))
        page = results[criteria.offset:criteria.offset + criteria.limit]
        return {"synthetic": True, "as_of": today.isoformat(), "total": len(results),
                "offset": criteria.offset, "next_offset": criteria.offset + len(page) if criteria.offset + len(page) < len(results) else None,
                "opportunities": [{k: v for k, v in x.model_dump(mode="json").items()
                                  if k not in {"description", "accepted_majors", "min_year", "min_gpa"}}
                                 for x in page]}


def load_student(student_id: str) -> Student:
    for obj in json.loads((ROOT / "data/students.json").read_text(encoding="utf-8")):
        if obj["id"] == student_id:
            return Student.model_validate(obj)
    raise ValueError("Unknown student. Choose S001 through S006.")


def check_eligibility(student: Student, item: Opportunity, today: date) -> dict:
    failures, missing, passed = [], [], []
    if item.status != "open":
        failures.append("opportunity_closed")
    if item.deadline < today:
        failures.append("deadline_passed")
    if item.start_date < today:
        failures.append("start_date_passed")
    checks = {
        "major": lambda v: v in item.accepted_majors,
        "year": lambda v: v >= item.min_year,
        "training_kind": lambda v: v == item.kind,
        "required_months": lambda v: v == item.duration_months,
        "available_from": lambda v: v <= item.start_date,
    }
    if item.min_gpa is not None:
        checks["gpa"] = lambda v: v >= item.min_gpa
    for name, test in checks.items():
        value = getattr(student, name)
        if value is None:
            missing.append(name)
        elif test(value):
            passed.append(name)
        else:
            failures.append(name + "_mismatch")
    status = "ineligible" if failures else "needs_info" if missing else "eligible"
    return {"opportunity_id": item.id, "status": status, "passed": passed,
            "failures": failures, "missing": missing,
            "notice": "Preliminary match to synthetic published requirements; not employer acceptance."}
