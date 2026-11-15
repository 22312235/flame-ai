from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class ImageAsset(Base, TimestampMixin):
    """Stores the extracted metadata of a processed image."""

    __tablename__ = "images"

    image_id: Mapped[uuid.UUID] = mapped_column(
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

    image_format: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    aspect_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    pixel_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    color_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    has_transparency: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    frame_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    exif_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    thumbnail_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    warnings: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships

    file: Mapped["File"] = relationship(
        "File",
        foreign_keys=[file_id],
    )

    thumbnail_file: Mapped["File | None"] = relationship(
        "File",
        foreign_keys=[thumbnail_file_id],
    )

    contexts: Mapped[list["ImageContext"]] = relationship(
        "ImageContext",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ImageContext(Base, TimestampMixin):
    """
    Describes the context in which an image was found.

    An image can be standalone or embedded in a document unit,
    such as a PDF page or PowerPoint slide.
    """

    __tablename__ = "image_contexts"

    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("images.image_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_units.unit_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    context_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="standalone",
    )

    context_label: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships

    image: Mapped["ImageAsset"] = relationship(
        "ImageAsset",
        back_populates="contexts",
    )

    document_unit: Mapped["DocumentUnit | None"] = relationship(
        "DocumentUnit",
    )