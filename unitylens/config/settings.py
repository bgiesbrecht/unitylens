"""Application settings loaded from environment variables."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _interpolate_env_vars(value: Any) -> Any:
    """Recursively replace ``${ENV_VAR}`` placeholders with env values."""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{(\w+)\}")

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            env_val = os.environ.get(var_name, "")
            if not env_val:
                logger.warning("Environment variable '%s' is not set", var_name)
            return env_val

        return pattern.sub(replacer, value)
    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]
    return value


class Settings(BaseSettings):
    """UnityLens application settings.

    All values can be overridden via environment variables prefixed with
    ``UNITYLENS_``.
    """

    # Server
    host: str = Field(default="0.0.0.0", alias="UNITYLENS_HOST")
    port: int = Field(default=8000, alias="UNITYLENS_PORT")

    # Database
    db_path: str = Field(
        default=str(_PROJECT_ROOT / "unitylens.db"),
        alias="UNITYLENS_DB_PATH",
    )

    # Context cache
    context_path: str = Field(
        default=str(_PROJECT_ROOT / "context_cache.txt"),
        alias="UNITYLENS_CONTEXT_PATH",
    )

    # Sources config file
    sources_config_path: str = Field(
        default=str(_PROJECT_ROOT / "unitylens" / "config" / "sources.yaml"),
        alias="UNITYLENS_SOURCES_CONFIG",
    )

    # Crawler schedule (cron expression or interval minutes)
    crawl_cron: str = Field(default="", alias="UNITYLENS_CRAWL_CRON")
    crawl_interval_minutes: int = Field(
        default=60, alias="UNITYLENS_CRAWL_INTERVAL"
    )

    # LLM
    llm_endpoint_url: str = Field(default="", alias="UNITYLENS_LLM_ENDPOINT")
    llm_token: str = Field(default="", alias="UNITYLENS_LLM_TOKEN")
    llm_max_tokens: int = Field(default=2048, alias="UNITYLENS_LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.1, alias="UNITYLENS_LLM_TEMPERATURE")

    # CORS
    cors_origins: str = Field(default="*", alias="UNITYLENS_CORS_ORIGINS")

    # Static files directory for frontend
    static_dir: str = Field(
        default=str(_PROJECT_ROOT / "unitylens" / "static"),
        alias="UNITYLENS_STATIC_DIR",
    )

    model_config = {"env_prefix": "UNITYLENS_", "case_sensitive": False}

    def get_cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def load_sources_config(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load and interpolate the sources.yaml configuration.

    Returns a mapping of source name to config dict.
    """
    settings = get_settings()
    config_path = path or settings.sources_config_path

    if not Path(config_path).exists():
        logger.warning("Sources config not found at %s", config_path)
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "sources" not in raw:
        logger.warning("No 'sources' key found in %s", config_path)
        return {}

    sources: dict[str, dict[str, Any]] = {}
    for source_def in raw["sources"]:
        name = source_def.get("name")
        if not name:
            logger.warning("Source entry missing 'name', skipping: %s", source_def)
            continue
        interpolated = _interpolate_env_vars(source_def)
        sources[name] = interpolated

    logger.info("Loaded %d source configs from %s", len(sources), config_path)
    return sources


# Module-level singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
