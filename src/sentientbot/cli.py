from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentientbot.app import SentientApplication
from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.ui import CSS, build_interface


def main() -> None:
    parser = argparse.ArgumentParser(description="EmotiWeave｜情绪织谱")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config.yaml")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    app = SentientApplication(config)
    if args.check:
        print(json.dumps(app.health(), ensure_ascii=False, indent=2))
        return
    build_interface(app).launch(
        server_name=config.system.host,
        server_port=config.system.port,
        inbrowser=config.system.open_browser and not args.no_browser,
        share=args.share,
        show_error=True,
        css=CSS,
        footer_links=[],
    )


if __name__ == "__main__":
    main()
