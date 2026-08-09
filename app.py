from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from sentientbot.app import SentientApplication  # noqa: E402
from sentientbot.config import load_config  # noqa: E402
from sentientbot.model_assets import ensure_face_landmarker  # noqa: E402
from sentientbot.ui.gradio_app import CSS, build_interface  # noqa: E402

PUBLIC_CONFIG = ROOT / "config.modelscope.yaml"
FACE_LANDMARKER = ROOT / "assets/models/face_landmarker.task"


def create_demo() -> tuple[Any, SentientApplication, str]:
    _, model_message = ensure_face_landmarker(FACE_LANDMARKER)
    config = load_config(PUBLIC_CONFIG)
    application = SentientApplication(config)
    interface = build_interface(application)
    return interface, application, model_message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EmotiWeave ModelScope deployment")
    parser.add_argument("--check", action="store_true", help="检查公网配置后退出")
    args = parser.parse_args(argv)

    interface, application, model_message = create_demo()
    if args.check:
        health = application.health(ping_ollama=False)
        health["model_preparation"] = model_message
        print(json.dumps(health, ensure_ascii=False, indent=2))
        return 0

    port = int(os.getenv("PORT", "7860"))
    interface.queue(default_concurrency_limit=1, max_size=16).launch(
        server_name="0.0.0.0",
        server_port=port,
        inbrowser=False,
        share=False,
        show_error=False,
        css=CSS,
        footer_links=[],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
