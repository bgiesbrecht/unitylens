"""Source registry: maps type strings to DataSource subclasses."""

from __future__ import annotations

import logging
from typing import Any, Type

from unitylens.sources.base import DataSource

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Type[DataSource]] = {}


def register(type_key: str):
    """Class decorator that registers a DataSource implementation.

    Usage::

        @register("databricks")
        class DatabricksSource(DataSource):
            ...
    """

    def decorator(cls: Type[DataSource]) -> Type[DataSource]:
        if type_key in _REGISTRY:
            logger.warning(
                "Overwriting existing registration for type '%s'", type_key
            )
        _REGISTRY[type_key] = cls
        return cls

    return decorator


def build_source(name: str, config: dict[str, Any]) -> DataSource:
    """Instantiate a registered DataSource by its type key.

    Parameters
    ----------
    name:
        Logical name for this source instance (e.g. ``"prod_databricks"``).
    config:
        Source configuration dict; must contain a ``"type"`` key whose
        value matches a previously registered type string.

    Returns
    -------
    DataSource
        A fully constructed source instance.

    Raises
    ------
    ValueError
        If the type key is missing or not registered.
    """
    type_key = config.get("type")
    if not type_key:
        raise ValueError(f"Source '{name}' config is missing a 'type' key")
    cls = _REGISTRY.get(type_key)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise ValueError(
            f"Unknown source type '{type_key}' for source '{name}'. "
            f"Registered types: {available}"
        )
    logger.info("Building source '%s' (type=%s)", name, type_key)
    return cls(name=name, config=config)


def registered_types() -> list[str]:
    """Return the list of currently registered type keys."""
    return sorted(_REGISTRY)
