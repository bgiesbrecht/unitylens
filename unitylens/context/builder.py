"""Context builder: serializes the metadata store into a hierarchical text file."""

from __future__ import annotations

import json
import logging
import os
from io import StringIO
from pathlib import Path

from unitylens.store import db

logger = logging.getLogger(__name__)

_CONTEXT_PATH: str = os.environ.get(
    "UNITYLENS_CONTEXT_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "context_cache.txt"),
)

_cached_context: str | None = None


def build_context(output_path: str | None = None) -> str:
    """Generate the full hierarchical metadata context string.

    The output is organized as::

        SOURCE: prod_databricks (databricks)
          CATALOG: main
            SCHEMA: default
              TABLE: customers (TABLE)
                Comment: Customer master table
                COLUMNS:
                  - id (BIGINT, NOT NULL) : Primary key
                  - name (STRING) : Customer name

    Returns the context string and writes it to disk as a cache file.
    """
    global _cached_context
    dest = output_path or _CONTEXT_PATH

    conn = db.get_connection()
    buf = StringIO()

    try:
        sources = db.list_sources(conn)
        if not sources:
            buf.write("(No sources have been crawled yet.)\n")
            text = buf.getvalue()
            _cached_context = text
            Path(dest).write_text(text, encoding="utf-8")
            return text

        for src in sources:
            src_name = src["source_name"]
            src_type = src["source_type"]
            buf.write(f"SOURCE: {src_name} ({src_type})\n")

            catalogs = db.list_catalogs(conn, src_name)
            for cat in catalogs:
                cat_name = cat["catalog_name"]
                cat_comment = cat.get("comment", "")
                buf.write(f"  CATALOG: {cat_name}\n")
                if cat_comment:
                    buf.write(f"    Comment: {cat_comment}\n")

                schemas = db.list_schemas(conn, src_name, cat_name)
                for sch in schemas:
                    sch_name = sch["schema_name"]
                    sch_comment = sch.get("comment", "")
                    buf.write(f"    SCHEMA: {sch_name}\n")
                    if sch_comment:
                        buf.write(f"      Comment: {sch_comment}\n")

                    tables = db.list_tables(conn, src_name, cat_name, sch_name)
                    for tbl in tables:
                        tbl_name = tbl["table_name"]
                        tbl_type = tbl.get("table_type", "TABLE")
                        tbl_comment = tbl.get("comment", "")
                        buf.write(f"      TABLE: {tbl_name} ({tbl_type})\n")
                        if tbl_comment:
                            buf.write(f"        Comment: {tbl_comment}\n")

                        detail = db.get_table_detail(
                            conn, src_name, cat_name, sch_name, tbl_name
                        )
                        if detail and detail.get("columns"):
                            buf.write("        COLUMNS:\n")
                            for col in detail["columns"]:
                                col_name = col["column_name"]
                                dtype = col.get("data_type", "")
                                nullable = (
                                    ""
                                    if col.get("is_nullable", 1)
                                    else ", NOT NULL"
                                )
                                col_comment = col.get("comment", "")
                                comment_part = (
                                    f" : {col_comment}" if col_comment else ""
                                )
                                buf.write(
                                    f"          - {col_name} ({dtype}{nullable}){comment_part}\n"
                                )

            buf.write("\n")

    finally:
        conn.close()

    text = buf.getvalue()
    _cached_context = text

    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(text, encoding="utf-8")
    logger.info("Context file written to %s (%d chars)", dest, len(text))

    return text


def get_cached_context() -> str:
    """Return the cached context, rebuilding if necessary."""
    global _cached_context
    if _cached_context is not None:
        return _cached_context

    dest = _CONTEXT_PATH
    if Path(dest).exists():
        _cached_context = Path(dest).read_text(encoding="utf-8")
        return _cached_context

    return build_context()


def invalidate_cache() -> None:
    """Clear the in-memory cache so the next call rebuilds."""
    global _cached_context
    _cached_context = None
