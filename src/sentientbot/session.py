from __future__ import annotations

import threading
import time
from collections import deque

from sentientbot.affect import (
    AffectFusion,
    AffectTracker,
    CalibrationProfile,
    InteractionPolicy,
    label_for,
)
from sentientbot.config import AffectConfig
from sentientbot.models import (
    AffectLabel,
    AffectState,
    AudioEvidence,
    ConversationTurn,
    ResponsePlan,
    UserCorrection,
    VisualEvidence,
)
from sentientbot.perception.text_cues import TextCueAnalyzer


class SessionController:
    """管理单个会话的状态与决策。"""

    CORRECTIONS = {
        "positive": UserCorrection("positive", 0.65, note="用户表示实际更积极"),
        "negative": UserCorrection("negative", -0.65, note="用户表示实际更消极"),
        "accurate": UserCorrection("accurate", None, note="用户确认当前判断基本正确"),
        "uncertain": UserCorrection("uncertain", None, note="用户要求系统暂不做情绪判断"),
    }

    def __init__(self, config: AffectConfig, max_history_turns: int = 6) -> None:
        self.calibration = CalibrationProfile(
            target_samples=config.calibration_samples,
            learning_rate=config.correction_learning_rate,
        )
        self.tracker = AffectTracker(
            calibration=self.calibration,
            half_life_seconds=config.smoothing_half_life,
            stale_after_seconds=config.stale_after_seconds,
        )
        self.fusion = AffectFusion.from_config(config)
        self.text_analyzer = TextCueAnalyzer()
        self.policy = InteractionPolicy()
        self.max_history_turns = max_history_turns
        self.visual_state = AffectState(timestamp_ms=self._now_ms())
        self.fused_state = self.visual_state
        self.trajectory: deque[AffectState] = deque(maxlen=180)
        self.turns: deque[ConversationTurn] = deque(maxlen=max_history_turns)
        self.last_text_evidence = None
        self.last_audio_evidence = None
        self.last_correction = ""
        self._suppress_until_ms = 0
        self._text_hold_until_ms = 0
        self._audio_hold_until_ms = 0
        self._manual_hold_until_ms = 0
        self._text_hold_ms = max(1, int(config.text_hold_seconds * 1000))
        self._audio_hold_ms = max(1, int(config.audio_hold_seconds * 1000))
        self._lock = threading.RLock()

    def observe(self, evidence: VisualEvidence) -> AffectState:
        with self._lock:
            self.visual_state = self.tracker.update(evidence)
            if evidence.timestamp_ms < self._suppress_until_ms:
                self.visual_state = AffectState(
                    timestamp_ms=evidence.timestamp_ms,
                    valence=self.visual_state.valence,
                    arousal=self.visual_state.arousal,
                    confidence=0.0,
                    stability=self.visual_state.stability,
                    label=AffectLabel.UNKNOWN,
                    age_ms=self.visual_state.age_ms,
                    sources=(),
                    reason="用户已选择暂不判断",
                )
            if (
                evidence.timestamp_ms < self._manual_hold_until_ms
                and "user_correction" in self.fused_state.sources
            ):
                self.trajectory.append(self.fused_state)
                return self.fused_state
            held_text = (
                self.last_text_evidence
                if evidence.timestamp_ms < self._text_hold_until_ms
                else None
            )
            held_audio = (
                self.last_audio_evidence
                if evidence.timestamp_ms < self._audio_hold_until_ms
                else None
            )
            self.fused_state = self.fusion.fuse(
                self.visual_state,
                held_text,
                evidence.timestamp_ms,
                audio=held_audio,
            )
            self.trajectory.append(self.fused_state)
            return self.fused_state

    def process_text(
        self,
        text: str,
        audio_evidence: AudioEvidence | None = None,
    ) -> tuple[AffectState, ResponsePlan]:
        with self._lock:
            timestamp_ms = self._now_ms()
            text_evidence = self.text_analyzer.analyze(text)
            self.last_text_evidence = text_evidence
            self._text_hold_until_ms = timestamp_ms + self._text_hold_ms
            self.last_audio_evidence = audio_evidence
            self._audio_hold_until_ms = timestamp_ms + self._audio_hold_ms if audio_evidence else 0
            self._manual_hold_until_ms = 0
            self.fused_state = self.fusion.fuse(
                self.visual_state,
                text_evidence,
                timestamp_ms,
                audio=audio_evidence,
            )
            self.trajectory.append(self.fused_state)
            return self.fused_state, self.policy.choose(self.fused_state)

    def apply_correction(self, kind: str) -> AffectState:
        with self._lock:
            correction = self.CORRECTIONS.get(kind)
            if correction is None:
                raise ValueError(f"未知纠正类型：{kind}")

            self.last_correction = correction.note
            self.last_text_evidence = None
            self.last_audio_evidence = None
            self._text_hold_until_ms = 0
            self._audio_hold_until_ms = 0
            if kind == "uncertain":
                self._suppress_until_ms = self._now_ms() + 10_000
                self.fused_state = AffectState(
                    timestamp_ms=self._now_ms(),
                    reason="用户已选择暂不判断，10 秒后恢复观察",
                )
                self.trajectory.append(self.fused_state)
                return self.fused_state

            current = self.fused_state
            before_valence = current.valence
            before_arousal = current.arousal
            self.calibration.apply_correction(correction, before_valence, before_arousal)
            if correction.target_valence is not None:
                valence_delta = self.calibration.learning_rate * (
                    correction.target_valence - before_valence
                )
                arousal_delta = 0.0
                if correction.target_arousal is not None:
                    arousal_delta = self.calibration.learning_rate * (
                        correction.target_arousal - before_arousal
                    )
                if self.visual_state.confidence > 0.05:
                    self.tracker.apply_bias_delta(valence_delta, arousal_delta)
                corrected_valence = before_valence + valence_delta
                corrected_arousal = before_arousal + arousal_delta
                corrected_confidence = max(0.55, current.confidence)
                self.fused_state = AffectState(
                    timestamp_ms=self._now_ms(),
                    valence=corrected_valence,
                    arousal=corrected_arousal,
                    confidence=corrected_confidence,
                    stability=current.stability,
                    label=label_for(
                        corrected_valence,
                        corrected_arousal,
                        corrected_confidence,
                    ),
                    sources=tuple(dict.fromkeys((*current.sources, "user_correction"))),
                    conflicts=current.conflicts,
                    reason=correction.note,
                )
            else:
                self.fused_state = AffectState(
                    timestamp_ms=self._now_ms(),
                    valence=current.valence,
                    arousal=current.arousal,
                    confidence=min(1.0, current.confidence + 0.08),
                    stability=current.stability,
                    conflict=current.conflict,
                    label=current.label,
                    sources=tuple(dict.fromkeys((*current.sources, "user_correction"))),
                    conflicts=current.conflicts,
                    reason=correction.note,
                )
            self.trajectory.append(self.fused_state)
            self._manual_hold_until_ms = self._now_ms() + 3_000
            return self.fused_state

    def record_turn(
        self,
        user: str,
        assistant: str,
        state: AffectState,
        plan: ResponsePlan,
        latency_seconds: float,
    ) -> None:
        with self._lock:
            self.turns.append(
                ConversationTurn(
                    user=user,
                    assistant=assistant,
                    state=state,
                    plan=plan,
                    latency_seconds=latency_seconds,
                )
            )

    def history_messages(self) -> list[dict[str, str]]:
        with self._lock:
            messages: list[dict[str, str]] = []
            for turn in self.turns:
                messages.append({"role": "user", "content": turn.user})
                messages.append({"role": "assistant", "content": turn.assistant})
            return messages[-self.max_history_turns * 2 :]

    def trajectory_snapshot(self) -> list[AffectState]:
        with self._lock:
            return list(self.trajectory)

    def reset(self) -> None:
        with self._lock:
            self.calibration.reset()
            self.tracker.reset()
            self.visual_state = AffectState(timestamp_ms=self._now_ms())
            self.fused_state = self.visual_state
            self.trajectory.clear()
            self.turns.clear()
            self.last_text_evidence = None
            self.last_audio_evidence = None
            self.last_correction = ""
            self._suppress_until_ms = 0
            self._text_hold_until_ms = 0
            self._audio_hold_until_ms = 0
            self._manual_hold_until_ms = 0

    @staticmethod
    def _now_ms() -> int:
        return time.monotonic_ns() // 1_000_000
