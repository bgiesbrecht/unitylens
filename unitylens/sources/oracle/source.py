"""Oracle Database metadata source (stub implementation)."""

from __future__ import annotations

from typing import Any

from unitylens.sources.base import (
    CatalogMeta,
    ColumnMeta,
    DataSource,
    SchemaMeta,
    TableMeta,
)
from unitylens.sources.registry import register


@register("oracle")
class OracleSource(DataSource):
    """Oracle Database metadata source.

    This is a structural stub.  The crawl interface is fully wired but
    the actual Oracle connector logic is not yet implemented.

    Expected config keys (for future implementation):

    - ``dsn``:      Oracle TNS connection string or Easy Connect string.
    - ``user``:     Authentication user.
    - ``password``: Authentication password.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._dsn: str = config.get("dsn", "")
        self._user: str = config.get("user", "")

    def validate_connection(self) -> bool:
        raise NotImplementedError(
            "OracleSource.validate_connection() is not yet implemented. "
            "Install the oracledb package and provide dsn, user, and "
            "password in the source config."
        )

    def crawl_catalogs(self) -> list[CatalogMeta]:
        raise NotImplementedError(
            "OracleSource.crawl_catalogs() is not yet implemented. "
            "Oracle does not have a catalog concept in the same way; "
            "this will likely map to the database/service name."
        )

    def crawl_schemas(self, catalog: str) -> list[SchemaMeta]:
        raise NotImplementedError(
            "OracleSource.crawl_schemas() is not yet implemented. "
            "This will query ALL_USERS or DBA_USERS to enumerate schemas."
        )

    def crawl_tables(
        self, catalog: str
    ) -> tuple[list[TableMeta], list[ColumnMeta]]:
        raise NotImplementedError(
            "OracleSource.crawl_tables() is not yet implemented. "
            f"This will query ALL_TAB_COLUMNS for catalog {catalog}."
        )
