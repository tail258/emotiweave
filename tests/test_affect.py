from sentientbot.affect.calibration import CalibrationProfile
from sentientbot.affect.fusion import AffectFusion
from sentientbot.affect.policy import InteractionPolicy
from sentientbot.affect.tracker import AffectTracker
from sentientbot.config import AffectConfig
from sentientbot.models import (
    AffectLabel,
    AffectState,
    AudioEvidence,
    InteractionStrategy,
    TextEvidence,
    UserCorrection,
    VisualEvidence,
)
from sentientbot.session import SessionController


def test_tracker_expires_stale_face_state() -> None:
    tracker = AffectTracker(
        CalibrationProfile(target_samples=0),
        half_life_seconds=0.2,
        stale_after_seconds=1.5,
    )
    state = tracker.update(
        VisualEvidence(
            timestamp_ms=1_000,
            face_present=True,
            valence=0.8,
            arousal=0.1,
            confidence=0.9,
        )
    )
    assert state.label is AffectLabel.POSITIVE

    stale = tracker.update(VisualEvidence(timestamp_ms=2_501, face_present=False))
    assert stale.label is AffectLabel.UNKNOWN
    assert stale.confidence == 0


def test_fusion_marks_opposite_modalities_as_conflict() -> None:
    visual = AffectState(
        timestamp_ms=1_000,
        valence=-0.75,
        arousal=0.55,
        confidence=0.8,
        stability=0.8,
        label=AffectLabel.TENSE,
        sources=("vision",),
    )
    text = TextEvidence(
        text="我今天非常开心",
        valence=0.85,
        arousal=0.4,
        confidence=0.72,
        matched_terms=("开心",),
    )
    fused = AffectFusion(conflict_threshold=0.65).fuse(visual, text, 1_100)
    assert fused.conflict is True
    assert fused.confidence < max(visual.confidence, text.confidence)


def test_correction_updates_session_bias() -> None:
    profile = CalibrationProfile(target_samples=0, learning_rate=0.25)
    profile.apply_correction(
        UserCorrection("positive", target_valence=0.65),
        current_valence=-0.2,
        current_arousal=0.0,
    )
    assert profile.valence_bias > 0


def test_policy_does_not_claim_emotion_when_confidence_is_low() -> None:
    plan = InteractionPolicy().choose(AffectState(timestamp_ms=1, confidence=0.1))
    assert plan.strategy is InteractionStrategy.INVITE_CORRECTION
    assert plan.allow_emotion_language is False


def test_policy_clarifies_conflict_first() -> None:
    plan = InteractionPolicy().choose(AffectState(timestamp_ms=1, confidence=0.7, conflict=True))
    assert plan.strategy is InteractionStrategy.CLARIFY_CONFLICT


def test_user_correction_immediately_updates_current_fused_state() -> None:
    session = SessionController(AffectConfig(calibration_samples=0))
    session.process_text("我今天非常开心")
    before = session.fused_state.valence
    corrected = session.apply_correction("negative")
    assert corrected.valence < before
    assert "user_correction" in corrected.sources


def test_recent_text_evidence_survives_following_visual_frame() -> None:
    session = SessionController(AffectConfig(calibration_samples=0))
    session.process_text("我今天非常开心")
    state = session.observe(
        VisualEvidence(
            timestamp_ms=session._now_ms(),
            face_present=False,
        )
    )
    assert "text" in state.sources
    assert state.valence > 0


def test_audio_changes_arousal_but_does_not_neutralise_text_valence() -> None:
    visual = AffectState(timestamp_ms=1, confidence=0)
    text = TextEvidence("开心", valence=0.8, arousal=0.2, confidence=0.8)
    audio = AudioEvidence(
        timestamp_ms=1,
        arousal=0.8,
        confidence=0.8,
        duration_seconds=2,
    )
    state = AffectFusion().fuse(visual, text, 2, audio=audio)
    assert state.valence == text.valence
    assert state.arousal > text.arousal
    assert state.sources == ("text", "audio")


def test_audio_text_activation_conflict_has_specific_cause() -> None:
    visual = AffectState(timestamp_ms=1, confidence=0)
    text = TextEvidence("太激动了", valence=0.6, arousal=0.8, confidence=0.8)
    audio = AudioEvidence(timestamp_ms=1, arousal=-0.7, confidence=0.8)
    state = AffectFusion().fuse(visual, text, 2, audio=audio)
    assert state.conflict is True
    assert "text_audio_arousal" in state.conflicts


def test_recent_audio_evidence_survives_following_visual_frame() -> None:
    session = SessionController(AffectConfig(calibration_samples=0))
    audio = AudioEvidence(
        timestamp_ms=session._now_ms(),
        arousal=0.7,
        confidence=0.8,
    )
    session.process_text("今天还可以", audio)
    state = session.observe(VisualEvidence(timestamp_ms=session._now_ms(), face_present=False))
    assert "audio" in state.sources


def test_correction_clears_held_audio_evidence() -> None:
    session = SessionController(AffectConfig(calibration_samples=0))
    session.process_text(
        "我很开心",
        AudioEvidence(timestamp_ms=session._now_ms(), arousal=0.7, confidence=0.8),
    )
    session.apply_correction("negative")
    assert session.last_audio_evidence is None


def test_audio_weight_changes_arousal_without_changing_valence() -> None:
    visual = AffectState(timestamp_ms=1, confidence=0)
    text = TextEvidence("开心", valence=0.8, arousal=0.0, confidence=0.8)
    audio = AudioEvidence(timestamp_ms=1, arousal=1.0, confidence=0.8)
    low = AffectFusion(audio_arousal_weight=0.5).fuse(visual, text, 2, audio)
    high = AffectFusion(audio_arousal_weight=2.0).fuse(visual, text, 2, audio)
    assert high.arousal > low.arousal
    assert high.valence == low.valence == 0.8


def test_minimum_modality_confidence_filters_weak_evidence() -> None:
    visual = AffectState(timestamp_ms=1, valence=0.8, confidence=0.2)
    fused = AffectFusion(minimum_modality_confidence=0.3).fuse(visual, None, 2)
    assert fused.label is AffectLabel.UNKNOWN
