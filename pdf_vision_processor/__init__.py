"""PDF Vision Processor packaged application."""

from ._version import __version__

__all__ = ["__version__", "create_app", "get_app"]


def create_app(*args, **kwargs):
	from .main import create_app as _create_app

	return _create_app(*args, **kwargs)


def get_app():
	from .main import app

	return app


def __getattr__(name):  # pragma: no cover - compatibility shim
	if name == "app":
		return get_app()
	raise AttributeError(name)
