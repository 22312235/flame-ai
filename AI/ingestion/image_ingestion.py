from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.file import File
from models.image import ImageAsset, ImageContext

from database.repositories.file_repository import FileRepository
from storage import LocalStorage, StorageBackend


@dataclass
class ImageIngestionResult:
    """Summary of an image ingestion operation."""

    image: ImageAsset

    thumbnail_file: File | None = None
    context: ImageContext | None = None

    registered_files: int = 0
    warnings: list[str] = field(default_factory=list)


class ImageIngestion:
    """
    Persists image processor output in the database.

    Original images remain registered as original files.
    Generated thumbnails are copied into managed storage and
    registered as derived files.

    This adapter does not commit transactions.
    """

    STORAGE_BACKEND = "local"

    # ---------------------------------------------------------
    # General helpers
    # ---------------------------------------------------------

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert values into JSON-compatible structures."""

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, Path):
            return value.name

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(key): ImageIngestion._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                ImageIngestion._json_safe(item)
                for item in value
            ]

        if hasattr(value, "item"):
            try:
                return value.item()
            except (ValueError, TypeError):
                pass

        return str(value)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Produce a safe filename for a storage key."""

        name = Path(filename).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        name = name.strip("._")

        return name or "artifact"

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
    def _parse_datetime(value: Any) -> datetime | None:
        """Convert an ISO-formatted timestamp into a datetime."""

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        return None

    # ---------------------------------------------------------
    # Image lookup
    # ---------------------------------------------------------

    @staticmethod
    def _get_existing_image(
        db: Session,
        file_id: UUID,
    ) -> ImageAsset | None:
        """Retrieve the image record associated with an original file."""

        return db.scalar(
            select(ImageAsset).where(
                ImageAsset.file_id == file_id
            )
        )

    # ---------------------------------------------------------
    # Thumbnail registration
    # ---------------------------------------------------------

    @staticmethod
    def _register_thumbnail(
        db: Session,
        original_file: File,
        thumbnail_path: str | Path | None,
        storage: StorageBackend,
    ) -> tuple[File | None, bool]:
        """
        Store a generated thumbnail and register it as a derived file.

        Returns:
            (registered_file, was_created)
        """

        if not thumbnail_path:
            return None, False

        path = Path(thumbnail_path)

        if not path.exists() or not path.is_file():
            return None, False

        if path.is_symlink():
            return None, False

        checksum = ImageIngestion._calculate_sha256(path)
        file_size = path.stat().st_size
        filename = ImageIngestion._safe_filename(path.name)

        storage_key = (
            f"investigations/{original_file.investigation_id}/"
            f"derived/thumbnail/"
            f"{checksum[:16]}_{filename}"
        )

        existing_file = db.scalar(
            select(File).where(
                File.parent_file_id == original_file.file_id,
                File.storage_key == storage_key,
            )
        )

        # Ensure the thumbnail exists in managed storage.
        if not storage.exists(storage_key):
            storage.store_file(
                source_path=path,
                object_key=storage_key,
            )

        if existing_file:
            existing_file.filename = filename
            existing_file.extension = path.suffix.lower()
            existing_file.detected_format = (
                path.suffix.lower().lstrip(".")
            )
            existing_file.file_category = "image"
            existing_file.file_role = "derived"
            existing_file.file_size_bytes = file_size
            existing_file.sha256 = checksum
            existing_file.storage_backend = (
                ImageIngestion.STORAGE_BACKEND
            )
            existing_file.storage_key = storage_key
            existing_file.storage_path = None
            existing_file.processing_status = "processed"

            db.flush()

            return existing_file, False

        registered_file = FileRepository.create(
            db=db,
            investigation_id=original_file.investigation_id,
            filename=filename,
            file_category="image",
            storage_path=None,
            storage_key=storage_key,
            storage_backend=ImageIngestion.STORAGE_BACKEND,
            file_size_bytes=file_size,
            extension=path.suffix.lower(),
            detected_format=path.suffix.lower().lstrip("."),
            file_role="derived",
            parent_file_id=original_file.file_id,
            sha256=checksum,
            processing_status="processed",
        )

        return registered_file, True

    # ---------------------------------------------------------
    # Image context
    # ---------------------------------------------------------

    @staticmethod
    def _save_context(
        db: Session,
        image: ImageAsset,
        document_unit_id: UUID | None,
        context_type: str,
        context_label: str | None,
        context_metadata: dict[str, Any] | None,
    ) -> ImageContext:
        """Create or update the context associated with an image."""

        existing_context = db.scalar(
            select(ImageContext).where(
                ImageContext.image_id == image.image_id,
                ImageContext.document_unit_id == document_unit_id,
                ImageContext.context_type == context_type,
            )
        )

        metadata = ImageIngestion._json_safe(
            context_metadata or {}
        )

        if existing_context:
            existing_context.context_label = context_label
            existing_context.metadata_json = metadata

            db.flush()

            return existing_context

        context = ImageContext(
            image_id=image.image_id,
            document_unit_id=document_unit_id,
            context_type=context_type,
            context_label=context_label,
            metadata_json=metadata,
        )

        db.add(context)
        db.flush()

        return context

    # ---------------------------------------------------------
    # Main ingestion method
    # ---------------------------------------------------------

    @staticmethod
    def ingest_image(
        db: Session,
        file_id: UUID,
        processor_result: dict[str, Any],
        document_unit_id: UUID | None = None,
        context_type: str = "standalone",
        context_label: str | None = None,
        context_metadata: dict[str, Any] | None = None,
        storage: StorageBackend | None = None,
    ) -> ImageIngestionResult:
        """
        Persist the output returned by processing.image_processor.

        Expected processor output is the dictionary returned by
        ImageProfile.to_dict().

        The method does not commit. The caller controls the
        transaction and must roll back if ingestion fails.
        """

        storage = storage or LocalStorage()

        original_file = FileRepository.get_by_id(
            db,
            file_id,
        )

        if original_file is None:
            raise ValueError(
                f"Original file does not exist: {file_id}"
            )

        if not isinstance(processor_result, dict):
            raise TypeError(
                "Image processor result must be a dictionary."
            )

        processing_status = processor_result.get(
            "processing_status"
        )

        if processing_status != "completed":
            raise ValueError(
                "Image processor did not complete successfully. "
                f"Status: {processing_status!r}"
            )

        required_fields = {
            "image_format",
            "mime_type",
            "width",
            "height",
            "aspect_ratio",
            "pixel_count",
            "color_mode",
            "has_transparency",
            "frame_count",
        }

        missing_fields = required_fields.difference(
            processor_result.keys()
        )

        if missing_fields:
            raise ValueError(
                "Image processor result is missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

        warnings_list = list(
            processor_result.get("warnings") or []
        )

        # -----------------------------------------------------
        # 1. Register the generated thumbnail
        # -----------------------------------------------------

        thumbnail_file, thumbnail_created = (
            ImageIngestion._register_thumbnail(
                db=db,
                original_file=original_file,
                thumbnail_path=processor_result.get(
                    "thumbnail_path"
                ),
                storage=storage,
            )
        )

        if (
            processor_result.get("thumbnail_path")
            and thumbnail_file is None
        ):
            warnings_list.append(
                "Thumbnail was generated but could not be registered."
            )

        # -----------------------------------------------------
        # 2. Create or update the image record
        # -----------------------------------------------------

        image = ImageIngestion._get_existing_image(
            db,
            file_id,
        )

        image_data = {
            "image_format": processor_result.get("image_format"),
            "mime_type": processor_result.get("mime_type"),
            "width": processor_result.get("width"),
            "height": processor_result.get("height"),
            "aspect_ratio": processor_result.get("aspect_ratio"),
            "pixel_count": processor_result.get("pixel_count"),
            "color_mode": processor_result.get("color_mode"),
            "has_transparency": processor_result.get(
                "has_transparency",
                False,
            ),
            "frame_count": processor_result.get("frame_count", 1),
            "exif_metadata": ImageIngestion._json_safe(
                processor_result.get("exif_metadata") or {}
            ),
            "thumbnail_file_id": (
                thumbnail_file.file_id
                if thumbnail_file else None
            ),
            "warnings": ImageIngestion._json_safe(
                warnings_list
            ),
            "processed_at": ImageIngestion._parse_datetime(
                processor_result.get("processed_at")
            ),
        }

        if image:
            for key, value in image_data.items():
                setattr(image, key, value)

            db.flush()

        else:
            image = ImageAsset(
                file_id=original_file.file_id,
                **image_data,
            )

            db.add(image)
            db.flush()

        # -----------------------------------------------------
        # 3. Create or update image context
        # -----------------------------------------------------

        context = ImageIngestion._save_context(
            db=db,
            image=image,
            document_unit_id=document_unit_id,
            context_type=context_type,
            context_label=context_label,
            context_metadata=context_metadata,
        )

        # -----------------------------------------------------
        # 4. Update original file status
        # -----------------------------------------------------

        FileRepository.update_status(
            db,
            file_id,
            "warning" if warnings_list else "processed",
        )

        db.flush()

        return ImageIngestionResult(
            image=image,
            thumbnail_file=thumbnail_file,
            context=context,
            registered_files=(
                1 if thumbnail_created else 0
            ),
            warnings=warnings_list,
        )