"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from unitylens.api.routes import admin, auth, browse, search
from unitylens.config.settings import get_settings, load_sources_config
from unitylens.context.builder import build_context
from unitylens.llm.client import init_llm_client
from unitylens.store import db

# Ensure all source types are registered by importing their modules
import unitylens.sources.databricks.source  # noqa: F401
import unitylens.sources.snowflake.source  # noqa: F401
import unitylens.sources.oracle.source  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize database
    db.init_db(settings.db_path)
    logger.info("Database initialized at %s", settings.db_path)

    # Build initial context from existing data
    try:
        build_context(settings.context_path)
    except Exception:
        logger.warning("Could not build initial context (store may be empty)")

    # Initialize LLM client if configured
    if settings.llm_endpoint_url and settings.llm_token:
        init_llm_client(
            endpoint_url=settings.llm_endpoint_url,
            token=settings.llm_token,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
    else:
        logger.info("LLM client not configured (set UNITYLENS_LLM_ENDPOINT and UNITYLENS_LLM_TOKEN)")

    # Optionally start the scheduler
    if settings.crawl_cron or settings.crawl_interval_minutes:
        try:
            from unitylens.crawler.scheduler import start_scheduler

            source_configs = load_sources_config()
            if source_configs:
                start_scheduler(
                    source_configs=source_configs,
                    cron_expression=settings.crawl_cron or None,
                    interval_minutes=settings.crawl_interval_minutes,
                )
        except Exception:
            logger.exception("Failed to start crawl scheduler")

    yield

    # Shutdown
    try:
        from unitylens.crawler.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        pass

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    from unitylens import __version__

    app = FastAPI(
        title="UnityLens",
        description="Cross-platform metadata catalog and search API",
        version=__version__,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(auth.router)
    app.include_router(browse.router)
    app.include_router(search.router)
    app.include_router(admin.router)

    # Health check
    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "healthy", "service": "unitylens", "version": __version__}

    @app.get("/api/version", tags=["health"])
    def version() -> dict:
        return {"version": __version__}

    # Serve frontend static files from / (must be last)
    static_dir = settings.static_dir
    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        logger.warning(
            "Static directory '%s' not found; frontend will not be served",
            static_dir,
        )

    return app


# The application instance used by gunicorn / uvicorn
app = create_app()
