from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.database.models import Song, UserFavorite, UserFeedback, UserProfile


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