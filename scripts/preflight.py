from __future__ import annotations

import importlib.util
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sentientbot.config import load_config  # noqa: E402


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def main() -> None:
    config = load_config()
    required_modules = ("yaml", "numpy", "cv2", "mediapipe", "gradio", "plotly")
    optional_modules = ("faster_whisper", "requests", "pyttsx3")
    required = {
        "python_3_11_or_3_12": (3, 11) <= sys.version_info[:2] < (3, 13),
        "face_landmarker_model": config.vision.model_path.exists(),
        "port_available": _port_available(config.system.host, config.system.port),
        **{
            f"module_{name}": importlib.util.find_spec(name) is not None
            for name in required_modules
        },
    }
    optional = {
        f"module_{name}": importlib.util.find_spec(name) is not None for name in optional_modules
    }
    result = {
        "ok": all(required.values()),
        "required": required,
        "optional": optional,
        "port": config.system.port,
        "hint": (
            "必需项通过，可以启动服务。"
            if all(required.values())
            else "存在必需项失败，请按 README 的安装步骤修复。"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
