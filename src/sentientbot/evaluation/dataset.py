from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentientbot.evaluation.schema import EvaluationSample


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    sample_count: int
    counts_by_split: dict[str, int]
    counts_by_label: dict[str, int]
    counts_by_kind: dict[str, int]
    expected_conflict_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "counts_by_split": self.counts_by_split,
            "counts_by_label": self.counts_by_label,
            "counts_by_kind": self.counts_by_kind,
            "expected_conflict_count": self.expected_conflict_count,
        }


def load_dataset(path: Path, split: str | None = None) -> list[EvaluationSample]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"dataset does not exist: {path}")
    samples: list[EvaluationSample] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                sample = EvaluationSample.from_dict(data, path.parent)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid dataset row {line_number}: {exc}") from exc
            if split is None or sample.split == split:
                samples.append(sample)
    return samples


def validate_dataset(
    samples: list[EvaluationSample], *, require_all_splits: bool = True
) -> DatasetSummary:
    if not samples:
        raise ValueError("dataset is empty")
    ids = [sample.scenario_id for sample in samples]
    duplicates = [scenario_id for scenario_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate scenario_id: {sorted(duplicates)}")
    splits = Counter(sample.split for sample in samples)
    if require_all_splits and any(splits.get(name, 0) == 0 for name in ("dev", "test", "scripted")):
        missing = [name for name in ("dev", "test", "scripted") if splits.get(name, 0) == 0]
        raise ValueError(f"dataset split is empty: {missing}")

    groups_by_split: dict[str, set[str]] = {"dev": set(), "test": set()}
    for sample in samples:
        if sample.participant_group and sample.split in groups_by_split:
            groups_by_split[sample.split].add(sample.participant_group)
    leakage = groups_by_split["dev"] & groups_by_split["test"]
    if leakage:
        raise ValueError(f"participant leakage between dev and test: {sorted(leakage)}")

    return DatasetSummary(
        sample_count=len(samples),
        counts_by_split=dict(sorted(splits.items())),
        counts_by_label=dict(
            sorted(Counter(sample.target.label.value for sample in samples).items())
        ),
        counts_by_kind=dict(sorted(Counter(sample.sample_kind for sample in samples).items())),
        expected_conflict_count=sum(bool(sample.expected_conflicts) for sample in samples),
    )


def append_sample(path: Path, sample: EvaluationSample) -> DatasetSummary:
    path = Path(path)
    existing = load_dataset(path) if path.exists() else []
    summary = validate_dataset(existing + [sample], require_all_splits=False) if existing else None
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sample.as_dict(path.parent), ensure_ascii=False) + "\n")
    return summary or validate_dataset([sample], require_all_splits=False)
