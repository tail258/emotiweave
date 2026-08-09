from pathlib import Path

import pytest

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.dataset import load_dataset
from sentientbot.evaluation.replay import replay_dataset
from sentientbot.evaluation.schema import EvaluationSample


@pytest.fixture(scope="module")
def scripted_records():
    samples = load_dataset(
        PROJECT_ROOT / "evaluation/datasets/scripted_conflicts.jsonl", split="scripted"
    )
    config = load_config(PROJECT_ROOT / "config.yaml")
    return {record.scenario_id: record for record in replay_dataset(samples, config)}


@pytest.mark.parametrize(
    ("scenario_id", "expected"),
    [
        ("vision-positive_text-negative-01", "vision_text_valence"),
        ("vision-high_audio-low-01", "vision_audio_arousal"),
        ("text-high_audio-low-01", "text_audio_arousal"),
    ],
)
def test_expected_conflict_is_detected(scripted_records, scenario_id, expected) -> None:
    record = scripted_records[scenario_id]
    assert record.prediction is not None
    assert expected in record.prediction.conflicts
    assert record.prediction.confidence < 0.8


@pytest.mark.parametrize(
    "scenario_id",
    [
        "vision-positive_text-positive-control",
        "vision-high_audio-high-control",
        "text-high_audio-high-control",
    ],
)
def test_non_conflict_controls_remain_clean(scripted_records, scenario_id) -> None:
    record = scripted_records[scenario_id]
    assert record.prediction is not None
    assert record.prediction.conflict is False
    assert record.prediction.conflicts == ()


def make_threshold_sample(
    tmp_path: Path,
    difference: float,
    visual_confidence: float = 0.8,
    text_confidence: float = 0.8,
) -> EvaluationSample:
    return EvaluationSample.from_dict(
        {
            "scenario_id": f"threshold-{difference}-{visual_confidence}",
            "split": "scripted",
            "sample_kind": "scripted",
            "target": {"valence": 0.0, "arousal": 0.0, "label": "neutral"},
            "expected_conflicts": [],
            "evidence_override": {
                "visual": {
                    "timestamp_ms": 1000,
                    "face_present": True,
                    "valence": difference / 2,
                    "arousal": 0.0,
                    "confidence": visual_confidence,
                },
                "text": {
                    "text": "",
                    "valence": -difference / 2,
                    "arousal": 0.0,
                    "confidence": text_confidence,
                },
                "audio": None,
            },
        },
        tmp_path,
    )


@pytest.mark.parametrize("difference, expected", [(0.64, False), (0.66, True)])
def test_conflict_threshold_boundary(tmp_path: Path, difference: float, expected: bool) -> None:
    sample = make_threshold_sample(tmp_path, difference)
    config = load_config(PROJECT_ROOT / "config.yaml")
    record = replay_dataset([sample], config)[0]
    assert record.prediction is not None
    assert record.prediction.conflict is expected


@pytest.mark.parametrize("confidence, expected", [(0.41, False), (0.43, True)])
def test_conflict_minimum_confidence_boundary(
    tmp_path: Path, confidence: float, expected: bool
) -> None:
    sample = make_threshold_sample(tmp_path, 0.8, visual_confidence=confidence)
    config = load_config(PROJECT_ROOT / "config.yaml")
    record = replay_dataset([sample], config)[0]
    assert record.prediction is not None
    assert record.prediction.conflict is expected
