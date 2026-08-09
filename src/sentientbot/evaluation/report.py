from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from sentientbot.evaluation.metrics import (
    EVALUATION_LABELS,
    PREDICTION_LABELS,
    MetricSummary,
    evaluate_predictions,
)
from sentientbot.evaluation.schema import PredictionRecord


def load_predictions(path: Path) -> list[PredictionRecord]:
    records: list[PredictionRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(PredictionRecord.from_dict(json.loads(line)))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid prediction row {line_number}: {exc}") from exc
    return records


def _write_per_sample(records: Iterable[PredictionRecord], path: Path) -> None:
    fieldnames = [
        "scenario_id",
        "split",
        "sample_kind",
        "target_valence",
        "target_arousal",
        "target_label",
        "prediction_valence",
        "prediction_arousal",
        "prediction_label",
        "valence_abs_error",
        "arousal_abs_error",
        "expected_conflicts",
        "predicted_conflicts",
        "active_modalities",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            prediction = record.prediction
            writer.writerow(
                {
                    "scenario_id": record.scenario_id,
                    "split": record.split,
                    "sample_kind": record.sample_kind,
                    "target_valence": record.target.valence,
                    "target_arousal": record.target.arousal,
                    "target_label": record.target.label.value,
                    "prediction_valence": prediction.valence if prediction else "",
                    "prediction_arousal": prediction.arousal if prediction else "",
                    "prediction_label": prediction.label.value if prediction else "",
                    "valence_abs_error": abs(record.target.valence - prediction.valence)
                    if prediction
                    else "",
                    "arousal_abs_error": abs(record.target.arousal - prediction.arousal)
                    if prediction
                    else "",
                    "expected_conflicts": ";".join(record.expected_conflicts),
                    "predicted_conflicts": ";".join(prediction.conflicts) if prediction else "",
                    "active_modalities": ";".join(prediction.sources) if prediction else "",
                    "error": record.error or "",
                }
            )


def _write_confusion_matrix(summary: MetricSummary, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["target\\prediction", *PREDICTION_LABELS])
        for target in EVALUATION_LABELS:
            writer.writerow(
                [
                    target,
                    *[
                        summary.confusion_matrix[target][prediction]
                        for prediction in PREDICTION_LABELS
                    ],
                ]
            )


def _write_plots(
    summary: MetricSummary, records: list[PredictionRecord], destination: Path
) -> None:
    import plotly.graph_objects as go

    matrix = [
        [summary.confusion_matrix[target][prediction] for prediction in PREDICTION_LABELS]
        for target in EVALUATION_LABELS
    ]
    confusion = go.Figure(
        data=go.Heatmap(
            z=matrix, x=list(PREDICTION_LABELS), y=list(EVALUATION_LABELS), colorscale="Blues"
        )
    )
    confusion.update_layout(
        title="Emotion label confusion matrix", xaxis_title="Predicted", yaxis_title="Target"
    )
    confusion.write_html(str(destination / "confusion_matrix.html"), include_plotlyjs=True)

    successful = [record for record in records if record.prediction is not None]
    scatter = go.Figure()
    scatter.add_trace(
        go.Scatter(
            x=[record.target.valence for record in successful],
            y=[record.prediction.valence for record in successful],
            mode="markers",
            name="valence",
            text=[record.scenario_id for record in successful],
        )
    )
    scatter.add_trace(
        go.Scatter(
            x=[record.target.arousal for record in successful],
            y=[record.prediction.arousal for record in successful],
            mode="markers",
            name="arousal",
            text=[record.scenario_id for record in successful],
        )
    )
    scatter.update_layout(
        title="Target versus predicted valence/arousal",
        xaxis_title="Target",
        yaxis_title="Predicted",
    )
    scatter.write_html(str(destination / "va_scatter.html"), include_plotlyjs=True)


def _metric_section(name: str, summary: MetricSummary) -> str:
    return "\n".join(
        [
            f"## {name}",
            f"- sample_count: {summary.sample_count}",
            f"- failed_count: {summary.failed_count}",
            f"- valence_mae: {summary.valence_mae}",
            f"- arousal_mae: {summary.arousal_mae}",
            f"- valence_pearson_r: {summary.valence_pearson_r}",
            f"- arousal_pearson_r: {summary.arousal_pearson_r}",
            f"- label_accuracy: {summary.label_accuracy}",
            f"- macro_f1: {summary.macro_f1}",
            f"- unknown_prediction_rate: {summary.unknown_prediction_rate}",
            f"- conflict_precision: {summary.conflict_precision}",
            f"- conflict_recall: {summary.conflict_recall}",
            f"- conflict_f1: {summary.conflict_f1}",
        ]
    )


def write_report(records: Iterable[PredictionRecord], destination: Path) -> MetricSummary:
    records = list(records)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    participant_summary = evaluate_predictions(records, sample_kind="participant")
    scripted_summary = evaluate_predictions(records, sample_kind="scripted")
    overall_summary = evaluate_predictions(records)
    summary = {
        "participant": participant_summary.as_dict(),
        "scripted": scripted_summary.as_dict(),
        "overall": overall_summary.as_dict(),
        "record_count": len(records),
        "scope_note": (
            "Participant and scripted records are reported separately; "
            "scripted records are deterministic fusion regression only."
        ),
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destination / "metrics.md").write_text(
        "# EmotiWeave emotion evaluation\n\n"
        + _metric_section("participant", participant_summary)
        + "\n\n"
        + _metric_section("scripted", scripted_summary)
        + "\n\n"
        + _metric_section("overall", overall_summary)
        + (
            "\n\nMetrics are descriptive for this dataset and are not a population-level "
            "emotion-recognition accuracy claim.\n"
        ),
        encoding="utf-8",
    )
    _write_per_sample(records, destination / "per_sample.csv")
    matrix_summary = participant_summary if participant_summary.sample_count else scripted_summary
    _write_confusion_matrix(matrix_summary, destination / "confusion_matrix.csv")
    matrix_records = [
        record
        for record in records
        if record.sample_kind == ("participant" if participant_summary.sample_count else "scripted")
    ]
    _write_plots(matrix_summary, matrix_records, destination)
    return participant_summary if participant_summary.sample_count else scripted_summary
