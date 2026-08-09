from __future__ import annotations

from sentientbot.models import (
    AffectLabel,
    AffectState,
    InteractionStrategy,
    ResponsePlan,
)


class InteractionPolicy:
    def choose(self, state: AffectState) -> ResponsePlan:
        if state.conflict:
            return ResponsePlan(
                strategy=InteractionStrategy.CLARIFY_CONFLICT,
                allow_emotion_language=False,
                reason="多模态线索冲突",
                prompt_context=(
                    "语言和可见表情线索不完全一致。不要断言用户的真实情绪；"
                    "先回应用户原话，再用一个自然问题确认用户是否愿意多说。"
                ),
                fallback_reply="我听见你这样说了，不过这些线索不太一致。你愿意再说说现在的感受吗？",
            )

        if state.confidence < 0.28 or state.label is AffectLabel.UNKNOWN:
            return ResponsePlan(
                strategy=InteractionStrategy.INVITE_CORRECTION,
                allow_emotion_language=False,
                reason="可用线索不足",
                prompt_context=(
                    "当前情绪线索不足。正常回应用户内容，不猜测情绪，也不要提及摄像头。"
                ),
                fallback_reply="我在听。你可以继续说说刚才最在意的部分。",
            )

        if state.label in {AffectLabel.LOW, AffectLabel.TENSE}:
            return ResponsePlan(
                strategy=InteractionStrategy.SUPPORT,
                allow_emotion_language=True,
                reason="融合状态偏负向",
                prompt_context=(
                    "可观察线索偏负向，但这只是估计。使用克制、支持性的语气，"
                    "不要诊断，不说“我知道你很难过”，而是给用户纠正空间。"
                ),
                fallback_reply="听起来这件事可能让你不太轻松。你想先从哪一部分说起？",
            )

        if state.label in {AffectLabel.POSITIVE, AffectLabel.EXCITED}:
            return ResponsePlan(
                strategy=InteractionStrategy.MIRROR_POSITIVE,
                allow_emotion_language=True,
                reason="融合状态偏正向",
                prompt_context=(
                    "可观察线索偏正向。自然地呼应这种能量，但不要夸张，也不要声称读心。"
                ),
                fallback_reply="听上去这是个不错的进展。哪一点最让你满意？",
            )

        return ResponsePlan(
            strategy=InteractionStrategy.NEUTRAL,
            allow_emotion_language=False,
            reason="状态平稳或接近中性",
            prompt_context="保持自然、简短、好奇的语气，围绕用户原话继续交流。",
            fallback_reply="明白了。你接下来最想处理的是哪一件事？",
        )
