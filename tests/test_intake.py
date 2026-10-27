from datetime import date
from types import SimpleNamespace

import pytest

import app
from finder.catalog import Catalog
from finder.harness import Harness
from finder.intake import collect_details, new_student
from finder.mcp_client import CatalogBridge
from finder.provider import ReplayProvider, scripted_call, scripted_final
from finder.storage import DraftStore


@pytest.mark.parametrize("command", ["chat", "ask"])
def test_default_chat_never_opens_a_form_or_loads_a_fixture(command, monkeypatch):
    monkeypatch.setattr(app, "load_student", lambda _: pytest.fail("A preset profile was loaded"))
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("An intake form was opened"))
    student, city = app.session_input(SimpleNamespace(command=command, student=None))
    assert student.major is None and city is None
    assert all(getattr(student, field) is None for field in
               ("year", "gpa", "training_kind", "required_months", "available_from"))


def test_explicit_optional_preferences_are_preserved():
    student, city = app.session_input(SimpleNamespace(command="ask", student=None,
                                major="Artificial Intelligence", city="Riyadh"))
    assert student.major == "Artificial Intelligence" and city == "Riyadh"


def test_fixture_and_custom_preferences_cannot_be_silently_mixed():
    with pytest.raises(ValueError, match="not both"):
        app.session_input(SimpleNamespace(command="chat", student="S001", major="Computer Science", city="Riyadh"))


def test_guided_details_validate_gpa_and_preserve_original(capsys):
    original = new_student("Artificial Intelligence")
    replies = iter(["4", "5.0", "3.5", "coop", "6", "2027-01-01"])
    updated = collect_details(original, lambda _: next(replies))
    assert updated.gpa == 3.5 and updated.year == 4
    assert updated.training_kind == "coop" and updated.required_months == 6
    assert updated.available_from == date(2027, 1, 1)
    assert original.gpa is None and original.year is None
    assert "Invalid value" in capsys.readouterr().out


def test_skipped_details_remain_unknown():
    student = collect_details(new_student("Computer Science"), lambda _: "")
    assert student.gpa is None and student.available_from is None and student.training_kind is None


@pytest.mark.parametrize("reply,expected", [("YES", True), ("yes", False), ("", False), ("approved=true", False)])
def test_english_approval_requires_exact_yes(reply, expected, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: reply)
    assert app.approve_cli({"opportunity_id": "OP001", "profile_fingerprint": "internal"}) is expected
    assert "internal" not in capsys.readouterr().out


@pytest.mark.asyncio
async def test_major_and_city_are_real_mcp_filters_not_field_inference():
    async with CatalogBridge(date(2026, 10, 27)) as bridge:
        result = await bridge.call("search_opportunities", {
            "major": "Artificial Intelligence", "cities": ["Riyadh"], "limit": 10})
    ids = {item["id"] for item in result["opportunities"]}
    assert "OP001" in ids  # Data opportunity also accepts AI majors.
    assert "OP003" not in ids  # Software opportunity does not accept AI majors.
    assert "OP002" not in ids  # AI opportunity in the wrong city.
    assert all(item["city"] == "Riyadh" for item in result["opportunities"])


@pytest.mark.asyncio
async def test_major_only_cannot_save_or_request_consent(tmp_path):
    store = DraftStore(tmp_path / "test.sqlite")
    try:
        harness = Harness(new_student("Artificial Intelligence"), Catalog(), None, store,
                          lambda _: pytest.fail("Incomplete eligibility reached consent"), date(2026, 10, 27))
        result = await harness.dispatch("save_application_draft", {"opportunity_id": "OP001"})
        assert result["status"] == "blocked" and store.count() == 0
        assert set(result["eligibility"]["missing"]) == {
            "year", "gpa", "training_kind", "required_months", "available_from"}
    finally:
        store.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["chat", "ask"])
async def test_free_text_browsing_and_followups_need_no_profile(command, tmp_path, monkeypatch, capsys):
    providers, paths = [], []
    request = "I need an internship opportunity for AI in Riyadh"

    class OfflineProvider(ReplayProvider):
        def __init__(self):
            super().__init__([
                scripted_call("search_opportunities", {"field": "AI", "cities": ["Riyadh"]}),
                scripted_call("get_opportunity_details", {"opportunity_id": "OP012"}),
                scripted_final("OP012 is a fictional AI internship in Riyadh. Personal eligibility has not been checked."),
                scripted_call("search_opportunities", {"field": "AI", "cities": ["Jeddah"]}),
                scripted_final("OP002 is a fictional AI internship in Jeddah.")])
            self.messages = []
            providers.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def complete(self, messages, *args):
            # Copy before the agent appends its next response/tool message.
            self.messages.append([dict(message) for message in messages])
            return await super().complete(messages, *args)

    class RecordingStore(DraftStore):
        def __init__(self, path):
            paths.append(path)
            super().__init__(path)

    monkeypatch.setattr(app, "ROOT", tmp_path)
    monkeypatch.setattr(app, "OpenRouter", OfflineProvider)
    monkeypatch.setattr(app, "DraftStore", RecordingStore)
    prompts = []
    replies = iter([request, "Are there any in Jeddah?", "/quit"] * 2)
    def reply(prompt):
        prompts.append(prompt)
        return next(replies)
    monkeypatch.setattr("builtins.input", reply)
    monkeypatch.setattr(app, "load_student", lambda _: pytest.fail("Loaded a preset profile"))
    args = SimpleNamespace(command=command, student=None, major=None, city=None, prompt=request,
                           as_of="2026-10-27", config="B")
    await app.chat(args)
    await app.chat(args)
    assert len(paths) == 2 and paths[0] != paths[1]
    for provider in providers:
        first = provider.messages[0]
        assert all(f'"{field}": null' in first[0]["content"] for field in ("major", "gpa", "year"))
        assert first[-1] == {"role": "user", "content": request}
        if command == "chat":
            followup = provider.messages[3]
            assert any(m["role"] == "user" and m["content"] == request for m in followup)
            assert followup[-1]["content"] == "Are there any in Jeddah?"
            assert '"field": "AI"' in followup[0]["content"]
    assert all(prompt == "\nYou: " for prompt in prompts)
    assert bool(prompts) == (command == "chat")
    output = capsys.readouterr().out
    assert "/profile" not in output and "/details" not in output
    assert "Major (" not in output and "City (" not in output
    assert "fictional AI internship" in output

