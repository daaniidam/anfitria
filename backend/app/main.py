"""Punto de entrada de la API de AnfitrIA."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

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

    return app


app = create_app()
