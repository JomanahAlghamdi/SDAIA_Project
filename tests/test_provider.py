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
@pytest.mark.parametrize("mandatory,expected", [(False, {"enabled": True, "max_tokens": 1024}), (True, {"enabled": True, "max_tokens": 1024})])
async def test_reasoning_control_keeps_room_for_tool_use(monkeypatch, mandatory, expected):
    async def metadata():
        return [{"id": "test/model:free", "supported_parameters": ["tools", "reasoning"],
                 "reasoning": {"mandatory": mandatory}}]
    monkeypatch.setattr("finder.provider.free_tool_models", metadata)
    async with OpenRouter(key="synthetic-test-key", model="test/model:free") as provider:
        assert provider.reasoning_options == expected


@pytest.mark.asyncio
async def test_provider_records_truncation_and_reasoning_usage():
    def respond(request):
        import json
        assert json.loads(request.content)["reasoning"] == {"enabled": False}
        return httpx.Response(200, json={"model": "test/model:free",
            "choices": [{"message": {"content": ""}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 2000, "completion_tokens": 900, "cost": 0,
                      "completion_tokens_details": {"reasoning_tokens": 900}}})
    provider = OpenRouter(key="synthetic-test-key", model="test/model:free")
    provider.reasoning_options = {"enabled": False}
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider.client = client
        result = await provider.complete([], [])
        assert result.finish_reason == "length" and result.reasoning_tokens == 900
        assert result.completion_tokens == 900


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


@pytest.mark.asyncio
@pytest.mark.parametrize("message,category", [
    ("free-models-per-day quota reached", "daily account quota"),
    ("temporarily rate-limited upstream", "upstream model capacity"),
    ("requests per minute exceeded", "per-minute request limit"),
])
async def test_rate_limit_category_without_raw_error_disclosure(message, category):
    provider = OpenRouter(key="synthetic-test-key", model="test/model:free")
    payload = {"error": {"message": message + " private-provider-detail"}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429, json=payload))) as client:
        provider.client = client
        with pytest.raises(ProviderError) as exc:
            await provider.complete([], [])
        assert category in str(exc.value) and "private-provider-detail" not in str(exc.value)
