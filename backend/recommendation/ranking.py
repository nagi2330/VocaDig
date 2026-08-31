from __future__ import annotations

from dataclasses import dataclass

from backend.database.models import Song
from backend.database.repository import LibraryRepository
from backend.recommendation.profile import build_metadata_profile
from backend.recommendation.scorer import MetadataScorer, RecommendationScore
from backend.recommendation.similarity import normalize_text


@dataclass(frozen=True)
class BaselineRecommendation:
    song: Song
    score: RecommendationScore


def generate_recommendations(
    repository: LibraryRepository, user_id: str, limit: int = 20
) -> list[BaselineRecommendation]:
    if limit < 1:
        raise ValueError("limit must be positive")
    favorites = repository.list_favorite_songs(user_id)
    if not favorites:
        return []
    candidates = repository.list_candidate_songs(user_id)
    profile = build_metadata_profile(favorites)
    scorer = MetadataScorer(
        profile,
        maximum_view_count=max((song.view_count for song in candidates), default=0),
    )
    recommendations = [
        BaselineRecommendation(song=song, score=scorer.score(song))
        for song in candidates
    ]
    return sorted(
        recommendations,
        key=lambda recommendation: (
            -recommendation.score.total,
            normalize_text(recommendation.song.title),
            recommendation.song.song_id,
        ),
    )[:limit]