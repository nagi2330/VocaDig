from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import requests

from backend.database.repository import LibraryRepository

LOGGER = logging.getLogger(__name__)
FAVORITES_ENDPOINT = "https://api.bilibili.com/x/v3/fav/resource/list"


@dataclass(frozen=True)
class BilibiliFavoritesConfig:
    media_id: int
    endpoint: str = FAVORITES_ENDPOINT
    page_size: int = 20
    max_pages: int = 100
    rate_limit_seconds: float = 1.0
    timeout_seconds: float = 20.0
    cookie: str | None = None
    user_agent: str = "VocaDig/0.1 (personal music discovery)"


def parse_bilibili_favorite(item: dict[str, Any]) -> dict[str, object] | None:
    bvid, title = item.get("bvid"), item.get("title")
    if not bvid or not title:
        return None
    upper = item.get("upper") if isinstance(item.get("upper"), dict) else {}
    stat = item.get("cnt_info") if isinstance(item.get("cnt_info"), dict) else {}
    return {
        "song_id": f"bilibili:{bvid}", "title": str(title), "producer": upper.get("name"),
        "upload_time": _unix_time(item.get("pubtime")), "description": item.get("intro"),
        "tags": None, "url": f"https://www.bilibili.com/video/{bvid}", "thumbnail_url": item.get("cover"),
        "duration": _duration_seconds(item.get("duration")), "vocalist": None,
        "view_count": _as_int(stat.get("play")) or 0, "like_count": _as_int(stat.get("collect")) or 0,
        "comment_count": _as_int(stat.get("reply")) or 0,
    }


class BilibiliFavoritesCrawler:
    """Import videos from one Bilibili favourite folder using the user's session cookie."""

    def __init__(self, config: BilibiliFavoritesConfig, http: requests.Session | None = None) -> None:
        self.config, self.http = config, http or requests.Session()
        self.http.headers.update({"User-Agent": config.user_agent})
        if config.cookie:
            self.http.headers.update({"Cookie": config.cookie})

    def crawl(self, repository: LibraryRepository, user_id: str) -> int:
        imported = 0
        repository.bootstrap_legacy_niconico_videos()
        for song in self.iter_songs():
            existed = repository.get_song(str(song["song_id"])) is not None
            repository.upsert_platform_song("bilibili", str(song["song_id"])[len("bilibili:"):], song)
            repository.add_favorite(user_id, str(song["song_id"]), source="bilibili_favorite")
            repository.suggest_niconico_matches(str(song["song_id"]))
            imported += not existed
        return imported

    def iter_songs(self) -> Iterator[dict[str, object]]:
        for item in self._iter_items():
            song = parse_bilibili_favorite(item)
            if song is None:
                LOGGER.warning("Skipping Bilibili favorite with missing BV ID or title: %s", item)
                continue
            yield song

    def _iter_items(self) -> Iterator[dict[str, Any]]:
        for page in range(1, self.config.max_pages + 1):
            response = self.http.get(self.config.endpoint, params={"media_id": self.config.media_id, "pn": page, "ps": self.config.page_size, "keyword": "", "order": "mtime", "type": 0, "tid": 0, "platform": "web"}, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                raise ValueError("Bilibili favorites response has no data object")
            items = data.get("medias")
            if not isinstance(items, list):
                return
            yield from (item for item in items if isinstance(item, dict))
            if not data.get("has_more"):
                return
            time.sleep(self.config.rate_limit_seconds)


def _as_int(value: object) -> int | None:
    try: return int(value) if value is not None else None
    except (TypeError, ValueError): return None


def _duration_seconds(value: object) -> int | None:
    if isinstance(value, int): return value
    if not isinstance(value, str): return _as_int(value)
    parts = value.split(":")
    try: return sum(int(part) * 60 ** index for index, part in enumerate(reversed(parts)))
    except ValueError: return None


def _unix_time(value: object):
    from datetime import datetime, timezone
    timestamp = _as_int(value)
    return datetime.fromtimestamp(timestamp, timezone.utc) if timestamp else None
