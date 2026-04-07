"""Browse API routes: hierarchical metadata navigation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from unitylens.store import db

router = APIRouter(prefix="/api", tags=["browse"])


@router.get("/dictionary")
def get_dictionary(
    source: str | None = None,
    catalog: str | None = None,
    schema: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict:
    """Return a flat data dictionary view: one row per table with column details."""
    conn = db.get_connection()
    try:
        conditions = []
        params: list = []

        if source:
            conditions.append("t.source_name = ?")
            params.append(source)
        if catalog:
            conditions.append("t.catalog_name = ?")
            params.append(catalog)
        if schema:
            conditions.append("t.schema_name = ?")
            params.append(schema)
        if search:
            conditions.append(
                "(t.table_name LIKE ? OR t.comment LIKE ? OR t.full_name LIKE ?)"
            )
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM tables t {where}"
        total = conn.execute(count_sql, params).fetchone()[0]

        # Get tables page
        sql = f"""
            SELECT t.source_name, t.catalog_name, t.schema_name, t.table_name,
                   t.full_name, t.table_type, t.comment, t.owner
            FROM tables t
            {where}
            ORDER BY t.source_name, t.catalog_name, t.schema_name, t.table_name
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(sql, params + [limit, offset]).fetchall()

        tables = []
        for row in rows:
            tbl = dict(row)
            # Get column count and column summary
            cols = conn.execute(
                """SELECT column_name, data_type, is_nullable, comment
                   FROM columns
                   WHERE source_name = ? AND catalog_name = ? AND schema_name = ? AND table_name = ?
                   ORDER BY ordinal_position""",
                (tbl["source_name"], tbl["catalog_name"], tbl["schema_name"], tbl["table_name"]),
            ).fetchall()
            tbl["column_count"] = len(cols)
            tbl["columns"] = [dict(c) for c in cols]
            tables.append(tbl)

        # Get filter options
        sources_list = [r[0] for r in conn.execute("SELECT DISTINCT source_name FROM tables ORDER BY 1").fetchall()]
        catalogs_list = [r[0] for r in conn.execute("SELECT DISTINCT catalog_name FROM tables ORDER BY 1").fetchall()]
        schemas_list = [r[0] for r in conn.execute("SELECT DISTINCT schema_name FROM tables ORDER BY 1").fetchall()]

        return {
            "tables": tables,
            "total": total,
            "offset": offset,
            "limit": limit,
            "filters": {
                "sources": sources_list,
                "catalogs": catalogs_list,
                "schemas": schemas_list,
            },
        }
    finally:
        conn.close()


@router.get("/stats")
def get_stats() -> dict:
    """Return aggregate counts for the dashboard."""
    conn = db.get_connection()
    try:
        counts = {}
        for name, table in [
            ("sources", "sources"),
            ("catalogs", "catalogs"),
            ("schemas", "schemas"),
            ("tables", "tables"),
            ("columns", "columns"),
        ]:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
            counts[name] = row["cnt"] if row else 0
        return counts
    finally:
        conn.close()


@router.get("/catalogs/detail")
def get_catalogs_detail(source: str | None = None) -> list[dict]:
    """List all catalogs with schema, table, and column counts."""
    conn = db.get_connection()
    try:
        base = """
            SELECT c.source_name, c.catalog_name, c.full_name, c.comment, c.owner,
                   (SELECT COUNT(*) FROM schemas s
                    WHERE s.source_name = c.source_name AND s.catalog_name = c.catalog_name) AS schema_count,
                   (SELECT COUNT(*) FROM tables t
                    WHERE t.source_name = c.source_name AND t.catalog_name = c.catalog_name) AS table_count,
                   (SELECT COUNT(*) FROM columns col
                    WHERE col.source_name = c.source_name AND col.catalog_name = c.catalog_name) AS column_count
            FROM catalogs c
        """
        if source:
            base += " WHERE c.source_name = ? ORDER BY c.catalog_name"
            rows = conn.execute(base, (source,)).fetchall()
        else:
            base += " ORDER BY c.source_name, c.catalog_name"
            rows = conn.execute(base).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/sources")
def get_sources() -> list[dict]:
    """List all registered data sources and their crawl status."""
    conn = db.get_connection()
    try:
        return db.list_sources(conn)
    finally:
        conn.close()


@router.get("/catalogs")
def get_catalogs(source: str | None = None) -> list[dict]:
    """List catalogs, optionally filtered by source name."""
    conn = db.get_connection()
    try:
        return db.list_catalogs(conn, source)
    finally:
        conn.close()


@router.get("/schemas/{source}/{catalog}")
def get_schemas(source: str, catalog: str) -> list[dict]:
    """List schemas within a source/catalog."""
    conn = db.get_connection()
    try:
        results = db.list_schemas(conn, source, catalog)
        if not results:
            # Check if the catalog exists at all
            cats = db.list_catalogs(conn, source)
            cat_names = [c["catalog_name"] for c in cats]
            if catalog not in cat_names:
                raise HTTPException(
                    status_code=404,
                    detail=f"Catalog '{catalog}' not found in source '{source}'",
                )
        return results
    finally:
        conn.close()


@router.get("/tables/{source}/{catalog}/{schema}")
def get_tables(source: str, catalog: str, schema: str) -> list[dict]:
    """List tables within a source/catalog/schema."""
    conn = db.get_connection()
    try:
        results = db.list_tables(conn, source, catalog, schema)
        if not results:
            schemas = db.list_schemas(conn, source, catalog)
            schema_names = [s["schema_name"] for s in schemas]
            if schema not in schema_names:
                raise HTTPException(
                    status_code=404,
                    detail=f"Schema '{schema}' not found in {source}::{catalog}",
                )
        return results
    finally:
        conn.close()


@router.get("/tables/{source}/{catalog}/{schema}/{table}")
def get_table_detail(
    source: str, catalog: str, schema: str, table: str
) -> dict:
    """Get full table details including columns."""
    conn = db.get_connection()
    try:
        result = db.get_table_detail(conn, source, catalog, schema, table)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Table '{table}' not found in {source}::{catalog}.{schema}",
            )
        return result
    finally:
        conn.close()
