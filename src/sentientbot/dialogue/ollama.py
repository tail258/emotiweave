from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from sentientbot.config import BrainConfig
from sentientbot.models import AffectState, ResponsePlan


@dataclass(frozen=True, slots=True)
class ChatStreamUpdate:
    text: str
    first_token_seconds: float | None
    elapsed_seconds: float
    done: bool
    used_fallback: bool = False


class OllamaChatClient:
    REPLY_SCHEMA = {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": "给用户的简短中文回答，不超过两句话",
            }
        },
        "required": ["reply"],
    }

    def __init__(self, config: BrainConfig) -> None:
        self.config = config
        self.available = config.enabled
        self.message = "Ollama 尚未检查"
        self.detail = ""
        self._reachable: bool | None = None
        self._retry_after = 0.0
        self._session: Any = None
        self._warmup_lock = threading.Lock()
        self._warmup_started = False
        self._warming_up = False
        if config.enabled:
            try:
                import requests

                self._session = requests.Session()
            except Exception as exc:
                self.available = False
                self.message = f"缺少 requests：{exc}"
        else:
            self.message = "LLM 已在配置中关闭"

    @property
    def warming_up(self) -> bool:
        return self._warming_up

    def _messages(
        self,
        user_text: str,
        state: AffectState,
        plan: ResponsePlan,
        history: list[dict[str, str]],
        *,
        plain_text: bool,
    ) -> list[dict[str, str]]:
        output_rule = (
            "只输出给用户的正文，不输出 JSON、标题、前缀或思考过程。"
            if plain_text
            else "按指定结构输出回答。"
        )
        system_prompt = (
            "你是 Sentient，一个本地运行的对话助手。"
            "回答使用中文，不超过两句话。不能诊断心理状态，不能声称读懂真实情绪，"
            "不能把表情当作事实；只围绕用户主动表达的内容交流。"
            f"{output_rule}"
            f"\n当前交互策略：{plan.prompt_context}"
            f"\n可观察状态（仅供调整语气）：效价 {state.valence:+.2f}，"
            f"激活度 {state.arousal:+.2f}，可信度 {state.confidence:.2f}。"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        return messages

    def _can_request(self) -> bool:
        if not self.available or self._session is None:
            return False
        return self._reachable is not False or time.monotonic() >= self._retry_after

    def _mark_ready(self) -> None:
        self._reachable = True
        self.detail = ""
        self.message = f"Ollama 已就绪：{self.config.model}"

    def _mark_failed(self, exc: Exception) -> None:
        self.detail = str(exc)
        self._reachable = False
        self._retry_after = time.monotonic() + 60.0
        self.message = "Ollama 未连接，已使用策略层降级回复"

    def chat(
        self,
        user_text: str,
        state: AffectState,
        plan: ResponsePlan,
        history: list[dict[str, str]],
    ) -> tuple[str, float]:
        if not self._can_request():
            return plan.fallback_reply, 0.0

        payload = {
            "model": self.config.model,
            "messages": self._messages(user_text, state, plan, history, plain_text=False),
            "stream": False,
            "format": self.REPLY_SCHEMA,
            "keep_alive": self.config.keep_alive,
            "options": {"temperature": self.config.temperature},
        }

        start = time.perf_counter()
        try:
            response = self._session.post(
                f"{self.config.host.rstrip('/')}/api/chat",
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            if response.status_code == 400:
                payload.pop("format", None)
                response = self._session.post(
                    f"{self.config.host.rstrip('/')}/api/chat",
                    json=payload,
                    timeout=self.config.timeout_seconds,
                )
            response.raise_for_status()
            content = response.json()["message"]["content"].strip()
            try:
                parsed = json.loads(content)
                reply = str(parsed.get("reply", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                reply = content
            self._mark_ready()
            return reply or plan.fallback_reply, time.perf_counter() - start
        except Exception as exc:
            self._mark_failed(exc)
            return plan.fallback_reply, time.perf_counter() - start

    def stream_chat(
        self,
        user_text: str,
        state: AffectState,
        plan: ResponsePlan,
        history: list[dict[str, str]],
    ) -> Iterator[ChatStreamUpdate]:
        if not self.config.stream:
            reply, latency = self.chat(user_text, state, plan, history)
            yield ChatStreamUpdate(reply, latency, latency, True, reply == plan.fallback_reply)
            return
        if not self._can_request():
            yield ChatStreamUpdate(plan.fallback_reply, 0.0, 0.0, True, True)
            return

        payload = {
            "model": self.config.model,
            "messages": self._messages(user_text, state, plan, history, plain_text=True),
            "stream": True,
            "keep_alive": self.config.keep_alive,
            "options": {"temperature": self.config.temperature},
        }
        start = time.perf_counter()
        first_token_seconds: float | None = None
        full_text = ""

        try:
            response = self._session.post(
                f"{self.config.host.rstrip('/')}/api/chat",
                json=payload,
                stream=True,
                timeout=(min(3.0, self.config.timeout_seconds), self.config.timeout_seconds),
            )
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                chunk = json.loads(raw_line)
                content = str(chunk.get("message", {}).get("content", ""))
                if content:
                    full_text += content
                    if first_token_seconds is None:
                        first_token_seconds = time.perf_counter() - start
                    if not chunk.get("done", False):
                        yield ChatStreamUpdate(
                            full_text,
                            first_token_seconds,
                            time.perf_counter() - start,
                            False,
                        )
                if chunk.get("done", False):
                    break

            elapsed = time.perf_counter() - start
            reply = full_text.strip() or plan.fallback_reply
            self._mark_ready()
            yield ChatStreamUpdate(
                reply,
                first_token_seconds if first_token_seconds is not None else elapsed,
                elapsed,
                True,
                not full_text.strip(),
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            self._mark_failed(exc)
            if full_text.strip():
                yield ChatStreamUpdate(
                    full_text.strip(),
                    first_token_seconds,
                    elapsed,
                    True,
                )
            else:
                yield ChatStreamUpdate(
                    plan.fallback_reply,
                    first_token_seconds,
                    elapsed,
                    True,
                    True,
                )

    def warmup(self) -> bool:
        if not self.available or self._session is None:
            return False
        self._warming_up = True
        self.message = f"Ollama 正在预热：{self.config.model}"
        try:
            response = self._session.post(
                f"{self.config.host.rstrip('/')}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": self.config.keep_alive,
                },
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            self._mark_ready()
            return True
        except Exception as exc:
            self._mark_failed(exc)
            return False
        finally:
            self._warming_up = False

    def start_warmup(self) -> bool:
        if not self.config.warmup_on_start or not self.available:
            return False
        with self._warmup_lock:
            if self._warmup_started:
                return False
            self._warmup_started = True
            self._warming_up = True
        threading.Thread(
            target=self.warmup,
            name="ollama-warmup",
            daemon=True,
        ).start()
        return True

    def ping(self) -> bool:
        if not self.available or self._session is None:
            return False
        try:
            response = self._session.get(
                f"{self.config.host.rstrip('/')}/api/tags",
                timeout=min(2.0, self.config.timeout_seconds),
            )
            response.raise_for_status()
            models = {item.get("name", "") for item in response.json().get("models", [])}
            if self.config.model in models:
                self.message = f"Ollama 已连接：{self.config.model}"
            else:
                self.message = (
                    f"Ollama 已连接，但未发现 {self.config.model}；"
                    f"可运行 ollama pull {self.config.model}"
                )
            self._reachable = True
            return True
        except Exception as exc:
            self._mark_failed(exc)
            return False
