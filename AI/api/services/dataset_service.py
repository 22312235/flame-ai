from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.numerical import (
    Dataset,
    DatasetVariable,
)

from storage.local_storage import LocalStorage


# =========================================================
# Exceptions
# =========================================================

class DatasetServiceError(Exception):
    """Base exception for dataset service operations."""


class DatasetNotFoundError(DatasetServiceError):
    """Raised when a dataset does not exist."""


class DatasetAccessError(DatasetServiceError):
    """Raised when a dataset belongs to another investigation."""


class DatasetStorageError(DatasetServiceError):
    """Raised when a dataset's numerical artifact is unavailable."""


class DatasetColumnError(DatasetServiceError):
    """Raised when requested columns do not exist."""


# =========================================================
# Dataset Service
# =========================================================

class DatasetService:
    """
    Shared dataset access service.

    Responsibilities:
        - Retrieve datasets from PostgreSQL.
        - Verify investigation ownership.
        - Retrieve dataset variable metadata.
        - Resolve Parquet storage keys.
        - Load numerical data for filtering and analysis.

    This service does not:
        - Commit database transactions.
        - Perform filtering calculations.
        - Perform statistical analysis.
        - Modify source Parquet files.
    """

    def __init__(
        self,
        storage: LocalStorage | None = None,
    ):
        self.storage = storage or LocalStorage()

    # =====================================================
    # Dataset Retrieval
    # =====================================================

    def get_dataset(
        self,
        db: Session,
        dataset_id: UUID,
        investigation_id: UUID | None = None,
    ) -> Dataset:
        """
        Retrieve a dataset and its associated metadata.

        When investigation_id is provided, verify that
        the dataset belongs to that investigation.
        """

        statement = (
            select(Dataset)
            .options(
                selectinload(Dataset.file),
                selectinload(
                    Dataset.dataset_variables
                ).selectinload(
                    DatasetVariable.variable
                ),
            )
            .where(
                Dataset.dataset_id == dataset_id
            )
        )

        dataset = db.execute(
            statement
        ).scalar_one_or_none()

        if dataset is None:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' was not found."
            )

        if investigation_id is not None:
            self._verify_investigation(
                dataset=dataset,
                investigation_id=investigation_id,
            )

        return dataset

    # =====================================================
    # Investigation Verification
    # =====================================================

    @staticmethod
    def _verify_investigation(
        dataset: Dataset,
        investigation_id: UUID,
    ) -> None:
        """
        Ensure the dataset belongs to the investigation.

        Dataset -> File -> Investigation
        """

        file_record = dataset.file

        if file_record is None:
            raise DatasetAccessError(
                "Dataset has no associated source file."
            )

        if file_record.investigation_id != investigation_id:
            raise DatasetAccessError(
                "Dataset does not belong to the requested investigation."
            )

    # =====================================================
    # Dataset Variables
    # =====================================================

    def get_dataset_variables(
        self,
        db: Session,
        dataset_id: UUID,
        investigation_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return the variables belonging to a dataset.

        Includes:
            - Variable identity.
            - Column names.
            - Data types.
            - Units.
            - Missing-value information.
            - Numerical statistics.
        """

        dataset = self.get_dataset(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        variables = []

        ordered_variables = sorted(
            dataset.dataset_variables,
            key=lambda item: item.column_position,
        )

        for association in ordered_variables:
            variable = association.variable

            if variable is None:
                continue

            variables.append({
                "dataset_variable_id": str(
                    association.dataset_variable_id
                ),
                "variable_id": str(
                    variable.variable_id
                ),
                "name": variable.name,
                "original_name": association.original_name,
                "inferred_type": variable.inferred_type,
                "unit": variable.unit,
                "column_position": association.column_position,
                "non_null_count": association.non_null_count,
                "missing_count": association.missing_count,
                "missing_percentage": association.missing_percentage,
                "unique_count": association.unique_count,
                "sample_values": association.sample_values,
                "statistics": association.statistics,
            })

        return variables

    # =====================================================
    # Dataset Metadata
    # =====================================================

    def get_dataset_metadata(
        self,
        db: Session,
        dataset_id: UUID,
        investigation_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Return dataset metadata suitable for API responses.

        Internal filesystem paths are deliberately excluded.
        """

        dataset = self.get_dataset(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        variables = self.get_dataset_variables(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        return {
            "dataset_id": str(dataset.dataset_id),
            "file_id": str(dataset.file_id),
            "investigation_id": str(
                dataset.file.investigation_id
            ),
            "processor_dataset_id": dataset.processor_dataset_id,
            "source_file": dataset.source_file,
            "source_format": dataset.source_format,
            "sheet_name": dataset.sheet_name,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "duplicate_rows": dataset.duplicate_rows,
            "duplicate_rows_removed": dataset.duplicate_rows_removed,
            "empty_rows_removed": dataset.empty_rows_removed,
            "empty_columns_removed": dataset.empty_columns_removed,
            "status": dataset.status,
            "warnings": dataset.warnings or [],
            "processed_at": (
                dataset.processed_at.isoformat()
                if dataset.processed_at
                else None
            ),
            "profile_metadata": dataset.profile_metadata or {},
            "parquet_available": bool(dataset.parquet_path),
            "profile_available": bool(dataset.profile_path),
            "variables": variables,
        }

    # =====================================================
    # Parquet Storage
    # =====================================================

    def get_parquet_path(
        self,
        db: Session,
        dataset_id: UUID,
        investigation_id: UUID | None = None,
    ) -> Path:
        """
        Resolve the local Parquet file for a dataset.

        Dataset.parquet_path is expected to contain a
        LocalStorage object key, not an absolute filesystem path.
        """

        dataset = self.get_dataset(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        storage_key = dataset.parquet_path

        if not storage_key:
            raise DatasetStorageError(
                f"Dataset '{dataset_id}' has no Parquet artifact."
            )

        try:
            path = self.storage.get_file_path(
                storage_key
            )

        except (ValueError, FileNotFoundError) as error:
            raise DatasetStorageError(
                "Unable to resolve the dataset's Parquet artifact."
            ) from error

        path = Path(path)

        if not path.is_file():
            raise DatasetStorageError(
                "The dataset's Parquet artifact does not exist."
            )

        if path.suffix.lower() != ".parquet":
            raise DatasetStorageError(
                "The dataset artifact is not a Parquet file."
            )

        return path

    # =====================================================
    # DataFrame Loading
    # =====================================================

    def load_dataframe(
        self,
        db: Session,
        dataset_id: UUID,
        investigation_id: UUID | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Load a dataset into a pandas DataFrame.

        Optional column selection reduces memory usage
        when only certain variables are needed.

        The original Parquet file is never modified.
        """

        parquet_path = self.get_parquet_path(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        if columns is not None:
            if not columns:
                raise DatasetColumnError(
                    "At least one column must be selected."
                )

            if len(columns) != len(set(columns)):
                raise DatasetColumnError(
                    "Selected columns must be unique."
                )

        try:
            dataframe = pd.read_parquet(
                parquet_path,
                columns=columns,
            )

        except (
            ValueError,
            KeyError,
        ) as error:
            raise DatasetColumnError(
                f"Unable to load the requested columns: {error}"
            ) from error

        except (
            OSError,
            ImportError,
        ) as error:
            raise DatasetStorageError(
                "Unable to read the dataset's Parquet artifact."
            ) from error

        return dataframe

    # =====================================================
    # Column Validation
    # =====================================================

    def validate_columns(
        self,
        db: Session,
        dataset_id: UUID,
        columns: list[str],
        investigation_id: UUID | None = None,
    ) -> list[str]:
        """
        Verify that requested columns exist in the dataset.

        Uses the dataset-variable associations stored
        in PostgreSQL.
        """

        if not columns:
            raise DatasetColumnError(
                "At least one column must be provided."
            )

        variables = self.get_dataset_variables(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
        )

        available_columns = {
            variable["name"]
            for variable in variables
        }

        missing_columns = [
            column
            for column in columns
            if column not in available_columns
        ]

        if missing_columns:
            raise DatasetColumnError(
                f"Unknown dataset columns: {missing_columns}"
            )

        return columns