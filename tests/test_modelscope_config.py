from sentientbot.config import PROJECT_ROOT, load_config


def test_modelscope_config_disables_local_only_services() -> None:
    config = load_config(PROJECT_ROOT / "config.modelscope.yaml")
    assert config.system.host == "0.0.0.0"
    assert config.system.port == 7860
    assert config.system.open_browser is False
    assert config.brain.enabled is False
    assert config.brain.warmup_on_start is False
    assert config.audio.enabled is False
    assert config.audio.feature_analysis_enabled is True
    assert config.voice.enabled is False
    assert config.privacy.log_events is False
    assert config.privacy.store_transcripts is False
    assert config.privacy.store_raw_media is False
