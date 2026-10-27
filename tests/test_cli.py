from types import SimpleNamespace

import pytest

import app
from finder.provider import ProviderError


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
