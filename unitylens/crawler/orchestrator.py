"""Crawl orchestrator: iterates sources, writes metadata to the store."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from unitylens.sources.base import DataSource
from unitylens.sources.registry import build_source
from unitylens.store import db

logger = logging.getLogger(__name__)


def crawl_source(source: DataSource) -> dict[str, Any]:
    """Run a full crawl for a single source.

    Performs a full refresh: deletes all existing data for this source
    and re-inserts everything within a single transaction.

    Returns a summary dict with counts and status.
    """
    name = source.name
    conn = db.get_connection()
    summary: dict[str, Any] = {
        "source": name,
        "status": "success",
        "catalogs": 0,
        "schemas": 0,
        "tables": 0,
        "columns": 0,
        "error": "",
    }

    crawl_log: list[dict[str, Any]] = []

    def log(level: str, message: str) -> None:
        crawl_log.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
            }
        )

    try:
        db.update_source_status(conn, name, "running")
        log("info", f"Starting crawl for source '{name}'")
        # Clear old data for this source upfront
        db.delete_source_data(conn, name)
        conn.commit()

        # Crawl catalogs
        catalogs = source.crawl_catalogs()
        summary["catalogs"] = len(catalogs)

        # Insert catalogs immediately so they show up
        db.insert_catalogs(conn, catalogs)
        conn.commit()

        total_schemas = 0
        total_tables = 0
        total_columns = 0

        for cat in catalogs:
            # Skip internal/system catalogs
            if cat.catalog_name.startswith("__"):
                logger.info("Skipping internal catalog '%s'", cat.catalog_name)
                continue

            try:
                schemas = source.crawl_schemas(cat.catalog_name)
                db.insert_schemas(conn, schemas)
                total_schemas += len(schemas)
                log(
                    "info",
                    f"Crawled {len(schemas)} schemas in catalog '{cat.catalog_name}'",
                )
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Error listing schemas for '%s': %s",
                    cat.catalog_name, detail, exc_info=True,
                )
                log(
                    "error",
                    f"crawl_schemas('{cat.catalog_name}') failed: {detail}",
                )
                summary["status"] = "error"
                continue

            try:
                tables, columns = source.crawl_tables(cat.catalog_name)
                if tables:
                    db.insert_tables(conn, tables)
                if columns:
                    db.insert_columns(conn, columns)
                total_tables += len(tables)
                total_columns += len(columns)
                log(
                    "info",
                    f"Crawled {len(tables)} tables / {len(columns)} columns "
                    f"in catalog '{cat.catalog_name}'",
                )
            except Exception as exc:
                err_str = str(exc)
                detail = f"{type(exc).__name__}: {err_str}"
                if "INSUFFICIENT_PERMISSIONS" in err_str:
                    logger.info(
                        "Skipping catalog '%s' (no USE CATALOG permission)",
                        cat.catalog_name,
                    )
                    log(
                        "warn",
                        f"Skipped catalog '{cat.catalog_name}': insufficient permissions",
                    )
                else:
                    logger.warning(
                        "Error crawling tables for catalog '%s': %s",
                        cat.catalog_name, detail, exc_info=True,
                    )
                    log(
                        "error",
                        f"crawl_tables('{cat.catalog_name}') failed: {detail}",
                    )
                    summary["status"] = "error"

            # Commit after each catalog so data appears incrementally
            conn.commit()

        summary["schemas"] = total_schemas
        summary["tables"] = total_tables
        summary["columns"] = total_columns

        # Rebuild search index
        try:
            db.rebuild_search_index(conn)
        except Exception as exc:
            logger.warning("Failed to rebuild search index, continuing", exc_info=True)
            log("warn", f"Search index rebuild failed: {type(exc).__name__}: {exc}")

        now = datetime.now(timezone.utc).isoformat()
        final_status = "success" if summary["status"] == "success" else "error"
        db.update_source_status(conn, name, final_status, crawl_time=now)
        conn.commit()

        log(
            "info",
            f"Crawl complete: {summary['catalogs']} catalogs, "
            f"{total_schemas} schemas, {total_tables} tables, "
            f"{total_columns} columns",
        )
        logger.info(
            "Crawl complete for '%s': %d catalogs, %d schemas, %d tables, %d columns",
            name,
            summary["catalogs"],
            summary["schemas"],
            summary["tables"],
            summary["columns"],
        )

    except Exception as exc:
        conn.rollback()
        error_msg = f"{type(exc).__name__}: {exc}"
        summary["status"] = "error"
        summary["error"] = error_msg
        logger.exception("Crawl failed for source '%s'", name)
        log("error", f"Crawl aborted: {error_msg}")
        log("error", traceback.format_exc(limit=5))

    finally:
        # Persist the structured crawl log regardless of outcome.
        try:
            db.update_source_log(conn, name, crawl_log)
            conn.commit()
        except Exception:
            logger.exception("Failed to persist crawl log for '%s'", name)
        # Always ensure status is not stuck on "running"
        try:
            current = db.get_source_status(conn, name)
            if current and current.get("last_status") == "running":
                now = datetime.now(timezone.utc).isoformat()
                status = "error" if summary["error"] else "success"
                db.update_source_status(conn, name, status, error=summary["error"], crawl_time=now)
                conn.commit()
                logger.info("Fixed stuck 'running' status for '%s' -> '%s'", name, status)
        except Exception:
            pass
        conn.close()

    return summary


def crawl_all(source_configs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Crawl all configured sources.

    Each source is crawled independently; a failure in one source does
    not prevent others from being crawled.

    Parameters
    ----------
    source_configs:
        Mapping of source name to its configuration dict (must include
        ``"type"`` key).

    Returns
    -------
    list[dict]
        A list of summary dicts, one per source.
    """
    summaries: list[dict[str, Any]] = []

    # Register sources in the store
    conn = db.get_connection()
    try:
        for name, cfg in source_configs.items():
            import json

            db.upsert_source(
                conn,
                source_name=name,
                source_type=cfg.get("type", "unknown"),
                host=cfg.get("host", ""),
                config_json=json.dumps(
                    {k: v for k, v in cfg.items() if k not in ("token", "password")}
                ),
            )
        conn.commit()
    finally:
        conn.close()

    for name, cfg in source_configs.items():
        try:
            source = build_source(name, cfg)
            summary = crawl_source(source)
            summaries.append(summary)
        except Exception as exc:
            logger.exception("Failed to build/crawl source '%s'", name)
            summaries.append(
                {
                    "source": name,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "catalogs": 0,
                    "schemas": 0,
                    "tables": 0,
                    "columns": 0,
                }
            )

    return summaries


def crawl_single(
    source_name: str, source_configs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Crawl a single named source."""
    cfg = source_configs.get(source_name)
    if cfg is None:
        return {
            "source": source_name,
            "status": "error",
            "error": f"Source '{source_name}' not found in configuration",
            "catalogs": 0,
            "schemas": 0,
            "tables": 0,
            "columns": 0,
        }

    import json

    conn = db.get_connection()
    try:
        db.upsert_source(
            conn,
            source_name=source_name,
            source_type=cfg.get("type", "unknown"),
            host=cfg.get("host", ""),
            config_json=json.dumps(
                {k: v for k, v in cfg.items() if k not in ("token", "password")}
            ),
        )
        conn.commit()
    finally:
        conn.close()

    source = build_source(source_name, cfg)
    return crawl_source(source)
