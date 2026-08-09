from __future__ import annotations

import shutil
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "assets/models/face_landmarker.task"
URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
MIN_EXPECTED_BYTES = 1_000_000


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and TARGET.stat().st_size >= MIN_EXPECTED_BYTES:
        print(f"模型已存在：{TARGET}")
        return

    print(f"下载 Face Landmarker：{URL}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".task") as handle:
        temporary = Path(handle.name)
    try:
        urllib.request.urlretrieve(URL, temporary)
        if temporary.stat().st_size < MIN_EXPECTED_BYTES:
            raise RuntimeError("下载文件过小，可能不是有效模型")
        shutil.move(str(temporary), TARGET)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"完成：{TARGET} ({TARGET.stat().st_size / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
