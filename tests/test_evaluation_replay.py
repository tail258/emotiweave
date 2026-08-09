from pathlib import Path

import numpy as np

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.replay import ReplayRunner, replay_dataset
from sentientbot.evaluation.schema import EvaluationSample
from sentientbot.models import AudioEvidence, VisualEvidence


class FakeFaceAnalyzer:
    backend = "fake_face"

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, frame, timestamp_ms):
        self.calls += 1
        return VisualEvidence(timestamp_ms, True, 0.6, 0.2, 0.8), frame


class FakeAudioAnalyzer:
    backend = "fake_audio"

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, audio_path, transcript="", timestamp_ms=None):
        self.calls += 1
        return AudioEvidence(timestamp_ms or 1000, 1.2, arousal=0.8, confidence=0.8)


def fake_frame_reader(video_path, stream_every):
    yield np.zeros((16, 16, 3), dtype=np.uint8), 1000


def participant_sample(tmp_path: Path) -> EvaluationSample:
    return EvaluationSample.from_dict(
        {
            "scenario_id": "p001-positive-01",
            "split": "dev",
            "sample_kind": "participant",
            "participant_group": "p001",
            "consent_recorded": True,
            "target": {"valence": 0.7, "arousal": 0.4, "label": "excited"},
            "expected_conflicts": [],
            "transcript": "今天很开心",
            "video_path": "media/sample.mp4",
            "audio_path": "media/sample.wav",
        },
        base_dir=tmp_path,
    )


def test_replay_fuses_last_visual_frame_with_text_and_audio(tmp_path: Path) -> None:
    config = load_config(PROJECT_ROOT / "config.yaml")
    face = FakeFaceAnalyzer()
    audio = FakeAudioAnalyzer()
    runner = ReplayRunner(
        config,
        face_analyzer=face,
        audio_analyzer=audio,
        frame_reader=fake_frame_reader,
    )
    result = runner.run(participant_sample(tmp_path))
    assert result.prediction is not None
    assert result.prediction.sources == ("vision", "text", "audio")
    assert result.config_fingerprint
    assert face.calls == 1
    assert audio.calls == 1


def test_replay_isolates_a_broken_sample(tmp_path: Path) -> None:
    config = load_config(PROJECT_ROOT / "config.yaml")
    broken = participant_sample(tmp_path)
    records = replay_dataset([broken], config)
    assert len(records) == 1
    assert records[0].prediction is None
    assert records[0].error is not None
