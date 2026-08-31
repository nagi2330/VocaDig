from __future__ import annotations

from dataclasses import dataclass
from math import log1p

from backend.database.models import Song
from backend.recommendation.profile import MetadataTasteProfile
from backend.recommendation.similarity import membership_similarity, split_tags, tag_similarity


@dataclass(frozen=True)
class RecommendationScore:
    total: float
    components: dict[str, float]


class MetadataScorer:
    """Score candidates with transparent metadata and novelty components."""

    def __init__(self, profile: MetadataTasteProfile, maximum_view_count: int) -> None:
        self.profile = profile
        self.maximum_view_count = max(maximum_view_count, 0)

    def score(self, song: Song) -> RecommendationScore:
        producer = membership_similarity(song.producer, self.profile.producers)
        vocalist = membership_similarity(song.vocalist, self.profile.vocalists)
        tags = tag_similarity(split_tags(song.tags), self.profile.tags)
        novelty = self._novelty(song.view_count)
        components = {
            "producer": producer,
            "vocalist": vocalist,
            "tags": tags,
            "novelty": novelty,
        }
        total = 0.35 * producer + 0.20 * vocalist + 0.35 * tags + 0.10 * novelty
        return RecommendationScore(total=total, components=components)

    def _novelty(self, view_count: int) -> float:
        if self.maximum_view_count == 0:
            return 0.0
        return 1.0 - log1p(max(view_count, 0)) / log1p(self.maximum_view_count)