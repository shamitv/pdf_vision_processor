"""Compatibility shim for legacy imports.

The application package moved to ``pdf_vision_processor``. Importers that still rely on
``app`` keep working by re-exporting the FastAPI application factory.
"""
from pdf_vision_processor import __version__, create_app, get_app

app = get_app()

__all__ = ("app", "create_app", "__version__")
