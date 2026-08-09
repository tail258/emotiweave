import pytest

from sentientbot.evaluation.metrics import evaluate_predictions
from sentientbot.evaluation.schema import EvaluationTarget, PredictionRecord
from sentientbot.models import AffectLabel, AffectState


def make_prediction(
    scenario_id: str,
    target_valence: float,
    target_arousal: float,
    predicted_valence: float,
    predicted_arousal: float,
    target_label: AffectLabel = AffectLabel.NEUTRAL,
    predicted_label: AffectLabel = AffectLabel.NEUTRAL,
    expected_conflicts: tuple[str, ...] = (),
    predicted_conflicts: tuple[str, ...] = (),
) -> PredictionRecord:
    return PredictionRecord(
        scenario_id=scenario_id,
        split="test",
        target=EvaluationTarget(target_valence, target_arousal, target_label),
        prediction=AffectState(
            timestamp_ms=1,
            valence=predicted_valence,
            arousal=predicted_arousal,
            confidence=0.8,
            label=predicted_label,
            conflicts=predicted_conflicts,
            conflict=bool(predicted_conflicts),
        ),
        expected_conflicts=expected_conflicts,
        config_fingerprint="test-config",
        sample_kind="participant",
        metadata={},
    )


def test_continuous_metrics_have_exact_values() -> None:
    records = [
        make_prediction("s1", -1.0, -0.5, -0.5, -0.5),
        make_prediction("s2", 0.0, 0.0, 0.0, 0.25),
        make_prediction("s3", 1.0, 0.5, 0.5, 0.5),
    ]
    result = evaluate_predictions(records)
    assert result.valence_mae == pytest.approx(1.0 / 3.0)
    assert result.arousal_mae == pytest.approx(1.0 / 12.0)
    assert result.valence_pearson_r == pytest.approx(1.0)


def test_classification_metrics_include_unknown_predictions() -> None:
    records = [
        make_prediction("s1", 0.5, 0.1, 0.5, 0.1, AffectLabel.POSITIVE, AffectLabel.POSITIVE),
        make_prediction("s2", 0.5, 0.5, 0.0, 0.0, AffectLabel.EXCITED, AffectLabel.UNKNOWN),
        make_prediction("s3", -0.5, -0.3, -0.5, 0.3, AffectLabel.LOW, AffectLabel.TENSE),
    ]
    result = evaluate_predictions(records)
    assert result.label_accuracy == pytest.approx(1 / 3)
    assert result.macro_f1 == pytest.approx(1 / 6)
    assert result.unknown_prediction_rate == pytest.approx(1 / 3)
    assert result.confusion_matrix["positive"]["positive"] == 1
    assert result.confusion_matrix["excited"]["unknown"] == 1
    assert result.confusion_matrix["low"]["tense"] == 1


def test_conflict_metrics_use_micro_set_counts() -> None:
    records = [
        make_prediction(
            "s1",
            0,
            0,
            0,
            0,
            expected_conflicts=("vision_text_valence",),
            predicted_conflicts=("vision_text_valence",),
        ),
        make_prediction(
            "s2",
            0,
            0,
            0,
            0,
            expected_conflicts=(),
            predicted_conflicts=("text_audio_arousal",),
        ),
        make_prediction(
            "s3",
            0,
            0,
            0,
            0,
            expected_conflicts=("vision_audio_arousal",),
            predicted_conflicts=(),
        ),
    ]
    result = evaluate_predictions(records)
    assert result.conflict_precision == pytest.approx(0.5)
    assert result.conflict_recall == pytest.approx(0.5)
    assert result.conflict_f1 == pytest.approx(0.5)


def test_failed_records_are_excluded_from_metrics_but_counted() -> None:
    failed = PredictionRecord(
        scenario_id="failed",
        split="test",
        target=EvaluationTarget(0.0, 0.0, AffectLabel.NEUTRAL),
        prediction=None,
        expected_conflicts=(),
        config_fingerprint="test-config",
        sample_kind="participant",
        metadata={},
        error="ValueError: broken media",
    )
    result = evaluate_predictions([failed])
    assert result.sample_count == 0
    assert result.failed_count == 1
    assert result.valence_mae is None
