from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from sentientbot.models import (
    AffectLabel,
    AffectState,
    AudioEvidence,
    TextEvidence,
    VisualEvidence,
)

ALLOWED_CONFLICTS = {
    "vision_text_valence",
    "vision_audio_arousal",
    "text_audio_arousal",
}
TARGET_LABELS = {
    AffectLabel.NEUTRAL,
    AffectLabel.CALM,
    AffectLabel.POSITIVE,
    AffectLabel.EXCITED,
    AffectLabel.LOW,
    AffectLabel.TENSE,
}


def _number(value: Any, name: str, low: float, high: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return result


def _relative_path(value: Any, base_dir: Path, name: str) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(str(value))
    if path.is_absolute():
        raise ValueError(f"{name} must be relative to the manifest")
    root = base_dir.resolve()
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{name} escapes the manifest directory") from exc
    return path


def _path_value(path: Path | None, base_dir: Path) -> str | None:
    if path is None:
        return None
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class EvaluationTarget:
    valence: float
    arousal: float
    label: AffectLabel

    def __post_init__(self) -> None:
        object.__setattr__(self, "valence", _number(self.valence, "target.valence", -1.0, 1.0))
        object.__setattr__(self, "arousal", _number(self.arousal, "target.arousal", -1.0, 1.0))
        label = self.label if isinstance(self.label, AffectLabel) else AffectLabel(str(self.label))
        if label not in TARGET_LABELS:
            raise ValueError("target.label must be a known evaluation label")
        object.__setattr__(self, "label", label)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "label": self.label.value,
        }


@dataclass(frozen=True, slots=True)
class EvidenceOverride:
    visual: VisualEvidence
    text: TextEvidence | None = None
    audio: AudioEvidence | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceOverride:
        visual_data = data.get("visual")
        if not isinstance(visual_data, dict):
            raise ValueError("evidence_override.visual is required")
        text_data = data.get("text")
        audio_data = data.get("audio")
        return cls(
            visual=VisualEvidence(**visual_data),
            text=TextEvidence(**text_data) if isinstance(text_data, dict) else None,
            audio=AudioEvidence(**audio_data) if isinstance(audio_data, dict) else None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "visual": asdict(self.visual),
            "text": asdict(self.text) if self.text else None,
            "audio": asdict(self.audio) if self.audio else None,
        }


@dataclass(frozen=True, slots=True)
class EvaluationSample:
    scenario_id: str
    split: Literal["dev", "test", "scripted"]
    sample_kind: Literal["participant", "scripted"]
    target: EvaluationTarget
    expected_conflicts: tuple[str, ...]
    transcript: str = ""
    video_path: Path | None = None
    audio_path: Path | None = None
    evidence_override: EvidenceOverride | None = None
    consent_recorded: bool = False
    participant_group: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path) -> EvaluationSample:
        if not isinstance(data, dict):
            raise ValueError("each dataset row must be an object")
        scenario_id = str(data.get("scenario_id", "")).strip()
        if not scenario_id:
            raise ValueError("scenario_id is required")
        split = str(data.get("split", ""))
        if split not in {"dev", "test", "scripted"}:
            raise ValueError("split must be dev, test, or scripted")
        sample_kind = str(data.get("sample_kind", ""))
        if sample_kind not in {"participant", "scripted"}:
            raise ValueError("sample_kind must be participant or scripted")
        if sample_kind == "scripted" and split != "scripted":
            raise ValueError("scripted samples must use the scripted split")
        if sample_kind == "participant" and split == "scripted":
            raise ValueError("participant samples cannot use the scripted split")

        target_data = data.get("target")
        if not isinstance(target_data, dict):
            raise ValueError("target is required")
        target = EvaluationTarget(
            valence=target_data.get("valence"),
            arousal=target_data.get("arousal"),
            label=target_data.get("label"),
        )
        conflicts = tuple(str(item) for item in data.get("expected_conflicts", []))
        invalid_conflicts = set(conflicts) - ALLOWED_CONFLICTS
        if invalid_conflicts:
            raise ValueError(f"unknown conflict names: {sorted(invalid_conflicts)}")
        transcript = str(data.get("transcript", ""))
        video_path = _relative_path(data.get("video_path"), base_dir, "video_path")
        audio_path = _relative_path(data.get("audio_path"), base_dir, "audio_path")
        override_data = data.get("evidence_override")
        override = (
            EvidenceOverride.from_dict(override_data) if isinstance(override_data, dict) else None
        )
        consent = bool(data.get("consent_recorded", False))
        participant_group = str(data.get("participant_group", "")).strip() or None

        if sample_kind == "participant" and not consent:
            raise ValueError("participant samples require consent_recorded=true")
        if sample_kind == "scripted" and override is None:
            raise ValueError("scripted samples require evidence_override")
        if sample_kind == "participant" and not any(
            (transcript.strip(), video_path, audio_path, override)
        ):
            raise ValueError("participant samples require at least one input modality")

        return cls(
            scenario_id=scenario_id,
            split=split,  # type: ignore[arg-type]
            sample_kind=sample_kind,  # type: ignore[arg-type]
            target=target,
            expected_conflicts=conflicts,
            transcript=transcript,
            video_path=video_path,
            audio_path=audio_path,
            evidence_override=override,
            consent_recorded=consent,
            participant_group=participant_group,
        )

    def as_dict(self, base_dir: Path) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "split": self.split,
            "sample_kind": self.sample_kind,
            "participant_group": self.participant_group,
            "consent_recorded": self.consent_recorded,
            "target": self.target.as_dict(),
            "expected_conflicts": list(self.expected_conflicts),
            "transcript": self.transcript,
            "video_path": _path_value(self.video_path, base_dir),
            "audio_path": _path_value(self.audio_path, base_dir),
            "evidence_override": self.evidence_override.as_dict()
            if self.evidence_override
            else None,
        }


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    sample: EvaluationSample
    visual_state: AffectState
    text_evidence: TextEvidence | None
    audio_evidence: AudioEvidence | None
    metadata: dict[str, Any]


def _state_from_dict(data: dict[str, Any]) -> AffectState:
    return AffectState(
        timestamp_ms=int(data.get("timestamp_ms", 0)),
        valence=float(data.get("valence", 0.0)),
        arousal=float(data.get("arousal", 0.0)),
        confidence=float(data.get("confidence", 0.0)),
        stability=float(data.get("stability", 0.0)),
        conflict=bool(data.get("conflict", False)),
        label=AffectLabel(str(data.get("label", AffectLabel.UNKNOWN.value))),
        age_ms=int(data.get("age_ms", 0)),
        sources=tuple(data.get("sources", ())),
        conflicts=tuple(data.get("conflicts", ())),
        reason=str(data.get("reason", "")),
    )


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    scenario_id: str
    split: str
    target: EvaluationTarget
    prediction: AffectState | None
    expected_conflicts: tuple[str, ...]
    config_fingerprint: str
    sample_kind: str
    metadata: dict[str, Any]
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "split": self.split,
            "target": self.target.as_dict(),
            "prediction": self.prediction.as_dict() if self.prediction else None,
            "expected_conflicts": list(self.expected_conflicts),
            "config_fingerprint": self.config_fingerprint,
            "sample_kind": self.sample_kind,
            "metadata": self.metadata,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PredictionRecord:
        target_data = data.get("target", {})
        return cls(
            scenario_id=str(data["scenario_id"]),
            split=str(data["split"]),
            target=EvaluationTarget(
                valence=target_data["valence"],
                arousal=target_data["arousal"],
                label=target_data["label"],
            ),
            prediction=_state_from_dict(data["prediction"]) if data.get("prediction") else None,
            expected_conflicts=tuple(data.get("expected_conflicts", ())),
            config_fingerprint=str(data.get("config_fingerprint", "")),
            sample_kind=str(data.get("sample_kind", "participant")),
            metadata=dict(data.get("metadata", {})),
            error=str(data["error"]) if data.get("error") else None,
        )
