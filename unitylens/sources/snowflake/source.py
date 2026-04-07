"""Snowflake metadata source (stub implementation)."""

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


@register("snowflake")
class SnowflakeSource(DataSource):
    """Snowflake metadata source.

    This is a structural stub.  The crawl interface is fully wired but
    the actual Snowflake connector logic is not yet implemented.

    Expected config keys (for future implementation):

    - ``account``:   Snowflake account identifier.
    - ``user``:      Authentication user.
    - ``password``:  Authentication password (or use key-pair auth).
    - ``warehouse``: Snowflake warehouse for queries.
    - ``role``:      Role to assume.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._account: str = config.get("account", "")
        self._user: str = config.get("user", "")
        self._warehouse: str = config.get("warehouse", "")
        self._role: str = config.get("role", "")

    def validate_connection(self) -> bool:
        raise NotImplementedError(
            "SnowflakeSource.validate_connection() is not yet implemented. "
            "Install the snowflake-connector-python package and provide "
            "account, user, password, warehouse, and role in the source config."
        )

    def crawl_catalogs(self) -> list[CatalogMeta]:
        raise NotImplementedError(
            "SnowflakeSource.crawl_catalogs() is not yet implemented. "
            "This will query SHOW DATABASES to enumerate catalogs."
        )

    def crawl_schemas(self, catalog: str) -> list[SchemaMeta]:
        raise NotImplementedError(
            "SnowflakeSource.crawl_schemas() is not yet implemented. "
            f"This will query SHOW SCHEMAS IN DATABASE {catalog}."
        )

    def crawl_tables(
        self, catalog: str
    ) -> tuple[list[TableMeta], list[ColumnMeta]]:
        raise NotImplementedError(
            "SnowflakeSource.crawl_tables() is not yet implemented. "
            f"This will query INFORMATION_SCHEMA.COLUMNS in {catalog}."
        )
