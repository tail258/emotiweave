from __future__ import annotations

from dataclasses import dataclass, field

from sentientbot.models import UserCorrection, VisualEvidence, clamp


@dataclass(slots=True)
class CalibrationProfile:
    """维护会话内中性基线与纠正偏置。"""

    target_samples: int = 24
    learning_rate: float = 0.22
    sample_count: int = 0
    baseline_valence: float = 0.0
    baseline_arousal: float = 0.0
    valence_bias: float = 0.0
    arousal_bias: float = 0.0
    cue_baselines: dict[str, float] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.sample_count >= self.target_samples

    @property
    def progress(self) -> float:
        if self.target_samples <= 0:
            return 1.0
        return min(1.0, self.sample_count / self.target_samples)

    def observe(self, evidence: VisualEvidence) -> None:
        if (
            not evidence.face_present
            or evidence.confidence < 0.4
            or self.sample_count >= self.target_samples
        ):
            return

        self.sample_count += 1
        rate = 1.0 / self.sample_count
        self.baseline_valence += rate * (evidence.valence - self.baseline_valence)
        self.baseline_arousal += rate * (evidence.arousal - self.baseline_arousal)
        for name, value in evidence.cues.items():
            previous = self.cue_baselines.get(name, value)
            self.cue_baselines[name] = previous + rate * (value - previous)

    def calibrate(self, evidence: VisualEvidence) -> VisualEvidence:
        if not evidence.face_present:
            return evidence
        baseline_weight = min(1.0, self.progress * 1.2)
        return VisualEvidence(
            timestamp_ms=evidence.timestamp_ms,
            face_present=True,
            valence=clamp(
                evidence.valence - self.baseline_valence * baseline_weight + self.valence_bias
            ),
            arousal=clamp(
                evidence.arousal - self.baseline_arousal * baseline_weight + self.arousal_bias
            ),
            confidence=evidence.confidence,
            cues=evidence.cues,
            source=evidence.source,
        )

    def apply_correction(
        self,
        correction: UserCorrection,
        current_valence: float,
        current_arousal: float,
    ) -> None:
        if correction.target_valence is not None:
            delta = correction.target_valence - current_valence
            self.valence_bias = clamp(
                self.valence_bias + self.learning_rate * delta,
                -0.55,
                0.55,
            )
        if correction.target_arousal is not None:
            delta = correction.target_arousal - current_arousal
            self.arousal_bias = clamp(
                self.arousal_bias + self.learning_rate * delta,
                -0.45,
                0.45,
            )

    def reset(self) -> None:
        self.sample_count = 0
        self.baseline_valence = 0.0
        self.baseline_arousal = 0.0
        self.valence_bias = 0.0
        self.arousal_bias = 0.0
        self.cue_baselines.clear()
