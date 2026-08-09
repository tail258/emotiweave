from __future__ import annotations

from itertools import combinations

from sentientbot.affect.tracker import label_for
from sentientbot.models import AffectState, AudioEvidence, TextEvidence, clamp


class AffectFusion:
    """按置信度融合证据并标记冲突。"""

    def __init__(
        self,
        conflict_threshold: float = 0.65,
        *,
        vision_valence_weight: float = 1.0,
        vision_arousal_weight: float = 1.0,
        text_valence_weight: float = 1.0,
        text_arousal_weight: float = 1.0,
        audio_arousal_weight: float = 1.10,
        minimum_modality_confidence: float = 0.05,
        conflict_min_confidence: float = 0.42,
        conflict_penalty: float = 0.62,
        agreement_base: float = 0.78,
        agreement_bonus: float = 0.22,
    ) -> None:
        self.conflict_threshold = conflict_threshold
        self.vision_valence_weight = vision_valence_weight
        self.vision_arousal_weight = vision_arousal_weight
        self.text_valence_weight = text_valence_weight
        self.text_arousal_weight = text_arousal_weight
        self.audio_arousal_weight = audio_arousal_weight
        self.minimum_modality_confidence = minimum_modality_confidence
        self.conflict_min_confidence = conflict_min_confidence
        self.conflict_penalty = conflict_penalty
        self.agreement_base = agreement_base
        self.agreement_bonus = agreement_bonus

    @classmethod
    def from_config(cls, config) -> AffectFusion:
        return cls(
            conflict_threshold=config.conflict_threshold,
            vision_valence_weight=config.vision_valence_weight,
            vision_arousal_weight=config.vision_arousal_weight,
            text_valence_weight=config.text_valence_weight,
            text_arousal_weight=config.text_arousal_weight,
            audio_arousal_weight=config.audio_arousal_weight,
            minimum_modality_confidence=config.minimum_modality_confidence,
            conflict_min_confidence=config.conflict_min_confidence,
            conflict_penalty=config.conflict_penalty,
            agreement_base=config.agreement_base,
            agreement_bonus=config.agreement_bonus,
        )

    def fuse(
        self,
        visual: AffectState,
        text: TextEvidence | None,
        timestamp_ms: int,
        audio: AudioEvidence | None = None,
    ) -> AffectState:
        visual_active = visual.confidence > self.minimum_modality_confidence
        text_active = text is not None and text.confidence > self.minimum_modality_confidence
        audio_active = audio is not None and audio.confidence > self.minimum_modality_confidence

        if not any((visual_active, text_active, audio_active)):
            return AffectState(
                timestamp_ms=timestamp_ms,
                stability=visual.stability,
                age_ms=visual.age_ms,
                reason="当前没有达到可信阈值的线索",
            )

        valence_items: list[tuple[str, float, float]] = []
        arousal_items: list[tuple[str, float, float]] = []
        sources: list[str] = []
        if visual_active:
            sources.append("vision")
            valence_items.append(
                ("vision", visual.valence, visual.confidence * self.vision_valence_weight)
            )
            arousal_items.append(
                ("vision", visual.arousal, visual.confidence * self.vision_arousal_weight)
            )
        if text_active and text is not None:
            sources.append("text")
            valence_items.append(("text", text.valence, text.confidence * self.text_valence_weight))
            arousal_items.append(("text", text.arousal, text.confidence * self.text_arousal_weight))
        if audio_active and audio is not None:
            sources.append("audio")
            # 语音韵律只参与激活度，避免稀释文本效价。
            arousal_items.append(
                ("audio", audio.arousal, audio.confidence * self.audio_arousal_weight)
            )

        valence = self._weighted_average(valence_items)
        arousal = self._weighted_average(arousal_items)
        conflicts = self._detect_conflicts(valence_items, arousal_items)
        conflict = bool(conflicts)

        active_confidences = [item[2] for item in arousal_items]
        base_confidence = sum(active_confidences) / len(active_confidences)
        agreement = self._agreement(valence_items, arousal_items)
        confidence = clamp(
            base_confidence
            * (
                self.conflict_penalty
                if conflict
                else self.agreement_base + self.agreement_bonus * agreement
            ),
            0.0,
            1.0,
        )

        if conflict:
            readable = {
                "vision_text_valence": "表情与文本效价方向冲突",
                "vision_audio_arousal": "表情与语音激活度冲突",
                "text_audio_arousal": "文本与语音激活度冲突",
            }
            reason = "；".join(readable[item] for item in conflicts)
            reason += "，已主动降低置信度"
        elif len(sources) == 1:
            source_name = {"vision": "表情", "text": "文本", "audio": "语音韵律"}[sources[0]]
            reason = f"当前仅有{source_name}线索，结论保持保守"
        else:
            reason = f"{'、'.join(sources)}线索已按可信度进行时间对齐融合"

        return AffectState(
            timestamp_ms=timestamp_ms,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            stability=visual.stability if visual_active else 0.5,
            conflict=conflict,
            label=label_for(valence, arousal, confidence),
            age_ms=visual.age_ms,
            sources=tuple(sources),
            conflicts=conflicts,
            reason=reason,
        )

    @staticmethod
    def _weighted_average(items: list[tuple[str, float, float]]) -> float:
        if not items:
            return 0.0
        if len(items) == 1:
            return items[0][1]
        total = sum(weight for _, _, weight in items)
        return sum(value * weight for _, value, weight in items) / max(total, 1e-6)

    def _detect_conflicts(
        self,
        valence_items: list[tuple[str, float, float]],
        arousal_items: list[tuple[str, float, float]],
    ) -> tuple[str, ...]:
        conflicts: list[str] = []
        values = {source: (value, confidence) for source, value, confidence in valence_items}
        if self._opposed(values.get("vision"), values.get("text")):
            conflicts.append("vision_text_valence")

        activation = {source: (value, confidence) for source, value, confidence in arousal_items}
        if self._opposed(activation.get("vision"), activation.get("audio")):
            conflicts.append("vision_audio_arousal")
        if self._opposed(activation.get("text"), activation.get("audio")):
            conflicts.append("text_audio_arousal")
        return tuple(conflicts)

    def _opposed(
        self,
        first: tuple[float, float] | None,
        second: tuple[float, float] | None,
    ) -> bool:
        if first is None or second is None:
            return False
        first_value, first_confidence = first
        second_value, second_confidence = second
        return (
            first_value * second_value < -0.035
            and abs(first_value - second_value) >= self.conflict_threshold
            and min(first_confidence, second_confidence) >= self.conflict_min_confidence
        )

    @staticmethod
    def _agreement(
        valence_items: list[tuple[str, float, float]],
        arousal_items: list[tuple[str, float, float]],
    ) -> float:
        distances: list[float] = []
        for items in (valence_items, arousal_items):
            for first, second in combinations(items, 2):
                distances.append(abs(first[1] - second[1]) / 2.0)
        return clamp(1.0 - sum(distances) / len(distances), 0.0, 1.0) if distances else 0.75
