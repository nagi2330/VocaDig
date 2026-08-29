"""Deterministic metadata matching for cross-platform Vocaloid uploads."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher


def normalize_text(value: str | None) -> str:
    """Make superficial Japanese/Latin title variations comparable."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[\[\(（].*?[\]\)）]", " ", value)
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)


def text_similarity(left: str | None, right: str | None) -> float:
    left_normalized, right_normalized = normalize_text(left), normalize_text(right)
    if not left_normalized or not right_normalized:
        return 0.0
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def duration_similarity(left: int | None, right: int | None) -> float | None:
    if left is None or right is None:
        return None
    difference = abs(left - right)
    if difference <= 3:
        return 1.0
    if difference >= 45:
        return 0.0
    return 1.0 - (difference - 3) / 42


@dataclass(frozen=True)
class MatchScore:
    confidence: float
    evidence: dict[str, float]


def score_song_match(left: object, right: object) -> MatchScore:
    """Score title, producer, vocalist and duration without external ML models."""
    title = text_similarity(getattr(left, "title", None), getattr(right, "title", None))
    producer = text_similarity(getattr(left, "producer", None), getattr(right, "producer", None))
    vocalist = text_similarity(getattr(left, "vocalist", None), getattr(right, "vocalist", None))
    duration = duration_similarity(getattr(left, "duration", None), getattr(right, "duration", None))
    weighted = [(title, 0.60), (producer, 0.20), (vocalist, 0.10)]
    if duration is not None:
        weighted.append((duration, 0.10))
    total_weight = sum(weight for _, weight in weighted)
    evidence = {"title": round(title, 4), "producer": round(producer, 4), "vocalist": round(vocalist, 4)}
    if duration is not None:
        evidence["duration"] = round(duration, 4)
    return MatchScore(round(sum(score * weight for score, weight in weighted) / total_weight, 4), evidence)
