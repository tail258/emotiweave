from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from sentientbot.config import AudioConfig
from sentientbot.perception.audio_cues import AudioCueAnalyzer


def _write_tone(
    path: Path,
    frequency: float = 200.0,
    amplitude: float = 0.35,
    duration: float = 1.2,
    sample_rate: int = 16_000,
) -> None:
    timeline = np.arange(int(duration * sample_rate), dtype=np.float32) / sample_rate
    samples = amplitude * np.sin(2 * np.pi * frequency * timeline)
    pcm = np.clip(samples * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def test_silence_has_no_trusted_audio_evidence(tmp_path: Path) -> None:
    path = tmp_path / "silence.wav"
    _write_tone(path, amplitude=0.0)
    evidence = AudioCueAnalyzer(AudioConfig()).analyze(path)
    assert evidence.confidence == 0
    assert evidence.features["voiced_ratio"] == 0


def test_tone_pitch_is_observable_and_close_to_frequency(tmp_path: Path) -> None:
    path = tmp_path / "tone.wav"
    _write_tone(path, frequency=200.0)
    evidence = AudioCueAnalyzer(AudioConfig()).analyze(path, transcript="这是测试语音")
    assert evidence.confidence > 0.5
    assert 185 <= evidence.features["pitch_median_hz"] <= 215


def test_transcript_contributes_only_to_speaking_rate(tmp_path: Path) -> None:
    path = tmp_path / "rate.wav"
    _write_tone(path)
    analyzer = AudioCueAnalyzer(AudioConfig())
    without_text = analyzer.analyze(path)
    with_text = analyzer.analyze(path, transcript="这是一个比较完整的句子")
    assert without_text.features["speaking_rate_cps"] == 0
    assert with_text.features["speaking_rate_cps"] > 0
    assert with_text.valence == 0


def test_disabled_audio_analysis_returns_empty_evidence(tmp_path: Path) -> None:
    path = tmp_path / "unused.wav"
    _write_tone(path)
    evidence = AudioCueAnalyzer(AudioConfig(feature_analysis_enabled=False)).analyze(path)
    assert evidence.confidence == 0
    assert evidence.features == {}
