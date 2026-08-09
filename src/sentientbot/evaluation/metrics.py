from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from sentientbot.evaluation.schema import PredictionRecord
from sentientbot.models import AffectLabel

EVALUATION_LABELS = (
    AffectLabel.NEUTRAL.value,
    AffectLabel.CALM.value,
    AffectLabel.POSITIVE.value,
    AffectLabel.EXCITED.value,
    AffectLabel.LOW.value,
    AffectLabel.TENSE.value,
)
PREDICTION_LABELS = (*EVALUATION_LABELS, AffectLabel.UNKNOWN.value)


@dataclass(frozen=True, slots=True)
class MetricSummary:
    sample_count: int
    failed_count: int
    valence_mae: float | None
    arousal_mae: float | None
    valence_pearson_r: float | None
    arousal_pearson_r: float | None
    label_accuracy: float | None
    macro_f1: float | None
    unknown_prediction_rate: float | None
    confusion_matrix: dict[str, dict[str, int]]
    conflict_precision: float | None
    conflict_recall: float | None
    conflict_f1: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pearson(targets: list[float], predictions: list[float]) -> float | None:
    if len(targets) < 2:
        return None
    target_array = np.asarray(targets, dtype=float)
    prediction_array = np.asarray(predictions, dtype=float)
    if np.std(target_array) == 0.0 or np.std(prediction_array) == 0.0:
        return None
    return float(np.corrcoef(target_array, prediction_array)[0, 1])


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    denominator = 2 * true_positive + false_positive + false_negative
    return 2 * true_positive / denominator if denominator else 0.0


def _confusion_matrix(records: Iterable[PredictionRecord]) -> dict[str, dict[str, int]]:
    matrix = {
        target: {prediction: 0 for prediction in PREDICTION_LABELS} for target in EVALUATION_LABELS
    }
    for record in records:
        assert record.prediction is not None
        matrix[record.target.label.value][record.prediction.label.value] += 1
    return matrix


def evaluate_predictions(
    records: Iterable[PredictionRecord],
    sample_kind: str | None = None,
) -> MetricSummary:
    selected = [
        record for record in records if sample_kind is None or record.sample_kind == sample_kind
    ]
    failed_count = sum(record.prediction is None for record in selected)
    successful = [record for record in selected if record.prediction is not None]
    if not successful:
        return MetricSummary(
            sample_count=0,
            failed_count=failed_count,
            valence_mae=None,
            arousal_mae=None,
            valence_pearson_r=None,
            arousal_pearson_r=None,
            label_accuracy=None,
            macro_f1=None,
            unknown_prediction_rate=None,
            confusion_matrix={
                target: {prediction: 0 for prediction in PREDICTION_LABELS}
                for target in EVALUATION_LABELS
            },
            conflict_precision=None,
            conflict_recall=None,
            conflict_f1=None,
        )

    target_valence = [record.target.valence for record in successful]
    target_arousal = [record.target.arousal for record in successful]
    predicted_valence = [record.prediction.valence for record in successful]
    predicted_arousal = [record.prediction.arousal for record in successful]
    target_labels = [record.target.label.value for record in successful]
    predicted_labels = [record.prediction.label.value for record in successful]
    correct = sum(
        target == prediction
        for target, prediction in zip(target_labels, predicted_labels, strict=False)
    )

    per_class_f1: list[float] = []
    for label in EVALUATION_LABELS:
        true_positive = sum(
            target == label and prediction == label
            for target, prediction in zip(target_labels, predicted_labels, strict=False)
        )
        false_positive = sum(
            target != label and prediction == label
            for target, prediction in zip(target_labels, predicted_labels, strict=False)
        )
        false_negative = sum(
            target == label and prediction != label
            for target, prediction in zip(target_labels, predicted_labels, strict=False)
        )
        per_class_f1.append(_f1(true_positive, false_positive, false_negative))

    true_positive = false_positive = false_negative = 0
    for record in successful:
        expected = set(record.expected_conflicts)
        predicted = set(record.prediction.conflicts)
        true_positive += len(expected & predicted)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    )

    return MetricSummary(
        sample_count=len(successful),
        failed_count=failed_count,
        valence_mae=float(
            np.mean(np.abs(np.asarray(target_valence) - np.asarray(predicted_valence)))
        ),
        arousal_mae=float(
            np.mean(np.abs(np.asarray(target_arousal) - np.asarray(predicted_arousal)))
        ),
        valence_pearson_r=_pearson(target_valence, predicted_valence),
        arousal_pearson_r=_pearson(target_arousal, predicted_arousal),
        label_accuracy=correct / len(successful),
        macro_f1=float(np.mean(per_class_f1)),
        unknown_prediction_rate=sum(
            label == AffectLabel.UNKNOWN.value for label in predicted_labels
        )
        / len(successful),
        confusion_matrix=_confusion_matrix(successful),
        conflict_precision=precision,
        conflict_recall=recall,
        conflict_f1=_f1(true_positive, false_positive, false_negative),
    )
