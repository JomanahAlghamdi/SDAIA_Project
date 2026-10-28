import json
from types import SimpleNamespace

import pytest

from evals import run as suite
from finder.provider import Completion, ProviderError, scripted_final


@pytest.mark.asyncio
async def test_resume_retains_behavioral_failures_and_retries_only_interruption(tmp_path, monkeypatch):
    class FakeProvider:
        model = "synthetic-test-model"
        total = 0
        fail_once = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def complete(self, *args):
            type(self).total += 1
            if self.fail_once and self.total == 3:
                type(self).fail_once = False
                raise ProviderError("synthetic quota interruption")
            return Completion(scripted_final("Synthetic test answer"), 0, 0, 0, self.model)

    monkeypatch.setattr(suite, "OpenRouter", FakeProvider)
    monkeypatch.setenv("OPENROUTER_MODEL", FakeProvider.model)
    args = SimpleNamespace(tasks=suite.ROOT / "tasks.jsonl", out=tmp_path, resume=None, config=["A", "B"], trials=1)
    assert await suite.evaluate(args) == 2
    out = next(tmp_path.iterdir())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["rows"] == 2 and len(manifest["provider_interruptions"]) == 1
    assert manifest["effective_limits"]["max_total_tokens"] == 32000
    tasks = suite.load_tasks(args.tasks)
    with pytest.raises(ValueError, match="matching"):
        suite.resume_state(out, args.config, 1, tasks, manifest["task_file_sha256"], "different-model")
    with monkeypatch.context() as ctx:
        ctx.setattr(suite, "hashes", lambda: {"changed": "source"})
        with pytest.raises(ValueError, match="matching"):
            suite.resume_state(out, args.config, 1, tasks, manifest["task_file_sha256"], FakeProvider.model)
    with monkeypatch.context() as ctx:
        ctx.setenv("IF_MAX_REQUEST_TOKENS", "48000")
        with pytest.raises(ValueError, match="matching"):
            suite.resume_state(out, args.config, 1, tasks, manifest["task_file_sha256"], FakeProvider.model)
    args.resume = out
    assert await suite.evaluate(args) == 0
    complete = json.loads((out / "manifest.json").read_text())
    assert complete["status"] == "complete" and complete["rows"] == len(tasks) * 2
    assert FakeProvider.total == 2 * sum(len(t["turns"]) for t in tasks) + 1
    assert len(complete["attempts"]) == 2 and len(complete["provider_interruptions"]) == 1
    assert (out / "summary.md").exists()
