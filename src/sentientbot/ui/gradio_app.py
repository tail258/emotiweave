from __future__ import annotations

import html
import time
from collections.abc import Iterator
from typing import Any

from sentientbot.app import SentientApplication
from sentientbot.models import AffectLabel, AffectState

CSS = """
:root {
  color-scheme: light;
  --sb-ink: #2B2D42;
  --sb-paper: #F6F0E2;
  --sb-sand: #D8C6B2;
  --sb-surface: #FFFCF5;
  --sb-muted: #666879;
  --sb-success: #536B58;
  --sb-warning: #8A6847;
  --sb-danger: #984F4A;
  --sb-line: rgba(43, 45, 66, .16);
  --sb-shadow: 0 14px 36px rgba(43, 45, 66, .09);
}

.gradio-container {
  background: var(--sb-paper) !important;
  color: var(--sb-ink) !important;
  font-family: "Microsoft YaHei UI", "Noto Sans SC", sans-serif !important;
  overflow-x: hidden;
  padding-left: max(16px, env(safe-area-inset-left));
  padding-right: max(16px, env(safe-area-inset-right));
  -webkit-tap-highlight-color: rgba(43, 45, 66, .14);
}

.sb-skip {
  position: fixed;
  left: 16px;
  top: -60px;
  z-index: 1000;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--sb-ink);
  color: var(--sb-paper) !important;
}
.sb-skip:focus { top: 12px; }

.sb-shell {
  max-width: 1380px;
  margin: 0 auto;
}
.sb-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 420px);
  gap: 32px;
  align-items: center;
  margin: 16px 0 12px;
  padding: 26px 30px;
  border: 1px solid rgba(246, 240, 226, .18);
  border-radius: 20px;
  background: var(--sb-ink);
  color: var(--sb-paper);
  box-shadow: var(--sb-shadow);
}
.sb-kicker {
  color: var(--sb-sand);
  font: 650 11px/1.4 "Cascadia Mono", Consolas, monospace;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.sb-header h1 {
  margin: 7px 0 0;
  color: var(--sb-paper);
  font: 650 clamp(30px, 4vw, 46px)/1.02 "Bahnschrift SemiCondensed",
    "Microsoft YaHei UI", sans-serif;
  letter-spacing: -.02em;
  text-wrap: balance;
}
.sb-header-note {
  margin: 0;
  padding-left: 18px;
  border-left: 2px solid var(--sb-sand);
  color: rgba(246, 240, 226, .78);
  font-size: 13px;
  line-height: 1.8;
  text-wrap: pretty;
}
.sb-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 18px;
}
.sb-strip span {
  padding: 7px 10px;
  border: 1px solid var(--sb-line);
  border-radius: 999px;
  background: rgba(216, 198, 178, .38);
  color: var(--sb-muted);
  font: 550 11px/1.2 "Cascadia Mono", Consolas, monospace;
}
.sb-strip b {
  color: var(--sb-ink);
  font-weight: 700;
}

.gradio-container .block,
.sb-panel {
  border-color: var(--sb-line) !important;
  background: var(--sb-surface) !important;
  color: var(--sb-ink) !important;
  box-shadow: none !important;
}
.sb-panel {
  padding: 17px;
  border: 1px solid var(--sb-line);
  border-radius: 14px;
}
.sb-section-title {
  margin-bottom: 8px;
  color: var(--sb-muted);
  font: 650 10px/1.35 "Cascadia Mono", Consolas, monospace;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.sb-help {
  color: var(--sb-muted);
  font-size: 12px;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.sb-state {
  padding: 20px;
  border: 1px solid rgba(43, 45, 66, .28);
  border-radius: 16px;
  background:
    linear-gradient(var(--sb-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--sb-line) 1px, transparent 1px),
    var(--sb-surface);
  background-size: 25px 25px;
  box-shadow: var(--sb-shadow);
}
.sb-state-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.sb-label {
  color: var(--sb-ink);
  font: 650 28px/1.08 "Bahnschrift SemiCondensed", "Microsoft YaHei UI", sans-serif;
  text-wrap: balance;
}
.sb-badge {
  padding: 6px 9px;
  border: 1px solid rgba(43, 45, 66, .24);
  border-radius: 999px;
  background: var(--sb-sand);
  color: var(--sb-ink);
  font: 650 10px/1 "Cascadia Mono", Consolas, monospace;
  white-space: nowrap;
}
.sb-badge.conflict {
  border-color: rgba(152, 79, 74, .34);
  background: rgba(152, 79, 74, .10);
  color: var(--sb-danger);
}
.sb-meters {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 9px;
  margin: 18px 0 14px;
}
.sb-meter {
  padding: 10px;
  border: 1px solid var(--sb-line);
  border-radius: 10px;
  background: var(--sb-paper);
}
.sb-meter small {
  display: block;
  margin-bottom: 5px;
  color: var(--sb-muted);
  font-size: 10px;
}
.sb-meter strong {
  color: var(--sb-ink);
  font: 700 17px/1 "Cascadia Mono", Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.sb-reason {
  color: var(--sb-muted);
  font-size: 13px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.sb-progress {
  height: 5px;
  margin-top: 13px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--sb-sand);
}
.sb-progress > i {
  display: block;
  height: 100%;
  background: var(--sb-ink);
}

.sb-runtime {
  display: block;
  padding: 3px 1px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.sb-status-ok { color: var(--sb-success); }
.sb-status-warn { color: var(--sb-warning); }
.sb-status-error { color: var(--sb-danger); }

.gradio-container button {
  touch-action: manipulation;
}
.gradio-container button.primary {
  border-color: var(--sb-ink) !important;
  background: var(--sb-ink) !important;
  color: var(--sb-paper) !important;
  font-weight: 700 !important;
}
.gradio-container button.primary:hover {
  border-color: #3A3D58 !important;
  background: #3A3D58 !important;
}
.gradio-container button.secondary,
.gradio-container .block button:not(.primary):not(.secondary) {
  border-color: rgba(43, 45, 66, .20) !important;
  background: var(--sb-sand) !important;
  color: var(--sb-ink) !important;
}
.gradio-container button.secondary:hover,
.gradio-container .block button:not(.primary):not(.secondary):hover {
  background: #CDB7A0 !important;
}
.gradio-container button:focus-visible,
.gradio-container input:focus-visible,
.gradio-container textarea:focus-visible,
.gradio-container [role="button"]:focus-visible {
  outline: 3px solid rgba(43, 45, 66, .42) !important;
  outline-offset: 2px;
}
.gradio-container textarea,
.gradio-container input {
  border-color: var(--sb-line) !important;
  background: #FFFAF0 !important;
  color: var(--sb-ink) !important;
}
.gradio-container label,
.gradio-container label span,
.gradio-container .prose,
.gradio-container .prose h1,
.gradio-container .prose h2,
.gradio-container .prose h3,
.gradio-container .prose h4 {
  color: var(--sb-ink) !important;
}
.gradio-container .prose h2 {
  scroll-margin-top: 16px;
  font: 650 19px/1.35 "Bahnschrift SemiCondensed", "Microsoft YaHei UI", sans-serif;
  letter-spacing: .02em;
  text-wrap: balance;
}
.gradio-container .sb-header h1 {
  color: var(--sb-paper) !important;
}
.gradio-container .sb-header-note {
  color: rgba(246, 240, 226, .78) !important;
}
.gradio-container select {
  border-color: var(--sb-line) !important;
  background: var(--sb-surface) !important;
  color: var(--sb-ink) !important;
}
.gradio-container select:focus-visible {
  outline: 3px solid rgba(43, 45, 66, .42) !important;
  outline-offset: 2px;
}
.sb-corrections button { min-height: 42px; }
.sb-footer {
  margin-top: 24px;
  padding: 18px 2px calc(30px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--sb-line);
  color: var(--sb-muted);
  font-size: 12px;
  line-height: 1.75;
}

@media (max-width: 760px) {
  .sb-header {
    grid-template-columns: 1fr;
    gap: 18px;
    padding: 22px;
  }
  .sb-meters { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    scroll-behavior: auto !important;
    transition: none !important;
  }
}
"""


LABELS = {
    AffectLabel.UNKNOWN: "等待有效线索",
    AffectLabel.NEUTRAL: "接近中性",
    AffectLabel.CALM: "低激活 / 平静",
    AffectLabel.POSITIVE: "偏积极",
    AffectLabel.EXCITED: "积极 / 高激活",
    AffectLabel.LOW: "低落倾向",
    AffectLabel.TENSE: "紧张倾向",
}


def _state_card(
    state: AffectState,
    calibration_progress: float,
    correction_note: str = "",
) -> str:
    badge_class = "sb-badge conflict" if state.conflict else "sb-badge"
    badge = "线索冲突" if state.conflict else "可纠正估计"
    reason = html.escape(correction_note or state.reason or "等待观察")
    return f"""
    <section class="sb-state" aria-live="polite">
      <div class="sb-section-title">当前状态 / Live estimate</div>
      <div class="sb-state-head">
        <div class="sb-label">{LABELS[state.label]}</div>
        <span class="{badge_class}">{badge}</span>
      </div>
      <div class="sb-meters">
        <div class="sb-meter"><small>效价 VALENCE</small><strong>{state.valence:+.2f}</strong></div>
        <div class="sb-meter"><small>激活 AROUSAL</small><strong>{state.arousal:+.2f}</strong></div>
        <div class="sb-meter">
          <small>可信 CONFIDENCE</small><strong>{state.confidence:.0%}</strong>
        </div>
      </div>
      <div class="sb-reason">{reason}</div>
      <div class="sb-progress" title="个人中性基线校准进度">
        <i style="width:{calibration_progress:.0%}"></i>
      </div>
    </section>
    """


def _affect_plot(states: list[AffectState]) -> Any:
    import plotly.graph_objects as go

    if not states:
        states = [AffectState(timestamp_ms=0)]
    states = states[-80:]
    x = [state.valence for state in states]
    y = [state.arousal for state in states]
    latest = states[-1]
    latest_color = "#984F4A" if latest.conflict else "#2B2D42"

    figure = go.Figure()
    figure.add_shape(
        type="line",
        x0=0,
        x1=0,
        y0=-1,
        y1=1,
        line={"color": "rgba(43,45,66,.22)", "width": 1},
    )
    figure.add_shape(
        type="line",
        x0=-1,
        x1=1,
        y0=0,
        y1=0,
        line={"color": "rgba(43,45,66,.22)", "width": 1},
    )
    figure.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line={"color": "#2B2D42", "width": 2},
            marker={
                "size": [3] * max(0, len(x) - 1) + [11],
                "color": ["rgba(43,45,66,.28)"] * max(0, len(x) - 1) + [latest_color],
            },
            hovertemplate="效价 %{x:.2f}<br>激活 %{y:.2f}<extra></extra>",
            showlegend=False,
        )
    )
    for ax, ay, text in (
        (-0.82, 0.88, "紧张"),
        (0.82, 0.88, "兴奋"),
        (-0.82, -0.88, "低落"),
        (0.82, -0.88, "平静积极"),
    ):
        figure.add_annotation(
            x=ax,
            y=ay,
            text=text,
            showarrow=False,
            font={"color": "#666879", "size": 11},
        )
    figure.update_layout(
        height=390,
        margin={"l": 38, "r": 20, "t": 24, "b": 38},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFCF5",
        font={"family": "Microsoft YaHei UI", "color": "#666879"},
        xaxis={
            "range": [-1, 1],
            "title": "负向  ←  效价  →  正向",
            "gridcolor": "rgba(43,45,66,.08)",
            "zeroline": False,
            "fixedrange": True,
        },
        yaxis={
            "range": [-1, 1],
            "title": "低激活  ←  激活度  →  高激活",
            "gridcolor": "rgba(43,45,66,.08)",
            "zeroline": False,
            "fixedrange": True,
        },
    )
    return figure


def _evidence_payload(
    app: SentientApplication,
    cues: dict[str, float] | None = None,
) -> dict[str, Any]:
    state = app.session.fused_state
    text = app.session.last_text_evidence
    audio = app.session.last_audio_evidence
    return {
        "state": state.as_dict(),
        "visual_cues": {key: round(value, 3) for key, value in (cues or {}).items()},
        "text_cues": (
            {
                "valence": round(text.valence, 3),
                "arousal": round(text.arousal, 3),
                "confidence": round(text.confidence, 3),
                "matched_terms": list(text.matched_terms),
            }
            if text
            else {}
        ),
        "audio_cues": (
            {
                "duration_seconds": round(audio.duration_seconds, 3),
                "arousal": round(audio.arousal, 3),
                "confidence": round(audio.confidence, 3),
                "observable_features": {
                    key: round(value, 3) for key, value in audio.features.items()
                },
                "emotion_label": None,
            }
            if audio
            else {}
        ),
        "calibration_progress": round(app.session.calibration.progress, 3),
        "raw_media_saved": False,
    }


def _runtime_status(app: SentientApplication, error: str = "") -> str:
    if error:
        return (
            '<span class="sb-runtime sb-status-error" role="status" aria-live="polite">'
            f"{html.escape(error)}</span>"
        )
    health = app.health(ping_ollama=False)
    vision = html.escape(health["vision"]["message"])
    audio = html.escape(health["audio_cues"]["message"])
    brain = html.escape(health["ollama"]["message"])
    return (
        '<span class="sb-runtime" role="status" aria-live="polite">'
        f'<span class="sb-status-ok">{vision}</span>'
        f' · <span class="sb-status-ok">{audio}</span>'
        f' · <span class="sb-status-warn">{brain}</span></span>'
    )


def build_interface(app: SentientApplication) -> Any:
    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError("缺少 Gradio，请运行：py -3.11 -m pip install -e .") from exc

    initial = app.session.fused_state
    app.brain.ping()
    app.brain.start_warmup()

    with gr.Blocks(
        title="EmotiWeave · 情绪织谱",
        fill_width=True,
    ) as interface:
        gr.HTML(
            """
            <div class="sb-shell">
              <a class="sb-skip" href="#sb-observation">跳到实时观察</a>
              <header class="sb-header">
                <div>
                  <div class="sb-kicker">Local multimodal affect workspace</div>
                  <h1>EmotiWeave</h1>
                </div>
                <p class="sb-header-note">
                  融合面部、文本和语音韵律中的可观察线索，
                  提供连续状态、置信度与冲突说明。所有判断均可由用户纠正。
                </p>
              </header>
              <div class="sb-strip" aria-label="系统特性">
                <span><b>LOCAL</b> 本地运行</span>
                <span><b>EPHEMERAL</b> 旧状态自动失效</span>
                <span><b>PRIVATE</b> 默认不保存原始媒体</span>
                <span><b>CORRECTABLE</b> 判断可纠正</span>
              </div>
            </div>
            """
        )

        with gr.Row(equal_height=False, elem_id="sb-observation"):
            with gr.Column(scale=7, min_width=420):
                gr.Markdown("## 实时观察")
                with gr.Row():
                    camera = gr.Image(
                        sources=["webcam"],
                        type="numpy",
                        streaming=True,
                        label="摄像头输入",
                        height=300,
                    )
                    processed = gr.Image(
                        label="线索叠加结果",
                        interactive=False,
                        height=300,
                    )
                runtime = gr.HTML(_runtime_status(app))
                with gr.Accordion("查看派生证据", open=False):
                    evidence = gr.JSON(
                        value=_evidence_payload(app),
                        label="派生线索",
                    )

            with gr.Column(scale=5, min_width=360):
                state_card = gr.HTML(_state_card(initial, app.session.calibration.progress))
                affect_plot = gr.Plot(
                    value=_affect_plot(app.session.trajectory_snapshot()),
                    label="效价—激活轨迹",
                )

        gr.Markdown("## 对话")
        with gr.Row(equal_height=False):
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    value=[],
                    label="会话记录",
                    height=360,
                )
                text_input = gr.Textbox(
                    label="输入内容",
                    placeholder="输入内容，或录制一段语音…",
                    lines=2,
                    html_attributes={
                        "name": "message",
                        "autocomplete": "off",
                    },
                )
                with gr.Row():
                    send = gr.Button("发送", variant="primary")
                    reset = gr.Button("清空会话", variant="secondary")

            with gr.Column(scale=5):
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="语音输入",
                )
                speak_toggle = gr.Checkbox(
                    value=app.config.voice.enabled,
                    label="播报回复",
                )
                gr.HTML(
                    """
                    <div class="sb-panel">
                      <div class="sb-section-title">融合原则</div>
                      <div class="sb-help">
                        可靠线索一致时提高可信度；线索冲突时降低可信度并优先确认；
                        证据不足时保持正常对话，不推断具体情绪。
                      </div>
                    </div>
                    """
                )

        gr.Markdown("## 校正当前判断")
        with gr.Row(elem_classes=["sb-corrections"]):
            more_positive = gr.Button("实际更积极", variant="secondary")
            accurate = gr.Button("判断基本准确", variant="secondary")
            more_negative = gr.Button("实际更消极", variant="secondary")
            uncertain = gr.Button("暂不判断", variant="secondary")

        gr.HTML(
            """
            <footer class="sb-footer">
              EmotiWeave 只估计当前可观察线索，不用于心理诊断、医疗决策或人员评估。
              默认日志不保存原始音视频与对话文本。
            </footer>
            """
        )

        def on_frame(frame: Any) -> tuple[Any, str, Any, dict[str, Any], str]:
            annotated, state, cues = app.process_frame(frame)
            return (
                annotated,
                _state_card(state, app.session.calibration.progress),
                _affect_plot(app.session.trajectory_snapshot()),
                _evidence_payload(app, cues),
                _runtime_status(app, app.last_error),
            )

        def on_load() -> Iterator[str]:
            while app.brain.warming_up:
                yield _runtime_status(app)
                time.sleep(0.25)
            yield _runtime_status(app)

        def on_submit(
            text: str,
            audio: str | None,
            history: list[dict[str, str]] | None,
            speak: bool,
        ) -> Iterator[tuple[list[dict[str, str]], str, None, str, Any, dict[str, Any], str]]:
            messages = list(history or [])
            turn_started = False
            for result in app.stream_turn(text, audio, speak):
                if result["ok"]:
                    if not turn_started:
                        messages.extend(
                            [
                                {"role": "user", "content": result["user_text"]},
                                {"role": "assistant", "content": "…"},
                            ]
                        )
                        turn_started = True
                    messages[-1] = {
                        "role": "assistant",
                        "content": result["reply"] or "…",
                    }
                    first_token = result.get("first_token_latency")
                    if result["done"]:
                        timing = f"完成 {result['latency']:.2f}s"
                        if first_token is not None:
                            timing = f"首字 {first_token:.2f}s · {timing}"
                        status = (
                            '<span class="sb-runtime sb-status-ok" role="status" '
                            f'aria-live="polite">{timing}</span>'
                        )
                    elif first_token is None:
                        status = (
                            '<span class="sb-runtime sb-status-warn" role="status" '
                            'aria-live="polite">正在生成…</span>'
                        )
                    else:
                        status = (
                            '<span class="sb-runtime sb-status-warn" role="status" '
                            f'aria-live="polite">正在生成 · 首字 {first_token:.2f}s</span>'
                        )
                else:
                    status = _runtime_status(app, result["error"])
                state = result["state"]
                yield (
                    messages,
                    "",
                    None,
                    _state_card(state, app.session.calibration.progress),
                    _affect_plot(app.session.trajectory_snapshot()),
                    _evidence_payload(app),
                    status,
                )

        def on_correct(kind: str) -> tuple[str, Any, dict[str, Any], str]:
            state = app.correct(kind)
            note = app.session.last_correction
            return (
                _state_card(state, app.session.calibration.progress, note),
                _affect_plot(app.session.trajectory_snapshot()),
                _evidence_payload(app),
                (
                    '<span class="sb-runtime sb-status-ok" role="status" '
                    f'aria-live="polite">{html.escape(note)}</span>'
                ),
            )

        def on_reset() -> tuple[
            list[dict[str, str]],
            str,
            None,
            str,
            Any,
            dict[str, Any],
            str,
        ]:
            app.reset()
            state = app.session.fused_state
            return (
                [],
                "",
                None,
                _state_card(state, app.session.calibration.progress),
                _affect_plot([]),
                _evidence_payload(app),
                _runtime_status(app),
            )

        camera.stream(
            on_frame,
            inputs=camera,
            outputs=[processed, state_card, affect_plot, evidence, runtime],
            stream_every=app.config.vision.stream_every,
            time_limit=3600,
            concurrency_limit=1,
        )
        interface.load(on_load, outputs=runtime)
        send.click(
            on_submit,
            inputs=[text_input, audio_input, chatbot, speak_toggle],
            outputs=[
                chatbot,
                text_input,
                audio_input,
                state_card,
                affect_plot,
                evidence,
                runtime,
            ],
            concurrency_limit=1,
        )
        text_input.submit(
            on_submit,
            inputs=[text_input, audio_input, chatbot, speak_toggle],
            outputs=[
                chatbot,
                text_input,
                audio_input,
                state_card,
                affect_plot,
                evidence,
                runtime,
            ],
            concurrency_limit=1,
        )
        for button, kind in (
            (more_positive, "positive"),
            (accurate, "accurate"),
            (more_negative, "negative"),
            (uncertain, "uncertain"),
        ):
            button.click(
                lambda correction_kind=kind: on_correct(correction_kind),
                outputs=[state_card, affect_plot, evidence, runtime],
                concurrency_limit=1,
            )
        reset.click(
            on_reset,
            outputs=[
                chatbot,
                text_input,
                audio_input,
                state_card,
                affect_plot,
                evidence,
                runtime,
            ],
            concurrency_limit=1,
        )

    return interface
