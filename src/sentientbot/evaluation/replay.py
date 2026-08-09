from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sentientbot.affect.calibration import CalibrationProfile
from sentientbot.affect.fusion import AffectFusion
from sentientbot.affect.tracker import AffectTracker
from sentientbot.config import AppConfig
from sentientbot.evaluation.schema import (
    EvaluationSample,
    EvidenceSnapshot,
    PredictionRecord,
)
from sentientbot.models import AffectState, AudioEvidence, TextEvidence
from sentientbot.perception.audio_cues import AudioCueAnalyzer
from sentientbot.perception.mediapipe_face import MediaPipeFaceAnalyzer
from sentientbot.perception.text_cues import TextCueAnalyzer

FrameReader = Callable[[Path, float], Iterable[tuple[Any, int]]]


def _config_fingerprint(config: AppConfig) -> str:
    payload = json.dumps(asdict(config.affect), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _default_frame_reader(path: Path, stream_every: float) -> Iterable[tuple[Any, int]]:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"video cannot be opened: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0.0:
        capture.release()
        raise ValueError(f"video has no valid FPS: {path}")
    stride = max(1, round(fps * max(stream_every, 0.01)))
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride == 0:
                timestamp_ms = max(1, round(frame_index * 1000.0 / fps))
                yield frame, timestamp_ms
            frame_index += 1
    finally:
        capture.release()


class ReplayRunner:
    def __init__(
        self,
        config: AppConfig,
        *,
        face_analyzer: Any | None = None,
        audio_analyzer: Any | None = None,
        frame_reader: FrameReader | None = None,
    ) -> None:
        self.config = config
        self.face_analyzer = face_analyzer or MediaPipeFaceAnalyzer(config.vision)
        self.audio_analyzer = audio_analyzer or AudioCueAnalyzer(config.audio)
        self.text_analyzer = TextCueAnalyzer()
        self.frame_reader = frame_reader or _default_frame_reader
        self.config_fingerprint = _config_fingerprint(config)

    def extract(self, sample: EvaluationSample) -> EvidenceSnapshot:
        if sample.evidence_override is not None:
            visual_state = AffectState(
                timestamp_ms=sample.evidence_override.visual.timestamp_ms,
                valence=sample.evidence_override.visual.valence,
                arousal=sample.evidence_override.visual.arousal,
                confidence=sample.evidence_override.visual.confidence,
                sources=("vision",) if sample.evidence_override.visual.face_present else (),
                reason="脚本证据覆盖",
            )
            return EvidenceSnapshot(
                sample=sample,
                visual_state=visual_state,
                text_evidence=sample.evidence_override.text,
                audio_evidence=sample.evidence_override.audio,
                metadata={"source": "evidence_override", "frame_count": 0},
            )

        visual_state = AffectState(timestamp_ms=time.monotonic_ns() // 1_000_000)
        frame_count = 0
        if sample.video_path is not None:
            tracker = AffectTracker(
                calibration=CalibrationProfile(
                    target_samples=self.config.affect.calibration_samples,
                    learning_rate=self.config.affect.correction_learning_rate,
                ),
                half_life_seconds=self.config.affect.smoothing_half_life,
                stale_after_seconds=self.config.affect.stale_after_seconds,
            )
            for frame, timestamp_ms in self.frame_reader(
                sample.video_path,
                self.config.vision.stream_every,
            ):
                evidence, _ = self.face_analyzer.analyze(frame, timestamp_ms)
                visual_state = tracker.update(evidence)
                frame_count += 1

        timestamp_ms = visual_state.timestamp_ms
        text_evidence: TextEvidence | None = (
            self.text_analyzer.analyze(sample.transcript) if sample.transcript.strip() else None
        )
        audio_evidence: AudioEvidence | None = None
        if sample.audio_path is not None:
            audio_evidence = self.audio_analyzer.analyze(
                sample.audio_path,
                transcript=sample.transcript,
                timestamp_ms=timestamp_ms,
            )
        return EvidenceSnapshot(
            sample=sample,
            visual_state=visual_state,
            text_evidence=text_evidence,
            audio_evidence=audio_evidence,
            metadata={
                "source": "media",
                "frame_count": frame_count,
                "face_backend": getattr(self.face_analyzer, "backend", "unknown"),
                "audio_backend": getattr(self.audio_analyzer, "message", "unknown"),
            },
        )

    def run(self, sample: EvaluationSample) -> PredictionRecord:
        snapshot = self.extract(sample)
        prediction = AffectFusion.from_config(self.config.affect).fuse(
            snapshot.visual_state,
            snapshot.text_evidence,
            snapshot.visual_state.timestamp_ms,
            audio=snapshot.audio_evidence,
        )
        return PredictionRecord(
            scenario_id=sample.scenario_id,
            split=sample.split,
            target=sample.target,
            prediction=prediction,
            expected_conflicts=sample.expected_conflicts,
            config_fingerprint=self.config_fingerprint,
            sample_kind=sample.sample_kind,
            metadata=snapshot.metadata,
        )


def extract_evidence(
    samples: Sequence[EvaluationSample], config: AppConfig
) -> list[EvidenceSnapshot]:
    runner = ReplayRunner(config)
    return [runner.extract(sample) for sample in samples]


def replay_dataset(
    samples: Sequence[EvaluationSample], config: AppConfig
) -> list[PredictionRecord]:
    runner = ReplayRunner(config)
    records: list[PredictionRecord] = []
    for sample in samples:
        try:
            records.append(runner.run(sample))
        except Exception as exc:
            records.append(
                PredictionRecord(
                    scenario_id=sample.scenario_id,
                    split=sample.split,
                    target=sample.target,
                    prediction=None,
                    expected_conflicts=sample.expected_conflicts,
                    config_fingerprint=runner.config_fingerprint,
                    sample_kind=sample.sample_kind,
                    metadata={},
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return records
