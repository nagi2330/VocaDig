from backend.database.repository import LibraryRepository


def test_library_crud_and_profile(session):
    repository = LibraryRepository(session)
    repository.upsert_song({"song_id": "sm1", "title": "First Song", "tags": "vocaloid"})
    repository.upsert_song({"song_id": "sm1", "title": "First Song Updated", "view_count": 42})

    assert repository.get_song("sm1").title == "First Song Updated"
    assert [song.song_id for song in repository.search_songs("updated")] == ["sm1"]

    favorite = repository.add_favorite("user-1", "sm1", rating=5)
    assert favorite.rating == 5
    assert len(repository.list_favorites("user-1")) == 1
    assert repository.remove_favorite("user-1", "sm1")
    assert not repository.remove_favorite("user-1", "sm1")

    repository.record_feedback("user-1", "sm1", "like")
    repository.set_profile("user-1", {"weights": {"metadata": 1.0}})
    assert repository.get_profile("user-1") == {"weights": {"metadata": 1.0}}


def test_recommendation_queries_return_favorites_and_unfavorited_candidates(session):
    repository = LibraryRepository(session)
    repository.upsert_song({"song_id": "sm1", "title": "Favorite"})
    repository.upsert_song({"song_id": "sm2", "title": "Candidate"})
    repository.add_favorite("user-1", "sm1")

    assert [song.song_id for song in repository.list_favorite_songs("user-1")] == ["sm1"]
    assert [song.song_id for song in repository.list_candidate_songs("user-1")] == ["sm2"]