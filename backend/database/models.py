from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Song(Base):
    __tablename__ = "songs"

    song_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    producer: Mapped[Optional[str]] = mapped_column(String(255))
    upload_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(2048))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(2048))
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    vocalist: Mapped[Optional[str]] = mapped_column(String(255))
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    __table_args__ = (UniqueConstraint("user_id", "song_id", name="uq_user_favorite_song"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    song_id: Mapped[str] = mapped_column(ForeignKey("songs.song_id"), nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    song_id: Mapped[str] = mapped_column(ForeignKey("songs.song_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferences_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CanonicalSong(Base):
    """A musical work which can have one or more platform video uploads."""

    __tablename__ = "canonical_songs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    producer: Mapped[Optional[str]] = mapped_column(String(255))
    vocalist: Mapped[Optional[str]] = mapped_column(String(255))
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlatformVideo(Base):
    """The immutable platform-specific identity of a video upload."""

    __tablename__ = "platform_videos"
    __table_args__ = (UniqueConstraint("platform", "video_id", name="uq_platform_video_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(128), nullable=False)
    song_id: Mapped[str] = mapped_column(ForeignKey("songs.song_id"), nullable=False, unique=True)
    canonical_song_id: Mapped[Optional[int]] = mapped_column(ForeignKey("canonical_songs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoMatchSuggestion(Base):
    """A reviewable proposal to place two platform videos under one work."""

    __tablename__ = "video_match_suggestions"
    __table_args__ = (
        UniqueConstraint("left_video_id", "right_video_id", name="uq_video_match_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    left_video_id: Mapped[int] = mapped_column(ForeignKey("platform_videos.id"), nullable=False)
    right_video_id: Mapped[int] = mapped_column(ForeignKey("platform_videos.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    auto_matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DefaultFavoriteCollection(Base):
    """A user-selected Niconico mylist or Bilibili favourite folder to monitor."""

    __tablename__ = "default_favorite_collections"
    __table_args__ = (UniqueConstraint("user_id", "platform", "remote_id", name="uq_default_collection"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    remote_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    credential_env: Mapped[Optional[str]] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=360)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FavoriteCollectionEntry(Base):
    """Latest observed membership of a monitored collection."""

    __tablename__ = "favorite_collection_entries"
    __table_args__ = (UniqueConstraint("collection_id", "song_id", name="uq_collection_song"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("default_favorite_collections.id"), nullable=False, index=True
    )
    song_id: Mapped[str] = mapped_column(ForeignKey("songs.song_id"), nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
