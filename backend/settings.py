from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.crawler.bilibili import FAVORITES_ENDPOINT
from backend.crawler.niconico import SNAPSHOT_SEARCH_ENDPOINT
from backend.crawler.niconico_favorites import MYLIST_ENDPOINT

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python < 3.11
    import tomli as tomllib

DEFAULT_CONFIG_PATH = Path("config/settings.toml")
DEFAULT_DATABASE_URL = "sqlite:///data/vocadig.db"
DEFAULT_USER_AGENT = "VocaDig/0.1 (personal music discovery)"


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = DEFAULT_DATABASE_URL


@dataclass(frozen=True)
class NiconicoSettings:
    endpoint: str = SNAPSHOT_SEARCH_ENDPOINT
    query: str = "VOCALOID"
    page_size: int = 100
    max_pages: int = 10
    rate_limit_seconds: float = 1.0
    max_retries: int = 3
    timeout_seconds: float = 20.0
    user_agent: str = DEFAULT_USER_AGENT
    proxy_url: str | None = None


@dataclass(frozen=True)
class BilibiliSettings:
    endpoint: str = FAVORITES_ENDPOINT
    page_size: int = 20
    max_pages: int = 100
    rate_limit_seconds: float = 1.0
    timeout_seconds: float = 20.0
    user_agent: str = DEFAULT_USER_AGENT


@dataclass(frozen=True)
class NiconicoMylistSettings:
    endpoint_template: str = MYLIST_ENDPOINT
    page_size: int = 100
    max_pages: int = 100
    rate_limit_seconds: float = 1.0
    timeout_seconds: float = 20.0
    user_agent: str = DEFAULT_USER_AGENT


@dataclass(frozen=True)
class CollectionSettings:
    sync_interval_minutes: int = 360


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings = DatabaseSettings()
    niconico: NiconicoSettings = NiconicoSettings()
    bilibili: BilibiliSettings = BilibiliSettings()
    niconico_mylist: NiconicoMylistSettings = NiconicoMylistSettings()
    collections: CollectionSettings = CollectionSettings()


def load_settings(path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Load optional TOML settings, falling back to code defaults when absent."""
    if not path.exists():
        return Settings()
    with path.open("rb") as config_file:
        data = tomllib.load(config_file)
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a TOML table")

    crawler = _table(data, "crawler")
    return Settings(
        database=DatabaseSettings(**_values(data, "database", DatabaseSettings)),
        niconico=NiconicoSettings(**_values(crawler, "niconico", NiconicoSettings)),
        bilibili=BilibiliSettings(**_values(crawler, "bilibili", BilibiliSettings)),
        niconico_mylist=NiconicoMylistSettings(
            **_values(crawler, "niconico_mylist", NiconicoMylistSettings)
        ),
        collections=CollectionSettings(
            **_values(data, "collections", CollectionSettings)
        ),
    )


def _table(parent: dict[str, Any], name: str) -> dict[str, Any]:
    value = parent.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Configuration field '{name}' must be a table")
    return value


def _values(
    parent: dict[str, Any], name: str, settings_type: type[Any]
) -> dict[str, Any]:
    values = _table(parent, name)
    valid_names = set(settings_type.__dataclass_fields__)
    unknown_names = set(values) - valid_names
    if unknown_names:
        unknown = ", ".join(sorted(unknown_names))
        raise ValueError(f"Unknown configuration field '{name}.{unknown}'")
    return values