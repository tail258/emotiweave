from __future__ import annotations

import threading
from typing import Any

from sentientbot.config import VoiceConfig


class Pyttsx3Speaker:
    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self.available = config.enabled
        self.message = "语音播报可在界面中启用" if config.enabled else "语音播报默认关闭"
        self._lock = threading.Lock()
        if config.enabled:
            try:
                import pyttsx3  # noqa: F401
            except Exception as exc:
                self.available = False
                self.message = f"缺少 pyttsx3：{exc}"

    def speak_async(self, text: str) -> None:
        if not self.available or not text.strip():
            return
        thread = threading.Thread(target=self._speak, args=(text,), daemon=True)
        thread.start()

    def _speak(self, text: str) -> None:
        with self._lock:
            engine: Any = None
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.setProperty("rate", self.config.speed)
                engine.setProperty("volume", self.config.volume)
                target_voice = self._find_voice(engine.getProperty("voices"))
                if target_voice:
                    engine.setProperty("voice", target_voice)
                engine.say(text)
                engine.runAndWait()
                self.message = "语音播报完成"
            except Exception as exc:
                self.message = f"语音播报失败：{exc}"
            finally:
                if engine is not None:
                    try:
                        engine.stop()
                    except Exception:
                        pass

    def _find_voice(self, voices: list[Any]) -> str | None:
        keywords = (
            ("chinese", "huihui", "xiaoxiao", "yaoyao")
            if self.config.language == "zh"
            else ("english", "david", "zira")
        )
        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            if any(keyword in name for keyword in keywords):
                return str(voice.id)
        return None
