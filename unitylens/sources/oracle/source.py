"""Oracle Database metadata source."""

from __future__ import annotations

import logging
import re
from typing import Any

from unitylens.sources.base import (
    CatalogMeta,
    ColumnMeta,
    DataSource,
    SchemaMeta,
    TableMeta,
)
from unitylens.sources.registry import register

logger = logging.getLogger(__name__)

# Oracle-internal schemas to skip by default.
_SYSTEM_SCHEMAS = frozenset(
    {
        "SYS", "SYSTEM", "OUTLN", "DBSNMP", "APPQOSSYS", "AUDSYS",
        "GSMADMIN_INTERNAL", "GSMCATUSER", "GSMUSER", "DIP", "ORACLE_OCM",
        "REMOTE_SCHEDULER_AGENT", "SYS$UMF", "DBSFWUSER", "GGSYS",
        "ANONYMOUS", "XDB", "WMSYS", "MDSYS", "CTXSYS", "ORDSYS", "ORDDATA",
        "ORDPLUGINS", "SI_INFORMTN_SCHEMA", "OLAPSYS", "LBACSYS", "DVSYS",
        "DVF", "FLOWS_FILES", "MDDATA", "APEX_PUBLIC_USER", "SPATIAL_CSW_ADMIN_USR",
        "SPATIAL_WFS_ADMIN_USR", "XS$NULL",
    }
)


@register("oracle")
class OracleSource(DataSource):
    """Crawls metadata from an Oracle database via python-oracledb (thin mode).

    Required config keys:

    - ``dsn``:      Oracle Easy Connect string, e.g. ``host:1521/SERVICE`` or a TNS name.
    - ``user``:     Authentication user.
    - ``password``: Authentication password.

    Optional config keys:

    - ``catalog_name``: Logical catalog name to surface (Oracle has no real
      catalog concept; defaults to the service name parsed from ``dsn``,
      falling back to ``ORACLE``).
    - ``schema_filter``: List of schema (owner) names to include. If empty,
      all non-system schemas are crawled.
    - ``include_system_schemas``: bool, default False.
    - ``include_views``: bool, default True.
    - ``deny_tags`` / ``allow_tags``: standard tag governance.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._dsn: str = config["dsn"]
        self._user: str = config["user"]
        self._password: str = config["password"]
        self._schema_filter: list[str] = [
            s.upper() for s in config.get("schema_filter", []) or []
        ]
        self._include_system: bool = bool(config.get("include_system_schemas", False))
        self._include_views: bool = bool(config.get("include_views", True))
        self._catalog_name: str = config.get("catalog_name") or self._derive_catalog_name()
        self._conn: Any | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _derive_catalog_name(self) -> str:
        # Easy Connect style: host:port/service
        m = re.search(r"/([A-Za-z0-9_.\-]+)\s*$", self._dsn)
        if m:
            return m.group(1).upper()
        return "ORACLE"

    def _get_connection(self) -> Any:
        if self._conn is None:
            try:
                import oracledb  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "The 'oracledb' package is required for OracleSource. "
                    "Install it with: pip install oracledb"
                ) from exc
            self._conn = oracledb.connect(
                user=self._user, password=self._password, dsn=self._dsn
            )
        return self._conn

    def _query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(sql, params or {})
            return cur.fetchall()
        finally:
            cur.close()

    def _schema_visible(self, owner: str) -> bool:
        if self._schema_filter:
            return owner.upper() in self._schema_filter
        if not self._include_system and owner.upper() in _SYSTEM_SCHEMAS:
            return False
        return True

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    def validate_connection(self) -> bool:
        try:
            rows = self._query("SELECT 1 FROM DUAL")
            return bool(rows)
        except Exception:
            logger.exception("Connection validation failed for source '%s'", self.name)
            return False

    def crawl_catalogs(self) -> list[CatalogMeta]:
        # Oracle has no native catalog concept; surface a single logical catalog.
        catalog = CatalogMeta(
            source_name=self.name,
            catalog_name=self._catalog_name,
            comment=f"Oracle database ({self._dsn})",
            owner="",
            tags={},
        )
        if not self.is_asset_visible(catalog.tags):
            return []
        logger.info("Source '%s': crawled 1 catalog (%s)", self.name, self._catalog_name)
        return [catalog]

    def crawl_schemas(self, catalog: str) -> list[SchemaMeta]:
        if catalog != self._catalog_name:
            return []
        rows = self._query("SELECT username FROM all_users ORDER BY username")
        schemas: list[SchemaMeta] = []
        for (owner,) in rows:
            if not self._schema_visible(owner):
                continue
            schemas.append(
                SchemaMeta(
                    source_name=self.name,
                    catalog_name=catalog,
                    schema_name=owner,
                    comment="",
                    owner=owner,
                    tags={},
                )
            )
        logger.info(
            "Source '%s': crawled %d schemas in catalog '%s'",
            self.name, len(schemas), catalog,
        )
        return schemas

    def crawl_tables(
        self, catalog: str
    ) -> tuple[list[TableMeta], list[ColumnMeta]]:
        if catalog != self._catalog_name:
            return [], []

        # Resolve which owners we will crawl.
        owners = [s.schema_name for s in self.crawl_schemas(catalog)]
        if not owners:
            return [], []

        # Build a bind list for the IN clause.
        bind_names = [f"o{i}" for i in range(len(owners))]
        in_clause = ", ".join(f":{b}" for b in bind_names)
        binds = dict(zip(bind_names, owners))

        # Tables (+ views) and their comments.
        type_filter = "('TABLE', 'VIEW')" if self._include_views else "('TABLE')"
        table_sql = f"""
            SELECT t.owner, t.object_name, t.object_type, c.comments
              FROM all_objects t
              LEFT JOIN all_tab_comments c
                ON c.owner = t.owner AND c.table_name = t.object_name
             WHERE t.owner IN ({in_clause})
               AND t.object_type IN {type_filter}
             ORDER BY t.owner, t.object_name
        """
        table_rows = self._query(table_sql, binds)

        tables: list[TableMeta] = []
        # Track (owner, table_name) we kept so we only emit columns for those.
        kept: set[tuple[str, str]] = set()
        for owner, name, obj_type, comment in table_rows:
            tags: dict[str, str] = {}
            if not self.is_asset_visible(tags):
                continue
            tables.append(
                TableMeta(
                    source_name=self.name,
                    catalog_name=catalog,
                    schema_name=owner,
                    table_name=name,
                    table_type=str(obj_type or "TABLE"),
                    comment=str(comment or ""),
                    owner=owner,
                    tags=tags,
                )
            )
            kept.add((owner, name))

        # Columns.
        col_sql = f"""
            SELECT c.owner, c.table_name, c.column_name, c.data_type,
                   c.column_id, c.nullable, cc.comments
              FROM all_tab_columns c
              LEFT JOIN all_col_comments cc
                ON cc.owner = c.owner
               AND cc.table_name = c.table_name
               AND cc.column_name = c.column_name
             WHERE c.owner IN ({in_clause})
             ORDER BY c.owner, c.table_name, c.column_id
        """
        col_rows = self._query(col_sql, binds)

        columns: list[ColumnMeta] = []
        for owner, table_name, col_name, data_type, col_id, nullable, comment in col_rows:
            if (owner, table_name) not in kept:
                continue
            columns.append(
                ColumnMeta(
                    source_name=self.name,
                    catalog_name=catalog,
                    schema_name=owner,
                    table_name=table_name,
                    column_name=col_name,
                    data_type=str(data_type or ""),
                    ordinal_position=int(col_id or 0),
                    is_nullable=(str(nullable or "Y").upper() == "Y"),
                    comment=str(comment or ""),
                )
            )

        logger.info(
            "Source '%s': crawled %d tables, %d columns in catalog '%s'",
            self.name, len(tables), len(columns), catalog,
        )
        return tables, columns
