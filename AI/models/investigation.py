import uuid
from datetime import date, datetime

from sqlalchemy import Date, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # NASA / PSI identifier, when available.
    # Example: PSI-XXXX
    external_id: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    principal_investigator: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Flexible investigation metadata from PSI or other sources.
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    files: Mapped[list["File"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Investigation("
            f"id={self.investigation_id}, "
            f"external_id={self.external_id}, "
            f"title={self.title!r})>"
        )