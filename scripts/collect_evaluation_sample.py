from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentientbot.config import PROJECT_ROOT
from sentientbot.evaluation.dataset import append_sample, load_dataset, validate_dataset
from sentientbot.evaluation.schema import EvaluationSample
from sentientbot.models import AffectLabel


def main() -> None:
    parser = argparse.ArgumentParser(description="追加或校验 EmotiWeave 标注样本")
    parser.add_argument("--validate", type=Path, help="只校验已有 JSONL 数据集")
    parser.add_argument(
        "--manifest", type=Path, default=PROJECT_ROOT / "data/evaluation/manifest.jsonl"
    )
    parser.add_argument("--scenario-id")
    parser.add_argument("--split", choices=("dev", "test"))
    parser.add_argument("--participant-group")
    parser.add_argument(
        "--label", choices=tuple(label.value for label in AffectLabel if label.value != "unknown")
    )
    parser.add_argument("--valence", type=float)
    parser.add_argument("--arousal", type=float)
    parser.add_argument("--transcript", default="")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--consent-recorded", action="store_true")
    args = parser.parse_args()

    if args.validate:
        summary = validate_dataset(load_dataset(args.validate), require_all_splits=True)
        print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
        return

    required = {
        "--scenario-id": args.scenario_id,
        "--split": args.split,
        "--participant-group": args.participant_group,
        "--label": args.label,
        "--valence": args.valence,
        "--arousal": args.arousal,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    if not args.consent_recorded:
        parser.error("--consent-recorded is required for participant samples")
    if not any((args.transcript.strip(), args.video, args.audio)):
        parser.error("provide at least one of --transcript, --video, or --audio")

    for name, value in (("--video", args.video), ("--audio", args.audio)):
        if value is not None:
            if value.is_absolute():
                parser.error(f"{name} must be relative to the manifest")
            if not (args.manifest.parent / value).is_file():
                parser.error(f"{name} does not exist: {args.manifest.parent / value}")

    row = {
        "scenario_id": args.scenario_id,
        "split": args.split,
        "sample_kind": "participant",
        "participant_group": args.participant_group,
        "consent_recorded": True,
        "target": {"valence": args.valence, "arousal": args.arousal, "label": args.label},
        "expected_conflicts": [],
        "transcript": args.transcript,
        "video_path": args.video.as_posix() if args.video else None,
        "audio_path": args.audio.as_posix() if args.audio else None,
    }
    sample = EvaluationSample.from_dict(row, args.manifest.parent)
    summary = append_sample(args.manifest, sample)
    print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
