from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
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