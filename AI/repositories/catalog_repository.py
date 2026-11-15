
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from models.investigation import Investigation
from models.file import File
from models.numerical import Dataset, DatasetVariable


class CatalogRepository:
    """Reads investigation and dataset information from PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_uuid(value: str | UUID) -> UUID:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError("Invalid investigation ID.") from error

    def get_investigation(
        self,
        investigation_id: str,
    ) -> dict[str, Any] | None:

        investigation_uuid = self._to_uuid(investigation_id)

        investigation = self.db.get(
            Investigation,
            investigation_uuid,
        )

        if investigation is None:
            return None

        return {
            "investigation_id": str(investigation.investigation_id),
            "external_id": investigation.external_id,
            "title": investigation.title,
            "description": investigation.description,
            "principal_investigator": investigation.principal_investigator,
            "start_date": investigation.start_date,
            "end_date": investigation.end_date,
            "metadata": investigation.metadata_json or {},
        }

    def count_investigations(self) -> int:
        """Return the total number of investigations."""

        statement = select(func.count()).select_from(Investigation)
        return self.db.scalar(statement) or 0

    def list_investigations(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        if limit < 1 or limit > 200:
            raise ValueError("Limit must be between 1 and 200.")

        if offset < 0:
            raise ValueError("Offset cannot be negative.")

        statement = (
            select(Investigation)
            .order_by(Investigation.investigation_id)
            .limit(limit)
            .offset(offset)
        )

        investigations = self.db.scalars(statement).all()

        return [
            {
                "investigation_id": str(item.investigation_id),
                "external_id": item.external_id,
                "title": item.title,
                "description": item.description,
                "principal_investigator": item.principal_investigator,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "metadata": item.metadata_json or {},
            }
            for item in investigations
        ]

    def get_datasets(
        self,
        investigation_id: str,
    ) -> list[dict[str, Any]]:

        investigation_uuid = self._to_uuid(investigation_id)

        statement = (
            select(Dataset)
            .join(File, Dataset.file_id == File.file_id)
            .where(File.investigation_id == investigation_uuid)
            .options(
                joinedload(Dataset.file),
                selectinload(
                    Dataset.dataset_variables
                ).joinedload(
                    DatasetVariable.variable
                ),
            )
            .order_by(Dataset.dataset_id)
        )

        datasets = self.db.scalars(statement).unique().all()

        results = []

        for dataset in datasets:
            source_file = dataset.file
            variables = []

            for association in dataset.dataset_variables:
                variable = association.variable

                if variable is None:
                    continue

                variables.append({
                    "variable_id": str(variable.variable_id),
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

            results.append({
                "dataset_id": str(dataset.dataset_id),
                "investigation_id": str(source_file.investigation_id),
                "file_id": str(dataset.file_id),
                "name": source_file.filename,
                "filename": source_file.filename,
                "extension": source_file.extension,
                "file_category": source_file.file_category,
                "detected_type": source_file.detected_format,
                "size_bytes": source_file.file_size_bytes,
                "file_role": source_file.file_role,
                "parent_file_id": (
                    str(source_file.parent_file_id)
                    if source_file.parent_file_id else None
                ),
                "source_file": dataset.source_file,
                "data_format": dataset.source_format,
                "sheet_name": dataset.sheet_name,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "processing_status": dataset.status,
                "file_processing_status": source_file.processing_status,
                "variables": variables,
                "profile": dataset.profile_metadata or {},
                "warnings": dataset.warnings or [],
            })

        return results
