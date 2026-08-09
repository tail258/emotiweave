from sentientbot.config import PROJECT_ROOT


def test_modelscope_entry_and_version_pin_exist() -> None:
    entry = PROJECT_ROOT / "app.py"
    assert entry.exists()
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "gradio==6.17.3" in requirements


def test_modelscope_entry_uses_public_config() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "config.modelscope.yaml" in source
    assert 'server_name="0.0.0.0"' in source


def test_public_interface_exposes_agpl_source_link() -> None:
    source = (PROJECT_ROOT / "src/sentientbot/ui/gradio_app.py").read_text(
        encoding="utf-8"
    )
    assert "https://github.com/tail258/emotiweave" in source
