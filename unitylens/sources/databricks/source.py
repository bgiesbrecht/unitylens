"""Databricks Unity Catalog metadata source."""

from __future__ import annotations

import json
import logging
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


def _tags_to_dict(tag_list: Any) -> dict[str, str]:
    """Convert a Databricks SDK tag list to a plain dict."""
    if not tag_list:
        return {}
    out: dict[str, str] = {}
    items = tag_list if isinstance(tag_list, list) else getattr(tag_list, "tags", []) or []
    for tag in items:
        key = getattr(tag, "key", None) or (tag.get("key") if isinstance(tag, dict) else None)
        val = getattr(tag, "value", None) or (tag.get("value") if isinstance(tag, dict) else None)
        if key is not None:
            out[str(key)] = str(val) if val is not None else ""
    return out


@register("databricks")
class DatabricksSource(DataSource):
    """Crawls metadata from a Databricks Unity Catalog workspace.

    Required config keys:

    - ``host``: Databricks workspace URL (e.g. ``https://myws.cloud.databricks.com``)
    - ``token``: Personal access token or service-principal token.
    - ``warehouse_id``: SQL warehouse ID used for ``information_schema`` queries.

    Optional config keys:

    - ``deny_tags``: ``dict[str, str]`` of tag key/value pairs to exclude.
    - ``allow_tags``: ``dict[str, str]`` of tag key/value pairs to require.
    - ``catalog_filter``: list of catalog name prefixes to include (default: all).
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._host: str = config["host"]
        self._token: str = config["token"]
        self._warehouse_id: str = config["warehouse_id"]
        self._catalog_filter: list[str] = config.get("catalog_filter", [])
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from databricks.sdk import WorkspaceClient  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "The 'databricks-sdk' package is required for DatabricksSource. "
                    "Install it with: pip install databricks-sdk"
                ) from exc
            self._client = WorkspaceClient(
                host=self._host,
                token=self._token,
            )
        return self._client

    def _execute_sql(self, statement: str) -> list[dict[str, Any]]:
        """Execute a SQL statement via the Databricks SQL Statement API."""
        import requests

        url = f"{self._host.rstrip('/')}/api/2.0/sql/statements/"
        payload = {
            "warehouse_id": self._warehouse_id,
            "statement": statement,
            "wait_timeout": "50s",
            "disposition": "INLINE",
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)

        # If the statement is still running, poll until complete
        body = None
        if resp.ok:
            body = resp.json()
            statement_id = body.get("statement_id")
            state = body.get("status", {}).get("state", "")
            while state in ("PENDING", "RUNNING") and statement_id:
                import time
                time.sleep(2)
                poll_resp = requests.get(
                    f"{self._host.rstrip('/')}/api/2.0/sql/statements/{statement_id}",
                    headers=headers,
                    timeout=30,
                )
                if not poll_resp.ok:
                    break
                body = poll_resp.json()
                state = body.get("status", {}).get("state", "")
        if not resp.ok:
            try:
                detail = resp.json().get("message", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            logger.warning(
                "SQL statement API returned %d for source '%s': %s",
                resp.status_code, self.name, detail,
            )
            raise RuntimeError(f"SQL API {resp.status_code}: {detail}")
        if body is None:
            body = resp.json()

        status = body.get("status", {}).get("state", "")
        if status == "FAILED":
            error_msg = body.get("status", {}).get("error", {}).get("message", "Unknown")
            raise RuntimeError(f"SQL execution failed: {error_msg}")

        if status != "SUCCEEDED":
            logger.warning(
                "SQL statement ended with state '%s' (not SUCCEEDED). Keys: %s",
                status, list(body.keys()),
            )

        # The SQL Statement API returns column metadata in "manifest.schema.columns"
        # and row data in "result.data_array"
        manifest = body.get("manifest", {})
        manifest_schema = manifest.get("schema", {})
        manifest_columns = manifest_schema.get("columns", [])

        result = body.get("result", {})
        if result is None:
            result = {}

        # Try manifest columns first, fall back to result columns
        raw_columns = manifest_columns or result.get("columns", [])
        columns = [col.get("name", col.get("column_name", "")) for col in raw_columns]
        data_array = result.get("data_array", [])

        logger.info(
            "SQL returned state=%s, %d columns, %d rows, body_keys=%s, result_keys=%s",
            status, len(columns), len(data_array),
            list(body.keys()), list(result.keys()),
        )

        rows: list[dict[str, Any]] = []
        for data_row in data_array:
            rows.append(dict(zip(columns, data_row)))
        return rows

    def _should_include_catalog(self, catalog_name: str) -> bool:
        if not self._catalog_filter:
            return True
        return any(catalog_name.startswith(prefix) for prefix in self._catalog_filter)

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    def validate_connection(self) -> bool:
        """Validate by listing catalogs (lightweight call)."""
        try:
            client = self._get_client()
            _ = list(client.catalogs.list())
            return True
        except Exception:
            logger.exception("Connection validation failed for source '%s'", self.name)
            return False

    def crawl_catalogs(self) -> list[CatalogMeta]:
        client = self._get_client()
        catalogs: list[CatalogMeta] = []
        for cat in client.catalogs.list():
            name = cat.name
            if not self._should_include_catalog(name):
                continue
            tags = _tags_to_dict(getattr(cat, "tags", None))
            if not self.is_asset_visible(tags):
                continue
            catalogs.append(
                CatalogMeta(
                    source_name=self.name,
                    catalog_name=name,
                    comment=getattr(cat, "comment", "") or "",
                    owner=getattr(cat, "owner", "") or "",
                    tags=tags,
                )
            )
        logger.info(
            "Source '%s': crawled %d catalogs", self.name, len(catalogs)
        )
        return catalogs

    def crawl_schemas(self, catalog: str) -> list[SchemaMeta]:
        client = self._get_client()
        schemas: list[SchemaMeta] = []
        for sch in client.schemas.list(catalog_name=catalog):
            tags = _tags_to_dict(getattr(sch, "tags", None))
            if not self.is_asset_visible(tags):
                continue
            schemas.append(
                SchemaMeta(
                    source_name=self.name,
                    catalog_name=catalog,
                    schema_name=sch.name,
                    comment=getattr(sch, "comment", "") or "",
                    owner=getattr(sch, "owner", "") or "",
                    tags=tags,
                )
            )
        logger.info(
            "Source '%s': crawled %d schemas in catalog '%s'",
            self.name,
            len(schemas),
            catalog,
        )
        return schemas

    def crawl_tables(
        self, catalog: str
    ) -> tuple[list[TableMeta], list[ColumnMeta]]:
        """Crawl all tables and columns in a catalog using the SDK.

        Uses SDK tables.list() for table metadata (works with PAT permissions),
        then fetches column details per table via SDK tables.get().
        """
        client = self._get_client()
        tables: list[TableMeta] = []
        columns: list[ColumnMeta] = []

        # Get all schemas for this catalog (already crawled, but we need the names)
        try:
            schema_list = list(client.schemas.list(catalog_name=catalog))
        except Exception:
            logger.warning("Cannot list schemas for catalog '%s', skipping", catalog)
            return [], []

        for sch in schema_list:
            if sch.name == "information_schema":
                continue

            try:
                for tbl in client.tables.list(
                    catalog_name=catalog, schema_name=sch.name
                ):
                    tags = _tags_to_dict(getattr(tbl, "tags", None))
                    if not self.is_asset_visible(tags):
                        continue

                    tables.append(
                        TableMeta(
                            source_name=self.name,
                            catalog_name=catalog,
                            schema_name=sch.name,
                            table_name=tbl.name,
                            table_type=str(getattr(tbl, "table_type", "TABLE") or "TABLE"),
                            comment=getattr(tbl, "comment", "") or "",
                            owner=getattr(tbl, "owner", "") or "",
                            tags=tags,
                        )
                    )

                    # Extract columns from the table's schema
                    tbl_columns = getattr(tbl, "columns", None) or []
                    for pos, col in enumerate(tbl_columns, 1):
                        columns.append(
                            ColumnMeta(
                                source_name=self.name,
                                catalog_name=catalog,
                                schema_name=sch.name,
                                table_name=tbl.name,
                                column_name=str(getattr(col, "name", "") or ""),
                                data_type=str(getattr(col, "type_name", getattr(col, "type_text", "")) or ""),
                                ordinal_position=int(getattr(col, "position", pos) or pos),
                                is_nullable=bool(getattr(col, "nullable", True)),
                                comment=str(getattr(col, "comment", "") or ""),
                            )
                        )
            except Exception:
                logger.warning(
                    "Error listing tables for %s.%s, skipping schema",
                    catalog, sch.name,
                )

        logger.info(
            "Source '%s': crawled %d tables, %d columns in catalog '%s'",
            self.name,
            len(tables),
            len(columns),
            catalog,
        )
        return tables, columns
