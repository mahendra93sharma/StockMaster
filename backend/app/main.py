"""StockMaster FastAPI application."""

import logging
from contextlib import asynccontextmanager

import firebase_admin
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.admin.routes import router as admin_dashboard_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.metrics import MetricsMiddleware
from app.core.metrics import router as metrics_router
from app.core.middleware import RateLimitMiddleware, RequestIdMiddleware, SecurityHeadersMiddleware
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Application startup/shutdown lifecycle."""
    setup_logging()
    logger.info("Starting StockMaster [env=%s]", settings.env)

    # Initialize Firebase Admin SDK (once)
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    # Start scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Shutting down StockMaster")


def create_app() -> FastAPI:
    """Application factory."""
    show_docs = settings.admin_docs or settings.env != "production"

    app = FastAPI(
        title="StockMaster API",
        version="0.1.0",
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        openapi_url="/openapi.json" if show_docs else None,
        lifespan=lifespan,
    )

    # CORS
    allowed_origins = ["*"] if settings.env == "qa" else []
    if settings.env == "uat":
        allowed_origins = ["https://uat.stockmaster.app"]
    elif settings.env == "production":
        allowed_origins = ["https://stockmaster.app", "https://admin.stockmaster.app"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware (order: outermost first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(MetricsMiddleware)
    if settings.env == "production":
        app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

    # Routers
    app.include_router(api_router)
    app.include_router(admin_dashboard_router)
    app.include_router(metrics_router)

    # Root
    @app.get("/", tags=["infra"], include_in_schema=False)
    async def root() -> dict:
        return {"app": "StockMaster API", "version": "0.1.0", "docs": "/docs"}

    # Health check
    @app.get("/health", tags=["infra"])
    async def health() -> dict:
        return {"status": "ok", "env": settings.env}

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": None}},
        )

    return app


app = create_app()
