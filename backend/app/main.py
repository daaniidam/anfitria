"""Punto de entrada de la API de AnfitrIA."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import (
    audit,
    auth,
    buildings,
    conversations,
    metrics,
    notifications,
    properties,
    whatsapp,
)
from app.config import get_settings
from app.db import init_db
from app.ratelimit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def _rate_limit_handler(request, exc):  # noqa: ANN001
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiadas peticiones, prueba de nuevo en un momento."},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Rate limiting (fuerza bruta / spam).
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

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
    app.include_router(notifications.router)
    app.include_router(audit.router)
    return app


app = create_app()
