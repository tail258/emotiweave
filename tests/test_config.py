from sentientbot.config import PROJECT_ROOT, load_config


def test_default_config_has_no_robot_hardware_sections() -> None:
    config = load_config(PROJECT_ROOT / "config.yaml")
    assert config.system.name == "EmotiWeave"
    assert config.privacy.store_raw_media is False
    assert config.vision.max_faces == 1
    assert config.audio.feature_analysis_enabled is True


def test_affect_fusion_parameters_can_be_overridden(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "affect:\n"
        "  audio_arousal_weight: 0.8\n"
        "  minimum_modality_confidence: 0.3\n"
        "  conflict_min_confidence: 0.5\n"
        "  text_hold_seconds: 5.0\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.affect.audio_arousal_weight == 0.8
    assert config.affect.minimum_modality_confidence == 0.3
    assert config.affect.conflict_min_confidence == 0.5
    assert config.affect.text_hold_seconds == 5.0
