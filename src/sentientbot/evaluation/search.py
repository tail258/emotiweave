from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import product

from sentientbot.affect.fusion import AffectFusion
from sentientbot.config import AppConfig
from sentientbot.evaluation.metrics import MetricSummary, evaluate_predictions
from sentientbot.evaluation.replay import _config_fingerprint, extract_evidence
from sentientbot.evaluation.schema import EvaluationSample, EvidenceSnapshot, PredictionRecord


@dataclass(frozen=True, slots=True)
class SearchGrid:
    conflict_threshold: tuple[float, ...]
    minimum_modality_confidence: tuple[float, ...]
    audio_arousal_weight: tuple[float, ...]

    @classmethod
    def default(cls) -> SearchGrid:
        return cls(
            conflict_threshold=(0.45, 0.55, 0.65, 0.75),
            minimum_modality_confidence=(0.05, 0.20, 0.35),
            audio_arousal_weight=(0.8, 1.0, 1.2),
        )

    def combinations(self) -> list[dict[str, float]]:
        return [
            {
                "conflict_threshold": conflict,
                "minimum_modality_confidence": minimum,
                "audio_arousal_weight": audio,
            }
            for conflict, minimum, audio in product(
                self.conflict_threshold,
                self.minimum_modality_confidence,
                self.audio_arousal_weight,
            )
        ]


@dataclass(frozen=True, slots=True)
class SearchResult:
    parameters: dict[str, float]
    metrics: MetricSummary
    safe: bool
    status: str


def _prediction_from_snapshot(snapshot: EvidenceSnapshot, config: AppConfig) -> PredictionRecord:
    prediction = AffectFusion.from_config(config.affect).fuse(
        snapshot.visual_state,
        snapshot.text_evidence,
        snapshot.visual_state.timestamp_ms,
        audio=snapshot.audio_evidence,
    )
    return PredictionRecord(
        scenario_id=snapshot.sample.scenario_id,
        split=snapshot.sample.split,
        target=snapshot.sample.target,
        prediction=prediction,
        expected_conflicts=snapshot.sample.expected_conflicts,
        config_fingerprint=_config_fingerprint(config),
        sample_kind=snapshot.sample.sample_kind,
        metadata=snapshot.metadata,
    )


def _sort_key(
    result: SearchResult, defaults: dict[str, float]
) -> tuple[float, float, float, float]:
    metrics = result.metrics
    mae = sum(value or 1.0 for value in (metrics.valence_mae, metrics.arousal_mae)) / 2.0
    distance = sum(abs(result.parameters[key] - defaults[key]) for key in defaults)
    return (
        -(metrics.macro_f1 or 0.0),
        mae,
        -(metrics.conflict_f1 or 0.0),
        distance,
    )


def search_fusion(
    samples: Sequence[EvaluationSample],
    base_config: AppConfig,
    grid: SearchGrid,
) -> list[SearchResult]:
    if not samples:
        raise ValueError("development samples are required")
    if any(sample.split != "dev" for sample in samples):
        raise ValueError("fusion search accepts dev samples only")

    snapshots = extract_evidence(samples, base_config)
    defaults = {
        "conflict_threshold": base_config.affect.conflict_threshold,
        "minimum_modality_confidence": base_config.affect.minimum_modality_confidence,
        "audio_arousal_weight": base_config.affect.audio_arousal_weight,
    }
    results: list[SearchResult] = []
    for parameters in grid.combinations():
        candidate_affect = replace(base_config.affect, **parameters)
        candidate_config = replace(base_config, affect=candidate_affect)
        records = [_prediction_from_snapshot(snapshot, candidate_config) for snapshot in snapshots]
        metrics = evaluate_predictions(records)
        safe = (metrics.conflict_precision or 0.0) >= 0.70
        results.append(
            SearchResult(
                parameters=parameters,
                metrics=metrics,
                safe=safe,
                status="candidate",
            )
        )

    safe_results = [result for result in results if result.safe]
    ranked = sorted(safe_results or results, key=lambda result: _sort_key(result, defaults))
    if not safe_results and ranked:
        ranked[0] = SearchResult(
            parameters=defaults,
            metrics=ranked[0].metrics,
            safe=False,
            status="no_safe_improvement",
        )
    elif ranked:
        ranked[0] = SearchResult(
            parameters=ranked[0].parameters,
            metrics=ranked[0].metrics,
            safe=True,
            status="selected",
        )
    return ranked
