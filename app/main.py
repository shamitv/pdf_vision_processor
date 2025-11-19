import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from . import models, database, routes
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    models.Base.metadata.create_all(bind=database.engine)
    yield

app = FastAPI(title="PDF Vision Processor", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

# Include routes
app.include_router(routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to PDF Vision Processor API"}
