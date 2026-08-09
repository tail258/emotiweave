from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

from sentientbot.config import VisionConfig
from sentientbot.models import VisualEvidence, clamp


class MediaPipeFaceAnalyzer:
    """封装 MediaPipe 人脸线索分析。"""

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    )

    def __init__(self, config: VisionConfig) -> None:
        self.config = config
        self.available = False
        self.backend = "disabled"
        self.message = "视觉分析已在配置中关闭"
        self._detector: Any = None
        self._mp: Any = None
        self._cv2: Any = None
        self._last_timestamp_ms = 0

        if not config.enabled:
            return
        try:
            import cv2
            import mediapipe as mp

            self._cv2 = cv2
            self._mp = mp
        except Exception as exc:
            self.message = f"缺少视觉依赖：{exc}"
            return

        if config.model_path.exists():
            try:
                self._init_tasks(config.model_path)
                return
            except Exception as exc:
                self.message = f"Face Landmarker 初始化失败，尝试兼容模式：{exc}"

        try:
            self._init_legacy()
        except Exception as exc:
            self.message = f"视觉模型不可用：{exc}。运行 scripts/download_models.py 下载模型。"

    def _init_tasks(self, model_path: Path) -> None:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        # 直接传入模型字节，兼容包含非 ASCII 字符的 Windows 路径。
        model_buffer = model_path.read_bytes()
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_buffer),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=self.config.max_faces,
            min_face_detection_confidence=self.config.min_detection_confidence,
            min_face_presence_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._detector = vision.FaceLandmarker.create_from_options(options)
        self.available = True
        self.backend = "face_landmarker"
        self.message = "Face Landmarker 已就绪"

    def _init_legacy(self) -> None:
        solutions = getattr(self._mp, "solutions", None)
        if solutions is None:
            raise RuntimeError("当前 MediaPipe 不含 solutions 兼容接口且模型文件缺失")
        self._detector = solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=self.config.max_faces,
            refine_landmarks=True,
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )
        self.available = True
        self.backend = "face_mesh_compat"
        self.message = "使用 FaceMesh 兼容模式；下载模型后可启用 52 维 Blendshapes"

    def analyze(
        self,
        frame_bgr: Any,
        timestamp_ms: int | None = None,
    ) -> tuple[VisualEvidence, Any]:
        now_ms = timestamp_ms or time.monotonic_ns() // 1_000_000
        now_ms = max(now_ms, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = now_ms

        if frame_bgr is None:
            return VisualEvidence(now_ms, False), frame_bgr
        if not self.available:
            return VisualEvidence(now_ms, False), frame_bgr

        if self.backend == "face_landmarker":
            return self._analyze_tasks(frame_bgr, now_ms)
        return self._analyze_legacy(frame_bgr, now_ms)

    def _analyze_tasks(
        self,
        frame_bgr: Any,
        timestamp_ms: int,
    ) -> tuple[VisualEvidence, Any]:
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=rgb,
        )
        result = self._detector.detect_for_video(mp_image, timestamp_ms)
        if not result.face_landmarks:
            return VisualEvidence(timestamp_ms, False), frame_bgr

        landmarks = result.face_landmarks[0]
        categories = result.face_blendshapes[0] if result.face_blendshapes else []
        cues = {
            category.category_name: float(category.score)
            for category in categories
            if category.category_name
        }
        valence, arousal = self._blendshapes_to_affect(cues)
        confidence = self._face_confidence(landmarks)
        evidence = VisualEvidence(
            timestamp_ms=timestamp_ms,
            face_present=True,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            cues=self._explainable_cues(cues),
            source="mediapipe_blendshapes",
        )
        return evidence, self._annotate(frame_bgr, landmarks, evidence)

    def _analyze_legacy(
        self,
        frame_bgr: Any,
        timestamp_ms: int,
    ) -> tuple[VisualEvidence, Any]:
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        result = self._detector.process(rgb)
        if not result.multi_face_landmarks:
            return VisualEvidence(timestamp_ms, False), frame_bgr

        landmarks = result.multi_face_landmarks[0].landmark
        cues = self._geometry_cues(landmarks)
        valence = clamp(1.25 * cues["smile"] - 1.05 * cues["frown"])
        arousal = clamp(
            0.75 * cues["mouth_open"] + 0.55 * cues["eye_open"] + 0.45 * cues["brow_raise"] - 0.28
        )
        evidence = VisualEvidence(
            timestamp_ms=timestamp_ms,
            face_present=True,
            valence=valence,
            arousal=arousal,
            confidence=min(0.68, self._face_confidence(landmarks)),
            cues=cues,
            source="mediapipe_geometry",
        )
        return evidence, self._annotate(frame_bgr, landmarks, evidence)

    @staticmethod
    def _blendshapes_to_affect(cues: dict[str, float]) -> tuple[float, float]:
        def mean(*names: str) -> float:
            return sum(cues.get(name, 0.0) for name in names) / len(names)

        smile = mean("mouthSmileLeft", "mouthSmileRight")
        frown = mean("mouthFrownLeft", "mouthFrownRight")
        cheek = mean("cheekSquintLeft", "cheekSquintRight")
        brow_down = mean("browDownLeft", "browDownRight")
        brow_up = cues.get("browInnerUp", 0.0)
        eye_wide = mean("eyeWideLeft", "eyeWideRight")
        jaw_open = cues.get("jawOpen", 0.0)
        nose_sneer = mean("noseSneerLeft", "noseSneerRight")

        valence = clamp(
            1.35 * smile + 0.35 * cheek - 1.05 * frown - 0.52 * brow_down - 0.28 * nose_sneer
        )
        arousal = clamp(
            0.7 * jaw_open
            + 0.62 * eye_wide
            + 0.48 * brow_up
            + 0.35 * brow_down
            + 0.2 * nose_sneer
            - 0.12
        )
        return valence, arousal

    @staticmethod
    def _explainable_cues(cues: dict[str, float]) -> dict[str, float]:
        def mean(*names: str) -> float:
            return sum(cues.get(name, 0.0) for name in names) / len(names)

        return {
            "smile": mean("mouthSmileLeft", "mouthSmileRight"),
            "frown": mean("mouthFrownLeft", "mouthFrownRight"),
            "brow_tension": mean("browDownLeft", "browDownRight"),
            "brow_raise": cues.get("browInnerUp", 0.0),
            "eye_wide": mean("eyeWideLeft", "eyeWideRight"),
            "mouth_open": cues.get("jawOpen", 0.0),
        }

    @staticmethod
    def _geometry_cues(landmarks: Any) -> dict[str, float]:
        def distance(a: int, b: int) -> float:
            return math.hypot(
                landmarks[a].x - landmarks[b].x,
                landmarks[a].y - landmarks[b].y,
            )

        face_height = max(0.05, distance(10, 152))
        mouth_center_y = (landmarks[13].y + landmarks[14].y) / 2
        corner_y = (landmarks[61].y + landmarks[291].y) / 2
        curve = (mouth_center_y - corner_y) / face_height
        eye_open = (distance(159, 145) + distance(386, 374)) / (2 * face_height)
        brow_raise = (distance(105, 159) + distance(334, 386)) / (2 * face_height)
        return {
            "smile": clamp(curve * 11.0, 0.0, 1.0),
            "frown": clamp(-curve * 11.0, 0.0, 1.0),
            "mouth_open": clamp(distance(13, 14) / face_height * 7.0, 0.0, 1.0),
            "eye_open": clamp(eye_open * 8.0, 0.0, 1.0),
            "brow_raise": clamp(brow_raise * 3.2, 0.0, 1.0),
        }

    @staticmethod
    def _face_confidence(landmarks: Any) -> float:
        xs = [point.x for point in landmarks]
        ys = [point.y for point in landmarks]
        area = max(0.0, max(xs) - min(xs)) * max(0.0, max(ys) - min(ys))
        return clamp(0.48 + area * 1.8, 0.0, 0.94)

    def _annotate(
        self,
        frame_bgr: Any,
        landmarks: Any,
        evidence: VisualEvidence,
    ) -> Any:
        if not self.config.draw_landmarks:
            return frame_bgr
        output = frame_bgr.copy()
        height, width = output.shape[:2]
        points = [
            (
                int(clamp(point.x, 0.0, 1.0) * width),
                int(clamp(point.y, 0.0, 1.0) * height),
            )
            for point in landmarks
        ]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        mint = (188, 233, 111)
        ink = (25, 35, 40)
        self._cv2.rectangle(
            output,
            (max(0, min(xs) - 12), max(0, min(ys) - 12)),
            (min(width - 1, max(xs) + 12), min(height - 1, max(ys) + 12)),
            mint,
            2,
        )
        for x, y in points[::10]:
            self._cv2.circle(output, (x, y), 1, mint, -1)
        self._cv2.rectangle(output, (12, 12), (310, 48), ink, -1)
        self._cv2.putText(
            output,
            f"V {evidence.valence:+.2f}   A {evidence.arousal:+.2f}",
            (24, 37),
            self._cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            mint,
            1,
            self._cv2.LINE_AA,
        )
        return output

    def close(self) -> None:
        close = getattr(self._detector, "close", None)
        if callable(close):
            close()
