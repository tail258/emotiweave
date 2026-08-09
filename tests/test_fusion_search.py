from pathlib import Path

import pytest

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.schema import EvaluationSample
from sentientbot.evaluation.search import SearchGrid, search_fusion


def neutral_sample(tmp_path: Path, split: str) -> EvaluationSample:
    return EvaluationSample.from_dict(
        {
            "scenario_id": f"search-{split}",
            "split": split,
            "sample_kind": "participant",
            "participant_group": "p001",
            "consent_recorded": True,
            "target": {"valence": 0.0, "arousal": 0.0, "label": "neutral"},
            "expected_conflicts": [],
            "transcript": "今天还可以",
            "video_path": None,
            "audio_path": None,
            "evidence_override": {
                "visual": {"timestamp_ms": 1, "face_present": True, "confidence": 0.8},
                "text": None,
                "audio": None,
            },
        },
        tmp_path,
    )


def test_search_rejects_test_samples(tmp_path: Path) -> None:
    config = load_config(PROJECT_ROOT / "config.yaml")
    with pytest.raises(ValueError, match="dev"):
        search_fusion([neutral_sample(tmp_path, "test")], config, SearchGrid.default())


def test_default_grid_has_36_configurations() -> None:
    grid = SearchGrid.default()
    assert len(grid.combinations()) == 36


def test_search_is_deterministic_for_same_development_samples(tmp_path: Path) -> None:
    config = load_config(PROJECT_ROOT / "config.yaml")
    samples = [neutral_sample(tmp_path, "dev")]
    first = search_fusion(samples, config, SearchGrid.default())
    second = search_fusion(samples, config, SearchGrid.default())
    assert [item.parameters for item in first] == [item.parameters for item in second]
    assert first[0].parameters == second[0].parameters
