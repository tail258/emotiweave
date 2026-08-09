from __future__ import annotations

import math
import time
import wave
from pathlib import Path

import numpy as np

from sentientbot.config import AudioConfig
from sentientbot.models import AudioEvidence, clamp


class AudioCueAnalyzer:
    """提取可观察的语音韵律特征。"""

    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self.available = config.feature_analysis_enabled
        self.message = "可解释韵律分析已就绪" if self.available else "韵律分析已在配置中关闭"

    def analyze(
        self,
        audio_path: str | Path | None,
        transcript: str = "",
        timestamp_ms: int | None = None,
    ) -> AudioEvidence:
        timestamp_ms = timestamp_ms or time.monotonic_ns() // 1_000_000
        if not audio_path or not self.available:
            return AudioEvidence(timestamp_ms=timestamp_ms)

        samples, sample_rate = self._read_pcm_wav(Path(audio_path))
        if samples.size == 0 or sample_rate <= 0:
            return AudioEvidence(timestamp_ms=timestamp_ms)

        max_samples = int(sample_rate * self.config.max_analysis_seconds)
        samples = samples[:max_samples]
        duration = samples.size / sample_rate
        frame_size = max(32, int(sample_rate * 0.04))
        hop_size = max(16, int(sample_rate * 0.02))
        frames = self._frame_signal(samples, frame_size, hop_size)
        if frames.size == 0:
            return AudioEvidence(timestamp_ms=timestamp_ms, duration_seconds=duration)

        rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
        noise_floor = float(np.percentile(rms, 20))
        upper_energy = float(np.percentile(rms, 90))
        voiced_threshold = max(0.004, min(noise_floor * 2.5, upper_energy * 0.55))
        voiced_mask = rms >= voiced_threshold
        voiced_ratio = float(np.mean(voiced_mask))
        voiced_rms = rms[voiced_mask]

        if voiced_rms.size:
            rms_mean = float(np.mean(voiced_rms))
            dynamic_range = float(np.percentile(voiced_rms, 90) - np.percentile(voiced_rms, 10))
            energy_variation = float(np.std(voiced_rms) / max(rms_mean, 1e-6))
        else:
            rms_mean = 0.0
            dynamic_range = 0.0
            energy_variation = 0.0

        pitches = self._estimate_pitches(frames, voiced_mask, sample_rate)
        pitch_median = float(np.median(pitches)) if pitches else 0.0
        pitch_variation = (
            float(np.std(pitches) / max(np.mean(pitches), 1e-6)) if len(pitches) > 1 else 0.0
        )
        speech_seconds = max(duration * voiced_ratio, 1e-6)
        speaking_rate = len("".join(transcript.split())) / speech_seconds if transcript else 0.0
        pause_ratio = 1.0 - voiced_ratio

        energy_score = clamp((rms_mean - 0.012) / 0.12, 0.0, 1.0)
        dynamics_score = clamp(energy_variation / 0.85, 0.0, 1.0)
        pitch_score = clamp(pitch_variation / 0.35, 0.0, 1.0)
        rate_score = clamp(speaking_rate / 7.0, 0.0, 1.0)
        activation_01 = (
            0.42 * energy_score
            + 0.20 * dynamics_score
            + 0.15 * pitch_score
            + 0.13 * rate_score
            + 0.10 * voiced_ratio
        )
        arousal = 2.0 * activation_01 - 1.0

        duration_factor = clamp(
            duration / max(self.config.min_duration_seconds * 2.0, 0.1),
            0.0,
            1.0,
        )
        voiced_factor = clamp(voiced_ratio / 0.35, 0.0, 1.0)
        pitch_factor = clamp(len(pitches) / max(5.0, frames.shape[0] * 0.25), 0.0, 1.0)
        confidence = duration_factor * voiced_factor * (0.72 + 0.28 * pitch_factor)
        if voiced_ratio < 0.04 or duration < self.config.min_duration_seconds:
            confidence = 0.0

        features = {
            "rms_mean": rms_mean,
            "dynamic_range": dynamic_range,
            "energy_variation": energy_variation,
            "pitch_median_hz": pitch_median,
            "pitch_variation": pitch_variation,
            "speaking_rate_cps": speaking_rate,
            "voiced_ratio": voiced_ratio,
            "pause_ratio": pause_ratio,
        }
        return AudioEvidence(
            timestamp_ms=timestamp_ms,
            duration_seconds=duration,
            valence=0.0,
            arousal=arousal,
            confidence=confidence,
            features=features,
        )

    @staticmethod
    def _read_pcm_wav(path: Path) -> tuple[np.ndarray, int]:
        if not path.exists():
            raise FileNotFoundError(f"录音文件不存在：{path}")
        try:
            with wave.open(str(path), "rb") as audio:
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                sample_rate = audio.getframerate()
                raw = audio.readframes(audio.getnframes())
        except (wave.Error, EOFError) as exc:
            raise ValueError("当前韵律分析仅支持 PCM WAV 录音") from exc

        if sample_width == 1:
            samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif sample_width == 3:
            bytes_ = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            values = (
                bytes_[:, 0].astype(np.int32)
                | (bytes_[:, 1].astype(np.int32) << 8)
                | (bytes_[:, 2].astype(np.int32) << 16)
            )
            values = np.where(values & 0x800000, values - 0x1000000, values)
            samples = values.astype(np.float32) / 8388608.0
        elif sample_width == 4:
            samples = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"不支持的 WAV 位深：{sample_width * 8} bit")

        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        samples = np.nan_to_num(samples, copy=False)
        samples -= float(np.mean(samples)) if samples.size else 0.0
        return samples, sample_rate

    @staticmethod
    def _frame_signal(samples: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
        if samples.size < frame_size:
            samples = np.pad(samples, (0, frame_size - samples.size))
        frame_count = 1 + (samples.size - frame_size) // hop_size
        starts = np.arange(frame_count)[:, None] * hop_size
        offsets = np.arange(frame_size)[None, :]
        return samples[starts + offsets] * np.hanning(frame_size)[None, :]

    @staticmethod
    def _estimate_pitches(
        frames: np.ndarray,
        voiced_mask: np.ndarray,
        sample_rate: int,
    ) -> list[float]:
        voiced_indices = np.flatnonzero(voiced_mask)
        if voiced_indices.size > 60:
            voiced_indices = voiced_indices[np.linspace(0, voiced_indices.size - 1, 60, dtype=int)]
        min_lag = max(1, int(sample_rate / 350))
        max_lag = min(frames.shape[1] - 2, int(sample_rate / 70))
        pitches: list[float] = []
        for index in voiced_indices:
            frame = frames[index]
            energy = float(np.dot(frame, frame))
            if energy <= 1e-8 or max_lag <= min_lag:
                continue
            spectrum = np.fft.rfft(frame, n=2 * frame.size)
            autocorrelation = np.fft.irfft(spectrum * np.conj(spectrum))[: frame.size]
            candidates = autocorrelation[min_lag : max_lag + 1]
            peak_offset = int(np.argmax(candidates))
            peak = float(candidates[peak_offset] / max(autocorrelation[0], 1e-8))
            if math.isfinite(peak) and peak >= 0.28:
                pitches.append(sample_rate / (min_lag + peak_offset))
        return pitches
