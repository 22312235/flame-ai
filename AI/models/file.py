import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, utc_now


class File(Base, TimestampMixin):
    __tablename__ = "files"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.investigation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Links a derived asset to the original file that produced it.
    parent_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    extension: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    detected_format: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Broad category: document, image, video, audio, tabular, etc.
    file_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # original, extracted_image, video_frame, scene_keyframe,
    # extracted_audio, thumbnail, transcript, etc.
    file_role: Mapped[str] = mapped_column(
        String(50),
        default="original",
        nullable=False,
    )

    # Identifies the storage implementation.
    # For the prototype, this will always be "local".
    storage_backend: Mapped[str] = mapped_column(
        String(30),
        default="local",
        nullable=False,
    )

    # Relative identifier within the configured storage root.
    # Example:
    # investigations/<investigation_id>/original/report.pdf
    storage_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        unique=True,
    )

    # Legacy field retained temporarily during migration.
    # New code should use storage_key instead.
    storage_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # pending, processing, processed, warning, failed, skipped
    processing_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        back_populates="files",
    )

    parent_file: Mapped["File | None"] = relationship(
        remote_side="File.file_id",
        back_populates="derived_files",
    )

    derived_files: Mapped[list["File"]] = relationship(
        back_populates="parent_file",
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_files_investigation_category",
            "investigation_id",
            "file_category",
        ),
        Index(
            "ix_files_investigation_role",
            "investigation_id",
            "file_role",
        ),
        Index(
            "ix_files_storage_backend",
            "storage_backend",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<File("
            f"id={self.file_id}, "
            f"filename={self.filename!r}, "
            f"category={self.file_category}, "
            f"status={self.processing_status})>"
        )