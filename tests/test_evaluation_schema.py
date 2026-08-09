from pathlib import Path

import pytest

from sentientbot.evaluation.dataset import load_dataset, validate_dataset
from sentientbot.evaluation.schema import EvaluationSample

PARTICIPANT_ROW = {
    "scenario_id": "p001-positive-01",
    "split": "dev",
    "sample_kind": "participant",
    "participant_group": "participant-001",
    "consent_recorded": True,
    "target": {"valence": 0.7, "arousal": 0.3, "label": "positive"},
    "expected_conflicts": [],
    "transcript": "今天很开心",
    "video_path": "media/p001-positive-01.mp4",
    "audio_path": "media/p001-positive-01.wav",
}


def test_sample_round_trips_through_json(tmp_path: Path) -> None:
    sample = EvaluationSample.from_dict(PARTICIPANT_ROW, base_dir=tmp_path)
    restored = EvaluationSample.from_dict(sample.as_dict(tmp_path), base_dir=tmp_path)
    assert restored == sample


def test_participant_sample_requires_consent() -> None:
    row = {**PARTICIPANT_ROW, "consent_recorded": False}
    with pytest.raises(ValueError, match="consent"):
        EvaluationSample.from_dict(row, Path("."))


def test_dataset_rejects_duplicate_ids_and_participant_leakage(tmp_path: Path) -> None:
    path = tmp_path / "manifest.jsonl"
    path.write_text(
        '{"scenario_id":"p001-a","split":"dev","sample_kind":"participant",'
        '"participant_group":"p001","consent_recorded":true,"target":{"valence":0,"arousal":0,"label":"neutral"},'
        '"expected_conflicts":[],"transcript":"还好"}\n'
        '{"scenario_id":"p001-b","split":"test","sample_kind":"participant",'
        '"participant_group":"p001","consent_recorded":true,"target":{"valence":0,"arousal":0,"label":"neutral"},'
        '"expected_conflicts":[],"transcript":"还好"}\n',
        encoding="utf-8",
    )
    samples = load_dataset(path)
    with pytest.raises(ValueError, match="leakage"):
        validate_dataset(samples, require_all_splits=False)


def test_scripted_sample_requires_evidence_override() -> None:
    row = {
        "scenario_id": "scripted-01",
        "split": "scripted",
        "sample_kind": "scripted",
        "consent_recorded": False,
        "target": {"valence": 0.0, "arousal": 0.0, "label": "neutral"},
        "expected_conflicts": [],
        "transcript": "",
    }
    with pytest.raises(ValueError, match="evidence_override"):
        EvaluationSample.from_dict(row, Path("."))


def test_strict_dataset_validation_rejects_missing_split(tmp_path: Path) -> None:
    sample = EvaluationSample.from_dict(PARTICIPANT_ROW, tmp_path)
    with pytest.raises(ValueError, match="split"):
        validate_dataset([sample])
