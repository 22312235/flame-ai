import uuid
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """Extracted textual and structural information from a document."""

    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    author: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    principal_investigator: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    file = relationship("File")

    units = relationship(
        "DocumentUnit",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentUnit.unit_number",
    )

    psi_fields = relationship(
        "PSIField",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    references = relationship(
        "DocumentReference",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    extracted_tables = relationship(
        "ExtractedTable",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    extracted_charts = relationship(
        "ExtractedChart",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentUnit(Base, TimestampMixin):
    """A page, slide, or logical section of a document."""

    __tablename__ = "document_units"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    unit_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    document = relationship(
        "Document",
        back_populates="units",
    )

    psi_fields = relationship(
        "PSIField",
        back_populates="unit",
    )

    extracted_tables = relationship(
        "ExtractedTable",
        back_populates="unit",
    )

    extracted_charts = relationship(
        "ExtractedChart",
        back_populates="unit",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "unit_type",
            "unit_number",
            name="uq_document_unit_number",
        ),
    )


class PSIField(Base, TimestampMixin):
    """A structured field extracted from a PSI document."""

    __tablename__ = "psi_fields"

    psi_field_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_units.unit_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        index=True,
    )

    value: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
    )

    field_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    source_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    document = relationship(
        "Document",
        back_populates="psi_fields",
    )

    unit = relationship(
        "DocumentUnit",
        back_populates="psi_fields",
    )


class DocumentReference(Base, TimestampMixin):
    """A bibliographic or DOI reference extracted from a document."""

    __tablename__ = "document_references"

    reference_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doi: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    authors: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    publication_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    citation_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    document = relationship(
        "Document",
        back_populates="references",
    )


class ExtractedTable(Base, TimestampMixin):
    """A table extracted from a PDF page or presentation slide."""

    __tablename__ = "extracted_tables"

    table_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_units.unit_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    table_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    headers: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    rows: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    document = relationship(
        "Document",
        back_populates="extracted_tables",
    )

    unit = relationship(
        "DocumentUnit",
        back_populates="extracted_tables",
    )


class ExtractedChart(Base, TimestampMixin):
    """A chart extracted from a document or presentation."""

    __tablename__ = "extracted_charts"

    chart_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_units.unit_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    chart_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    document = relationship(
        "Document",
        back_populates="extracted_charts",
    )

    unit = relationship(
        "DocumentUnit",
        back_populates="extracted_charts",
    )

    series = relationship(
        "ChartSeries",
        back_populates="chart",
        cascade="all, delete-orphan",
    )


class ChartSeries(Base, TimestampMixin):
    """An individual data series belonging to an extracted chart."""

    __tablename__ = "chart_series"

    series_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("extracted_charts.chart_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    x_values: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    y_values: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    x_unit: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    y_unit: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    chart = relationship(
        "ExtractedChart",
        back_populates="series",
    )