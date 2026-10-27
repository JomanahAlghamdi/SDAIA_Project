import httpx
import pytest

from finder.provider import OpenRouter, ProviderError


def test_missing_key_fails_without_network(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="missing"):
        OpenRouter()


@pytest.mark.asyncio
async def test_provider_payload_and_usage():
    def respond(request):
        import json
        body = json.loads(request.content)
        assert body["provider"]["max_price"] == {"prompt": 0, "completion": 0}
        assert body["model"] == "test/model:free"
        assert body["temperature"] == 0 and body["stream"] is False
        return httpx.Response(200, json={"model": "test/model:free", "choices": [{"message": {"content": "{}"}}],
                                        "usage": {"prompt_tokens": 20, "completion_tokens": 5, "cost": 0}})
    provider = OpenRouter(key="synthetic-test-key", model="test/model:free")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider.client = client
        result = await provider.complete([], [])
        assert result.prompt_tokens == 20 and result.completion_tokens == 5 and result.cost_usd == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body", [(429, {"error": "secret must not be echoed"}),
                                        (200, {"choices": [{"message": {"content": "hello"}}]})])
async def test_provider_errors_never_invent_usage_or_echo_body(status, body):
    provider = OpenRouter(key="synthetic-test-key", model="test/model:free")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status, json=body))) as client:
        provider.client = client
        with pytest.raises(ProviderError) as exc:
            await provider.complete([], [])
        assert "secret" not in str(exc.value) and "synthetic-test-key" not in str(exc.value)
