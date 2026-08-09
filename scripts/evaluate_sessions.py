from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentientbot.evaluation.report import load_predictions, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 EmotiWeave 情绪识别评估报告")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = load_predictions(args.predictions)
    if not records:
        raise SystemExit("prediction file is empty")
    summary = write_report(records, args.output)
    print(
        json.dumps(
            {
                "sample_count": summary.sample_count,
                "failed_count": summary.failed_count,
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
