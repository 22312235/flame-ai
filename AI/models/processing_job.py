import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, utc_now


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Examples: tabular_processor, pdf_processor, video_processor.
    processor_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    processor_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # queued, running, completed, warning, failed, cancelled
    status: Mapped[str] = mapped_column(
        String(30),
        default="queued",
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Preserve all warnings returned by a processor.
    warnings: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Record settings used for this particular processing attempt.
    processing_parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    file: Mapped["File"] = relationship(
        back_populates="processing_jobs",
    )

    __table_args__ = (
        Index("ix_processing_jobs_file_status", "file_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessingJob("
            f"id={self.job_id}, "
            f"processor={self.processor_type}, "
            f"status={self.status})>"
        )