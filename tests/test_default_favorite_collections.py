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


def test_remove_default_collection_deletes_its_unshared_songs(session):
    repository = LibraryRepository(session)
    repository.upsert_song({"song_id": "sm9", "title": "Still here"})
    collection = repository.save_default_collection("user-1", "niconico", "123")
    repository.apply_collection_snapshot(collection.id, {"sm9"})

    assert repository.remove_default_collection("user-1", collection.id)
    assert repository.get_song("sm9") is None
    assert repository.list_default_collections("user-1") == []


def test_remove_default_collection_keeps_songs_in_another_collection(session):
    repository = LibraryRepository(session)
    repository.upsert_song({"song_id": "sm9", "title": "Shared song"})
    first = repository.save_default_collection("user-1", "niconico", "123")
    second = repository.save_default_collection("user-1", "niconico", "456")
    repository.apply_collection_snapshot(first.id, {"sm9"})
    repository.apply_collection_snapshot(second.id, {"sm9"})

    assert repository.remove_default_collection("user-1", first.id)
    assert repository.get_song("sm9") is not None
