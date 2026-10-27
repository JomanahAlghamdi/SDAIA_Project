from datetime import date

import pytest
from pydantic import ValidationError

from finder.catalog import Catalog, check_eligibility, load_student
from finder.models import OpportunityArgs, SearchArgs, Student
from evals.run import load_tasks
from finder.catalog import ROOT

TODAY = date(2026, 10, 27)


@pytest.mark.parametrize("student,opportunity,status,reason", [
    ("S001", "OP001", "eligible", None),
    ("S001", "OP002", "eligible", None),
    ("S003", "OP003", "eligible", None),
    ("S002", "OP005", "eligible", None),
    ("S001", "OP005", "ineligible", "major_mismatch"),
    ("S001", "OP006", "ineligible", "gpa_mismatch"),
    ("S001", "OP007", "ineligible", "opportunity_closed"),
    ("S003", "OP008", "ineligible", "deadline_passed"),
    ("S001", "OP009", "ineligible", "required_months_mismatch"),
    ("S004", "OP001", "ineligible", "available_from_mismatch"),
    ("S001", "OP022", "ineligible", "start_date_passed"),
    ("S005", "OP001", "needs_info", "major"),
    ("S006", "OP001", "ineligible", "year_mismatch"),
])
def test_eligibility_golden_cases(student, opportunity, status, reason):
    result = check_eligibility(load_student(student), Catalog().get(opportunity), TODAY)
    assert result["status"] == status
    if reason:
        assert reason in result["failures"] + result["missing"]


@pytest.mark.parametrize("field", ["major", "year", "gpa", "training_kind", "required_months", "available_from"])
def test_missing_fields_are_not_assumed(field):
    student = load_student("S001")
    setattr(student, field, None)
    result = check_eligibility(student, Catalog().get("OP001"), TODAY)
    assert result["status"] == "needs_info"
    assert field in result["missing"]


def test_exact_filters_and_pagination():
    catalog = Catalog()
    page = catalog.search(SearchArgs(field="Data", cities=["Riyadh"], kind="coop", limit=1), TODAY)
    ids = []
    while True:
        ids.extend(x["id"] for x in page["opportunities"])
        if page["next_offset"] is None:
            break
        page = catalog.search(SearchArgs(field="Data", cities=["Riyadh"], kind="coop", limit=1,
                                         offset=page["next_offset"]), TODAY)
    assert set(ids) == {"OP001", "OP006", "OP030"}
    assert len(ids) == len(set(ids))


def test_empty_search_does_not_relax_city():
    assert Catalog().search(SearchArgs(field="Data", cities=["Makkah"], kind="coop"), TODAY)["total"] == 0


def test_deadline_today_is_open_but_tomorrow_expires():
    catalog = Catalog()
    ids_today = {x["id"] for x in catalog.search(SearchArgs(field="Cybersecurity", limit=10), TODAY)["opportunities"]}
    ids_tomorrow = {x["id"] for x in catalog.search(SearchArgs(field="Cybersecurity", limit=10), date(2026, 10, 28))["opportunities"]}
    assert "OP029" in ids_today and "OP029" not in ids_tomorrow


@pytest.mark.parametrize("payload", [{"opportunity_id": "OP001", "approved": True},
                                    {"opportunity_id": "OP001", "student_id": "S002"},
                                    {"opportunity_id": "../../secret"}])
def test_tool_schema_rejects_authority_and_paths(payload):
    with pytest.raises(ValidationError):
        OpportunityArgs.model_validate(payload)


@pytest.mark.parametrize("kwargs", [{"gpa": 4.5}, {"year": 0}, {"id": "../../path"}, {"synthetic": False}])
def test_invalid_profiles(kwargs):
    raw = load_student("S001").model_dump(mode="json")
    raw.update(kwargs)
    with pytest.raises(ValidationError):
        Student.model_validate(raw)


def test_optional_gpa_requirement():
    student = load_student("S002")
    student.gpa = None
    assert check_eligibility(student, Catalog().get("OP010"), TODAY)["status"] == "eligible"


def test_fixtures_and_eval_coverage():
    catalog = Catalog()
    assert len(catalog.items) == 30
    assert all(x.synthetic and x.company.startswith("Synthetic") for x in catalog.items.values())
    tasks = load_tasks(ROOT / "tasks.jsonl")
    assert len(tasks) == 20
    assert {t["category"] for t in tasks} == {"search", "missing", "constraints", "approval", "security"}
    assert {t["lang"] for t in tasks} == {"ar", "en"}
