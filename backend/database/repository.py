from __future__ import annotations

import json
from collections.abc import Iterable

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from backend.database.models import (
    CanonicalSong,
    DefaultFavoriteCollection,
    FavoriteCollectionEntry,
    PlatformVideo,
    Song,
    UserFavorite,
    UserFeedback,
    UserProfile,
    VideoMatchSuggestion,
)
from backend.matching import score_song_match


@dataclass(frozen=True)
class CollectionDifference:
    added_song_ids: tuple[str, ...]
    removed_song_ids: tuple[str, ...]
    unchanged_count: int


class LibraryRepository:
    """Persistence boundary for songs and one user's personal library."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_song(self, song_data: dict[str, object]) -> Song:
        song_id = str(song_data["song_id"])
        song = self.session.get(Song, song_id)
        if song is None:
            song = Song(song_id=song_id, title=str(song_data["title"]))
            self.session.add(song)

        for field, value in song_data.items():
            if field != "song_id" and hasattr(song, field) and value is not None:
                setattr(song, field, value)
        self.session.commit()
        return song

    def get_song(self, song_id: str) -> Song | None:
        return self.session.get(Song, song_id)

    def upsert_platform_song(
        self, platform: str, video_id: str, song_data: dict[str, object]
    ) -> Song:
        """Store video metadata and its platform-specific, immutable video ID."""
        song = self.upsert_song(song_data)
        video = self.session.scalar(
            select(PlatformVideo).where(
                PlatformVideo.platform == platform, PlatformVideo.video_id == video_id
            )
        )
        if video is None:
            video = PlatformVideo(platform=platform, video_id=video_id, song_id=song.song_id)
            self.session.add(video)
        elif video.song_id != song.song_id:
            raise ValueError(f"{platform} video {video_id} is already linked to another song record")
        self.session.commit()
        return song

    def bootstrap_legacy_niconico_videos(self) -> int:
        """Expose pre-cross-platform library rows to matching without changing their IDs.

        Before this feature all stored Song rows came from the Niconico crawler, so an
        unregistered legacy row is safely treated as a Niconico upload.
        """
        registered_song_ids = set(self.session.scalars(select(PlatformVideo.song_id)))
        added = 0
        for song in self.session.scalars(select(Song)):
            if song.song_id not in registered_song_ids:
                self.session.add(
                    PlatformVideo(platform="niconico", video_id=song.song_id, song_id=song.song_id)
                )
                added += 1
        if added:
            self.session.commit()
        return added

    def save_default_collection(
        self,
        user_id: str,
        platform: str,
        remote_id: str,
        *,
        name: str | None = None,
        credential_env: str | None = None,
        sync_interval_minutes: int = 360,
        enabled: bool = True,
    ) -> DefaultFavoriteCollection:
        if platform not in {"niconico", "bilibili"}:
            raise ValueError("platform must be niconico or bilibili")
        if sync_interval_minutes < 1:
            raise ValueError("sync_interval_minutes must be positive")
        collection = self.session.scalar(
            select(DefaultFavoriteCollection).where(
                DefaultFavoriteCollection.user_id == user_id,
                DefaultFavoriteCollection.platform == platform,
                DefaultFavoriteCollection.remote_id == str(remote_id),
            )
        )
        if collection is None:
            collection = DefaultFavoriteCollection(
                user_id=user_id, platform=platform, remote_id=str(remote_id)
            )
            self.session.add(collection)
        collection.name = name
        collection.credential_env = credential_env
        collection.sync_interval_minutes = sync_interval_minutes
        collection.enabled = enabled
        self.session.commit()
        return collection

    def list_default_collections(self, user_id: str, due_only: bool = False) -> list[DefaultFavoriteCollection]:
        collections = list(
            self.session.scalars(
                select(DefaultFavoriteCollection)
                .where(
                    DefaultFavoriteCollection.user_id == user_id,
                    DefaultFavoriteCollection.enabled.is_(True),
                )
                .order_by(DefaultFavoriteCollection.platform, DefaultFavoriteCollection.id)
            )
        )
        if not due_only:
            return collections
        now = datetime.now(timezone.utc)
        def is_due(collection: DefaultFavoriteCollection) -> bool:
            if collection.last_synced_at is None:
                return True
            last_synced = collection.last_synced_at
            if last_synced.tzinfo is None:
                last_synced = last_synced.replace(tzinfo=timezone.utc)
            return last_synced + timedelta(minutes=collection.sync_interval_minutes) <= now
        return [
            collection for collection in collections if is_due(collection)
        ]

    def remove_default_collection(self, user_id: str, collection_id: int) -> bool:
        """Remove a collection and songs that no other monitored collection contains."""
        collection = self.session.scalar(
            select(DefaultFavoriteCollection).where(
                DefaultFavoriteCollection.id == collection_id,
                DefaultFavoriteCollection.user_id == user_id,
            )
        )
        if collection is None:
            return False
        collection_entries = list(self.session.scalars(
            select(FavoriteCollectionEntry).where(FavoriteCollectionEntry.collection_id == collection_id)
        ))
        candidate_song_ids = {entry.song_id for entry in collection_entries}
        deletable_song_ids = {
            song_id
            for song_id in candidate_song_ids
            if not self.session.scalar(
                select(FavoriteCollectionEntry.id).where(
                    FavoriteCollectionEntry.song_id == song_id,
                    FavoriteCollectionEntry.collection_id != collection_id,
                    FavoriteCollectionEntry.present.is_(True),
                )
            )
        }
        for entry in collection_entries:
            self.session.delete(entry)
        self.session.delete(collection)
        self.session.flush()

        for song_id in deletable_song_ids:
            videos = list(self.session.scalars(
                select(PlatformVideo).where(PlatformVideo.song_id == song_id)
            ))
            video_ids = [video.id for video in videos]
            canonical_ids = {video.canonical_song_id for video in videos if video.canonical_song_id is not None}
            if video_ids:
                self.session.execute(
                    delete(VideoMatchSuggestion).where(
                        VideoMatchSuggestion.left_video_id.in_(video_ids)
                        | VideoMatchSuggestion.right_video_id.in_(video_ids)
                    )
                )
            self.session.execute(delete(FavoriteCollectionEntry).where(FavoriteCollectionEntry.song_id == song_id))
            self.session.execute(delete(UserFavorite).where(UserFavorite.song_id == song_id))
            self.session.execute(delete(UserFeedback).where(UserFeedback.song_id == song_id))
            self.session.execute(delete(PlatformVideo).where(PlatformVideo.song_id == song_id))
            self.session.execute(delete(Song).where(Song.song_id == song_id))
            for canonical_id in canonical_ids:
                has_uploads = self.session.scalar(
                    select(PlatformVideo.id).where(PlatformVideo.canonical_song_id == canonical_id)
                )
                if has_uploads is None:
                    self.session.execute(delete(CanonicalSong).where(CanonicalSong.id == canonical_id))
        self.session.commit()
        return True

    def apply_collection_snapshot(
        self, collection_id: int, song_ids: set[str]
    ) -> CollectionDifference:
        """Persist the current remote membership and report differences from the last run."""
        collection = self.session.get(DefaultFavoriteCollection, collection_id)
        if collection is None:
            raise ValueError(f"Unknown default collection {collection_id}")
        now = datetime.now(timezone.utc)
        entries = {
            entry.song_id: entry
            for entry in self.session.scalars(
                select(FavoriteCollectionEntry).where(
                    FavoriteCollectionEntry.collection_id == collection_id
                )
            )
        }
        added, removed, unchanged = [], [], 0
        for song_id in song_ids:
            entry = entries.get(song_id)
            if entry is None:
                self.session.add(FavoriteCollectionEntry(collection_id=collection_id, song_id=song_id))
                added.append(song_id)
            else:
                if not entry.present:
                    added.append(song_id)
                else:
                    unchanged += 1
                entry.present, entry.last_seen_at, entry.removed_at = True, now, None
        for song_id, entry in entries.items():
            if entry.present and song_id not in song_ids:
                entry.present, entry.removed_at = False, now
                removed.append(song_id)
        collection.last_synced_at = now
        self.session.commit()
        return CollectionDifference(tuple(sorted(added)), tuple(sorted(removed)), unchanged)

    def set_default_collection_name(self, collection_id: int, name: str) -> DefaultFavoriteCollection:
        collection = self.session.get(DefaultFavoriteCollection, collection_id)
        if collection is None:
            raise ValueError(f"Unknown default collection {collection_id}")
        collection.name = name
        self.session.commit()
        return collection

    def list_match_suggestions(self, status: str = "pending") -> list[VideoMatchSuggestion]:
        return list(
            self.session.scalars(
                select(VideoMatchSuggestion)
                .where(VideoMatchSuggestion.status == status)
                .order_by(VideoMatchSuggestion.confidence.desc(), VideoMatchSuggestion.created_at)
            )
        )

    def get_platform_counterparts(self, song_id: str, platform: str) -> list[Song]:
        """Return linked uploads on another platform after a match is confirmed."""
        source = self.session.scalar(select(PlatformVideo).where(PlatformVideo.song_id == song_id))
        if source is None or source.canonical_song_id is None:
            return []
        return list(
            self.session.scalars(
                select(Song)
                .join(PlatformVideo, PlatformVideo.song_id == Song.song_id)
                .where(
                    PlatformVideo.platform == platform,
                    PlatformVideo.canonical_song_id == source.canonical_song_id,
                )
                .order_by(Song.upload_time.desc(), Song.title)
            )
        )

    def suggest_niconico_matches(
        self, song_id: str, review_threshold: float = 0.65, auto_threshold: float = 0.90
    ) -> list[VideoMatchSuggestion]:
        """Create review items; auto-link only an unambiguous, very strong match."""
        source_video = self.session.scalar(select(PlatformVideo).where(PlatformVideo.song_id == song_id))
        source_song = self.get_song(song_id)
        if source_video is None or source_song is None:
            raise ValueError(f"Song {song_id} has no platform video")
        candidates = list(
            self.session.execute(
                select(PlatformVideo, Song)
                .join(Song, PlatformVideo.song_id == Song.song_id)
                .where(PlatformVideo.platform == "niconico")
            ).all()
        )
        scored = sorted(
            ((video, song, score_song_match(source_song, song)) for video, song in candidates),
            key=lambda item: item[2].confidence,
            reverse=True,
        )
        suggestions: list[VideoMatchSuggestion] = []
        for index, (candidate_video, _, score) in enumerate(scored):
            if score.confidence < review_threshold:
                break
            left_id, right_id = sorted((source_video.id, candidate_video.id))
            suggestion = self.session.scalar(
                select(VideoMatchSuggestion).where(
                    VideoMatchSuggestion.left_video_id == left_id,
                    VideoMatchSuggestion.right_video_id == right_id,
                )
            )
            if suggestion is None:
                unambiguous = index == 0 and (
                    len(scored) == 1 or score.confidence - scored[1][2].confidence >= 0.08
                )
                should_auto_match = score.confidence >= auto_threshold and unambiguous
                suggestion = VideoMatchSuggestion(
                    left_video_id=left_id,
                    right_video_id=right_id,
                    confidence=score.confidence,
                    evidence_json=json.dumps(score.evidence, ensure_ascii=False, sort_keys=True),
                    status="confirmed" if should_auto_match else "pending",
                    auto_matched=should_auto_match,
                    reviewed_at=datetime.now(timezone.utc) if should_auto_match else None,
                )
                self.session.add(suggestion)
                if should_auto_match:
                    self._link_videos(source_video, candidate_video)
            suggestions.append(suggestion)
        self.session.commit()
        return suggestions

    def review_match_suggestion(self, suggestion_id: int, confirmed: bool) -> VideoMatchSuggestion:
        suggestion = self.session.get(VideoMatchSuggestion, suggestion_id)
        if suggestion is None:
            raise ValueError(f"Unknown match suggestion {suggestion_id}")
        if suggestion.status != "pending":
            raise ValueError(f"Match suggestion {suggestion_id} was already reviewed")
        suggestion.status = "confirmed" if confirmed else "rejected"
        suggestion.reviewed_at = datetime.now(timezone.utc)
        if confirmed:
            left = self.session.get(PlatformVideo, suggestion.left_video_id)
            right = self.session.get(PlatformVideo, suggestion.right_video_id)
            assert left is not None and right is not None
            self._link_videos(left, right)
        self.session.commit()
        return suggestion

    def _link_videos(self, left: PlatformVideo, right: PlatformVideo) -> CanonicalSong:
        if left.canonical_song_id and right.canonical_song_id:
            if left.canonical_song_id != right.canonical_song_id:
                raise ValueError("Cannot merge two existing canonical songs automatically")
            return self.session.get(CanonicalSong, left.canonical_song_id)  # type: ignore[return-value]
        existing_id = left.canonical_song_id or right.canonical_song_id
        canonical = self.session.get(CanonicalSong, existing_id) if existing_id else None
        if canonical is None:
            source = self.get_song(left.song_id)
            assert source is not None
            canonical = CanonicalSong(
                title=source.title, producer=source.producer, vocalist=source.vocalist, duration=source.duration
            )
            self.session.add(canonical)
            self.session.flush()
        left.canonical_song_id = canonical.id
        right.canonical_song_id = canonical.id
        return canonical

    def search_songs(self, query: str, limit: int = 50) -> list[Song]:
        statement: Select[tuple[Song]] = (
            select(Song)
            .where(Song.title.ilike(f"%{query}%"))
            .order_by(Song.upload_time.desc(), Song.title)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add_favorite(
        self, user_id: str, song_id: str, rating: int | None = None, source: str = "manual"
    ) -> UserFavorite:
        favorite = self.session.scalar(
            select(UserFavorite).where(
                UserFavorite.user_id == user_id, UserFavorite.song_id == song_id
            )
        )
        if favorite is None:
            favorite = UserFavorite(user_id=user_id, song_id=song_id, source=source)
            self.session.add(favorite)
        favorite.rating = rating
        favorite.source = source
        self.session.commit()
        return favorite

    def remove_favorite(self, user_id: str, song_id: str) -> bool:
        favorite = self.session.scalar(
            select(UserFavorite).where(
                UserFavorite.user_id == user_id, UserFavorite.song_id == song_id
            )
        )
        if favorite is None:
            return False
        self.session.delete(favorite)
        self.session.commit()
        return True

    def list_favorites(self, user_id: str) -> list[UserFavorite]:
        return list(
            self.session.scalars(
                select(UserFavorite).where(UserFavorite.user_id == user_id).order_by(UserFavorite.created_at)
            )
        )

    def record_feedback(self, user_id: str, song_id: str, action: str) -> UserFeedback:
        feedback = UserFeedback(user_id=user_id, song_id=song_id, action=action)
        self.session.add(feedback)
        self.session.commit()
        return feedback

    def set_profile(self, user_id: str, preferences: dict[str, object]) -> UserProfile:
        profile = self.session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self.session.add(profile)
        profile.preferences_json = json.dumps(preferences, ensure_ascii=False, sort_keys=True)
        self.session.commit()
        return profile

    def get_profile(self, user_id: str) -> dict[str, object]:
        profile = self.session.get(UserProfile, user_id)
        return json.loads(profile.preferences_json) if profile else {}

    def insert_songs(self, songs: Iterable[dict[str, object]]) -> int:
        inserted = 0
        for song_data in songs:
            if self.get_song(str(song_data["song_id"])) is None:
                inserted += 1
            self.upsert_song(song_data)
        return inserted
