from __future__ import annotations

import uuid

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


if TYPE_CHECKING:
    from models.file import File


class Video(Base, TimestampMixin):
    """Stores technical metadata for a processed video."""

    __tablename__ = "videos"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    fps: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    frame_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    video_codec: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    audio_codec: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    has_audio: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships

    file: Mapped["File"] = relationship(
        "File",
        foreign_keys=[file_id],
    )

    frames: Mapped[list["VideoFrame"]] = relationship(
        "VideoFrame",
        back_populates="video",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    audio_tracks: Mapped[list["AudioTrack"]] = relationship(
        "AudioTrack",
        back_populates="video",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VideoFrame(Base, TimestampMixin):
    """
    Stores extracted video frames and detected scene events.

    frame_type:
        regular  - frame extracted at a regular interval.
        scene    - detected scene-change timestamp.
        keyframe - image extracted at a scene-change timestamp.
    """

    __tablename__ = "video_frames"

    frame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    frame_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    timestamp_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    frame_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    frame_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships

    video: Mapped["Video"] = relationship(
        "Video",
        back_populates="frames",
    )

    frame_file: Mapped["File | None"] = relationship(
        "File",
        foreign_keys=[frame_file_id],
    )


class AudioTrack(Base, TimestampMixin):
    """Stores metadata for audio extracted from a video."""

    __tablename__ = "audio_tracks"

    audio_track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    audio_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sample_rate: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    channels: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    audio_format: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships

    video: Mapped["Video"] = relationship(
        "Video",
        back_populates="audio_tracks",
    )

    audio_file: Mapped["File | None"] = relationship(
        "File",
        foreign_keys=[audio_file_id],
    )

    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="audio_track",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Transcript(Base, TimestampMixin):
    """Stores transcription output and its associated metadata."""

    __tablename__ = "transcripts"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    audio_track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audio_tracks.audio_track_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    transcript_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    segments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    warnings: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships

    audio_track: Mapped["AudioTrack"] = relationship(
        "AudioTrack",
        back_populates="transcripts",
    )

    transcript_file: Mapped["File | None"] = relationship(
        "File",
        foreign_keys=[transcript_file_id],
    )