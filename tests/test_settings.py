from __future__ import annotations

from types import SimpleNamespace

from pdf_vision_processor.settings import (
    AppSettings,
    apply_runtime_settings,
    get_settings,
    reset_settings_cache,
)


def _namespace(**kwargs):
    return SimpleNamespace(**kwargs)


def _clear_env(monkeypatch):
    for suffix in ("HOST", "PORT", "RELOAD", "LOG_LEVEL", "HOME", "DATA_DIR", "LOG_DIR", "DATABASE_URL"):
        monkeypatch.delenv(f"PDF_VISION_PROCESSOR_{suffix}", raising=False)


def test_cli_overrides_environment(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PDF_VISION_PROCESSOR_HOST", "0.0.0.0")
    monkeypatch.setenv("PDF_VISION_PROCESSOR_PORT", "7000")
    args = _namespace(
        host="1.2.3.4",
        port=8123,
        reload=True,
        log_level="debug",
        home=None,
        data_dir=tmp_path / "data-alt",
        logs_dir=None,
        database_url="sqlite:///tmp.db",
        env_file=None,
        config=None,
    )

    settings = AppSettings.from_sources(cli_args=args)
    assert settings.host == "1.2.3.4"
    assert settings.port == 8123
    assert settings.reload is True
    assert str(settings.data_dir).endswith("data-alt")


def test_config_file_loaded(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    config = tmp_path / "config.toml"
    config.write_text(
        """
[server]
host = "0.0.0.0"
port = 9999
reload = true
log_level = "warning"

[paths]
home = "./state"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = AppSettings.from_sources(config_path=config)
    assert settings.host == "0.0.0.0"
    assert settings.port == 9999
    assert settings.reload is True
    assert "state" in str(settings.home_dir)


def test_apply_runtime_settings_sets_environment(tmp_path):
    reset_settings_cache()
    settings = AppSettings(home_dir=tmp_path / "home-test", host="0.0.0.0", port=8100)
    apply_runtime_settings(settings)

    assert settings.data_dir.exists()
    assert settings.logs_dir.exists()

    try:
        resolved = get_settings()
        assert resolved.host == "0.0.0.0"
        assert resolved.port == 8100
    finally:
        reset_settings_cache()
