from pathlib import Path
from types import SimpleNamespace

from sentientbot.app import SentientApplication


def test_health_contains_only_current_components() -> None:
    application = object.__new__(SentientApplication)
    application.config = SimpleNamespace(
        system=SimpleNamespace(name="EmotiWeave"),
        vision=SimpleNamespace(model_path=Path("face_landmarker.task")),
        privacy=SimpleNamespace(store_raw_media=False, store_transcripts=False),
    )
    application.vision = SimpleNamespace(available=True, backend="test", message="ready")
    application.transcriber = SimpleNamespace(available=True, message="ready")
    application.audio_cues = SimpleNamespace(available=True, message="ready")
    application.brain = SimpleNamespace(message="not checked")
    application.speaker = SimpleNamespace(available=False, message="disabled")

    health = application.health(ping_ollama=False)

    assert set(health) == {
        "application",
        "dependencies",
        "vision",
        "asr",
        "audio_cues",
        "ollama",
        "tts",
        "privacy",
    }
    assert "removed" not in health.values()
