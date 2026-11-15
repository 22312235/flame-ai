import hashlib
import json
import uuid

from typing import Any, Optional

from sqlalchemy import (
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    """A processed numerical dataset or an individual spreadsheet sheet."""

    __tablename__ = "datasets"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
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

    processor_dataset_id: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    source_file: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_format: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    sheet_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
    )

    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)

    duplicate_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    duplicate_rows_removed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    empty_rows_removed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    empty_columns_removed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    parquet_path: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    profile_path: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    warnings: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    processed_at: Mapped[Optional[Any]] = mapped_column(
        # The processor supplies an ISO-formatted timestamp.
        # PostgreSQL stores it as a timezone-aware timestamp.
        __import__("sqlalchemy").DateTime(timezone=True),
        nullable=True,
    )

    profile_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    file = relationship("File", back_populates="datasets")

    dataset_variables: Mapped[list["DatasetVariable"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "processor_dataset_id",
            name="uq_dataset_file_processor_id",
        ),
        Index("ix_datasets_source_format", "source_format"),
        Index("ix_datasets_status", "status"),
    )


class Variable(Base, TimestampMixin):
    """A reusable numerical or categorical column definition."""

    __tablename__ = "variables"

    variable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    variable_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        index=True,
    )

    inferred_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    unit: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    dataset_variables: Mapped[list["DatasetVariable"]] = relationship(
        back_populates="variable",
        cascade="all, delete-orphan",
    )


class DatasetVariable(Base, TimestampMixin):
    """A variable's occurrence and profile within a particular dataset."""

    __tablename__ = "dataset_variables"

    dataset_variable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("variables.variable_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    column_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    non_null_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unique_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sample_values: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    statistics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    dataset = relationship(
        "Dataset",
        back_populates="dataset_variables",
    )

    variable = relationship(
        "Variable",
        back_populates="dataset_variables",
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "variable_id",
            name="uq_dataset_variable",
        ),
        Index(
            "ix_dataset_variables_dataset_position",
            "dataset_id",
            "column_position",
        ),
    )


def build_variable_key(
    name: str,
    inferred_type: str,
    unit: Optional[str],
) -> str:
    """Build a stable identity for a variable definition."""

    identity = json.dumps(
        [name, inferred_type, unit],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()