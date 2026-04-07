"""SQLite metadata store with WAL mode and full-text search."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from unitylens.sources.base import CatalogMeta, ColumnMeta, SchemaMeta, TableMeta

logger = logging.getLogger(__name__)

_SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()

_DEFAULT_DB_PATH: str = str(
    Path(__file__).resolve().parent.parent.parent / "unitylens.db"
)


def _resolve_db_path() -> str:
    """Resolve the database path from the environment at call time."""
    return os.environ.get("UNITYLENS_DB_PATH", _DEFAULT_DB_PATH)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode enabled.

    Each caller gets its own connection; SQLite WAL mode allows
    concurrent readers alongside a single writer.
    """
    path = db_path or _resolve_db_path()
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create all tables if they do not exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("Database initialized at %s", db_path or _resolve_db_path())
    finally:
        conn.close()


# ------------------------------------------------------------------
# Write helpers
# ------------------------------------------------------------------


def upsert_source(
    conn: sqlite3.Connection,
    source_name: str,
    source_type: str,
    host: str = "",
    config_json: str = "{}",
) -> None:
    conn.execute(
        """
        INSERT INTO sources (source_name, source_type, host, config_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_name) DO UPDATE SET
            source_type = excluded.source_type,
            host        = excluded.host,
            config_json = excluded.config_json
        """,
        (source_name, source_type, host, config_json),
    )


def update_source_status(
    conn: sqlite3.Connection,
    source_name: str,
    status: str,
    error: str = "",
    crawl_time: str | None = None,
) -> None:
    if crawl_time:
        conn.execute(
            """
            UPDATE sources
            SET last_status = ?, last_error = ?, last_crawl_at = ?
            WHERE source_name = ?
            """,
            (status, error, crawl_time, source_name),
        )
    else:
        conn.execute(
            """
            UPDATE sources
            SET last_status = ?, last_error = ?
            WHERE source_name = ?
            """,
            (status, error, source_name),
        )


def delete_source_data(conn: sqlite3.Connection, source_name: str) -> None:
    """Remove all metadata rows for a given source (full refresh)."""
    for table in ("columns", "tables", "schemas", "catalogs"):
        conn.execute(f"DELETE FROM {table} WHERE source_name = ?", (source_name,))


def insert_catalogs(conn: sqlite3.Connection, catalogs: list[CatalogMeta]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO catalogs
            (source_name, catalog_name, full_name, comment, owner, tags_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                c.source_name,
                c.catalog_name,
                c.full_name,
                c.comment,
                c.owner,
                json.dumps(c.tags),
            )
            for c in catalogs
        ],
    )


def insert_schemas(conn: sqlite3.Connection, schemas: list[SchemaMeta]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO schemas
            (source_name, catalog_name, schema_name, full_name, comment, owner, tags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                s.source_name,
                s.catalog_name,
                s.schema_name,
                s.full_name,
                s.comment,
                s.owner,
                json.dumps(s.tags),
            )
            for s in schemas
        ],
    )


def insert_tables(conn: sqlite3.Connection, tables: list[TableMeta]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO tables
            (source_name, catalog_name, schema_name, table_name,
             full_name, table_type, comment, owner, tags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                t.source_name,
                t.catalog_name,
                t.schema_name,
                t.table_name,
                t.full_name,
                t.table_type,
                t.comment,
                t.owner,
                json.dumps(t.tags),
            )
            for t in tables
        ],
    )


def insert_columns(conn: sqlite3.Connection, columns: list[ColumnMeta]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO columns
            (source_name, catalog_name, schema_name, table_name, column_name,
             full_name, data_type, ordinal_position, is_nullable, comment, tags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                c.source_name,
                c.catalog_name,
                c.schema_name,
                c.table_name,
                c.column_name,
                c.full_name,
                c.data_type,
                c.ordinal_position,
                1 if c.is_nullable else 0,
                c.comment,
                json.dumps(c.tags),
            )
            for c in columns
        ],
    )


def rebuild_search_index(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS5 search index from current metadata."""
    conn.execute("DELETE FROM search_index")

    # Index catalogs
    for row in conn.execute("SELECT full_name, comment FROM catalogs"):
        conn.execute(
            "INSERT INTO search_index (full_name, object_type, comment, extra) VALUES (?, ?, ?, ?)",
            (row["full_name"], "catalog", row["comment"], ""),
        )

    # Index schemas
    for row in conn.execute("SELECT full_name, comment FROM schemas"):
        conn.execute(
            "INSERT INTO search_index (full_name, object_type, comment, extra) VALUES (?, ?, ?, ?)",
            (row["full_name"], "schema", row["comment"], ""),
        )

    # Index tables
    for row in conn.execute("SELECT full_name, table_type, comment FROM tables"):
        conn.execute(
            "INSERT INTO search_index (full_name, object_type, comment, extra) VALUES (?, ?, ?, ?)",
            (row["full_name"], "table", row["comment"], row["table_type"]),
        )

    # Index columns
    for row in conn.execute(
        "SELECT full_name, data_type, comment FROM columns"
    ):
        conn.execute(
            "INSERT INTO search_index (full_name, object_type, comment, extra) VALUES (?, ?, ?, ?)",
            (row["full_name"], "column", row["comment"], row["data_type"]),
        )

    logger.info("Search index rebuilt")


# ------------------------------------------------------------------
# Read helpers
# ------------------------------------------------------------------


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def list_sources(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT source_name, source_type, host, last_crawl_at, last_status, last_error FROM sources"
    ).fetchall()
    return _rows_to_dicts(rows)


def get_source_status(conn: sqlite3.Connection, source_name: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM sources WHERE source_name = ?", (source_name,)
    ).fetchone()
    return dict(row) if row else None


def list_catalogs(
    conn: sqlite3.Connection, source_name: str | None = None
) -> list[dict[str, Any]]:
    if source_name:
        rows = conn.execute(
            "SELECT * FROM catalogs WHERE source_name = ? ORDER BY catalog_name",
            (source_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM catalogs ORDER BY source_name, catalog_name"
        ).fetchall()
    return _rows_to_dicts(rows)


def list_schemas(
    conn: sqlite3.Connection, source_name: str, catalog_name: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM schemas
        WHERE source_name = ? AND catalog_name = ?
        ORDER BY schema_name
        """,
        (source_name, catalog_name),
    ).fetchall()
    return _rows_to_dicts(rows)


def list_tables(
    conn: sqlite3.Connection,
    source_name: str,
    catalog_name: str,
    schema_name: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM tables
        WHERE source_name = ? AND catalog_name = ? AND schema_name = ?
        ORDER BY table_name
        """,
        (source_name, catalog_name, schema_name),
    ).fetchall()
    return _rows_to_dicts(rows)


def get_table_detail(
    conn: sqlite3.Connection,
    source_name: str,
    catalog_name: str,
    schema_name: str,
    table_name: str,
) -> dict[str, Any] | None:
    tbl = conn.execute(
        """
        SELECT * FROM tables
        WHERE source_name = ? AND catalog_name = ? AND schema_name = ? AND table_name = ?
        """,
        (source_name, catalog_name, schema_name, table_name),
    ).fetchone()
    if not tbl:
        return None
    cols = conn.execute(
        """
        SELECT * FROM columns
        WHERE source_name = ? AND catalog_name = ? AND schema_name = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        (source_name, catalog_name, schema_name, table_name),
    ).fetchall()
    result = dict(tbl)
    result["columns"] = _rows_to_dicts(cols)
    return result


_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "of", "in", "to",
    "for", "with", "on", "at", "from", "by", "about", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than", "too",
    "very", "just", "that", "this", "these", "those", "it", "its",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who",
    "whom", "how", "when", "where", "why", "if", "then", "else",
    "show", "find", "list", "get", "give", "tell", "related",
})


def _build_fts_query(raw: str) -> str:
    """Turn a natural-language query into an FTS5 OR expression."""
    import re
    tokens = re.findall(r"[a-zA-Z0-9_]+", raw.lower())
    terms = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
    if not terms:
        terms = [t for t in tokens if len(t) > 1] or tokens
    # Use OR so any matching term scores
    return " OR ".join(f'"{t}"' for t in terms)


def keyword_search(
    conn: sqlite3.Connection, query: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Search the FTS5 index for matching metadata objects."""
    fts_query = _build_fts_query(query)
    if not fts_query:
        return []
    rows = conn.execute(
        """
        SELECT full_name, object_type, comment, extra,
               rank
        FROM search_index
        WHERE search_index MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (fts_query, limit),
    ).fetchall()
    return _rows_to_dicts(rows)


def keyword_search_like(
    conn: sqlite3.Connection, query: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Fallback keyword search using LIKE on the tables and columns tables."""
    pattern = f"%{query}%"
    results: list[dict[str, Any]] = []

    for obj_type, tbl, extra_col in [
        ("catalog", "catalogs", None),
        ("schema", "schemas", None),
        ("table", "tables", "table_type"),
        ("column", "columns", "data_type"),
    ]:
        extra_select = f", {extra_col}" if extra_col else ", '' AS extra"
        sql = f"""
            SELECT full_name, '{obj_type}' AS object_type, comment{extra_select}
            FROM {tbl}
            WHERE full_name LIKE ? OR comment LIKE ?
            LIMIT ?
        """
        rows = conn.execute(sql, (pattern, pattern, limit)).fetchall()
        results.extend(_rows_to_dicts(rows))

    results.sort(key=lambda r: r["full_name"])
    return results[:limit]
