import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.file import File


class FileRepository:
    """
    Handles database operations for original files
    and derived assets.

    Supports local filesystem storage and future storage backends.

    This repository does not commit transactions.
    Transaction management is handled by the caller.
    """

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create(
        db: Session,
        investigation_id: uuid.UUID,
        filename: str,
        file_category: str,
        storage_path: str | None,
        file_size_bytes: int,
        extension: str | None = None,
        detected_format: str | None = None,
        file_role: str = "original",
        parent_file_id: uuid.UUID | None = None,
        sha256: str | None = None,
        processing_status: str = "pending",
        storage_key: str | None = None,
        storage_backend: str = "local",
    ) -> File:
        """
        Registers an original file or derived asset.

        Storage fields:
            storage_backend:
                Identifies the storage implementation.
                Example: "local", "s3".

            storage_key:
                Relative identifier used by the storage backend.
                Example:
                    investigations/<id>/original/report.pdf

            storage_path:
                Legacy filesystem path retained for compatibility.

        At least one of storage_key or storage_path is required.

        Examples:
            Original PDF:
                file_role="original"

            Image extracted from PDF:
                file_role="extracted_image"
                parent_file_id=<original PDF UUID>
        """

        if file_size_bytes < 0:
            raise ValueError("file_size_bytes cannot be negative.")

        if not filename or not filename.strip():
            raise ValueError("filename cannot be empty.")

        if not file_category or not file_category.strip():
            raise ValueError("file_category cannot be empty.")

        if not storage_backend or not storage_backend.strip():
            raise ValueError("storage_backend cannot be empty.")

        if storage_key is not None and not storage_key.strip():
            raise ValueError("storage_key cannot be empty.")

        if storage_path is not None and not storage_path.strip():
            raise ValueError("storage_path cannot be empty.")

        if storage_key is None and storage_path is None:
            raise ValueError(
                "Either storage_key or storage_path must be provided."
            )

        # Ensure the parent file exists and belongs
        # to the same investigation.
        if parent_file_id is not None:
            parent = db.get(File, parent_file_id)

            if parent is None:
                raise ValueError("Parent file does not exist.")

            if parent.investigation_id != investigation_id:
                raise ValueError(
                    "Parent file belongs to another investigation."
                )

        file_record = File(
            investigation_id=investigation_id,
            parent_file_id=parent_file_id,
            filename=filename,
            extension=extension,
            detected_format=detected_format,
            file_category=file_category,
            file_role=file_role,
            storage_backend=storage_backend,
            storage_key=storage_key,
            storage_path=storage_path,
            file_size_bytes=file_size_bytes,
            sha256=sha256,
            processing_status=processing_status,
        )

        db.add(file_record)
        db.flush()

        return file_record

    # =====================================================
    # READ
    # =====================================================

    @staticmethod
    def get_by_id(
        db: Session,
        file_id: uuid.UUID,
    ) -> File | None:
        """Retrieves a file using its UUID."""

        return db.get(File, file_id)

    @staticmethod
    def get_by_storage_key(
        db: Session,
        storage_key: str,
    ) -> File | None:
        """
        Retrieves a file using its storage key.

        Useful when resolving a stored file through
        the storage abstraction.
        """

        if not storage_key:
            return None

        statement = (
            select(File)
            .where(File.storage_key == storage_key)
            .limit(1)
        )

        return db.scalar(statement)

    @staticmethod
    def get_by_investigation(
        db: Session,
        investigation_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[File]:
        """Retrieves files belonging to an investigation."""

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        statement = (
            select(File)
            .where(File.investigation_id == investigation_id)
            .order_by(File.registered_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_by_category(
        db: Session,
        investigation_id: uuid.UUID,
        file_category: str,
    ) -> list[File]:
        """Retrieves files of a particular category."""

        statement = (
            select(File)
            .where(
                File.investigation_id == investigation_id,
                File.file_category == file_category,
            )
            .order_by(File.registered_at.desc())
        )

        return list(db.scalars(statement).all())

    # =====================================================
    # DUPLICATE DETECTION
    # =====================================================

    @staticmethod
    def find_duplicate(
        db: Session,
        investigation_id: uuid.UUID,
        sha256: str,
    ) -> File | None:
        """
        Finds an existing original file with the same SHA-256
        within the same investigation.

        Identical files in different investigations
        are not automatically treated as duplicates.
        """

        if not sha256:
            return None

        statement = (
            select(File)
            .where(
                File.investigation_id == investigation_id,
                File.sha256 == sha256,
                File.file_role == "original",
            )
            .order_by(File.registered_at.asc())
            .limit(1)
        )

        return db.scalar(statement)

    # =====================================================
    # DERIVED FILES
    # =====================================================

    @staticmethod
    def get_derived_files(
        db: Session,
        parent_file_id: uuid.UUID,
    ) -> list[File]:
        """Retrieves all files derived from a parent file."""

        statement = (
            select(File)
            .where(File.parent_file_id == parent_file_id)
            .order_by(File.registered_at.asc())
        )

        return list(db.scalars(statement).all())

    # =====================================================
    # PROCESSING STATUS
    # =====================================================

    @staticmethod
    def update_status(
        db: Session,
        file_id: uuid.UUID,
        status: str,
    ) -> File | None:
        """
        Updates the processing status of a file.

        Allowed statuses:
            pending, processing, processed,
            warning, failed, skipped
        """

        allowed_statuses = {
            "pending",
            "processing",
            "processed",
            "warning",
            "failed",
            "skipped",
        }

        if status not in allowed_statuses:
            raise ValueError(f"Invalid processing status: {status}")

        file_record = FileRepository.get_by_id(db, file_id)

        if file_record is None:
            return None

        file_record.processing_status = status

        db.flush()

        return file_record

    # =====================================================
    # GENERAL UPDATE
    # =====================================================

    @staticmethod
    def update(
        db: Session,
        file_id: uuid.UUID,
        **updates,
    ) -> File | None:
        """
        Updates permitted file metadata.

        Storage metadata can be updated using:
            storage_backend
            storage_key
            storage_path
        """

        allowed_fields = {
            "filename",
            "extension",
            "detected_format",
            "file_category",
            "file_role",
            "storage_backend",
            "storage_key",
            "storage_path",
            "file_size_bytes",
            "sha256",
        }

        invalid_fields = set(updates) - allowed_fields

        if invalid_fields:
            raise ValueError(
                f"Invalid file fields: "
                f"{', '.join(sorted(invalid_fields))}"
            )

        if (
            "file_size_bytes" in updates
            and updates["file_size_bytes"] < 0
        ):
            raise ValueError("file_size_bytes cannot be negative.")

        if (
            "storage_backend" in updates
            and (
                not updates["storage_backend"]
                or not updates["storage_backend"].strip()
            )
        ):
            raise ValueError("storage_backend cannot be empty.")

        if (
            "storage_key" in updates
            and updates["storage_key"] is not None
            and not updates["storage_key"].strip()
        ):
            raise ValueError("storage_key cannot be empty.")

        if (
            "storage_path" in updates
            and updates["storage_path"] is not None
            and not updates["storage_path"].strip()
        ):
            raise ValueError("storage_path cannot be empty.")

        file_record = FileRepository.get_by_id(db, file_id)

        if file_record is None:
            return None

        # Validate the final storage location after applying updates.
        final_storage_key = updates.get(
            "storage_key",
            file_record.storage_key,
        )

        final_storage_path = updates.get(
            "storage_path",
            file_record.storage_path,
        )

        if final_storage_key is None and final_storage_path is None:
            raise ValueError(
                "A file must have either storage_key or storage_path."
            )

        for field, value in updates.items():
            setattr(file_record, field, value)

        db.flush()

        return file_record

    # =====================================================
    # COUNT
    # =====================================================

    @staticmethod
    def count_by_investigation(
        db: Session,
        investigation_id: uuid.UUID,
    ) -> int:
        """Returns the number of registered files in an investigation."""

        statement = (
            select(func.count())
            .select_from(File)
            .where(File.investigation_id == investigation_id)
        )

        return db.scalar(statement) or 0

    # =====================================================
    # DELETE
    # =====================================================

    @staticmethod
    def delete(
        db: Session,
        file_id: uuid.UUID,
    ) -> bool:
        """
        Deletes a file record.

        Associated processing jobs are deleted through
        the configured relationship cascade.

        This operation does not delete the physical file
        from storage.
        """

        file_record = FileRepository.get_by_id(db, file_id)

        if file_record is None:
            return False

        db.delete(file_record)
        db.flush()

        return True