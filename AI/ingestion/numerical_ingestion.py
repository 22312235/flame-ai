from __future__ import annotations

import hashlib
import re

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.file import File
from models.numerical import (
    Dataset,
    Variable,
    DatasetVariable,
    build_variable_key,
)

from database.repositories.file_repository import FileRepository
from storage import LocalStorage, StorageBackend


@dataclass
class NumericalIngestionResult:
    datasets_created: int = 0
    datasets_updated: int = 0
    variables_linked: int = 0
    registered_files: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_datasets(self) -> int:
        return self.datasets_created + self.datasets_updated


class NumericalIngestion:
    """
    Persist tabular processor profiles in the numerical database tables.

    Generated Parquet and profile JSON files are copied into managed
    storage. Their relative storage keys are persisted in Dataset.

    This adapter does not commit database transactions.
    """

    STORAGE_BACKEND = "local"

    # ---------------------------------------------------------
    # General helpers
    # ---------------------------------------------------------

    @staticmethod
    def _to_dict(value: Any) -> dict:
        if is_dataclass(value):
            return asdict(value)

        if isinstance(value, dict):
            return value

        raise TypeError(
            f"Expected a dataclass or dictionary, got {type(value).__name__}."
        )

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert nested processor values into JSON-compatible values."""

        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, Path):
            # Avoid persisting absolute local filesystem paths.
            return value.name

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, dict):
            return {
                str(key): NumericalIngestion._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                NumericalIngestion._json_safe(item)
                for item in value
            ]

        if hasattr(value, "item"):
            try:
                value = value.item()
            except (ValueError, TypeError):
                pass

        if isinstance(value, (str, int, float, bool)):
            return value

        return str(value)

    @staticmethod
    def _parse_datetime(
        value: Optional[str],
    ) -> Optional[datetime]:
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid processor timestamp: {value}"
            ) from error

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

    # ---------------------------------------------------------
    # Artifact storage
    # ---------------------------------------------------------

    @staticmethod
    def _store_artifact(
        db: Session,
        original_file: File,
        artifact_path: str | Path | None,
        artifact_type: str,
        file_category: str,
        storage: StorageBackend,
    ) -> tuple[str | None, bool]:
        """
        Copy a generated artifact into managed storage.

        Register it as a derived File associated with the original
        uploaded file.

        Returns:
            (storage_key, was_created)

        A missing artifact returns (None, False).
        """

        if not artifact_path:
            return None, False

        path = Path(artifact_path)

        if not path.exists() or not path.is_file():
            return None, False

        if path.is_symlink():
            raise ValueError(
                f"Generated artifact cannot be a symbolic link: {path}"
            )

        checksum = NumericalIngestion._calculate_sha256(path)
        file_size = path.stat().st_size
        filename = NumericalIngestion._safe_filename(path.name)

        storage_key = (
            f"investigations/{original_file.investigation_id}/"
            f"derived/{artifact_type}/"
            f"{checksum[:16]}_{filename}"
        )

        existing_file = db.scalar(
            select(File).where(
                File.parent_file_id == original_file.file_id,
                File.storage_key == storage_key,
            )
        )

        # Ensure the binary exists in managed storage.
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
            existing_file.file_category = file_category
            existing_file.file_role = "derived"
            existing_file.file_size_bytes = file_size
            existing_file.sha256 = checksum
            existing_file.storage_backend = (
                NumericalIngestion.STORAGE_BACKEND
            )
            existing_file.storage_key = storage_key
            existing_file.storage_path = None
            existing_file.processing_status = "processed"

            db.flush()

            return storage_key, False

        FileRepository.create(
            db=db,
            investigation_id=original_file.investigation_id,
            filename=filename,
            file_category=file_category,
            storage_path=None,
            storage_key=storage_key,
            storage_backend=NumericalIngestion.STORAGE_BACKEND,
            file_size_bytes=file_size,
            extension=path.suffix.lower(),
            detected_format=path.suffix.lower().lstrip("."),
            file_role="derived",
            parent_file_id=original_file.file_id,
            sha256=checksum,
            processing_status="processed",
        )

        return storage_key, True

    # ---------------------------------------------------------
    # Dataset lookup
    # ---------------------------------------------------------

    @staticmethod
    def _get_dataset(
        db: Session,
        file_id: UUID,
        processor_dataset_id: str,
    ) -> Optional[Dataset]:
        return db.scalar(
            select(Dataset).where(
                Dataset.file_id == file_id,
                Dataset.processor_dataset_id == processor_dataset_id,
            )
        )

    # ---------------------------------------------------------
    # Variable management
    # ---------------------------------------------------------

    @staticmethod
    def _get_or_create_variable(
        db: Session,
        name: str,
        inferred_type: str,
        unit: Optional[str],
    ) -> Variable:
        variable_key = build_variable_key(
            name=name,
            inferred_type=inferred_type,
            unit=unit,
        )

        variable = db.scalar(
            select(Variable).where(
                Variable.variable_key == variable_key
            )
        )

        if variable is not None:
            return variable

        variable = Variable(
            variable_key=variable_key,
            name=name,
            inferred_type=inferred_type,
            unit=unit,
        )

        db.add(variable)
        db.flush()

        return variable

    @staticmethod
    def _create_dataset_variable(
        db: Session,
        dataset: Dataset,
        column: dict,
        position: int,
    ) -> DatasetVariable:
        required_fields = (
            "name",
            "original_name",
            "inferred_type",
            "non_null_count",
            "missing_count",
            "missing_percentage",
            "unique_count",
        )

        missing_fields = [
            name for name in required_fields if name not in column
        ]

        if missing_fields:
            raise ValueError(
                "Column profile is missing required fields: "
                + ", ".join(missing_fields)
            )

        name = str(column["name"])
        inferred_type = str(column["inferred_type"])
        unit = column.get("unit")

        variable = NumericalIngestion._get_or_create_variable(
            db=db,
            name=name,
            inferred_type=inferred_type,
            unit=unit,
        )

        association = DatasetVariable(
            dataset=dataset,
            variable=variable,
            original_name=str(column["original_name"]),
            column_position=position,
            non_null_count=int(column["non_null_count"]),
            missing_count=int(column["missing_count"]),
            missing_percentage=float(column["missing_percentage"]),
            unique_count=int(column["unique_count"]),
            sample_values=NumericalIngestion._json_safe(
                column.get("sample_values", [])
            ),
            statistics=NumericalIngestion._json_safe(
                column.get("statistics", {})
            ),
        )

        db.add(association)
        return association

    # ---------------------------------------------------------
    # File status
    # ---------------------------------------------------------

    @staticmethod
    def _update_file_status(
        file: File,
        profiles: list[dict],
    ) -> None:
        statuses = {
            str(profile.get("status", "")).lower()
            for profile in profiles
        }

        if not statuses:
            file.processing_status = "warning"
        elif statuses.intersection({"failed", "error"}):
            file.processing_status = "failed"
        elif statuses.intersection({"warning", "partial"}):
            file.processing_status = "warning"
        elif statuses.issubset({"completed", "success"}):
            file.processing_status = "processed"
        else:
            file.processing_status = "warning"

    # ---------------------------------------------------------
    # Main ingestion method
    # ---------------------------------------------------------

    @classmethod
    def ingest_profiles(
        cls,
        db: Session,
        file_id: UUID,
        profiles: list[Any],
        storage: StorageBackend | None = None,
    ) -> NumericalIngestionResult:
        """
        Persist DatasetProfile objects returned by process_tabular_file().

        Generated Parquet and profile JSON artifacts are copied into
        managed storage. Dataset.parquet_path and Dataset.profile_path
        contain their relative storage keys.

        The caller controls the transaction and must commit or roll back.
        """

        storage = storage or LocalStorage()

        file = db.get(File, file_id)

        if file is None:
            raise ValueError(f"File not found: {file_id}")

        if file.file_category != "numerical_dataset":
            raise ValueError(
                f"File {file_id} is not registered as a numerical dataset."
            )

        if not isinstance(profiles, list):
            raise TypeError("profiles must be a list.")

        result = NumericalIngestionResult()
        normalized_profiles: list[dict] = []
        seen_dataset_ids: set[str] = set()

        # Validate the profile collection before modifying database records.
        for profile in profiles:
            data = cls._to_dict(profile)

            processor_dataset_id = data.get("dataset_id")

            if not processor_dataset_id:
                raise ValueError(
                    "A dataset profile is missing its dataset_id."
                )

            processor_dataset_id = str(processor_dataset_id)

            if processor_dataset_id in seen_dataset_ids:
                raise ValueError(
                    f"Duplicate dataset_id in processor output: "
                    f"{processor_dataset_id}"
                )

            seen_dataset_ids.add(processor_dataset_id)

            if not isinstance(data.get("columns"), list):
                raise ValueError(
                    f"Dataset {processor_dataset_id} has no valid columns list."
                )

            normalized_profiles.append(data)

        # Ingest each CSV dataset or Excel worksheet.
        for data in normalized_profiles:
            processor_dataset_id = str(data["dataset_id"])

            required_fields = (
                "source_file",
                "source_format",
                "row_count",
                "column_count",
                "status",
            )

            missing_fields = [
                name for name in required_fields if name not in data
            ]

            if missing_fields:
                raise ValueError(
                    f"Dataset {processor_dataset_id} is missing fields: "
                    + ", ".join(missing_fields)
                )

            dataset = cls._get_dataset(
                db=db,
                file_id=file_id,
                processor_dataset_id=processor_dataset_id,
            )

            is_new = dataset is None

            if is_new:
                dataset = Dataset(
                    file_id=file_id,
                    processor_dataset_id=processor_dataset_id,
                    source_file=str(data["source_file"]),
                    source_format=str(data["source_format"]),
                    row_count=int(data["row_count"]),
                    column_count=int(data["column_count"]),
                    status=str(data["status"]),
                )

                db.add(dataset)
                db.flush()

                result.datasets_created += 1

            else:
                result.datasets_updated += 1

                # Remove old column associations before rebuilding them.
                dataset.dataset_variables.clear()
                db.flush()

            dataset.source_file = str(data["source_file"])
            dataset.source_format = str(data["source_format"])
            dataset.sheet_name = data.get("sheet_name")

            dataset.row_count = int(data["row_count"])
            dataset.column_count = int(data["column_count"])

            dataset.duplicate_rows = int(
                data.get("duplicate_rows", 0)
            )
            dataset.duplicate_rows_removed = int(
                data.get("duplicate_rows_removed", 0)
            )
            dataset.empty_rows_removed = int(
                data.get("empty_rows_removed", 0)
            )
            dataset.empty_columns_removed = int(
                data.get("empty_columns_removed", 0)
            )

            # -------------------------------------------------
            # Store generated artifacts
            # -------------------------------------------------

            parquet_key, parquet_created = cls._store_artifact(
                db=db,
                original_file=file,
                artifact_path=data.get("parquet_path"),
                artifact_type="numerical",
                file_category="numerical_dataset",
                storage=storage,
            )

            profile_key, profile_created = cls._store_artifact(
                db=db,
                original_file=file,
                artifact_path=data.get("profile_path"),
                artifact_type="profiles",
                file_category="metadata",
                storage=storage,
            )

            dataset.parquet_path = parquet_key
            dataset.profile_path = profile_key

            if parquet_created:
                result.registered_files += 1

            if profile_created:
                result.registered_files += 1

            # Report missing artifacts without persisting their local paths.
            if data.get("parquet_path") and parquet_key is None:
                result.warnings.append(
                    f"Parquet artifact could not be stored for dataset "
                    f"{processor_dataset_id}."
                )

            if data.get("profile_path") and profile_key is None:
                result.warnings.append(
                    f"Profile artifact could not be stored for dataset "
                    f"{processor_dataset_id}."
                )

            dataset.status = str(data["status"])

            dataset.warnings = cls._json_safe(
                data.get("warnings", [])
            )

            dataset.processed_at = cls._parse_datetime(
                data.get("processed_at")
            )

            # Preserve any additional processor profile information.
            known_fields = {
                "dataset_id",
                "source_file",
                "source_format",
                "sheet_name",
                "row_count",
                "column_count",
                "duplicate_rows",
                "duplicate_rows_removed",
                "empty_rows_removed",
                "empty_columns_removed",
                "columns",
                "parquet_path",
                "profile_path",
                "status",
                "warnings",
                "processed_at",
            }

            dataset.profile_metadata = cls._json_safe({
                key: value
                for key, value in data.items()
                if key not in known_fields
            })

            # -------------------------------------------------
            # Rebuild variable associations
            # -------------------------------------------------

            for position, column in enumerate(data["columns"]):
                column_data = cls._to_dict(column)

                cls._create_dataset_variable(
                    db=db,
                    dataset=dataset,
                    column=column_data,
                    position=position,
                )

                result.variables_linked += 1

            db.flush()

        # Update the original uploaded file's processing status.
        cls._update_file_status(file, normalized_profiles)

        # Artifact warnings should also be reflected in the file status.
        if result.warnings and file.processing_status == "processed":
            file.processing_status = "warning"

        db.flush()

        return result