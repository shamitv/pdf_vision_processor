"""Application configuration helpers with layered precedence.

Order of precedence:
1. Command-line overrides supplied via ``pdf-vision-processor`` CLI.
2. Environment variables prefixed with ``PDF_VISION_PROCESSOR_``.
3. ``config.toml`` (or a user-provided config file) residing in the current working directory.
4. Built-in defaults that store data under ``~/.pdf-vision-processor``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import os
import threading

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.10
    import tomli as tomllib  # type: ignore

ENV_PREFIX = "PDF_VISION_PROCESSOR_"
DEFAULT_HOME = Path.home() / ".pdf-vision-processor"
_ACTIVE_SETTINGS: "AppSettings | None" = None
_SETTINGS_LOCK = threading.Lock()
_BOOL_TRUE = {"1", "true", "t", "yes", "y", "on"}
_BOOL_FALSE = {"0", "false", "f", "no", "n", "off"}


def _parse_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _BOOL_TRUE:
        return True
    if text in _BOOL_FALSE:
        return False
    return None


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None


def _load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


@dataclass(slots=True)
class AppSettings:
    """Container for runtime configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"
    home_dir: Path = field(default_factory=lambda: DEFAULT_HOME)
    data_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    database_url: Optional[str] = None
    env_file: Optional[Path] = None
    config_file: Optional[Path] = None
    uploads_dir: Path = field(init=False)
    images_dir: Path = field(init=False)
    llm_log_dir: Path = field(init=False)
    processing_log_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.home_dir = Path(self.home_dir).expanduser()
        if self.data_dir is None:
            self.data_dir = self.home_dir / "data"
        else:
            self.data_dir = Path(self.data_dir).expanduser()

        if self.logs_dir is None:
            self.logs_dir = self.home_dir / "logs"
        else:
            self.logs_dir = Path(self.logs_dir).expanduser()

        if self.database_url is None:
            db_path = self.home_dir / "db.sqlite3"
            self.database_url = f"sqlite:///{db_path}"

        # Derived directories
        self.uploads_dir: Path = self.data_dir / "uploads"
        self.images_dir: Path = self.data_dir / "images"
        self.llm_log_dir: Path = self.logs_dir / "llm_debug"
        self.processing_log_dir: Path = self.logs_dir / "processing"

    def ensure_directories(self) -> None:
        for directory in (
            self.home_dir,
            self.data_dir,
            self.logs_dir,
            self.uploads_dir,
            self.images_dir,
            self.llm_log_dir,
            self.processing_log_dir,
        ):
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_sources(
        cls,
        cli_args: Any | None = None,
        *,
        config_path: Path | None = None,
        env: Dict[str, str] | None = None,
    ) -> "AppSettings":
        env = env or os.environ
        config_path = _discover_config_path(config_path)
        config_data = _parse_config(config_path)

        values: Dict[str, Any] = {}

        # Config file values (lower precedence than env + CLI)
        if config_data:
            server_cfg = config_data.get("server", {})
            paths_cfg = config_data.get("paths", {})
            db_cfg = config_data.get("database", {})

            values.update({
                "host": server_cfg.get("host"),
                "port": server_cfg.get("port"),
                "reload": server_cfg.get("reload"),
                "log_level": server_cfg.get("log_level"),
                "home_dir": paths_cfg.get("home"),
                "data_dir": paths_cfg.get("data"),
                "logs_dir": paths_cfg.get("logs"),
                "database_url": db_cfg.get("url"),
            })

        # Environment variables override config
        env_map = {
            "host": env.get(f"{ENV_PREFIX}HOST"),
            "port": _parse_int(env.get(f"{ENV_PREFIX}PORT")),
            "reload": _parse_bool(env.get(f"{ENV_PREFIX}RELOAD")),
            "log_level": env.get(f"{ENV_PREFIX}LOG_LEVEL"),
            "home_dir": env.get(f"{ENV_PREFIX}HOME"),
            "data_dir": env.get(f"{ENV_PREFIX}DATA_DIR"),
            "logs_dir": env.get(f"{ENV_PREFIX}LOG_DIR"),
            "database_url": env.get(f"{ENV_PREFIX}DATABASE_URL"),
        }
        values.update({k: v for k, v in env_map.items() if v not in (None, "")})

        # CLI arguments override everything else
        if cli_args is not None:
            cli_map = {
                "host": getattr(cli_args, "host", None),
                "port": getattr(cli_args, "port", None),
                "reload": getattr(cli_args, "reload", None),
                "log_level": getattr(cli_args, "log_level", None),
                "home_dir": getattr(cli_args, "home", None),
                "data_dir": getattr(cli_args, "data_dir", None),
                "logs_dir": getattr(cli_args, "logs_dir", None),
                "database_url": getattr(cli_args, "database_url", None),
            }
            values.update({k: v for k, v in cli_map.items() if v not in (None, "")})
            values["env_file"] = getattr(cli_args, "env_file", None)
            values["config_file"] = config_path or getattr(cli_args, "config", None)
        else:
            values["config_file"] = config_path

        clean_values = {
            key: value
            for key, value in values.items()
            if value not in (None, "")
        }

        settings = cls(**clean_values)
        return settings


def _discover_config_path(explicit: Path | None) -> Path | None:
    if explicit and explicit.exists():
        return explicit
    default_path = Path.cwd() / "config.toml"
    return default_path if default_path.exists() else None


def _parse_config(path: Path | None) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        return _load_toml(path)
    except FileNotFoundError:  # pragma: no cover - race condition guard
        return {}


def apply_runtime_settings(settings: AppSettings) -> AppSettings:
    """Register settings for downstream modules and export env overrides."""
    global _ACTIVE_SETTINGS
    settings.ensure_directories()
    os.environ.setdefault(f"{ENV_PREFIX}HOME", str(settings.home_dir))
    os.environ[f"{ENV_PREFIX}DATA_DIR"] = str(settings.data_dir)
    os.environ[f"{ENV_PREFIX}LOG_DIR"] = str(settings.logs_dir)
    os.environ[f"{ENV_PREFIX}DATABASE_URL"] = str(settings.database_url)

    with _SETTINGS_LOCK:
        _ACTIVE_SETTINGS = settings
    return settings


def get_settings() -> AppSettings:
    """Return the active ``AppSettings`` instance (creating one if needed)."""
    global _ACTIVE_SETTINGS
    with _SETTINGS_LOCK:
        if _ACTIVE_SETTINGS is None:
            _ACTIVE_SETTINGS = AppSettings.from_sources()
            _ACTIVE_SETTINGS.ensure_directories()
    return _ACTIVE_SETTINGS


def reset_settings_cache() -> None:
    """Testing helper: clear cached settings so new sources can be loaded."""
    global _ACTIVE_SETTINGS
    with _SETTINGS_LOCK:
        _ACTIVE_SETTINGS = None