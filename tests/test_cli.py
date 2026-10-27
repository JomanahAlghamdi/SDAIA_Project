from types import SimpleNamespace

import pytest

import app
from finder.provider import ProviderError
from finder.agent import Run


def test_failed_final_still_reports_a_committed_draft(capsys):
    run = Run(stopped="token_budget", requests=4, prompt_tokens=12000, completion_tokens=600,
              events=[{"event": "tool_result", "tool": "save_application_draft",
                       "result": {"status": "Draft", "opportunity_id": "OP001", "draft_id": "DRAFT-TEST"}}])
    app.show_run(run)
    output = capsys.readouterr().out
    assert "token limit" in output and "tokens=12600" in output
    assert "Local draft result: Draft OP001 DRAFT-TEST" in output
    assert "No application sent" in output


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", ["", "/help", "/details"])
async def test_ask_rejects_empty_or_interactive_commands_instead_of_looping(prompt):
    with pytest.raises(ValueError, match="ask needs"):
        await app.chat(SimpleNamespace(command="ask", prompt=prompt))


@pytest.mark.asyncio
async def test_ask_reports_failure_with_nonzero_status(tmp_path, monkeypatch):
    class UnavailableProvider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def complete(self, *args):
            raise ProviderError("Unavailable test model")

    monkeypatch.setattr(app, "ROOT", tmp_path)
    monkeypatch.setattr(app, "OpenRouter", UnavailableProvider)
    args = SimpleNamespace(command="ask", prompt="Check OP001", as_of="2026-10-27", student="S001", config="B")
    assert await app.chat(args) == 2
