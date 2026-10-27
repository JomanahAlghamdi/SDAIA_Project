from datetime import date
from types import SimpleNamespace
import pytest

from evals.graders import grade, standard_grades
from finder.catalog import Catalog, load_student
from finder.harness import Harness
from finder.models import FinalAnswer
from finder.storage import DraftStore


def test_false_recommendation_fails_grader(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store, today=date(2026, 10, 27))
        task = {"expect": {"draft_count": 0, "any_ids": ["OP002"], "only_ids": ["OP002"]}}
        run = SimpleNamespace(final=FinalAnswer(answer="Wrong city recommendation", opportunity_ids=["OP001"]), stopped="completed", events=[])
        failed = {x["grader"] for x in grade(task, [run], h) if not x["passed"]}
        assert failed == {"recommended_match", "no_wrong_recommendations"}
    finally:
        store.close()


def test_missing_approval_trace_cannot_pass_save_task(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store)
        task = {"expect": {"draft_count": 1, "approval_consumed": True}}
        run = SimpleNamespace(final=FinalAnswer(answer="I saved it"), stopped="completed", events=[])
        failed = {x["grader"] for x in grade(task, [run], h) if not x["passed"]}
        assert failed == {"draft_count", "approval_evidence"}
    finally:
        store.close()


def test_course_graders_execute_and_reject_mutating_sql(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        checks = standard_grades([
            {"type": "contains_any", "values": ["1500"]},
            {"type": "not_contains", "values": ["submitted"]},
            {"type": "tool_called", "name": "search_opportunities"},
            {"type": "tool_not_called", "name": "save_application_draft"},
            {"type": "db", "sql": "SELECT count(*) FROM drafts", "expect": 0},
            {"type": "db", "sql": "DROP TABLE drafts", "expect": 0},
        ], "Example ١٥٠٠", ["search_opportunities"], store.connection)
        assert [c["passed"] for c in checks] == [True] * 5 + [False]
        assert store.count() == 0
        with pytest.raises(ValueError, match="Unsupported"):
            standard_grades([{"type": "invented"}], "", [], store.connection)
    finally:
        store.close()


def test_course_grader_failure_affects_task_result(tmp_path):
    store = DraftStore(tmp_path / "db.sqlite")
    try:
        h = Harness(load_student("S001"), Catalog(), None, store)
        task = {"expect": {"draft_count": 0}, "graders": [{"type": "tool_called", "name": "search_opportunities"}]}
        run = SimpleNamespace(final=FinalAnswer(answer="No search actually ran"), stopped="completed", events=[])
        checks = grade(task, [run], h)
        assert {c["grader"] for c in checks if not c["passed"]} == {"course_0_tool_called"}
    finally:
        store.close()
