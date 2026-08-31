from __future__ import annotations

from dataclasses import dataclass

from backend.database.models import Song
from backend.recommendation.similarity import normalize_text, split_tags


@dataclass(frozen=True)
class MetadataTasteProfile:
    producers: frozenset[str]
    vocalists: frozenset[str]
    tags: frozenset[str]


def build_metadata_profile(favorites: list[Song]) -> MetadataTasteProfile:
    return MetadataTasteProfile(
        producers=frozenset(
            normalized
            for song in favorites
            if (normalized := normalize_text(song.producer))
        ),
        vocalists=frozenset(
            normalized
            for song in favorites
            if (normalized := normalize_text(song.vocalist))
        ),
        tags=frozenset(tag for song in favorites for tag in split_tags(song.tags)),
    )