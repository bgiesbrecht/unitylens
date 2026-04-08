"""Admin API routes: crawl triggers and source status."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from unitylens.auth.deps import require_admin
from unitylens.config.settings import get_settings, load_sources_config
from unitylens.context.builder import build_context, invalidate_cache
from unitylens.crawler.orchestrator import crawl_all, crawl_single
from unitylens.store import db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _run_crawl_all() -> list[dict[str, Any]]:
    """Run a full crawl and rebuild context (used as background task)."""
    source_configs = load_sources_config()
    results = crawl_all(source_configs)
    invalidate_cache()
    build_context()
    return results


def _run_crawl_single(source_name: str) -> dict[str, Any]:
    """Crawl a single source and rebuild context (used as background task)."""
    source_configs = load_sources_config()
    result = crawl_single(source_name, source_configs)
    invalidate_cache()
    build_context()
    return result


@router.post("/crawl")
def trigger_crawl_all(background_tasks: BackgroundTasks) -> dict:
    """Trigger a full metadata crawl of all configured sources.

    The crawl runs in the background.  Poll ``GET /api/sources`` or
    ``GET /api/sources/{name}/status`` for progress.
    """
    background_tasks.add_task(_run_crawl_all)
    return {"status": "crawl_started", "message": "Full crawl initiated in the background"}


@router.post("/crawl/{source_name}")
def trigger_crawl_single(
    source_name: str, background_tasks: BackgroundTasks
) -> dict:
    """Trigger a crawl for a single named source."""
    source_configs = load_sources_config()
    if source_name not in source_configs:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_name}' not found in configuration",
        )
    background_tasks.add_task(_run_crawl_single, source_name)
    return {
        "status": "crawl_started",
        "message": f"Crawl initiated for source '{source_name}'",
    }


@router.get("/sources/{source_name}/status")
def get_source_status(source_name: str) -> dict:
    """Get the current crawl status for a source."""
    conn = db.get_connection()
    try:
        status = db.get_source_status(conn, source_name)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Source '{source_name}' not found",
            )
        # crawl_log is stored as a JSON string; decode for clients.
        raw_log = status.get("crawl_log") or "[]"
        try:
            status["crawl_log"] = json.loads(raw_log)
        except Exception:
            status["crawl_log"] = []
        return status
    finally:
        conn.close()
