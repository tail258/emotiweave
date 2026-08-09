from __future__ import annotations

from pathlib import Path

from sentientbot.model_assets import ensure_face_landmarker

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "assets/models/face_landmarker.task"


def main() -> None:
    ok, message = ensure_face_landmarker(TARGET)
    print(message)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
