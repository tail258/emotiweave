from __future__ import annotations

import shutil
import tempfile
import urllib.request
from pathlib import Path

FACE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
MINIMUM_FACE_LANDMARKER_BYTES = 1_000_000


def ensure_face_landmarker(
    target: Path,
    *,
    url: str = FACE_LANDMARKER_URL,
    minimum_bytes: int = MINIMUM_FACE_LANDMARKER_BYTES,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str]:
    """Ensure a validated Face Landmarker asset exists without blocking startup."""

    target = Path(target)
    if target.exists() and target.stat().st_size >= minimum_bytes:
        return True, "Face Landmarker 模型已就绪"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=target.parent,
            suffix=".task.download",
        ) as handle:
            temporary = Path(handle.name)
            with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
                shutil.copyfileobj(response, handle)

        if temporary.stat().st_size < minimum_bytes:
            raise RuntimeError("下载文件过小，可能不是有效模型")
        temporary.replace(target)
        return True, "Face Landmarker 模型下载完成"
    except Exception as exc:
        return False, f"Face Landmarker 下载失败：{exc}"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
