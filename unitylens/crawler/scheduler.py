"""APScheduler-based crawl scheduler."""

from __future__ import annotations

import logging
from typing import Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False
    BackgroundScheduler = None  # type: ignore

from unitylens.crawler.orchestrator import crawl_all

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(
    source_configs: dict[str, dict[str, Any]],
    cron_expression: str | None = None,
    interval_minutes: int | None = None,
) -> BackgroundScheduler:
    """Start the background crawl scheduler.

    Exactly one of ``cron_expression`` or ``interval_minutes`` should
    be provided.  If neither is given the default is a 60-minute
    interval.

    Parameters
    ----------
    source_configs:
        The source configuration mapping passed through to ``crawl_all``.
    cron_expression:
        A cron string such as ``"0 */2 * * *"`` (every 2 hours).
    interval_minutes:
        Run every N minutes.
    """
    global _scheduler

    if not _HAS_APSCHEDULER:
        logger.warning("APScheduler not installed; crawl scheduling disabled. pip install apscheduler to enable.")
        return None  # type: ignore

    if _scheduler is not None:
        logger.warning("Scheduler already running; stopping the old one first")
        _scheduler.shutdown(wait=False)

    _scheduler = BackgroundScheduler(daemon=True)

    if cron_expression:
        parts = cron_expression.split()
        trigger = CronTrigger(
            minute=parts[0] if len(parts) > 0 else "*",
            hour=parts[1] if len(parts) > 1 else "*",
            day=parts[2] if len(parts) > 2 else "*",
            month=parts[3] if len(parts) > 3 else "*",
            day_of_week=parts[4] if len(parts) > 4 else "*",
        )
        logger.info("Scheduling crawl with cron: %s", cron_expression)
    else:
        minutes = interval_minutes or 60
        trigger = IntervalTrigger(minutes=minutes)
        logger.info("Scheduling crawl every %d minutes", minutes)

    _scheduler.add_job(
        crawl_all,
        trigger=trigger,
        args=[source_configs],
        id="metadata_crawl",
        name="UnityLens metadata crawl",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info("Scheduler started")
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully stop the scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler() -> BackgroundScheduler | None:
    """Return the current scheduler instance (or None)."""
    return _scheduler
