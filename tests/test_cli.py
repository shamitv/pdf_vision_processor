from __future__ import annotations

from pdf_vision_processor import cli
from pdf_vision_processor.settings import reset_settings_cache


def test_cli_invokes_uvicorn(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("PDF_VISION_PROCESSOR_PORT=8123\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    captured = {}

    def fake_run(app, host, port, reload, log_level):
        captured.update({
            "app": app,
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": log_level,
        })

    monkeypatch.setattr(cli.uvicorn, "run", fake_run)

    try:
        cli.main(["--host", "0.0.0.0", "--reload", "--log-level", "info"])
    finally:
        reset_settings_cache()

    assert captured["app"] == "pdf_vision_processor.main:app"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8123
    assert captured["reload"] is True
    assert captured["log_level"] == "info"
