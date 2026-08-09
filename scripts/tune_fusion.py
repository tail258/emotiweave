from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.dataset import load_dataset
from sentientbot.evaluation.search import SearchGrid, search_fusion


def main() -> None:
    parser = argparse.ArgumentParser(description="只在开发集上搜索 EmotiWeave 融合参数")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config.yaml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    samples = load_dataset(args.dataset, split="dev")
    results = search_fusion(samples, load_config(args.config), SearchGrid.default())
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "search_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = ["rank", "status", "safe", "parameters", "metrics"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, result in enumerate(results, 1):
            writer.writerow(
                {
                    "rank": rank,
                    "status": result.status,
                    "safe": result.safe,
                    "parameters": json.dumps(result.parameters, ensure_ascii=False, sort_keys=True),
                    "metrics": json.dumps(
                        result.metrics.as_dict(), ensure_ascii=False, sort_keys=True
                    ),
                }
            )
    best = results[0]
    with (args.output / "best_config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"affect": best.parameters}, handle, allow_unicode=True, sort_keys=False)
    with (args.output / "selection.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "status": best.status,
                "safe": best.safe,
                "parameters": best.parameters,
                "metrics": best.metrics.as_dict(),
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    print(
        json.dumps(
            {"status": best.status, "safe": best.safe, "output": str(args.output)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
