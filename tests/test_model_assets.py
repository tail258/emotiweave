from pathlib import Path

from sentientbot.model_assets import ensure_face_landmarker


def test_ensure_face_landmarker_copies_and_validates_local_asset(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.task"
    source.write_bytes(b"valid-model")
    target = tmp_path / "models" / "face_landmarker.task"

    ok, _ = ensure_face_landmarker(
        target,
        url=source.as_uri(),
        minimum_bytes=4,
    )

    assert ok is True
    assert target.read_bytes() == b"valid-model"


def test_ensure_face_landmarker_degrades_when_download_fails(tmp_path: Path) -> None:
    target = tmp_path / "face_landmarker.task"

    ok, message = ensure_face_landmarker(
        target,
        url=(tmp_path / "missing.task").as_uri(),
        minimum_bytes=4,
    )

    assert ok is False
    assert "下载失败" in message
    assert not target.exists()
