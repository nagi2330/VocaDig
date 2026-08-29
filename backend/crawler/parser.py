from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_niconico_item(item: dict[str, Any]) -> dict[str, object] | None:
    """Normalize common Niconico search API item shapes into the Song schema."""
    song_id = item.get("contentId") or item.get("videoId") or item.get("id")
    title = item.get("title")
    if not song_id or not title:
        return None

    raw_tags = item.get("tags") or item.get("tagsExact") or []
    tags = ",".join(raw_tags) if isinstance(raw_tags, list) else str(raw_tags)
    upload_time = _parse_datetime(item.get("startTime") or item.get("uploadTime"))
    return {
        "song_id": str(song_id),
        "title": str(title),
        "producer": item.get("producer") or item.get("channelName"),
        "upload_time": upload_time,
        "description": item.get("description"),
        "tags": tags,
        "url": item.get("watchUrl") or f"https://www.nicovideo.jp/watch/{song_id}",
        "thumbnail_url": item.get("thumbnailUrl"),
        "duration": _as_int(item.get("lengthSeconds") or item.get("duration")),
        "vocalist": item.get("vocalist"),
        "view_count": _as_int(item.get("viewCounter") or item.get("viewCount")) or 0,
        "like_count": _as_int(item.get("likeCounter") or item.get("likeCount")) or 0,
        "comment_count": _as_int(item.get("commentCounter") or item.get("commentCount")) or 0,
    }


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract item arrays from documented or wrapper-shaped JSON responses."""
    for key in ("data", "items", "contents"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    meta = payload.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("data"), list):
        return [item for item in meta["data"] if isinstance(item, dict)]
    return []


def _as_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None