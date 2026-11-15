from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.common import (
    DataSourceReference,
    FilterSet,
    PaginationMetadata,
)

from api.schemas.filtering import (
    InvestigationFilterRequest,
    InvestigationFilterResponse,
    DatasetFilterRequest,
    DatasetFilterResponse,
    VariableFilterRequest,
    VariableFilterResponse,
    RowFilterRequest,
    RowFilterResponse,
)

from models.investigation import Investigation
from models.file import File
from models.numerical import Dataset

from filtering.dataset_filter import filter_dataset_catalog
from filtering.variable_filter import (
    filter_variable_catalog,
    filter_dataframe_rows,
)

from services.dataset_service import DatasetService


class FilteringService:
    """
    Application service for investigation, dataset,
    variable, and numerical observation filtering.

    Database operations are read-only.

    The service does not:
        - Commit transactions.
        - Modify Parquet files.
        - Perform statistical analysis.
        - Manage HTTP requests directly.
    """

    def __init__(
        self,
        dataset_service: DatasetService | None = None,
    ):
        self.dataset_service = (
            dataset_service or DatasetService()
        )

    # =====================================================
    # Shared Helpers
    # =====================================================

    @staticmethod
    def _paginate(
        records: list[Any],
        limit: int,
        offset: int,
    ) -> tuple[list[Any], PaginationMetadata]:
        """Paginate a list of records."""

        total = len(records)

        page = records[offset:offset + limit]

        pagination = PaginationMetadata(
            total=total,
            limit=limit,
            offset=offset,
            returned=len(page),
            has_more=offset + len(page) < total,
        )

        return page, pagination

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        """
        Convert pandas, NumPy, UUID, and datetime
        values into JSON-compatible objects.
        """

        if value is None or value is pd.NA or value is pd.NaT:
            return None

        if isinstance(value, dict):
            return {
                str(key): cls._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                cls._json_safe(item)
                for item in value
            ]

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.isoformat()

        if isinstance(value, np.ndarray):
            return cls._json_safe(value.tolist())

        if isinstance(value, np.generic):
            return cls._json_safe(value.item())

        if isinstance(value, float):
            return value if math.isfinite(value) else None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        return value

    @staticmethod
    def _conditions_to_dicts(
        filters: FilterSet,
    ) -> list[dict[str, Any]]:
        """Convert Pydantic conditions to plain dictionaries."""

        return [
            condition.model_dump(mode="json")
            for condition in filters.conditions
        ]

    # =====================================================
    # Investigation Filtering
    # =====================================================

    def filter_investigations(
        self,
        db: Session,
        request: InvestigationFilterRequest,
    ) -> InvestigationFilterResponse:
        """
        Filter investigation records using available
        metadata and related dataset/file information.
        """

        investigations = db.execute(
            select(Investigation)
        ).scalars().all()

        selected = []

        requested_ids = set(request.investigation_ids)

        keywords = [
            keyword.casefold()
            for keyword in request.keywords
        ]

        requested_variables = {
            name.casefold()
            for name in request.required_variables
        }

        requested_formats = {
            value.casefold().lstrip(".")
            for value in request.file_types
        }

        requested_statuses = {
            value.casefold()
            for value in request.processing_statuses
        }

        for investigation in investigations:
            if (
                requested_ids
                and investigation.investigation_id not in requested_ids
            ):
                continue

            searchable_text = " ".join(
                str(value)
                for value in (
                    investigation.external_id,
                    investigation.title,
                    investigation.description,
                    investigation.principal_investigator,
                )
                if value is not None
            ).casefold()

            if keywords and not any(
                keyword in searchable_text
                for keyword in keywords
            ):
                continue

            files = db.execute(
                select(File).where(
                    File.investigation_id
                    == investigation.investigation_id
                )
            ).scalars().all()

            if requested_formats:
                available_formats = {
                    str(file.extension).casefold().lstrip(".")
                    for file in files
                    if getattr(file, "extension", None)
                }

                if not requested_formats.intersection(
                    available_formats
                ):
                    continue

            if requested_statuses:
                available_statuses = {
                    str(file.processing_status).casefold()
                    for file in files
                    if getattr(file, "processing_status", None)
                }

                if not requested_statuses.intersection(
                    available_statuses
                ):
                    continue

            if requested_variables:
                datasets = db.execute(
                    select(Dataset)
                    .join(File, Dataset.file_id == File.file_id)
                    .where(
                        File.investigation_id
                        == investigation.investigation_id
                    )
                ).scalars().all()

                available_variables = set()

                for dataset in datasets:
                    variables = (
                        self.dataset_service.get_dataset_variables(
                            db=db,
                            dataset_id=dataset.dataset_id,
                            investigation_id=investigation.investigation_id,
                        )
                    )

                    available_variables.update(
                        variable["name"].casefold()
                        for variable in variables
                    )

                if not requested_variables.issubset(
                    available_variables
                ):
                    continue

            selected.append({
                "investigation_id": str(
                    investigation.investigation_id
                ),
                "external_id": investigation.external_id,
                "title": investigation.title,
                "description": investigation.description,
                "principal_investigator": (
                    investigation.principal_investigator
                ),
                "file_count": len(files),
            })

        page, pagination = self._paginate(
            selected,
            request.pagination.limit,
            request.pagination.offset,
        )

        return InvestigationFilterResponse(
            investigations=page,
            pagination=pagination,
            applied_filters=request.model_dump(
                mode="json",
                exclude={"pagination"},
            ),
        )

    # =====================================================
    # Dataset Filtering
    # =====================================================

    def filter_datasets(
        self,
        db: Session,
        request: DatasetFilterRequest,
    ) -> DatasetFilterResponse:
        """
        Filter datasets within one investigation.

        Uses the existing:
            filter_dataset_catalog()
        """

        statement = (
            select(Dataset)
            .join(
                File,
                Dataset.file_id == File.file_id,
            )
            .where(
                File.investigation_id
                == request.investigation_id
            )
        )

        datasets = db.execute(
            statement
        ).scalars().all()

        catalog = []

        for dataset in datasets:
            metadata = (
                self.dataset_service.get_dataset_metadata(
                    db=db,
                    dataset_id=dataset.dataset_id,
                    investigation_id=request.investigation_id,
                )
            )

            # Adapt database metadata to the format expected
            # by filter_dataset_catalog().
            catalog.append({
                **metadata,
                "name": metadata["source_file"],
                "data_format": metadata["source_format"],
                "processing_status": metadata["status"],
                "variables": metadata["variables"],
            })

        filter_result = filter_dataset_catalog(
            catalog=catalog,
            investigation_id=str(request.investigation_id),
            catalog_is_scoped=False,
            name_contains=request.name_contains,
            description_contains=request.description_contains,
            keywords=request.keywords,
            file_types=request.file_types,
            data_formats=request.data_formats,
            categories=request.categories,
            data_types=request.data_types,
            processing_statuses=request.processing_statuses,
            required_tags=request.required_tags,
            required_variables=request.required_variables,
            minimum_size_bytes=request.minimum_size_bytes,
            maximum_size_bytes=request.maximum_size_bytes,
            minimum_rows=request.minimum_rows,
            maximum_rows=request.maximum_rows,
            minimum_columns=request.minimum_columns,
            maximum_columns=request.maximum_columns,
            maximum_missing_percentage=(
                request.maximum_missing_percentage
            ),
            coverage_start=request.coverage_start,
            coverage_end=request.coverage_end,
            dataset_ids=[
                str(value)
                for value in request.dataset_ids
            ],
            excluded_dataset_ids=[
                str(value)
                for value in request.excluded_dataset_ids
            ],
        )

        selected = [
            entry["dataset"]
            for entry in filter_result["selected"]
        ]

        page, pagination = self._paginate(
            selected,
            request.pagination.limit,
            request.pagination.offset,
        )

        return DatasetFilterResponse(
            investigation_id=request.investigation_id,
            total_datasets=filter_result["total_datasets"],
            selected_count=filter_result["selected_count"],
            datasets=self._json_safe(page),
            pagination=pagination,
            applied_filters=filter_result["applied_filters"],
        )

    # =====================================================
    # Variable Filtering
    # =====================================================

    def filter_variables(
        self,
        db: Session,
        request: VariableFilterRequest,
        investigation_id: UUID | None = None,
    ) -> VariableFilterResponse:
        """
        Filter variables using their database profiles.

        Uses the existing:
            filter_variable_catalog()
        """

        variables = (
            self.dataset_service.get_dataset_variables(
                db=db,
                dataset_id=request.dataset_id,
                investigation_id=investigation_id,
            )
        )

        profile = {
            "variables": variables,
        }

        filter_result = filter_variable_catalog(
            profile=profile,
            name_contains=request.name_contains,
            keywords=request.keywords,
            variable_types=request.variable_types,
            units=request.units,
            minimum_unique_values=(
                request.minimum_unique_values
            ),
            maximum_unique_values=(
                request.maximum_unique_values
            ),
            maximum_missing_percentage=(
                request.maximum_missing_percentage
            ),
            minimum_value=request.minimum_value,
            maximum_value=request.maximum_value,
        )

        selected = filter_result["selected_variables"]

        page, pagination = self._paginate(
            selected,
            request.pagination.limit,
            request.pagination.offset,
        )

        return VariableFilterResponse(
            dataset_id=request.dataset_id,
            selected_count=filter_result["selected_count"],
            variables=self._json_safe(page),
            pagination=pagination,
            applied_filters=filter_result["filters_applied"],
        )

    # =====================================================
    # Numerical Row Filtering
    # =====================================================

    def filter_rows(
        self,
        db: Session,
        request: RowFilterRequest,
    ) -> RowFilterResponse:
        """
        Filter numerical observations stored in Parquet.

        Uses:
            DatasetService.load_dataframe()
            filter_dataframe_rows()

        Conditions are evaluated before selecting the
        final output columns.
        """

        dataset = self.dataset_service.get_dataset(
            db=db,
            dataset_id=request.dataset_id,
            investigation_id=request.investigation_id,
        )

        conditions = self._conditions_to_dicts(
            request.filters
        )

        # All columns used for filtering must be loaded.
        condition_columns = [
            condition["column"]
            for condition in conditions
        ]

        selected_columns = request.selected_columns

        # If no output columns are specified, return all.
        if selected_columns:
            required_columns = list(
                dict.fromkeys(
                    selected_columns + condition_columns
                )
            )
        else:
            required_columns = None

        dataframe = self.dataset_service.load_dataframe(
            db=db,
            dataset_id=request.dataset_id,
            investigation_id=request.investigation_id,
            columns=required_columns,
        )

        filtered, metadata = filter_dataframe_rows(
            data=dataframe,
            conditions=conditions,
            combine=request.filters.combine.value,
        )

        if selected_columns:
            missing_columns = [
                column
                for column in selected_columns
                if column not in filtered.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"Requested columns not found: {missing_columns}"
                )

            filtered = filtered[selected_columns].copy()

        total = len(filtered)

        limit = request.pagination.limit
        offset = request.pagination.offset

        page = filtered.iloc[
            offset:offset + limit
        ]

        rows = self._json_safe(
            page.to_dict(orient="records")
        )

        pagination = PaginationMetadata(
            total=total,
            limit=limit,
            offset=offset,
            returned=len(rows),
            has_more=offset + len(rows) < total,
        )

        return RowFilterResponse(
            dataset_id=request.dataset_id,
            source=DataSourceReference(
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                file_id=dataset.file_id,
            ),
            columns=list(filtered.columns),
            rows=rows,
            original_row_count=metadata["original_row_count"],
            filtered_row_count=metadata["filtered_row_count"],
            pagination=pagination,
            applied_filters=request.filters,
        )