from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).casefold().strip()


def split_tags(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(
        normalized
        for tag in re.split(r"[,，\s]+", value)
        if (normalized := normalize_text(tag))
    )


def membership_similarity(value: str | None, preferences: frozenset[str]) -> float:
    normalized = normalize_text(value)
    return 1.0 if normalized and normalized in preferences else 0.0


def tag_similarity(candidate_tags: frozenset[str], preferences: frozenset[str]) -> float:
    if not candidate_tags or not preferences:
        return 0.0
    return len(candidate_tags & preferences) / len(candidate_tags)