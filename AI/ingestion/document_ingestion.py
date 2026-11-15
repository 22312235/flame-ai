from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.file import File
from models.document import (
    Document,
    DocumentUnit,
    PSIField,
    DocumentReference,
    ExtractedTable,
    ExtractedChart,
    ChartSeries,
)
from models.image import ImageAsset, ImageContext

from database.repositories.file_repository import FileRepository
from storage import LocalStorage, StorageBackend


@dataclass
class DocumentIngestionResult:
    """Summary of persisted document extraction results."""

    document: Document
    units_created: int = 0
    psi_fields_created: int = 0
    references_created: int = 0
    tables_created: int = 0
    charts_created: int = 0
    chart_series_created: int = 0
    images_created: int = 0
    registered_files: int = 0
    warnings: list[str] = field(default_factory=list)


class DocumentIngestion:
    """Persists extracted document content into the database."""

    STORAGE_BACKEND = "local"

    # ---------------------------------------------------------
    # General helpers
    # ---------------------------------------------------------

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert values into structures supported by PostgreSQL JSONB."""

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Path):
            return value.name

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, dict):
            return {
                str(key): DocumentIngestion._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                DocumentIngestion._json_safe(item)
                for item in value
            ]

        if hasattr(value, "item"):
            try:
                return DocumentIngestion._json_safe(value.item())
            except (ValueError, TypeError):
                pass

        return str(value)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Return a safe filename suitable for a storage key."""

        name = Path(filename).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        name = name.strip("._")

        return name or "extracted_image"

    @staticmethod
    def _calculate_sha256(path: Path) -> str:
        """Calculate a file checksum without loading it entirely."""

        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _get_existing_document(
        db: Session,
        file_id: UUID,
    ) -> Optional[Document]:
        """Find the document already associated with a file."""

        statement = select(Document).where(
            Document.file_id == file_id
        )

        return db.scalars(statement).first()

    @staticmethod
    def _combine_text(
        extracted_content: list[dict[str, Any]],
        content_type: str,
    ) -> str:
        """Combine text extracted from pages or slides."""

        parts = []

        for item in extracted_content:
            text = item.get("text", "")
            notes = item.get("notes", "")

            if text:
                parts.append(str(text))

            if content_type == "pptx" and notes:
                parts.append(str(notes))

        return "\n\n".join(parts)

    @staticmethod
    def _extract_metadata(
        processor_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize metadata returned by the document processors."""

        metadata = dict(processor_result.get("metadata") or {})

        metadata["source"] = processor_result.get("source")
        metadata["investigation_id"] = processor_result.get(
            "investigation_id"
        )
        metadata["file_type"] = processor_result.get(
            "file_type",
            metadata.get("file_type"),
        )

        return DocumentIngestion._json_safe(metadata)

    # ---------------------------------------------------------
    # Extracted image ingestion
    # ---------------------------------------------------------

    @staticmethod
    def _inspect_image(path: Path) -> dict[str, Any]:
        """Extract basic image metadata using Pillow."""

        with Image.open(path) as image:
            width, height = image.size

            return {
                "image_format": image.format,
                "mime_type": Image.MIME.get(image.format),
                "width": width,
                "height": height,
                "aspect_ratio": (
                    round(width / height, 6) if height else None
                ),
                "pixel_count": width * height,
                "color_mode": image.mode,
                "has_transparency": (
                    "A" in image.getbands()
                    or "transparency" in image.info
                ),
                "frame_count": getattr(image, "n_frames", 1),
            }

    @staticmethod
    def _register_extracted_image(
        db: Session,
        original_file: File,
        image_data: dict[str, Any],
        unit: Optional[DocumentUnit],
        content_type: str,
        storage: StorageBackend,
    ) -> tuple[Optional[ImageAsset], bool]:
        """
        Store an extracted image and register its File and ImageAsset.

        The original document remains the parent file. The resulting
        ImageContext links the image to its source page or slide.
        """

        source_path_value = image_data.get("path")

        if not source_path_value:
            raise ValueError(
                "Extracted image is missing its source path."
            )

        source_path = Path(source_path_value)

        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError(
                f"Extracted image does not exist: {source_path}"
            )

        if source_path.is_symlink():
            raise ValueError(
                f"Extracted image cannot be a symbolic link: {source_path}"
            )

        checksum = DocumentIngestion._calculate_sha256(source_path)
        filename = DocumentIngestion._safe_filename(source_path.name)
        file_size = source_path.stat().st_size

        storage_key = (
            f"investigations/{original_file.investigation_id}/"
            f"derived/extracted_images/"
            f"{checksum[:16]}_{filename}"
        )

        # Look for a previously registered copy of this extracted image.
        existing_file = db.scalar(
            select(File).where(
                File.parent_file_id == original_file.file_id,
                File.storage_key == storage_key,
            )
        )

        # Ensure the binary is available in managed storage.
        if not storage.exists(storage_key):
            storage.store_file(
                source_path=source_path,
                object_key=storage_key,
            )

        if existing_file is not None:
            image_file = existing_file

            image_file.filename = filename
            image_file.extension = source_path.suffix.lower()
            image_file.detected_format = (
                source_path.suffix.lower().lstrip(".")
            )
            image_file.file_category = "image"
            image_file.file_role = "derived"
            image_file.file_size_bytes = file_size
            image_file.sha256 = checksum
            image_file.storage_backend = (
                DocumentIngestion.STORAGE_BACKEND
            )
            image_file.storage_key = storage_key
            image_file.storage_path = None
            image_file.processing_status = "processed"

            db.flush()

            was_created = False

        else:
            image_file = FileRepository.create(
                db=db,
                investigation_id=original_file.investigation_id,
                filename=filename,
                file_category="image",
                storage_path=None,
                storage_key=storage_key,
                storage_backend=DocumentIngestion.STORAGE_BACKEND,
                file_size_bytes=file_size,
                extension=source_path.suffix.lower(),
                detected_format=source_path.suffix.lower().lstrip("."),
                file_role="derived",
                parent_file_id=original_file.file_id,
                sha256=checksum,
                processing_status="processed",
            )

            was_created = True

        # Extract metadata for the ImageAsset record.
        try:
            image_metadata = DocumentIngestion._inspect_image(
                source_path
            )
        except (UnidentifiedImageError, OSError) as error:
            image_metadata = {
                "image_format": image_data.get("format"),
                "mime_type": None,
                "width": None,
                "height": None,
                "aspect_ratio": None,
                "pixel_count": None,
                "color_mode": None,
                "has_transparency": False,
                "frame_count": 1,
            }

        image_asset = db.scalar(
            select(ImageAsset).where(
                ImageAsset.file_id == image_file.file_id
            )
        )

        if image_asset is None:
            image_asset = ImageAsset(
                file_id=image_file.file_id,
                **image_metadata,
                exif_metadata={},
                warnings=[],
                processed_at=datetime.now(timezone.utc),
            )
            db.add(image_asset)
            db.flush()

        else:
            for field_name, value in image_metadata.items():
                setattr(image_asset, field_name, value)

            image_asset.processed_at = datetime.now(timezone.utc)

        # Link the extracted image to its source page or slide.
        context_type = (
            "document_page" if content_type == "pdf"
            else "document_slide"
        )

        context_label = (
            f"Page {unit.unit_number}" if content_type == "pdf"
            else f"Slide {unit.unit_number}"
        ) if unit else "Extracted document image"

        context_statement = select(ImageContext).where(
            ImageContext.image_id == image_asset.image_id,
            ImageContext.document_unit_id == (
                unit.unit_id if unit else None
            ),
            ImageContext.context_type == context_type,
        )

        context = db.scalar(context_statement)

        if context is None:
            context = ImageContext(
                image_id=image_asset.image_id,
                document_unit_id=unit.unit_id if unit else None,
                context_type=context_type,
                context_label=context_label,
                metadata_json={
                    "source_document_file_id": str(
                        original_file.file_id
                    ),
                    "source_image_id": image_data.get("image_id"),
                    "source_format": content_type,
                },
            )
            db.add(context)

        return image_asset, was_created

    @staticmethod
    def _register_extracted_images(
        db: Session,
        original_file: File,
        extracted_content: list[dict[str, Any]],
        units_by_number: dict[int, DocumentUnit],
        content_type: str,
        result: DocumentIngestionResult,
        storage: StorageBackend,
    ) -> None:
        """Register images extracted from PDF pages or PPTX slides."""

        for index, item in enumerate(extracted_content, start=1):
            unit_number = item.get(
                "page" if content_type == "pdf" else "slide",
                index,
            )

            unit = units_by_number.get(unit_number)
            registered_images = []

            for image_data in item.get("images", []):
                try:
                    image_asset, was_created = (
                        DocumentIngestion._register_extracted_image(
                            db=db,
                            original_file=original_file,
                            image_data=image_data,
                            unit=unit,
                            content_type=content_type,
                            storage=storage,
                        )
                    )

                    if image_asset is None:
                        continue

                    registered_images.append({
                        "image_id": str(image_asset.image_id),
                        "file_id": str(image_asset.file_id),
                        "storage_key": image_asset.file.storage_key
                        if image_asset.file
                        else None,
                        "source_image_id": image_data.get("image_id"),
                    })

                    result.images_created += 1

                    if was_created:
                        result.registered_files += 1

                except (OSError, ValueError, RuntimeError) as error:
                    result.warnings.append(
                        f"Could not register an extracted image from "
                        f"{content_type} unit {unit_number}: {error}"
                    )

            # Replace temporary processor paths with database references.
            if unit is not None:
                metadata = dict(unit.metadata_json or {})
                metadata["images"] = registered_images
                unit.metadata_json = DocumentIngestion._json_safe(
                    metadata
                )

            db.flush()

    # ---------------------------------------------------------
    # Document references
    # ---------------------------------------------------------

    @staticmethod
    def _extract_references(
        document: Document,
        references: dict[str, Any],
        result: DocumentIngestionResult,
    ) -> None:
        """Persist DOI references extracted by the processors."""

        dois = references.get("dois", [])

        for doi in sorted(set(dois)):
            if not doi:
                continue

            reference = DocumentReference(
                document_id=document.document_id,
                doi=str(doi),
                authors=[],
                metadata_json={},
            )

            result.references_created += 1
            document.references.append(reference)

    # ---------------------------------------------------------
    # PSI sections
    # ---------------------------------------------------------

    @staticmethod
    def _create_psi_sections(
        document: Document,
        sections: list[dict[str, Any]],
        result: DocumentIngestionResult,
    ) -> None:
        """Persist PSI sections and their structured fields."""

        for section_number, section in enumerate(sections, start=1):
            unit = DocumentUnit(
                document_id=document.document_id,
                unit_type="section",
                unit_number=section_number,
                title=section.get("name"),
                extracted_text=None,
                metadata_json={
                    "source": "document_loader",
                    "section_name": section.get("name"),
                },
            )

            document.units.append(unit)
            result.units_created += 1

            for field_data in section.get("fields", []):
                field_name = field_data.get("name")

                if not field_name:
                    continue

                values = field_data.get("values", [])

                psi_field = PSIField(
                    document_id=document.document_id,
                    name=field_name,
                    value=DocumentIngestion._json_safe(values),
                    field_type="list",
                    source_text="\t".join(
                        [field_name] + [str(value) for value in values]
                    ),
                    metadata_json={
                        "source": "PSI investigation metadata",
                    },
                )

                unit.psi_fields.append(psi_field)
                result.psi_fields_created += 1

    # ---------------------------------------------------------
    # Pages and slides
    # ---------------------------------------------------------

    @staticmethod
    def _create_units(
        document: Document,
        extracted_content: list[dict[str, Any]],
        content_type: str,
        result: DocumentIngestionResult,
    ) -> dict[int, DocumentUnit]:
        """Persist PDF pages or PPTX slides."""

        units_by_number = {}

        for index, item in enumerate(extracted_content, start=1):
            unit_number = item.get(
                "page" if content_type == "pdf" else "slide",
                index,
            )

            unit_type = "page" if content_type == "pdf" else "slide"
            unit_text = item.get("text", "")

            metadata = {}

            if content_type == "pdf":
                metadata["extraction_method"] = item.get(
                    "extraction_method"
                )

            elif content_type == "pptx":
                metadata["notes"] = item.get("notes", "")

            # Image paths are deliberately not copied into database metadata.
            # They are replaced with managed storage references after
            # extracted images have been registered.
            metadata["images"] = []

            unit = DocumentUnit(
                document_id=document.document_id,
                unit_type=unit_type,
                unit_number=unit_number,
                extracted_text=unit_text or None,
                metadata_json=DocumentIngestion._json_safe(metadata),
            )

            document.units.append(unit)

            units_by_number[unit_number] = unit
            result.units_created += 1

        return units_by_number

    # ---------------------------------------------------------
    # Extracted tables
    # ---------------------------------------------------------

    @staticmethod
    def _create_tables(
        document: Document,
        extracted_content: list[dict[str, Any]],
        units_by_number: dict[int, DocumentUnit],
        content_type: str,
        result: DocumentIngestionResult,
    ) -> None:
        """Persist tables extracted from PDF pages or PPTX slides."""

        table_number = 0

        for index, item in enumerate(extracted_content, start=1):
            unit_number = item.get(
                "page" if content_type == "pdf" else "slide",
                index,
            )

            unit = units_by_number.get(unit_number)

            for extracted_table in item.get("tables", []):
                rows = extracted_table.get("rows", [])

                if not rows:
                    continue

                table_number += 1

                table = ExtractedTable(
                    document_id=document.document_id,
                    table_number=table_number,
                    headers=[],
                    rows=DocumentIngestion._json_safe(rows),
                    metadata_json={
                        "source_table_id": extracted_table.get("table_id"),
                        "source_page_or_slide": unit_number,
                        "content_type": content_type,
                    },
                )

                if unit is not None:
                    unit.extracted_tables.append(table)
                else:
                    document.extracted_tables.append(table)

                result.tables_created += 1

    # ---------------------------------------------------------
    # Extracted charts
    # ---------------------------------------------------------

    @staticmethod
    def _create_charts(
        document: Document,
        extracted_content: list[dict[str, Any]],
        units_by_number: dict[int, DocumentUnit],
        result: DocumentIngestionResult,
    ) -> None:
        """Persist PPTX charts and their individual data series."""

        for index, item in enumerate(extracted_content, start=1):
            slide_number = item.get("slide", index)
            unit = units_by_number.get(slide_number)

            for extracted_chart in item.get("charts", []):
                chart = ExtractedChart(
                    document_id=document.document_id,
                    title=extracted_chart.get("title"),
                    chart_type=extracted_chart.get("chart_type"),
                    metadata_json={
                        "source_chart_id": extracted_chart.get("chart_id"),
                        "source_slide": slide_number,
                        "categories": DocumentIngestion._json_safe(
                            extracted_chart.get("categories", [])
                        ),
                    },
                )

                if unit is not None:
                    unit.extracted_charts.append(chart)
                else:
                    document.extracted_charts.append(chart)

                result.charts_created += 1

                categories = extracted_chart.get("categories", [])

                for extracted_series in extracted_chart.get("series", []):
                    values = extracted_series.get("values", [])

                    series = ChartSeries(
                        name=extracted_series.get("name"),
                        x_values=DocumentIngestion._json_safe(categories),
                        y_values=DocumentIngestion._json_safe(values),
                        metadata_json={},
                    )

                    chart.series.append(series)
                    result.chart_series_created += 1

    # ---------------------------------------------------------
    # Re-ingestion cleanup
    # ---------------------------------------------------------

    @staticmethod
    def _clear_existing_extraction(document: Document) -> None:
        """Remove old extracted children before re-ingestion."""

        document.units.clear()
        document.psi_fields.clear()
        document.references.clear()
        document.extracted_tables.clear()
        document.extracted_charts.clear()

    # ---------------------------------------------------------
    # Main ingestion method
    # ---------------------------------------------------------

    @staticmethod
    def ingest_document(
        db: Session,
        file_id: UUID,
        processor_result: dict[str, Any],
        storage: StorageBackend | None = None,
    ) -> DocumentIngestionResult:
        """
        Persist the output of a TXT, PDF, or PPTX processor.

        Supported processor outputs:
            - load_text_document()
            - process_pdf()
            - process_pptx()

        Extracted PDF/PPTX images are registered as derived files and
        linked to their source document page or slide.

        The caller controls the transaction and must commit or roll back.
        """

        storage = storage or LocalStorage()

        file_record = db.get(File, file_id)

        if file_record is None:
            raise ValueError(
                f"File does not exist in the database: {file_id}"
            )

        if not isinstance(processor_result, dict):
            raise TypeError("processor_result must be a dictionary.")

        content_type = str(
            processor_result.get("file_type", "")
        ).lower().lstrip(".")

        if content_type not in {"txt", "pdf", "pptx"}:
            raise ValueError(
                f"Unsupported document type: {content_type}"
            )

        metadata = DocumentIngestion._extract_metadata(
            processor_result
        )

        existing_document = DocumentIngestion._get_existing_document(
            db,
            file_id,
        )

        if existing_document is None:
            document = Document(
                file_id=file_id,
                metadata_json=metadata,
            )
            db.add(document)
            db.flush()

        else:
            document = existing_document
            DocumentIngestion._clear_existing_extraction(document)
            document.metadata_json = metadata

        document.title = metadata.get("title")
        document.author = metadata.get("author")
        document.principal_investigator = metadata.get(
            "principal_investigator"
        )

        warnings = list(processor_result.get("warnings") or [])

        result = DocumentIngestionResult(
            document=document,
            warnings=[str(warning) for warning in warnings],
        )

        if content_type == "txt":
            document.extracted_text = processor_result.get("text")
            document.extraction_method = "text"

            sections = processor_result.get("sections", [])

            if sections:
                DocumentIngestion._create_psi_sections(
                    document,
                    sections,
                    result,
                )

        else:
            extracted_content = processor_result.get(
                "extracted_content",
                [],
            )

            if not isinstance(extracted_content, list):
                raise ValueError(
                    "extracted_content must be a list."
                )

            document.extracted_text = (
                DocumentIngestion._combine_text(
                    extracted_content,
                    content_type,
                )
            )

            if content_type == "pdf":
                methods = {
                    item.get("extraction_method")
                    for item in extracted_content
                    if item.get("extraction_method")
                }

                if len(methods) == 1:
                    document.extraction_method = next(iter(methods))
                elif methods:
                    document.extraction_method = "mixed"
                else:
                    document.extraction_method = None

            else:
                document.extraction_method = "text"

            units_by_number = DocumentIngestion._create_units(
                document,
                extracted_content,
                content_type,
                result,
            )

            # Flush to ensure DocumentUnit IDs are available for ImageContext.
            db.flush()

            DocumentIngestion._register_extracted_images(
                db=db,
                original_file=file_record,
                extracted_content=extracted_content,
                units_by_number=units_by_number,
                content_type=content_type,
                result=result,
                storage=storage,
            )

            DocumentIngestion._create_tables(
                document,
                extracted_content,
                units_by_number,
                content_type,
                result,
            )

            if content_type == "pptx":
                DocumentIngestion._create_charts(
                    document,
                    extracted_content,
                    units_by_number,
                    result,
                )

        DocumentIngestion._extract_references(
            document,
            processor_result.get("references") or {},
            result,
        )

        # Update the source file's processing status.
        processor_status = processor_result.get(
            "processing_status",
            "success",
        )

        if processor_status == "success":
            FileRepository.update_status(
                db,
                file_id,
                "processed",
            )

        elif processor_status == "warning":
            FileRepository.update_status(
                db,
                file_id,
                "warning",
            )

        elif processor_status in {"failed", "error"}:
            FileRepository.update_status(
                db,
                file_id,
                "failed",
            )

        else:
            FileRepository.update_status(
                db,
                file_id,
                "warning",
            )

            result.warnings.append(
                f"Unrecognized processor status: {processor_status}"
            )

        if result.warnings and file_record.processing_status == "processed":
            FileRepository.update_status(
                db,
                file_id,
                "warning",
            )

        db.flush()

        return result