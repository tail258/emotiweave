from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.dataset import load_dataset
from sentientbot.evaluation.replay import replay_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="离线回放 EmotiWeave 多模态样本")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config.yaml")
    parser.add_argument("--split", choices=("dev", "test", "scripted"), default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    samples = load_dataset(args.dataset, split=args.split)
    if not samples:
        raise SystemExit("dataset split is empty")
    records = replay_dataset(samples, load_config(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")
    failed = sum(record.error is not None for record in records)
    print(
        json.dumps(
            {"completed": len(records) - failed, "failed": failed, "output": str(args.output)},
            ensure_ascii=False,
        )
    )
    if failed == len(records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
