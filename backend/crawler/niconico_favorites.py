"""Niconico mylist reader used by the default-collection synchronizer."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import requests

from backend.crawler.cookies import load_cookie_header
from backend.crawler.parser import parse_niconico_item

MYLIST_ENDPOINT = "https://nvapi.nicovideo.jp/v2/mylists/{mylist_id}"


@dataclass(frozen=True)
class NiconicoMylistConfig:
    mylist_id: str
    endpoint_template: str = MYLIST_ENDPOINT
    page_size: int = 100
    max_pages: int = 100
    rate_limit_seconds: float = 1.0
    timeout_seconds: float = 20.0
    cookie: str | None = None
    user_agent: str = "VocaDig/0.1 (personal music discovery)"


class NiconicoMylistCrawler:
    def __init__(self, config: NiconicoMylistConfig, http: requests.Session | None = None) -> None:
        self.config, self.http = config, http or requests.Session()
        self.collection_name: str | None = None
        self.http.headers.update({
            "User-Agent": config.user_agent,
            "X-Frontend-Id": "6",
            "X-Frontend-Version": "0",
        })
        if config.cookie:
            self.http.headers.update({"Cookie": load_cookie_header(config.cookie, ".nicovideo.jp")})

    def iter_songs(self) -> Iterator[dict[str, object]]:
        for page in range(1, self.config.max_pages + 1):
            response = self.http.get(
                self.config.endpoint_template.format(mylist_id=self.config.mylist_id),
                params={"page": page, "pageSize": self.config.page_size},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            mylist = data.get("mylist") if isinstance(data, dict) else None
            items = mylist.get("items") if isinstance(mylist, dict) else None
            if isinstance(mylist, dict) and isinstance(mylist.get("name"), str):
                self.collection_name = mylist["name"]
            if not isinstance(items, list):
                return
            for item in items:
                song = _parse_mylist_item(item)
                if song is not None:
                    yield song
            if len(items) < self.config.page_size:
                return
            time.sleep(self.config.rate_limit_seconds)


def _parse_mylist_item(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    video = item.get("video") if isinstance(item.get("video"), dict) else item
    normalized = {
        "contentId": video.get("id") or video.get("watchId"),
        "title": video.get("title"),
        "description": video.get("description"),
        "tags": video.get("tags"),
        "startTime": video.get("registeredAt") or video.get("startTime"),
        "viewCounter": video.get("count", {}).get("view") if isinstance(video.get("count"), dict) else video.get("viewCounter"),
        "likeCounter": video.get("count", {}).get("like") if isinstance(video.get("count"), dict) else video.get("likeCounter"),
        "commentCounter": video.get("count", {}).get("comment") if isinstance(video.get("count"), dict) else video.get("commentCounter"),
        "lengthSeconds": video.get("duration") or video.get("lengthSeconds"),
        "thumbnailUrl": video.get("thumbnail", {}).get("url") if isinstance(video.get("thumbnail"), dict) else video.get("thumbnailUrl"),
        "channelName": video.get("owner", {}).get("name") if isinstance(video.get("owner"), dict) else None,
    }
    return parse_niconico_item(normalized)
