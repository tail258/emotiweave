from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


class AffectLabel(StrEnum):
    UNKNOWN = "unknown"
    NEUTRAL = "neutral"
    CALM = "calm"
    POSITIVE = "positive"
    EXCITED = "excited"
    LOW = "low"
    TENSE = "tense"


class InteractionStrategy(StrEnum):
    NEUTRAL = "neutral"
    MIRROR_POSITIVE = "mirror_positive"
    SUPPORT = "support"
    CLARIFY_CONFLICT = "clarify_conflict"
    INVITE_CORRECTION = "invite_correction"


@dataclass(slots=True)
class VisualEvidence:
    timestamp_ms: int
    face_present: bool
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0
    cues: dict[str, float] = field(default_factory=dict)
    source: str = "vision"

    def __post_init__(self) -> None:
        self.valence = clamp(self.valence)
        self.arousal = clamp(self.arousal)
        self.confidence = clamp(self.confidence, 0.0, 1.0)


@dataclass(slots=True)
class TextEvidence:
    text: str
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0
    matched_terms: tuple[str, ...] = ()
    source: str = "text"

    def __post_init__(self) -> None:
        self.valence = clamp(self.valence)
        self.arousal = clamp(self.arousal)
        self.confidence = clamp(self.confidence, 0.0, 1.0)


@dataclass(slots=True)
class AudioEvidence:
    """保存可解释的语音韵律证据。"""

    timestamp_ms: int
    duration_seconds: float = 0.0
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0
    features: dict[str, float] = field(default_factory=dict)
    source: str = "audio"

    def __post_init__(self) -> None:
        self.duration_seconds = max(0.0, float(self.duration_seconds))
        self.valence = clamp(self.valence)
        self.arousal = clamp(self.arousal)
        self.confidence = clamp(self.confidence, 0.0, 1.0)


@dataclass(slots=True)
class AffectState:
    timestamp_ms: int
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0
    stability: float = 0.0
    conflict: bool = False
    label: AffectLabel = AffectLabel.UNKNOWN
    age_ms: int = 0
    sources: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        self.valence = clamp(self.valence)
        self.arousal = clamp(self.arousal)
        self.confidence = clamp(self.confidence, 0.0, 1.0)
        self.stability = clamp(self.stability, 0.0, 1.0)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["label"] = self.label.value
        return data


@dataclass(slots=True)
class ResponsePlan:
    strategy: InteractionStrategy
    allow_emotion_language: bool
    reason: str
    prompt_context: str
    fallback_reply: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data


@dataclass(slots=True)
class UserCorrection:
    kind: str
    target_valence: float | None
    target_arousal: float | None = None
    note: str = ""


@dataclass(slots=True)
class ConversationTurn:
    user: str
    assistant: str
    state: AffectState
    plan: ResponsePlan
    latency_seconds: float
