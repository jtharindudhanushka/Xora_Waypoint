"""Application factory. Modules register their routers under /api/v1 (docs/05-api-contract.md)."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.ops.clock_router import router as clock_router
from app.modules.stream.router import router as stream_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.settings = settings

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    for router in (health_router, auth_router, clock_router, stream_router):
        api.include_router(router)
    app.include_router(api)
    return app


app = create_app()
