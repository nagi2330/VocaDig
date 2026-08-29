from backend.database.repository import LibraryRepository


def test_default_collection_tracks_added_removed_and_unchanged_members(session):
    repository = LibraryRepository(session)
    collection = repository.save_default_collection(
        "user-1", "bilibili", "123", name="Vocaloid", sync_interval_minutes=60
    )
    for song_id in ("bilibili:BV1", "bilibili:BV2", "bilibili:BV3"):
        repository.upsert_song({"song_id": song_id, "title": song_id})

    first = repository.apply_collection_snapshot(collection.id, {"bilibili:BV1", "bilibili:BV2"})
    assert first.added_song_ids == ("bilibili:BV1", "bilibili:BV2")
    assert first.removed_song_ids == ()
    assert repository.list_default_collections("user-1", due_only=True) == []

    second = repository.apply_collection_snapshot(collection.id, {"bilibili:BV2", "bilibili:BV3"})
    assert second.added_song_ids == ("bilibili:BV3",)
    assert second.removed_song_ids == ("bilibili:BV1",)
    assert second.unchanged_count == 1
