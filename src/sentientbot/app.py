from __future__ import annotations

import importlib.util
import time
from collections.abc import Iterator
from typing import Any

from sentientbot.config import AppConfig
from sentientbot.dialogue import OllamaChatClient, Pyttsx3Speaker
from sentientbot.models import AffectState, VisualEvidence
from sentientbot.perception import AudioCueAnalyzer, MediaPipeFaceAnalyzer, WhisperTranscriber
from sentientbot.session import SessionController
from sentientbot.storage import SessionLogger


class SentientApplication:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = SessionController(
            config.affect,
            max_history_turns=config.brain.max_history_turns,
        )
        self.vision = MediaPipeFaceAnalyzer(config.vision)
        self.transcriber = WhisperTranscriber(config.audio)
        self.audio_cues = AudioCueAnalyzer(config.audio)
        self.brain = OllamaChatClient(config.brain)
        self.speaker = Pyttsx3Speaker(config.voice)
        self.logger = SessionLogger(config.privacy)
        self.last_error = ""

    def process_frame(self, frame_rgb: Any) -> tuple[Any, AffectState, dict[str, Any]]:
        timestamp_ms = time.monotonic_ns() // 1_000_000
        if frame_rgb is None:
            return None, self.session.fused_state, {}

        try:
            cv2 = __import__("cv2")
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            evidence, annotated_bgr = self.vision.analyze(frame_bgr, timestamp_ms)
            state = self.session.observe(evidence)
            annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
            return annotated_rgb, state, evidence.cues
        except Exception as exc:
            self.last_error = f"视觉处理失败：{exc}"
            evidence = VisualEvidence(timestamp_ms, False)
            state = self.session.observe(evidence)
            return frame_rgb, state, {}

    def handle_turn(
        self,
        text: str,
        audio_path: str | None = None,
        speak: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] | None = None
        for update in self.stream_turn(text, audio_path, speak):
            result = update
        if result is not None:
            return result
        return {
            "ok": False,
            "user_text": "",
            "reply": "",
            "error": "对话未产生结果。",
            "state": self.session.fused_state,
            "plan": None,
            "done": True,
        }

    def stream_turn(
        self,
        text: str,
        audio_path: str | None = None,
        speak: bool = False,
    ) -> Iterator[dict[str, Any]]:
        user_text = text.strip()
        audio_evidence = None
        if not user_text and audio_path:
            try:
                user_text = self.transcriber.transcribe(audio_path)
            except Exception as exc:
                self.last_error = f"语音识别失败：{exc}"
                yield {
                    "ok": False,
                    "user_text": "",
                    "reply": "",
                    "error": self.last_error,
                    "state": self.session.fused_state,
                    "plan": None,
                    "done": True,
                }
                return
        if audio_path:
            try:
                audio_evidence = self.audio_cues.analyze(audio_path, user_text)
            except Exception as exc:
                self.last_error = f"韵律分析已跳过：{exc}"
        if not user_text:
            yield {
                "ok": False,
                "user_text": "",
                "reply": "",
                "error": "请输入文字或录制一段语音。",
                "state": self.session.fused_state,
                "plan": None,
                "done": True,
            }
            return

        state, plan = self.session.process_text(user_text, audio_evidence)
        history = self.session.history_messages()
        yield {
            "ok": True,
            "user_text": user_text,
            "reply": "",
            "error": "",
            "state": state,
            "plan": plan,
            "latency": 0.0,
            "first_token_latency": None,
            "audio_evidence": audio_evidence,
            "done": False,
        }

        final_update = None
        for update in self.brain.stream_chat(user_text, state, plan, history):
            final_update = update
            if not update.done:
                yield {
                    "ok": True,
                    "user_text": user_text,
                    "reply": update.text,
                    "error": "",
                    "state": state,
                    "plan": plan,
                    "latency": update.elapsed_seconds,
                    "first_token_latency": update.first_token_seconds,
                    "audio_evidence": audio_evidence,
                    "done": False,
                }

        if final_update is None:
            reply = plan.fallback_reply
            latency = 0.0
            first_token_latency = 0.0
        else:
            reply = final_update.text
            latency = final_update.elapsed_seconds
            first_token_latency = final_update.first_token_seconds

        self.session.record_turn(user_text, reply, state, plan, latency)
        if speak:
            self.speaker.speak_async(reply)

        payload = {
            "strategy": plan.strategy.value,
            "latency_seconds": round(latency, 3),
            "first_token_seconds": (
                round(first_token_latency, 3) if first_token_latency is not None else None
            ),
            "sources": list(state.sources),
            "conflicts": list(state.conflicts),
        }
        if audio_evidence is not None:
            payload["audio_features"] = {
                key: round(value, 4) for key, value in audio_evidence.features.items()
            }
        if self.config.privacy.store_transcripts:
            payload.update({"user": user_text, "assistant": reply})
        self.logger.write("conversation_turn", state, payload)
        yield {
            "ok": True,
            "user_text": user_text,
            "reply": reply,
            "error": "",
            "state": state,
            "plan": plan,
            "latency": latency,
            "first_token_latency": first_token_latency,
            "audio_evidence": audio_evidence,
            "done": True,
        }

    def correct(self, kind: str) -> AffectState:
        state = self.session.apply_correction(kind)
        self.logger.write(
            "user_correction",
            state,
            {"kind": kind, "note": self.session.last_correction},
        )
        return state

    def reset(self) -> None:
        self.session.reset()
        self.last_error = ""

    def health(self, ping_ollama: bool = True) -> dict[str, Any]:
        dependencies = {
            name: bool(importlib.util.find_spec(name))
            for name in (
                "cv2",
                "numpy",
                "mediapipe",
                "gradio",
                "plotly",
                "faster_whisper",
                "requests",
                "yaml",
                "pyttsx3",
            )
        }
        ollama_reachable = self.brain.ping() if ping_ollama else None
        return {
            "application": self.config.system.name,
            "hardware_layer": "removed",
            "dependencies": dependencies,
            "vision": {
                "available": self.vision.available,
                "backend": self.vision.backend,
                "message": self.vision.message,
                "model_path": str(self.config.vision.model_path),
            },
            "asr": {
                "available": self.transcriber.available,
                "message": self.transcriber.message,
            },
            "audio_cues": {
                "available": self.audio_cues.available,
                "message": self.audio_cues.message,
            },
            "ollama": {
                "reachable": ollama_reachable,
                "message": self.brain.message,
            },
            "tts": {
                "available": self.speaker.available,
                "message": self.speaker.message,
            },
            "privacy": {
                "store_raw_media": self.config.privacy.store_raw_media,
                "store_transcripts": self.config.privacy.store_transcripts,
            },
        }
