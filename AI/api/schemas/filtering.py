from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from api.schemas.common import (
    APIModel,
    DataSourceReference,
    FilterSet,
    PaginationMetadata,
    PaginationParams,
)


# =========================================================
# Investigation Filtering
# =========================================================

class InvestigationFilterRequest(APIModel):
    """
    Search investigations using metadata criteria.
    """

    keywords: list[str] = Field(default_factory=list)

    investigation_ids: list[UUID] = Field(
        default_factory=list,
    )

    required_variables: list[str] = Field(
        default_factory=list,
    )

    file_types: list[str] = Field(
        default_factory=list,
    )

    processing_statuses: list[str] = Field(
        default_factory=list,
    )

    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
    )


class InvestigationFilterResponse(APIModel):
    investigations: list[dict[str, Any]]

    pagination: PaginationMetadata

    applied_filters: dict[str, Any]


# =========================================================
# Dataset Catalog Filtering
# =========================================================

class DatasetFilterRequest(APIModel):
    """
    Filter datasets belonging to one investigation.

    Designed around:
        filtering.dataset_filter.filter_dataset_catalog()
    """

    investigation_id: UUID

    name_contains: str | None = None

    description_contains: str | None = None

    keywords: list[str] = Field(default_factory=list)

    file_types: list[str] = Field(default_factory=list)

    data_formats: list[str] = Field(default_factory=list)

    categories: list[str] = Field(default_factory=list)

    data_types: list[str] = Field(default_factory=list)

    processing_statuses: list[str] = Field(
        default_factory=list,
    )

    required_tags: list[str] = Field(default_factory=list)

    required_variables: list[str] = Field(
        default_factory=list,
    )

    minimum_size_bytes: float | None = Field(
        default=None,
        ge=0,
    )

    maximum_size_bytes: float | None = Field(
        default=None,
        ge=0,
    )

    minimum_rows: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_rows: int | None = Field(
        default=None,
        ge=0,
    )

    minimum_columns: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_columns: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_missing_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    coverage_start: str | None = None

    coverage_end: str | None = None

    dataset_ids: list[UUID] = Field(
        default_factory=list,
    )

    excluded_dataset_ids: list[UUID] = Field(
        default_factory=list,
    )

    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
    )


class DatasetFilterResponse(APIModel):
    investigation_id: UUID

    total_datasets: int

    selected_count: int

    datasets: list[dict[str, Any]]

    pagination: PaginationMetadata

    applied_filters: dict[str, Any]


# =========================================================
# Variable Filtering
# =========================================================

class VariableFilterRequest(APIModel):
    """
    Filter the variable catalog of a dataset.

    Designed around:
        filtering.variable_filter.filter_variable_catalog()
    """

    dataset_id: UUID

    name_contains: str | None = None

    keywords: list[str] = Field(default_factory=list)

    variable_types: list[str] = Field(default_factory=list)

    units: list[str] = Field(default_factory=list)

    minimum_unique_values: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_unique_values: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_missing_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    minimum_value: float | None = None

    maximum_value: float | None = None

    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
    )


class VariableFilterResponse(APIModel):
    dataset_id: UUID

    selected_count: int

    variables: list[dict[str, Any]]

    pagination: PaginationMetadata

    applied_filters: dict[str, Any]


# =========================================================
# Numerical Row Filtering
# =========================================================

class RowFilterRequest(APIModel):
    """
    Filter observations in a numerical dataset.

    Designed around:
        filtering.variable_filter.filter_dataframe_rows()
    """

    investigation_id: UUID

    dataset_id: UUID

    filters: FilterSet = Field(
        default_factory=FilterSet,
    )

    selected_columns: list[str] = Field(
        default_factory=list,
    )

    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
    )


class RowFilterResponse(APIModel):
    dataset_id: UUID

    source: DataSourceReference

    columns: list[str]

    rows: list[dict[str, Any]]

    original_row_count: int

    filtered_row_count: int

    pagination: PaginationMetadata

    applied_filters: FilterSet