from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.base import utc_now
from models.processing_job import ProcessingJob


class ProcessingJobRepository:
    """Database operations for file-processing jobs."""

    VALID_STATUSES = {
        "queued",
        "running",
        "completed",
        "warning",
        "failed",
        "cancelled",
    }

    TERMINAL_STATUSES = {
        "completed",
        "warning",
        "failed",
        "cancelled",
    }

    RETRYABLE_STATUSES = {
        "failed",
        "warning",
        "cancelled",
    }

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create(
        db: Session,
        file_id: UUID,
        processor_type: str,
        processor_version: Optional[str] = None,
        processing_parameters: Optional[dict[str, Any]] = None,
        status: str = "queued",
    ) -> ProcessingJob:
        """Create a processing job for an existing file."""

        if not processor_type or not processor_type.strip():
            raise ValueError("processor_type cannot be empty.")

        if status not in ProcessingJobRepository.VALID_STATUSES:
            raise ValueError(f"Invalid processing status: {status}")

        job = ProcessingJob(
            file_id=file_id,
            processor_type=processor_type.strip(),
            processor_version=processor_version,
            status=status,
            processing_parameters=processing_parameters or {},
        )

        db.add(job)
        db.flush()

        return job

    # =====================================================
    # READ
    # =====================================================

    @staticmethod
    def get_by_id(
        db: Session,
        job_id: UUID,
    ) -> Optional[ProcessingJob]:
        """Retrieve a processing job by its ID."""

        return db.get(ProcessingJob, job_id)

    @staticmethod
    def get_by_file(
        db: Session,
        file_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessingJob]:
        """Retrieve processing jobs belonging to a file."""

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        statement = (
            select(ProcessingJob)
            .where(ProcessingJob.file_id == file_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_latest_for_file(
        db: Session,
        file_id: UUID,
        processor_type: Optional[str] = None,
    ) -> Optional[ProcessingJob]:
        """Retrieve the most recent job for a file."""

        statement = select(ProcessingJob).where(
            ProcessingJob.file_id == file_id
        )

        if processor_type is not None:
            statement = statement.where(
                ProcessingJob.processor_type == processor_type
            )

        statement = (
            statement
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )

        return db.scalars(statement).first()

    # =====================================================
    # QUEUED JOBS
    # =====================================================

    @staticmethod
    def get_queued(
        db: Session,
        limit: int = 10,
    ) -> list[ProcessingJob]:
        """
        Retrieve queued jobs in creation order.

        The oldest queued jobs are returned first.
        """

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        statement = (
            select(ProcessingJob)
            .where(ProcessingJob.status == "queued")
            .order_by(
                ProcessingJob.created_at.asc(),
                ProcessingJob.job_id.asc(),
            )
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_next_queued(
        db: Session,
    ) -> Optional[ProcessingJob]:
        """Retrieve the oldest queued job, if one exists."""

        statement = (
            select(ProcessingJob)
            .where(ProcessingJob.status == "queued")
            .order_by(
                ProcessingJob.created_at.asc(),
                ProcessingJob.job_id.asc(),
            )
            .limit(1)
        )

        return db.scalars(statement).first()

    # =====================================================
    # STATUS MANAGEMENT
    # =====================================================

    @staticmethod
    def update_status(
        db: Session,
        job_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        warnings: Optional[list[Any]] = None,
    ) -> Optional[ProcessingJob]:
        """Update a job's status and lifecycle timestamps."""

        if status not in ProcessingJobRepository.VALID_STATUSES:
            raise ValueError(f"Invalid processing status: {status}")

        job = db.get(ProcessingJob, job_id)

        if job is None:
            return None

        now = utc_now()

        if status == "running":
            if job.started_at is None:
                job.started_at = now

        if status in ProcessingJobRepository.TERMINAL_STATUSES:
            if job.started_at is None:
                job.started_at = now

            job.completed_at = now

        job.status = status

        if error_message is not None:
            job.error_message = error_message

        if warnings is not None:
            job.warnings = warnings

        db.flush()

        return job

    # =====================================================
    # RETRY
    # =====================================================

    @staticmethod
    def reset_for_retry(
        db: Session,
        job_id: UUID,
    ) -> Optional[ProcessingJob]:
        """
        Reset a failed, warning, or cancelled job for another attempt.

        Clears previous execution timestamps, errors and warnings.
        The job returns to the queued state.
        """

        job = db.get(ProcessingJob, job_id)

        if job is None:
            return None

        if job.status not in ProcessingJobRepository.RETRYABLE_STATUSES:
            raise ValueError(
                f"Job with status '{job.status}' cannot be retried."
            )

        job.status = "queued"
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.warnings = []

        db.flush()

        return job

    # =====================================================
    # PROCESSING PARAMETERS
    # =====================================================

    @staticmethod
    def update_processing_parameters(
        db: Session,
        job_id: UUID,
        parameters: dict[str, Any],
    ) -> Optional[ProcessingJob]:
        """Replace the processing parameters stored for a job."""

        job = db.get(ProcessingJob, job_id)

        if job is None:
            return None

        job.processing_parameters = parameters

        db.flush()

        return job

    # =====================================================
    # COUNTERS
    # =====================================================

    @staticmethod
    def count_by_file(
        db: Session,
        file_id: UUID,
    ) -> int:
        """Count all processing jobs associated with a file."""

        statement = (
            select(func.count())
            .select_from(ProcessingJob)
            .where(ProcessingJob.file_id == file_id)
        )

        return db.scalar(statement) or 0

    @staticmethod
    def count_by_status(
        db: Session,
        status: str,
    ) -> int:
        """Count processing jobs having a particular status."""

        if status not in ProcessingJobRepository.VALID_STATUSES:
            raise ValueError(f"Invalid processing status: {status}")

        statement = (
            select(func.count())
            .select_from(ProcessingJob)
            .where(ProcessingJob.status == status)
        )

        return db.scalar(statement) or 0

    # =====================================================
    # RECENT JOBS
    # =====================================================

    @staticmethod
    def get_recent(
        db: Session,
        limit: int = 50,
    ) -> list[ProcessingJob]:
        """Retrieve the most recently created processing jobs."""

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        statement = (
            select(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc())
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    # =====================================================
    # DELETE
    # =====================================================

    @staticmethod
    def delete(
        db: Session,
        job_id: UUID,
    ) -> bool:
        """Delete a processing job."""

        job = db.get(ProcessingJob, job_id)

        if job is None:
            return False

        db.delete(job)
        db.flush()

        return True