from __future__ import annotations

import re

from sentientbot.models import TextEvidence, clamp


class TextCueAnalyzer:
    """分析可解释的中文文本线索。"""

    POSITIVE = {
        "开心": (0.85, 0.35),
        "高兴": (0.8, 0.3),
        "快乐": (0.85, 0.25),
        "喜欢": (0.65, 0.15),
        "期待": (0.65, 0.45),
        "兴奋": (0.75, 0.9),
        "激动": (0.55, 0.9),
        "舒服": (0.55, -0.25),
        "放松": (0.5, -0.55),
        "满意": (0.65, 0.1),
        "顺利": (0.55, 0.15),
        "太棒": (0.9, 0.65),
        "很好": (0.7, 0.25),
        "不错": (0.55, 0.15),
    }
    NEGATIVE = {
        "难过": (-0.85, -0.15),
        "伤心": (-0.9, -0.2),
        "生气": (-0.85, 0.8),
        "愤怒": (-0.95, 0.95),
        "烦躁": (-0.7, 0.75),
        "烦": (-0.55, 0.45),
        "焦虑": (-0.75, 0.75),
        "紧张": (-0.65, 0.7),
        "害怕": (-0.85, 0.8),
        "担心": (-0.55, 0.5),
        "失望": (-0.75, -0.25),
        "讨厌": (-0.7, 0.35),
        "糟糕": (-0.8, 0.4),
        "疲惫": (-0.55, -0.55),
        "很累": (-0.5, -0.65),
        "不舒服": (-0.65, 0.15),
    }
    NEGATIONS = ("没有", "不是", "并不", "不太", "没", "不")
    INTENSIFIERS = ("非常", "特别", "真的", "太", "很")

    def analyze(self, text: str) -> TextEvidence:
        normalized = re.sub(r"\s+", "", text.strip().lower())
        if not normalized:
            return TextEvidence(text=text)

        matches: list[tuple[str, float, float]] = []
        lexicon = {**self.POSITIVE, **self.NEGATIVE}
        for term, (valence, arousal) in lexicon.items():
            start = normalized.find(term)
            if start < 0:
                continue
            prefix = normalized[max(0, start - 3) : start]
            negated = any(prefix.endswith(token) for token in self.NEGATIONS)
            intensified = any(prefix.endswith(token) for token in self.INTENSIFIERS)
            if negated and term not in {"不舒服"}:
                valence *= -0.72
                arousal *= 0.7
            if intensified:
                valence *= 1.18
                arousal *= 1.16
            matches.append((term, valence, arousal))

        if not matches:
            return TextEvidence(text=text)

        valence = clamp(sum(item[1] for item in matches) / len(matches))
        arousal = clamp(sum(item[2] for item in matches) / len(matches))
        confidence = min(0.92, 0.46 + 0.13 * len(matches))
        return TextEvidence(
            text=text,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            matched_terms=tuple(item[0] for item in matches),
        )
