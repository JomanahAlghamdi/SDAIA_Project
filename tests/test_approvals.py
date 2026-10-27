from datetime import date

import pytest

from finder.catalog import Catalog, load_student
from finder.harness import Harness, Trace
from finder.storage import DraftStore


@pytest.fixture
def store(tmp_path):
    value = DraftStore(tmp_path / "test.sqlite")
    yield value
    value.close()


def harness(store, approve=None):
    return Harness(load_student("S001"), Catalog(), None, store, approve,
                   date(2026, 10, 27), Trace())


@pytest.mark.asyncio
async def test_no_consent_no_write(store):
    h = harness(store)
    result = await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    assert result["status"] == "denied" and store.count() == 0


@pytest.mark.asyncio
async def test_real_host_callback_write_and_duplicate(store):
    previews = []
    def consent(p):
        previews.append(p)
        return True
    h = harness(store, consent)
    first = await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    second = await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    assert first["status"] == "Draft" and first["sent_to_employer"] is False
    assert second["draft_id"] == first["draft_id"] and second["status"] == "existing"
    assert store.count() == 1 and len(previews) == 1
    assert [e["event"] for e in h.trace.events].index("approval_requested") < [e["event"] for e in h.trace.events].index("approval_consumed")


@pytest.mark.asyncio
async def test_no_repeat_pressure_after_denial(store):
    attempts = []
    h = harness(store, lambda preview: attempts.append(preview) or False)
    await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    assert len(attempts) == 1 and store.count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("opportunity", ["OP006", "OP007", "OP008", "OP009", "OP022"])
async def test_eligibility_enforced_even_if_human_would_approve(store, opportunity):
    h = harness(store, lambda _: True)
    result = await h.dispatch("save_application_draft", {"opportunity_id": opportunity})
    assert result["status"] == "blocked" and store.count() == 0
    assert not any(e["event"] == "approval_requested" for e in h.trace.events)


@pytest.mark.asyncio
async def test_missing_profile_prevents_save(store):
    h = harness(store, lambda _: True)
    h.student.gpa = None
    assert (await h.dispatch("save_application_draft", {"opportunity_id": "OP001"}))["status"] == "blocked"
    assert store.count() == 0


@pytest.mark.asyncio
async def test_stale_preview_blocked_after_user_decision(store):
    h = harness(store)
    def stale(preview):
        h.student.gpa = 3.7  # Still eligible, but exact reviewed profile changed.
        return True
    h.approve = stale
    result = await h.dispatch("save_application_draft", {"opportunity_id": "OP001"})
    assert result["status"] == "blocked" and store.count() == 0


@pytest.mark.asyncio
async def test_forged_approval_arg_and_unknown_tool(store):
    h = harness(store, lambda _: True)
    assert (await h.dispatch("save_application_draft", {"opportunity_id": "OP001", "approved": True}))["error"] == "invalid_arguments"
    assert (await h.dispatch("issue_approval", {}))["error"] == "unknown_tool"
    assert store.count() == 0


def test_nonce_replay_expiry_content_and_session_binding(store):
    h = harness(store)
    payload = h.preview("OP001")
    token = store.issue_approval(h.session_id, h.student.id, payload)
    with pytest.raises(PermissionError):
        store.commit(token, "another-session", h.student.id, payload)
    with pytest.raises(PermissionError):
        store.commit(token, h.session_id, h.student.id, {**payload, "title": "Altered"})
    result = store.commit(token, h.session_id, h.student.id, payload)
    assert result["status"] == "Draft"
    with pytest.raises(PermissionError):
        store.commit(token, h.session_id, h.student.id, payload)
    expired = store.issue_approval(h.session_id, h.student.id, payload, ttl=-1)
    with pytest.raises(PermissionError):
        store.commit(expired, h.session_id, h.student.id, payload)
    assert store.count() == 1


def test_no_cross_student_access(store):
    h = harness(store)
    payload = h.preview("OP001")
    token = store.issue_approval(h.session_id, "S001", payload)
    store.commit(token, h.session_id, "S001", payload)
    assert store.existing("S002", "OP001") is None
    assert store.count("S002") == 0
