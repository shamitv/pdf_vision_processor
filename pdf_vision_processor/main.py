from __future__ import annotations

from contextlib import asynccontextmanager
from importlib import resources
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import database, models, routes
from .settings import AppSettings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema exists before serving requests."""
    models.Base.metadata.create_all(bind=database.engine)
    yield


def _resource_path(*parts: str) -> str:
    return str(resources.files("pdf_vision_processor").joinpath(*parts))


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    """Construct a FastAPI application wired with packaged assets."""
    settings = settings or get_settings()
    application = FastAPI(title="PDF Vision Processor", lifespan=lifespan)

    static_dir = _resource_path("static")
    application.mount("/static", StaticFiles(directory=static_dir), name="static")

    settings.ensure_directories()
    application.mount("/data", StaticFiles(directory=str(settings.data_dir)), name="data")

    application.include_router(routes.router)

    @application.get("/")
    def read_root():  # pragma: no cover - trivial response
        return {"message": "Welcome to PDF Vision Processor API"}

    return application


app = create_app()
