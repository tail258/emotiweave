from __future__ import annotations

import math
from dataclasses import dataclass

from sentientbot.affect.calibration import CalibrationProfile
from sentientbot.models import AffectLabel, AffectState, VisualEvidence, clamp


def label_for(
    valence: float,
    arousal: float,
    confidence: float,
) -> AffectLabel:
    if confidence < 0.22:
        return AffectLabel.UNKNOWN
    if abs(valence) < 0.18 and abs(arousal) < 0.22:
        return AffectLabel.NEUTRAL
    if valence >= 0.18:
        return AffectLabel.EXCITED if arousal >= 0.28 else AffectLabel.POSITIVE
    if valence <= -0.18:
        return AffectLabel.TENSE if arousal >= 0.24 else AffectLabel.LOW
    return AffectLabel.CALM if arousal < -0.15 else AffectLabel.NEUTRAL


@dataclass(slots=True)
class _LabelCandidate:
    label: AffectLabel = AffectLabel.UNKNOWN
    count: int = 0


class AffectTracker:
    """将帧级证据平滑为可过期状态。"""

    def __init__(
        self,
        calibration: CalibrationProfile,
        half_life_seconds: float = 0.75,
        stale_after_seconds: float = 1.5,
        label_hold_frames: int = 3,
    ) -> None:
        self.calibration = calibration
        self.half_life_seconds = max(0.05, half_life_seconds)
        self.stale_after_ms = max(100, int(stale_after_seconds * 1000))
        self.label_hold_frames = max(1, label_hold_frames)
        self._last_timestamp_ms: int | None = None
        self._last_seen_ms: int | None = None
        self._valence = 0.0
        self._arousal = 0.0
        self._stability = 0.0
        self._confidence = 0.0
        self._label = AffectLabel.UNKNOWN
        self._candidate = _LabelCandidate()

    def update(self, evidence: VisualEvidence) -> AffectState:
        timestamp_ms = evidence.timestamp_ms
        if not evidence.face_present:
            return self.tick(timestamp_ms)

        self.calibration.observe(evidence)
        evidence = self.calibration.calibrate(evidence)
        previous_valence = self._valence
        previous_arousal = self._arousal

        if self._last_timestamp_ms is None:
            alpha = 1.0
        else:
            dt = max(0.001, (timestamp_ms - self._last_timestamp_ms) / 1000)
            alpha = 1.0 - math.exp(-math.log(2.0) * dt / self.half_life_seconds)

        self._valence += alpha * (evidence.valence - self._valence)
        self._arousal += alpha * (evidence.arousal - self._arousal)
        movement = abs(self._valence - previous_valence) + abs(self._arousal - previous_arousal)
        instant_stability = clamp(1.0 - movement * 2.5, 0.0, 1.0)
        self._stability = (
            instant_stability
            if self._last_timestamp_ms is None
            else 0.82 * self._stability + 0.18 * instant_stability
        )
        self._confidence = clamp(
            evidence.confidence * (0.72 + 0.28 * self._stability),
            0.0,
            1.0,
        )
        self._last_timestamp_ms = timestamp_ms
        self._last_seen_ms = timestamp_ms
        self._update_label()
        return self._state(timestamp_ms, age_ms=0)

    def tick(self, timestamp_ms: int) -> AffectState:
        self._last_timestamp_ms = timestamp_ms
        if self._last_seen_ms is None:
            self._confidence = 0.0
            self._label = AffectLabel.UNKNOWN
            return self._state(timestamp_ms, age_ms=0)

        age_ms = max(0, timestamp_ms - self._last_seen_ms)
        if age_ms >= self.stale_after_ms:
            self._confidence = 0.0
            self._stability = 0.0
            self._label = AffectLabel.UNKNOWN
            self._candidate = _LabelCandidate()
        else:
            decay = math.exp(-3.0 * age_ms / self.stale_after_ms)
            self._confidence = clamp(self._confidence * decay, 0.0, 1.0)
            self._update_label()
        return self._state(timestamp_ms, age_ms=age_ms)

    def apply_bias_delta(self, valence_delta: float, arousal_delta: float = 0.0) -> None:
        self._valence = clamp(self._valence + valence_delta)
        self._arousal = clamp(self._arousal + arousal_delta)
        self._update_label(force=True)

    def reset(self) -> None:
        self._last_timestamp_ms = None
        self._last_seen_ms = None
        self._valence = 0.0
        self._arousal = 0.0
        self._stability = 0.0
        self._confidence = 0.0
        self._label = AffectLabel.UNKNOWN
        self._candidate = _LabelCandidate()

    def _update_label(self, force: bool = False) -> None:
        candidate = label_for(self._valence, self._arousal, self._confidence)
        if force or self._label is AffectLabel.UNKNOWN:
            self._label = candidate
            self._candidate = _LabelCandidate()
            return
        if candidate == self._label:
            self._candidate = _LabelCandidate()
            return
        if candidate == self._candidate.label:
            self._candidate.count += 1
        else:
            self._candidate = _LabelCandidate(candidate, 1)
        if self._candidate.count >= self.label_hold_frames:
            self._label = candidate
            self._candidate = _LabelCandidate()

    def _state(self, timestamp_ms: int, age_ms: int) -> AffectState:
        reason = (
            "未检测到有效人脸"
            if self._label is AffectLabel.UNKNOWN
            else "已进行个人基线校准与时间平滑"
        )
        return AffectState(
            timestamp_ms=timestamp_ms,
            valence=self._valence,
            arousal=self._arousal,
            confidence=self._confidence,
            stability=self._stability,
            label=self._label,
            age_ms=age_ms,
            sources=("vision",) if self._confidence > 0 else (),
            reason=reason,
        )
