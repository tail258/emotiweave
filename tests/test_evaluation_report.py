from pathlib import Path

from sentientbot.config import PROJECT_ROOT, load_config
from sentientbot.evaluation.dataset import load_dataset
from sentientbot.evaluation.replay import replay_dataset
from sentientbot.evaluation.report import write_report


def test_report_writes_all_required_artifacts(tmp_path: Path) -> None:
    samples = load_dataset(
        PROJECT_ROOT / "evaluation/datasets/scripted_conflicts.jsonl", split="scripted"
    )
    records = replay_dataset(samples, load_config(PROJECT_ROOT / "config.yaml"))
    write_report(records, tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == {
        "summary.json",
        "metrics.md",
        "per_sample.csv",
        "confusion_matrix.csv",
        "confusion_matrix.html",
        "va_scatter.html",
    }


def test_report_marks_scripted_results_separately(tmp_path: Path) -> None:
    samples = load_dataset(
        PROJECT_ROOT / "evaluation/datasets/scripted_conflicts.jsonl", split="scripted"
    )
    records = replay_dataset(samples, load_config(PROJECT_ROOT / "config.yaml"))
    write_report(records, tmp_path)
    text = (tmp_path / "metrics.md").read_text(encoding="utf-8")
    assert "scripted" in text
    assert "participant" in text
