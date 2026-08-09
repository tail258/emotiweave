from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentientbot.app import SentientApplication
from sentientbot.config import load_config
from sentientbot.ui.gradio_app import CSS, build_interface

ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EmotiWeave｜情绪织谱：本地多模态情绪交互工具"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--check", action="store_true", help="检查依赖与模型后退出")
    parser.add_argument("--share", action="store_true", help="创建 Gradio 临时分享链接")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    parser.add_argument("--host", help="覆盖配置中的监听地址")
    parser.add_argument("--port", type=int, help="覆盖配置中的监听端口")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    application = SentientApplication(config)

    if args.check:
        print(json.dumps(application.health(), ensure_ascii=False, indent=2))
        return

    interface = build_interface(application)
    interface.launch(
        server_name=args.host or config.system.host,
        server_port=args.port or config.system.port,
        inbrowser=config.system.open_browser and not args.no_browser,
        share=args.share,
        show_error=True,
        css=CSS,
        footer_links=[],
    )


if __name__ == "__main__":
    main()
