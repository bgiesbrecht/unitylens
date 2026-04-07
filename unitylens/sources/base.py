"""DataSource abstract base class and metadata dataclasses."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalogMeta:
    """Metadata for a catalog (database-level container)."""

    source_name: str
    catalog_name: str
    comment: str = ""
    owner: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.source_name}::{self.catalog_name}"


@dataclass(frozen=True)
class SchemaMeta:
    """Metadata for a schema within a catalog."""

    source_name: str
    catalog_name: str
    schema_name: str
    comment: str = ""
    owner: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.source_name}::{self.catalog_name}.{self.schema_name}"


@dataclass(frozen=True)
class TableMeta:
    """Metadata for a table within a schema."""

    source_name: str
    catalog_name: str
    schema_name: str
    table_name: str
    table_type: str = "TABLE"
    comment: str = ""
    owner: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return (
            f"{self.source_name}::{self.catalog_name}"
            f".{self.schema_name}.{self.table_name}"
        )


@dataclass(frozen=True)
class ColumnMeta:
    """Metadata for a column within a table."""

    source_name: str
    catalog_name: str
    schema_name: str
    table_name: str
    column_name: str
    data_type: str = ""
    ordinal_position: int = 0
    is_nullable: bool = True
    comment: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return (
            f"{self.source_name}::{self.catalog_name}"
            f".{self.schema_name}.{self.table_name}.{self.column_name}"
        )


class DataSource(ABC):
    """Abstract base class for all metadata sources.

    Each concrete source must implement the crawl methods and
    connection validation.  The ``is_asset_visible`` helper supports
    governance-based filtering using tag deny/allow lists supplied in
    the source configuration.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self._deny_tags: dict[str, str] = config.get("deny_tags", {})
        self._allow_tags: dict[str, str] = config.get("allow_tags", {})

    # ------------------------------------------------------------------
    # Governance helpers
    # ------------------------------------------------------------------

    def is_asset_visible(self, tags: dict[str, str]) -> bool:
        """Determine whether an asset should be surfaced.

        Filtering modes:
        - **deny mode**: if *any* deny tag key/value pair matches the
          asset's tags the asset is hidden.
        - **allow mode**: if allow tags are configured the asset must
          carry *at least one* matching key/value pair to be visible.

        When neither deny nor allow tags are configured every asset is
        visible.
        """
        for key, value in self._deny_tags.items():
            if tags.get(key) == value:
                return False

        if self._allow_tags:
            for key, value in self._allow_tags.items():
                if tags.get(key) == value:
                    return True
            return False

        return True

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def validate_connection(self) -> bool:
        """Return True when the source is reachable."""

    @abstractmethod
    def crawl_catalogs(self) -> list[CatalogMeta]:
        """Return all catalogs visible in this source."""

    @abstractmethod
    def crawl_schemas(self, catalog: str) -> list[SchemaMeta]:
        """Return all schemas within *catalog*."""

    @abstractmethod
    def crawl_tables(
        self, catalog: str
    ) -> tuple[list[TableMeta], list[ColumnMeta]]:
        """Return all tables and their columns for *catalog*."""
