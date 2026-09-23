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


# Rutas exentas de CSRF: no hay sesión aún (login/registro/refresh) o usan otra
# verificación (webhook de WhatsApp con firma HMAC).
_CSRF_EXEMPT = ("/auth/login", "/auth/register", "/auth/refresh", "/channels/whatsapp/webhook")
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


async def _csrf_middleware(request, call_next):  # noqa: ANN001
    """Protección CSRF double-submit para mutaciones autenticadas por cookie.

    Si la petición trae `Authorization: Bearer` (API/curl) no hay riesgo CSRF y se
    omite. Para el flujo por cookie, exige que la cabecera X-CSRF-Token coincida con
    la cookie csrf_token.
    """
    from fastapi.responses import JSONResponse

    from app.deps import ACCESS_COOKIE, CSRF_COOKIE

    if (
        request.method not in _SAFE_METHODS
        and not request.url.path.startswith(_CSRF_EXEMPT)
        and request.headers.get("Authorization") is None
        and request.cookies.get(ACCESS_COOKIE) is not None
    ):
        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or cookie_token != header_token:
            return JSONResponse(status_code=403, content={"detail": "CSRF token inválido"})

    return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Rate limiting (fuerza bruta / spam).
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.middleware("http")(_csrf_middleware)

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
