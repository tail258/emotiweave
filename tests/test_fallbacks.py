import json
from typing import Any

from sentientbot.config import BrainConfig
from sentientbot.dialogue.ollama import OllamaChatClient
from sentientbot.models import (
    AffectState,
    InteractionStrategy,
    ResponsePlan,
)


class FakeResponse:
    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        lines: list[dict[str, Any]] | None = None,
        status_code: int = 200,
    ) -> None:
        self.payload = payload or {}
        self.lines = lines or []
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self.payload

    def iter_lines(self, decode_unicode: bool = False) -> list[str]:
        assert decode_unicode
        return [json.dumps(line, ensure_ascii=False) for line in self.lines]


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.posts: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.posts.append({"url": url, **kwargs})
        return self.responses.pop(0)


def neutral_plan() -> ResponsePlan:
    return ResponsePlan(
        strategy=InteractionStrategy.NEUTRAL,
        allow_emotion_language=False,
        reason="test",
        prompt_context="test",
        fallback_reply="本地降级回复",
    )


def test_disabled_llm_uses_policy_fallback() -> None:
    client = OllamaChatClient(BrainConfig(enabled=False))
    plan = neutral_plan()
    reply, latency = client.chat("你好", AffectState(timestamp_ms=1), plan, [])
    assert reply == "本地降级回复"
    assert latency == 0


def test_disabled_llm_stream_uses_policy_fallback() -> None:
    client = OllamaChatClient(BrainConfig(enabled=False))

    updates = list(client.stream_chat("你好", AffectState(timestamp_ms=1), neutral_plan(), []))

    assert len(updates) == 1
    assert updates[0].text == "本地降级回复"
    assert updates[0].done
    assert updates[0].used_fallback


def test_stream_chat_combines_ndjson_chunks() -> None:
    client = OllamaChatClient(BrainConfig())
    fake = FakeSession(
        [
            FakeResponse(
                lines=[
                    {"message": {"content": "你"}, "done": False},
                    {"message": {"content": "好"}, "done": False},
                    {"message": {"content": ""}, "done": True},
                ]
            )
        ]
    )
    client._session = fake

    updates = list(client.stream_chat("你好", AffectState(timestamp_ms=1), neutral_plan(), []))

    assert [update.text for update in updates] == ["你", "你好", "你好"]
    assert updates[-1].done
    assert updates[-1].first_token_seconds is not None
    assert fake.posts[0]["stream"] is True
    assert fake.posts[0]["json"]["stream"] is True
    assert "format" not in fake.posts[0]["json"]


def test_warmup_preloads_model_and_keeps_it_alive() -> None:
    config = BrainConfig(model="test-model", keep_alive="20m")
    client = OllamaChatClient(config)
    fake = FakeSession([FakeResponse(payload={"done": True})])
    client._session = fake

    assert client.warmup()

    request = fake.posts[0]
    assert request["url"].endswith("/api/generate")
    assert request["json"] == {
        "model": "test-model",
        "prompt": "",
        "stream": False,
        "keep_alive": "20m",
    }
    assert client.message == "Ollama 已就绪：test-model"


def test_stream_can_be_disabled_without_breaking_chat() -> None:
    client = OllamaChatClient(BrainConfig(stream=False))
    fake = FakeSession([FakeResponse(payload={"message": {"content": '{"reply":"同步回复"}'}})])
    client._session = fake

    updates = list(client.stream_chat("你好", AffectState(timestamp_ms=1), neutral_plan(), []))

    assert len(updates) == 1
    assert updates[0].text == "同步回复"
    assert updates[0].done
    assert fake.posts[0]["json"]["stream"] is False
