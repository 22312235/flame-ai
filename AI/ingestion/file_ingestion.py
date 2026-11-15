import uuid

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from classifier.file_types import FileCategory
from models.classified_file import ClassifiedFile
from models.file import File
from models.processing_job import ProcessingJob

from database.repositories.file_repository import FileRepository
from database.repositories.processing_job_repository import (
    ProcessingJobRepository,
)

from storage import LocalStorage, StorageBackend


@dataclass
class FileIngestionResult:
    """Summary of the files registered from a classification report."""

    registered_files: list[File] = field(default_factory=list)
    processing_jobs: list[ProcessingJob] = field(default_factory=list)
    skipped_files: list[File] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_registered(self) -> int:
        return len(self.registered_files)

    @property
    def total_jobs_created(self) -> int:
        return len(self.processing_jobs)

    @property
    def total_skipped(self) -> int:
        return len(self.skipped_files)


class FileIngestion:
    """
    Persists classified files, stores their binaries,
    and creates their processing jobs.
    """

    STORAGE_BACKEND = "local"

    # =====================================================
    # STORAGE HELPERS
    # =====================================================

    @staticmethod
    def _build_storage_key(
        investigation_id: UUID,
        filename: str,
    ) -> str:
        """
        Generates a unique storage key for an original file.

        The original filename is preserved, but a UUID prefix
        prevents collisions between files with identical names.
        """

        # Remove directory components from the filename.
        safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1]

        if not safe_filename:
            safe_filename = "unnamed_file"

        unique_id = uuid.uuid4().hex

        return (
            f"investigations/{investigation_id}/"
            f"original/{unique_id}_{safe_filename}"
        )

    # =====================================================
    # CLASSIFICATION HELPERS
    # =====================================================

    @staticmethod
    def _get_category_value(
        classified_file: ClassifiedFile,
    ) -> str:
        """Extract the string value of a file category."""

        category = classified_file.category

        if isinstance(category, FileCategory):
            return category.value

        return str(category)

    @staticmethod
    def _determine_file_status(
        classified_file: ClassifiedFile,
        is_duplicate: bool,
        category: str,
    ) -> tuple[str, bool]:
        """
        Determine the database status and whether a job can be created.

        Returns:
            (database_status, should_create_job)
        """

        if is_duplicate:
            return "skipped", False

        if classified_file.status == "error":
            return "failed", False

        if classified_file.status == "unsupported":
            return "skipped", False

        if classified_file.status == "extension_mismatch":
            return "warning", False

        if category == FileCategory.UNKNOWN.value:
            return "skipped", False

        if classified_file.status != "classified":
            return "warning", False

        if not classified_file.processor:
            return "skipped", False

        return "pending", True

    # =====================================================
    # FILE STORAGE
    # =====================================================

    @staticmethod
    def _store_classified_file(
        classified_file: ClassifiedFile,
        investigation_id: UUID,
        storage: StorageBackend,
    ) -> str:
        """
        Copies the original file into the configured storage backend.

        Returns:
            The relative storage key.

        Raises:
            Any storage-related exception if the file cannot be stored.
        """

        storage_key = FileIngestion._build_storage_key(
            investigation_id=investigation_id,
            filename=classified_file.filename,
        )

        storage.store_file(
            source_path=classified_file.file_path,
            object_key=storage_key,
        )

        return storage_key

    # =====================================================
    # MAIN INGESTION
    # =====================================================

    @staticmethod
    def ingest_classification_report(
        db: Session,
        investigation_id: UUID,
        report: Any,
        storage: StorageBackend | None = None,
    ) -> FileIngestionResult:
        """
        Registers classified files, stores their binaries,
        and creates processing jobs.

        Args:
            db:
                Active SQLAlchemy session.

            investigation_id:
                Investigation owning the uploaded files.

            report:
                ClassificationReport containing ClassifiedFile objects.

            storage:
                Storage backend. Defaults to LocalStorage.

        Returns:
            FileIngestionResult containing registered files,
            processing jobs, duplicates, skipped files, and warnings.

        Note:
            This method does not commit the database transaction.
            The caller is responsible for committing or rolling back.
        """

        if not hasattr(report, "files"):
            raise ValueError(
                "Invalid classification report: missing 'files' attribute."
            )

        if storage is None:
            storage = LocalStorage()

        result = FileIngestionResult()

        for classified_file in report.files:

            if not isinstance(classified_file, ClassifiedFile):
                raise TypeError(
                    "Classification report contains an invalid file object."
                )

            category = FileIngestion._get_category_value(
                classified_file
            )

            # -------------------------------------------------
            # DUPLICATE DETECTION
            # -------------------------------------------------

            existing_duplicate = None

            if classified_file.sha256:
                existing_duplicate = FileRepository.find_duplicate(
                    db=db,
                    investigation_id=investigation_id,
                    sha256=classified_file.sha256,
                )

            is_duplicate = (
                classified_file.duplicate_of is not None
                or existing_duplicate is not None
            )

            database_status, should_create_job = (
                FileIngestion._determine_file_status(
                    classified_file=classified_file,
                    is_duplicate=is_duplicate,
                    category=category,
                )
            )

            # -------------------------------------------------
            # STORE ORIGINAL FILE
            # -------------------------------------------------

            storage_key = FileIngestion._store_classified_file(
                classified_file=classified_file,
                investigation_id=investigation_id,
                storage=storage,
            )

            # -------------------------------------------------
            # REGISTER FILE IN DATABASE
            # -------------------------------------------------

            file_record = FileRepository.create(
                db=db,
                investigation_id=investigation_id,
                filename=classified_file.filename,
                extension=classified_file.extension,
                detected_format=classified_file.detected_format,
                file_category=category,
                file_role="original",
                storage_path=None,
                storage_key=storage_key,
                storage_backend=FileIngestion.STORAGE_BACKEND,
                file_size_bytes=classified_file.file_size,
                sha256=classified_file.sha256,
                processing_status=database_status,
            )

            result.registered_files.append(file_record)

            # -------------------------------------------------
            # HANDLE DUPLICATES
            # -------------------------------------------------

            if is_duplicate:

                duplicate_reference = classified_file.duplicate_of

                if existing_duplicate is not None:
                    duplicate_reference = str(
                        existing_duplicate.file_id
                    )

                result.duplicates.append(
                    {
                        "file_id": str(file_record.file_id),
                        "filename": classified_file.filename,
                        "duplicate_of": duplicate_reference,
                    }
                )

                result.skipped_files.append(file_record)

                continue

            # -------------------------------------------------
            # HANDLE FILES THAT CANNOT BE PROCESSED
            # -------------------------------------------------

            if not should_create_job:

                result.skipped_files.append(file_record)

                if classified_file.status == "extension_mismatch":
                    result.warnings.append(
                        f"{classified_file.filename}: extension mismatch. "
                        "Processing was not scheduled."
                    )

                elif classified_file.status == "error":
                    result.warnings.append(
                        f"{classified_file.filename}: "
                        f"{classified_file.error or 'Classification error.'}"
                    )

                elif classified_file.status == "warning":
                    result.warnings.append(
                        f"{classified_file.filename}: "
                        "Classification requires review."
                    )

                continue

            # -------------------------------------------------
            # CREATE PROCESSING JOB
            # -------------------------------------------------

            job = ProcessingJobRepository.create(
                db=db,
                file_id=file_record.file_id,
                processor_type=classified_file.processor,
                processing_parameters={
                    "relative_path": classified_file.relative_path,
                    "extension": classified_file.extension,
                    "detected_format": classified_file.detected_format,
                    "file_category": category,
                    "processing_priority": (
                        classified_file.processing_priority
                    ),
                    "classifier_status": classified_file.status,
                },
            )

            result.processing_jobs.append(job)

        return result