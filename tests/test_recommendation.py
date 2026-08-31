from backend.database.repository import LibraryRepository
from backend.recommendation.ranking import generate_recommendations


def test_metadata_recommendations_prioritize_matching_candidate(session):
    repository = LibraryRepository(session)
    repository.upsert_song(
        {
            "song_id": "sm-favorite",
            "title": "Favorite",
            "producer": "Composer",
            "vocalist": "Miku",
            "tags": "vocaloid,electronic",
        }
    )
    repository.upsert_song(
        {
            "song_id": "sm-match",
            "title": "Matching Candidate",
            "producer": "Composer",
            "vocalist": "Miku",
            "tags": "vocaloid,electronic",
            "view_count": 100,
        }
    )
    repository.upsert_song(
        {
            "song_id": "sm-other",
            "title": "Other Candidate",
            "producer": "Another Composer",
            "vocalist": "Rin",
            "tags": "rock",
            "view_count": 10,
        }
    )
    repository.add_favorite("user-1", "sm-favorite")

    recommendations = generate_recommendations(repository, "user-1")

    assert [item.song.song_id for item in recommendations] == ["sm-match", "sm-other"]
    assert recommendations[0].score.components == {
        "producer": 1.0,
        "vocalist": 1.0,
        "tags": 1.0,
        "novelty": 0.0,
    }
    assert recommendations[0].score.total > recommendations[1].score.total


def test_metadata_recommendations_require_a_favorite_seed(session):
    repository = LibraryRepository(session)
    repository.upsert_song({"song_id": "sm-candidate", "title": "Candidate"})

    assert generate_recommendations(repository, "user-1") == []