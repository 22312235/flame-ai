from __future__ import annotations

import logging

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models.file import File
from models.processing_job import ProcessingJob

from database.repositories.processing_job_repository import (
    ProcessingJobRepository,
)

from orchestration.processor_registry import ProcessorRegistry
from orchestration.exceptions import (
    ProcessorNotRegisteredError,
    SourceFileNotFoundError,
    ProcessorExecutionError,
    IngestionError,
    ProcessingJobError,
)

from storage import LocalStorage, StorageBackend


logger = logging.getLogger(__name__)


class ProcessingOrchestrator:
    """
    Coordinates processing jobs from source-file retrieval to database ingestion.

    Responsibilities:
        1. Retrieve a queued processing job.
        2. Resolve its processor registration.
        3. Retrieve the original file from managed storage.
        4. Execute the processor.
        5. Persist the processor output through its ingestion adapter.
        6. Update the processing job status.

    The orchestrator owns transaction boundaries.
    """

    def __init__(
        self,
        registry: ProcessorRegistry,
        storage: StorageBackend | None = None,
    ):
        self.registry = registry
        self.storage = storage or LocalStorage()

    # ---------------------------------------------------------
    # General helpers
    # ---------------------------------------------------------

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _set_job_status(
        job: ProcessingJob,
        status: str,
        error_message: str | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        """Update processing-job status and timestamps."""

        job.status = status

        if status == "running":
            job.started_at = ProcessingOrchestrator._utc_now()
            job.completed_at = None
            job.error_message = None
            job.warnings = []

        elif status in {
            "completed",
            "warning",
            "failed",
            "cancelled",
        }:
            job.completed_at = ProcessingOrchestrator._utc_now()
            job.error_message = error_message
            job.warnings = warnings or []

    @staticmethod
    def _collect_warnings(value: Any) -> list[str]:
        """Collect warnings from dictionaries, dataclasses, or lists."""

        warnings = []

        if value is None:
            return warnings

        if isinstance(value, dict):
            warnings.extend(
                str(item)
                for item in value.get("warnings", []) or []
            )

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    warnings.extend(
                        str(warning)
                        for warning in item.get("warnings", []) or []
                    )
                elif hasattr(item, "warnings"):
                    warnings.extend(
                        str(warning)
                        for warning in getattr(item, "warnings", []) or []
                    )

        elif hasattr(value, "warnings"):
            warnings.extend(
                str(item)
                for item in getattr(value, "warnings", []) or []
            )

        return warnings

    @staticmethod
    def _get_processor_status(value: Any) -> str | None:
        """Extract an explicit processing status when one is available."""

        if isinstance(value, dict):
            status = value.get("processing_status")
            if status:
                return str(status).lower()

        return None

    @staticmethod
    def _get_profile_statuses(value: Any) -> list[str]:
        """Extract statuses from tabular processor profile collections."""

        if not isinstance(value, list):
            return []

        statuses = []

        for item in value:
            if isinstance(item, dict):
                status = item.get("status")
            else:
                status = getattr(item, "status", None)

            if status:
                statuses.append(str(status).lower())

        return statuses

    @staticmethod
    def _resolve_processor_options(job: ProcessingJob) -> dict:
        """
        Return processor parameters stored when the job was created.

        The classifier metadata is retained because processors may use
        additional options in future versions.
        """

        parameters = job.processing_parameters or {}

        if not isinstance(parameters, dict):
            raise ValueError(
                "Processing job parameters must be a dictionary."
            )

        return dict(parameters)

    # ---------------------------------------------------------
    # Source file retrieval
    # ---------------------------------------------------------

    def _get_source_file(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> tuple[File, Path]:
        """Retrieve the source file and resolve its managed path."""

        file_record = db.get(File, job.file_id)

        if file_record is None:
            raise SourceFileNotFoundError(
                str(job.file_id),
                "File record does not exist.",
            )

        if not file_record.storage_key:
            raise SourceFileNotFoundError(
                str(job.file_id),
                "",
            )

        if file_record.storage_backend != "local":
            raise ValueError(
                f"Unsupported storage backend: "
                f"{file_record.storage_backend}"
            )

        source_path = self.storage.get_file_path(
            file_record.storage_key
        )

        if not source_path.exists() or not source_path.is_file():
            raise SourceFileNotFoundError(
                str(job.file_id),
                file_record.storage_key,
            )

        return file_record, source_path

    # ---------------------------------------------------------
    # Job execution
    # ---------------------------------------------------------

    def process_job(
        self,
        db: Session,
        job_id: UUID,
    ) -> ProcessingJob:
        """
        Execute one queued processing job.

        A failed job is marked as failed and returned to the caller.
        It does not propagate processor or ingestion exceptions.

        The job must already be in the queued state.
        """

        job = db.get(ProcessingJob, job_id)

        if job is None:
            raise ValueError(
                f"Processing job does not exist: {job_id}"
            )

        if job.status != "queued":
            raise ProcessingJobError(
                str(job_id),
                f"Cannot execute a job with status '{job.status}'.",
            )

        try:
            # -------------------------------------------------
            # 1. Resolve processor registration
            # -------------------------------------------------

            registration = self.registry.get(job.processor_type)

            if registration is None:
                raise ProcessorNotRegisteredError(
                    job.processor_type
                )

            # -------------------------------------------------
            # 2. Retrieve source file
            # -------------------------------------------------

            file_record, source_path = self._get_source_file(
                db,
                job,
            )

            logger.info(
                "Starting processing job %s for file %s using %s",
                job.job_id,
                job.file_id,
                job.processor_type,
            )

            # -------------------------------------------------
            # 3. Mark job as running
            # -------------------------------------------------

            self._set_job_status(job, "running")

            db.flush()

            # Commit before the potentially expensive processing operation.
            # This makes the running state visible to other database sessions.
            db.commit()

            # -------------------------------------------------
            # 4. Execute processor
            # -------------------------------------------------

            processor_options = self._resolve_processor_options(job)

            try:
                processor_result = registration.processor(
                    source_path,
                    processor_options,
                )

            except Exception as error:
                raise ProcessorExecutionError(
                    job.processor_type,
                    str(job.file_id),
                    str(error),
                ) from error

            processor_status = self._get_processor_status(
                processor_result
            )

            if processor_status in {"failed", "error"}:
                raise ProcessorExecutionError(
                    job.processor_type,
                    str(job.file_id),
                    f"Processor returned status '{processor_status}'.",
                )

            # -------------------------------------------------
            # 5. Persist processor output
            # -------------------------------------------------

            try:
                ingestion_result = registration.ingestion_adapter(
                    db,
                    job.file_id,
                    processor_result,
                )

            except Exception as error:
                raise IngestionError(
                    job.processor_type,
                    str(job.file_id),
                    str(error),
                ) from error

            # -------------------------------------------------
            # 6. Determine final job status
            # -------------------------------------------------

            warnings = []

            warnings.extend(
                self._collect_warnings(processor_result)
            )

            warnings.extend(
                self._collect_warnings(ingestion_result)
            )

            profile_statuses = self._get_profile_statuses(
                processor_result
            )

            has_partial_profiles = any(
                status in {"warning", "partial", "failed", "error"}
                for status in profile_statuses
            )

            has_failed_profiles = (
                bool(profile_statuses)
                and all(
                    status in {"failed", "error"}
                    for status in profile_statuses
                )
            )

            if has_failed_profiles:
                raise IngestionError(
                    job.processor_type,
                    str(job.file_id),
                    "All returned dataset profiles have failed.",
                )

            should_warn = (
                bool(warnings)
                or processor_status in {"warning", "partial"}
                or has_partial_profiles
            )

            final_status = "warning" if should_warn else "completed"

            self._set_job_status(
                job,
                final_status,
                warnings=warnings,
            )

            db.flush()
            db.commit()

            logger.info(
                "Processing job %s finished with status %s",
                job.job_id,
                final_status,
            )

            db.refresh(job)

            return job

        except Exception as error:
            # -------------------------------------------------
            # 7. Handle processing failure
            # -------------------------------------------------

            logger.exception(
                "Processing job %s failed: %s",
                job_id,
                error,
            )

            # Roll back partially persisted ingestion records.
            db.rollback()

            # Reload the job because rollback expires ORM state.
            job = db.get(ProcessingJob, job_id)

            if job is None:
                raise

            self._set_job_status(
                job,
                "failed",
                error_message=str(error),
                warnings=[],
            )

            db.flush()
            db.commit()
            db.refresh(job)

            return job

    # ---------------------------------------------------------
    # Queue processing
    # ---------------------------------------------------------

    def process_next(
        self,
        db: Session,
    ) -> ProcessingJob | None:
        """Retrieve and execute the oldest queued job."""

        job = ProcessingJobRepository.get_next_queued(db)

        if job is None:
            return None

        return self.process_job(
            db=db,
            job_id=job.job_id,
        )

    def process_pending(
        self,
        db: Session,
        limit: int = 10,
    ) -> list[ProcessingJob]:
        """
        Process up to `limit` queued jobs in creation order.

        This implementation is intended for a single worker.
        """

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        queued_jobs = ProcessingJobRepository.get_queued(
            db,
            limit=limit,
        )

        results = []

        for queued_job in queued_jobs:
            result = self.process_job(
                db=db,
                job_id=queued_job.job_id,
            )

            results.append(result)

        return results