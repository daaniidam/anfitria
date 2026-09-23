"""Punto de entrada de la API de AnfitrIA."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, buildings, conversations, metrics, properties, whatsapp
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "ai_provider": settings.ai_provider,
            "channel_provider": settings.channel_provider,
        }

    app.include_router(auth.router)
    app.include_router(buildings.router)
    app.include_router(properties.router)
    app.include_router(conversations.router)
    app.include_router(whatsapp.router)
    app.include_router(metrics.router)
    return app


app = create_app()
