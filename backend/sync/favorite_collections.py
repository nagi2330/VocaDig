"""Synchronize monitored favourite collections and record their differences."""

from __future__ import annotations

import os
from dataclasses import dataclass

from backend.crawler.bilibili import BilibiliFavoritesConfig, BilibiliFavoritesCrawler
from backend.crawler.niconico_favorites import NiconicoMylistConfig, NiconicoMylistCrawler
from backend.database.models import DefaultFavoriteCollection
from backend.database.repository import CollectionDifference, LibraryRepository


@dataclass(frozen=True)
class CollectionSyncReport:
    collection_id: int
    platform: str
    difference: CollectionDifference


class FavoriteCollectionSyncService:
    """Runs due collection synchronizations; schedule this class externally as desired."""

    def __init__(self, repository: LibraryRepository) -> None:
        self.repository = repository

    def sync_due(self, user_id: str, force: bool = False) -> list[CollectionSyncReport]:
        collections = self.repository.list_default_collections(user_id, due_only=not force)
        return [self.sync_collection(collection) for collection in collections]

    def sync_collection(self, collection: DefaultFavoriteCollection) -> CollectionSyncReport:
        if collection.platform == "bilibili":
            self.repository.bootstrap_legacy_niconico_videos()
        songs = list(self._fetch_songs(collection))
        song_ids: set[str] = set()
        for song in songs:
            song_id = str(song["song_id"])
            video_id = song_id.removeprefix("bilibili:") if collection.platform == "bilibili" else song_id
            self.repository.upsert_platform_song(collection.platform, video_id, song)
            self.repository.add_favorite(collection.user_id, song_id, source=f"{collection.platform}_collection")
            if collection.platform == "bilibili":
                self.repository.suggest_niconico_matches(song_id)
            song_ids.add(song_id)
        difference = self.repository.apply_collection_snapshot(collection.id, song_ids)
        return CollectionSyncReport(collection.id, collection.platform, difference)

    def _fetch_songs(self, collection: DefaultFavoriteCollection):
        cookie = self._cookie_for(collection)
        if collection.platform == "bilibili":
            crawler = BilibiliFavoritesCrawler(
                BilibiliFavoritesConfig(media_id=int(collection.remote_id), cookie=cookie)
            )
            return crawler.iter_songs()
        crawler = NiconicoMylistCrawler(NiconicoMylistConfig(mylist_id=collection.remote_id, cookie=cookie))
        return crawler.iter_songs()

    @staticmethod
    def _cookie_for(collection: DefaultFavoriteCollection) -> str | None:
        if not collection.credential_env:
            return None
        cookie = os.environ.get(collection.credential_env)
        if not cookie:
            raise RuntimeError(f"Set {collection.credential_env} before syncing collection {collection.id}")
        return cookie
