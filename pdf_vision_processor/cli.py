"""Console entry point for ``pdf-vision-processor``."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv
import uvicorn

from . import __version__
from .settings import AppSettings, apply_runtime_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-vision-processor",
        description="Serve the PDF Vision Processor API",
    )
    parser.add_argument("--host", help="Host interface to bind", default=None)
    parser.add_argument("--port", type=int, help="Port to bind", default=None)
    parser.add_argument("--log-level", choices=["critical", "error", "warning", "info", "debug", "trace"], default=None)
    parser.add_argument("--config", type=Path, help="Path to config.toml file", default=None)
    parser.add_argument("--env-file", type=Path, help="Path to .env file", default=None)
    parser.add_argument("--data-dir", type=Path, help="Override data directory", default=None)
    parser.add_argument("--logs-dir", type=Path, help="Override logs directory", default=None)
    parser.add_argument("--home", type=Path, help="Override application home directory", default=None)
    parser.add_argument("--database-url", help="Override SQLAlchemy database URL", default=None)
    parser.add_argument("--version", action="store_true", help="Print package version and exit")
    parser.add_argument("--reload", dest="reload", action="store_true", help="Enable autoreload (development only)")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable autoreload")
    parser.set_defaults(reload=None)
    return parser


def _resolve_env_file(candidate: Path | None) -> Path | None:
    if candidate and candidate.exists():
        return candidate
    default_env = Path.cwd() / ".env"
    return default_env if default_env.exists() else None


def _load_env_file(path: Path | None) -> None:
    if path:
        load_dotenv(path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return

    env_file = _resolve_env_file(args.env_file)
    if env_file:
        _load_env_file(env_file)
        args.env_file = env_file

    settings = AppSettings.from_sources(cli_args=args, config_path=args.config)
    apply_runtime_settings(settings)

    uvicorn.run(
        "pdf_vision_processor.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )

if __name__ == "__main__":  # pragma: no cover
    main()
