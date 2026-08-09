from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from sentientbot.config import AudioConfig


class WhisperTranscriber:
    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self.available = config.enabled
        self.message = "ASR 将在首次使用时加载"
        self._model: Any = None
        self._lock = threading.Lock()
        if config.enabled:
            try:
                import faster_whisper  # noqa: F401
            except Exception as exc:
                self.available = False
                self.message = f"缺少 faster-whisper：{exc}"
        else:
            self.message = "ASR 已在配置中关闭"

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not self.available:
            raise RuntimeError(self.message)
        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        except Exception:
            if self.config.device != "cuda":
                raise
            self._model = WhisperModel(
                self.config.model_size,
                device="cpu",
                compute_type="int8",
            )
            self.message = "CUDA 初始化失败，已回退 CPU int8"
        else:
            self.message = f"{self.config.model_size} 模型已就绪"
        return self._model

    def transcribe(self, audio_path: str | Path | None) -> str:
        if not audio_path:
            return ""
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"录音文件不存在：{path}")
        with self._lock:
            model = self._ensure_model()
            segments, _ = model.transcribe(
                str(path),
                beam_size=self.config.beam_size,
                language=self.config.language,
                vad_filter=self.config.vad_filter,
            )
            return "".join(segment.text for segment in segments).strip()
