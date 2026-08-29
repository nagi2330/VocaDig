from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import requests

from backend.crawler.parser import extract_items, parse_niconico_item
from backend.database.repository import LibraryRepository

LOGGER = logging.getLogger(__name__)
SNAPSHOT_SEARCH_ENDPOINT = (
    "https://snapshot.search.nicovideo.jp/api/v2/snapshot/video/contents/search"
)
SNAPSHOT_FIELDS = ",".join(
    (
        "contentId",
        "title",
        "description",
        "tags",
        "startTime",
        "viewCounter",
        "likeCounter",
        "commentCounter",
        "lengthSeconds",
        "thumbnailUrl",
    )
)


@dataclass(frozen=True)
class NiconicoCrawlerConfig:
    endpoint: str = SNAPSHOT_SEARCH_ENDPOINT
    query: str = "VOCALOID"
    page_size: int = 100
    max_pages: int = 10
    rate_limit_seconds: float = 1.0
    max_retries: int = 3
    timeout_seconds: float = 20.0
    user_agent: str = "VocaDig/0.1 (personal music discovery)"
    proxy_url: str | None = None


class NiconicoCrawler:
    """Incrementally import Niconico JSON feed/search results into the song library."""

    def __init__(
        self, config: NiconicoCrawlerConfig, http: requests.Session | None = None
    ) -> None:
        self.config = config
        self.http = http or requests.Session()
        self.http.headers.update({"User-Agent": config.user_agent})
        if config.proxy_url:
            self.http.proxies.update(
                {"http": config.proxy_url, "https": config.proxy_url}
            )

    def crawl(self, repository: LibraryRepository) -> int:
        inserted = 0
        for item in self._iter_items():
            song_data = parse_niconico_item(item)
            if song_data is None:
                LOGGER.warning(
                    "Skipping Niconico item with missing ID or title: %s", item
                )
                continue
            song_id = str(song_data["song_id"])
            exists = repository.get_song(song_id) is not None
            repository.upsert_platform_song("niconico", song_id, song_data)
            if not exists:
                inserted += 1
        LOGGER.info("Niconico crawl completed: %d new songs", inserted)
        return inserted

    def _iter_items(self) -> Iterator[dict[str, Any]]:
        for page_number in range(self.config.max_pages):
            payload = self._fetch_page(page_number)
            items = extract_items(payload)
            if not items:
                return
            yield from items
            if len(items) < self.config.page_size:
                return
            time.sleep(self.config.rate_limit_seconds)

    def _fetch_page(self, page_number: int) -> dict[str, Any]:
        params = {
            "q": self.config.query,
            "targets": "title,description,tags",
            "fields": SNAPSHOT_FIELDS,
            "_sort": "-startTime",
            "_offset": page_number * self.config.page_size,
            "_limit": self.config.page_size,
            "_context": "VocaDig",
        }
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = self.http.get(
                    self.config.endpoint,
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Niconico response root must be an object")
                return payload
            except (requests.RequestException, ValueError) as error:
                if attempt == self.config.max_retries:
                    LOGGER.exception(
                        "Niconico request failed after %d attempts", attempt
                    )
                    raise
                delay = self.config.rate_limit_seconds * attempt
                LOGGER.warning(
                    "Niconico request failed (%s); retrying in %.1fs", error, delay
                )
                time.sleep(delay)
        raise RuntimeError("Unreachable retry state")
