from datetime import date
from types import SimpleNamespace

from evals.graders import grade
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
