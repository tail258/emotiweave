from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def ensure_localhost_bypasses_proxy() -> None:
    required = {"127.0.0.1", "localhost", "::1"}
    for variable in ("NO_PROXY", "no_proxy"):
        existing = {
            item.strip() for item in os.environ.get(variable, "").split(",") if item.strip()
        }
        os.environ[variable] = ",".join(sorted(existing | required))


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def _project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(slots=True)
class SystemConfig:
    name: str = "EmotiWeave"
    host: str = "127.0.0.1"
    port: int = 7860
    open_browser: bool = True
    log_level: str = "INFO"


@dataclass(slots=True)
class VisionConfig:
    enabled: bool = True
    model_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "assets/models/face_landmarker.task"
    )
    max_faces: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    stream_every: float = 0.15
    draw_landmarks: bool = True


@dataclass(slots=True)
class AudioConfig:
    enabled: bool = True
    feature_analysis_enabled: bool = True
    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = "zh"
    beam_size: int = 3
    vad_filter: bool = True
    min_duration_seconds: float = 0.35
    max_analysis_seconds: float = 20.0


@dataclass(slots=True)
class BrainConfig:
    enabled: bool = True
    model: str = "qwen2.5:3b"
    host: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 30.0
    warmup_on_start: bool = True
    stream: bool = True
    keep_alive: str = "15m"
    max_history_turns: int = 6
    temperature: float = 0.35


@dataclass(slots=True)
class VoiceConfig:
    enabled: bool = False
    speed: int = 165
    volume: float = 1.0
    language: str = "zh"


@dataclass(slots=True)
class AffectConfig:
    smoothing_half_life: float = 0.75
    stale_after_seconds: float = 1.5
    conflict_threshold: float = 0.65
    vision_valence_weight: float = 1.0
    vision_arousal_weight: float = 1.0
    text_valence_weight: float = 1.0
    text_arousal_weight: float = 1.0
    audio_arousal_weight: float = 1.10
    minimum_modality_confidence: float = 0.05
    conflict_min_confidence: float = 0.42
    conflict_penalty: float = 0.62
    agreement_base: float = 0.78
    agreement_bonus: float = 0.22
    text_hold_seconds: float = 8.0
    audio_hold_seconds: float = 8.0
    calibration_samples: int = 24
    correction_learning_rate: float = 0.22

    def __post_init__(self) -> None:
        for name in (
            "vision_valence_weight",
            "vision_arousal_weight",
            "text_valence_weight",
            "text_arousal_weight",
            "audio_arousal_weight",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        for name in (
            "conflict_threshold",
            "minimum_modality_confidence",
            "conflict_min_confidence",
            "conflict_penalty",
            "agreement_base",
            "agreement_bonus",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.agreement_base + self.agreement_bonus > 1.0:
            raise ValueError("agreement_base + agreement_bonus must be at most 1")
        for name in (
            "smoothing_half_life",
            "stale_after_seconds",
            "text_hold_seconds",
            "audio_hold_seconds",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(slots=True)
class PrivacyConfig:
    log_events: bool = True
    store_transcripts: bool = False
    store_raw_media: bool = False
    log_directory: Path = field(default_factory=lambda: PROJECT_ROOT / "data/sessions")


@dataclass(slots=True)
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    affect: AffectConfig = field(default_factory=AffectConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    ensure_localhost_bypasses_proxy()
    config_path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    system = _section(data, "system")
    vision = _section(data, "vision")
    audio = _section(data, "audio")
    brain = _section(data, "brain")
    voice = _section(data, "voice")
    affect = _section(data, "affect")
    privacy = _section(data, "privacy")

    return AppConfig(
        system=SystemConfig(**system),
        vision=VisionConfig(
            **{
                **vision,
                "model_path": _project_path(
                    vision.get("model_path", "assets/models/face_landmarker.task")
                ),
            }
        ),
        audio=AudioConfig(**audio),
        brain=BrainConfig(**brain),
        voice=VoiceConfig(**voice),
        affect=AffectConfig(**affect),
        privacy=PrivacyConfig(
            **{
                **privacy,
                "log_directory": _project_path(privacy.get("log_directory", "data/sessions")),
            }
        ),
    )
