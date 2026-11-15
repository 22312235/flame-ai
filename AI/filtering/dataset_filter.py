from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import math
import re


def _get_nested(data: dict, *paths: str, default=None):
    """
    Return the first available value from a list of possible
    top-level or dotted metadata paths.
    """
    for path in paths:
        current = data

        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break

            current = current[part]

        if current is not None:
            return current

    return default


def _as_list(value: Any) -> list:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    return [value]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _normalize_tags(value: Any) -> set[str]:
    return {
        _normalize_text(item)
        for item in _as_list(value)
        if _normalize_text(item)
    }


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    """
    Parse date/datetime values without assuming a timezone.

    ISO strings are supported, including strings ending in Z.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_dataset_variables(dataset: dict) -> list[dict]:
    """
    Read variables from common dataset/profile structures.

    Supported examples:
        "variables": [{"name": "temperature", ...}]
        "profile": {"variables": [...]}
        "profile": {"variables": {"temperature": {...}}}
    """
    variables = _get_nested(
        dataset,
        "variables",
        "profile.variables",
        "dataset_profile.variables",
        default=[],
    )

    if isinstance(variables, dict):
        result = []

        for name, metadata in variables.items():
            if isinstance(metadata, dict):
                result.append({"name": name, **metadata})
            else:
                result.append({"name": name, "type": metadata})

        return result

    if isinstance(variables, list):
        return [
            item for item in variables
            if isinstance(item, dict)
        ]

    return []


def _extract_variable_names(dataset: dict) -> set[str]:
    names = set()

    for variable in _extract_dataset_variables(dataset):
        name = variable.get("name") or variable.get("column")

        if name:
            names.add(_normalize_text(name))

    return names


def _extract_dataset_text(dataset: dict) -> str:
    """
    Build searchable text from descriptive dataset metadata.
    """
    fields = [
        "name",
        "dataset_name",
        "filename",
        "file_name",
        "description",
        "title",
        "original_filename",
        "file_metadata.filename",
        "metadata.description",
    ]

    values = []

    for field in fields:
        value = _get_nested(dataset, field)

        if value is not None:
            values.append(str(value))

    return " ".join(values).lower()


def _extract_size(dataset: dict) -> float | None:
    """
    Return file size in bytes when available.
    """
    value = _get_nested(
        dataset,
        "size_bytes",
        "file_size_bytes",
        "file_metadata.size_bytes",
        "metadata.size_bytes",
        "size",
    )

    return _to_number(value)


def _extract_row_count(dataset: dict) -> float | None:
    return _to_number(
        _get_nested(
            dataset,
            "row_count",
            "rows",
            "profile.overview.row_count",
            "profile.row_count",
            "dataset_profile.overview.row_count",
        )
    )


def _extract_column_count(dataset: dict) -> float | None:
    value = _get_nested(
        dataset,
        "column_count",
        "columns_count",
        "profile.overview.column_count",
        "profile.column_count",
        "dataset_profile.overview.column_count",
    )

    if value is None:
        variables = _extract_dataset_variables(dataset)

        if variables:
            return float(len(variables))

    return _to_number(value)


def _extract_missing_percentage(dataset: dict) -> float | None:
    """
    Extract an overall missing-value percentage when available.

    This is distinct from a variable's individual missing percentage.
    """
    value = _get_nested(
        dataset,
        "missing_percentage",
        "missing_percent",
        "quality.missing_percentage",
        "quality.missing_percent",
        "profile.data_quality.missing_percentage",
        "profile.data_quality.missing_percent",
        "dataset_profile.data_quality.missing_percentage",
    )

    return _to_number(value)


def _extract_date_coverage(dataset: dict) -> tuple[Any, Any]:
    """
    Extract the dataset's time coverage.

    Expected metadata examples:
        start_time / end_time
        date_range: {"start": "...", "end": "..."}
        time_coverage: {"start": "...", "end": "..."}
    """
    start = _get_nested(
        dataset,
        "start_time",
        "start_date",
        "date_range.start",
        "time_coverage.start",
        "profile.time_range.start",
    )

    end = _get_nested(
        dataset,
        "end_time",
        "end_date",
        "date_range.end",
        "time_coverage.end",
        "profile.time_range.end",
    )

    return start, end


def normalize_dataset_catalog(
    catalog: Any,
) -> list[dict]:
    """
    Accept either a list of dataset records or a catalog dictionary.

    Supported dictionary forms:
        {"datasets": [...]}
        {"items": [...]}
    """
    if isinstance(catalog, list):
        records = catalog

    elif isinstance(catalog, dict):
        records = catalog.get("datasets")

        if records is None:
            records = catalog.get("items")

        if records is None:
            raise ValueError(
                "Catalog dictionary must contain 'datasets' or 'items'."
            )

    else:
        raise TypeError(
            "Catalog must be a list or a dictionary containing datasets."
        )

    if not isinstance(records, list):
        raise TypeError("Dataset catalog entries must be a list.")

    normalized = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Dataset entry at index {index} must be a dictionary."
            )

        normalized.append(record)

    return normalized


def filter_dataset_catalog(
    catalog: Any,
    *,
    investigation_id: str,
    catalog_is_scoped: bool = False,

    # Text search
    name_contains: str | None = None,
    description_contains: str | None = None,
    keywords: Iterable[str] | None = None,

    # Dataset classification
    file_types: Iterable[str] | None = None,
    data_formats: Iterable[str] | None = None,
    categories: Iterable[str] | None = None,
    data_types: Iterable[str] | None = None,
    processing_statuses: Iterable[str] | None = None,

    # Tags and variables
    required_tags: Iterable[str] | None = None,
    required_variables: Iterable[str] | None = None,

    # Dataset size and dimensions
    minimum_size_bytes: float | None = None,
    maximum_size_bytes: float | None = None,
    minimum_rows: int | None = None,
    maximum_rows: int | None = None,
    minimum_columns: int | None = None,
    maximum_columns: int | None = None,

    # Data quality
    maximum_missing_percentage: float | None = None,

    # Time coverage
    coverage_start: str | datetime | date | None = None,
    coverage_end: str | datetime | date | None = None,

    # Explicit dataset selection
    dataset_ids: Iterable[str] | None = None,
    excluded_dataset_ids: Iterable[str] | None = None,
) -> dict:
    """
    Filter datasets within one investigation.

    Every supplied criterion is combined using AND logic.

    Scope protection:
      - Every dataset must have the requested investigation_id.
      - Records without an investigation_id are accepted only when
        catalog_is_scoped=True, meaning the caller has already loaded
        an authorized, investigation-specific catalog.

    This function does not perform authorization or database access.
    """

    if not investigation_id or not str(investigation_id).strip():
        raise ValueError("investigation_id is required.")

    investigation_id = str(investigation_id)

    records = normalize_dataset_catalog(catalog)

    requested_file_types = {
        _normalize_text(item)
        for item in _as_list(file_types)
    }

    requested_formats = {
        _normalize_text(item)
        for item in _as_list(data_formats)
    }

    requested_categories = {
        _normalize_text(item)
        for item in _as_list(categories)
    }

    requested_data_types = {
        _normalize_text(item)
        for item in _as_list(data_types)
    }

    requested_statuses = {
        _normalize_text(item)
        for item in _as_list(processing_statuses)
    }

    requested_tags = {
        _normalize_text(item)
        for item in _as_list(required_tags)
    }

    requested_variables = {
        _normalize_text(item)
        for item in _as_list(required_variables)
    }

    requested_keywords = {
        _normalize_text(item)
        for item in _as_list(keywords)
        if _normalize_text(item)
    }

    included_ids = {
        str(item)
        for item in _as_list(dataset_ids)
    }

    excluded_ids = {
        str(item)
        for item in _as_list(excluded_dataset_ids)
    }

    requested_start = _to_datetime(coverage_start)
    requested_end = _to_datetime(coverage_end)

    if coverage_start is not None and requested_start is None:
        raise ValueError("coverage_start is not a valid date or datetime.")

    if coverage_end is not None and requested_end is None:
        raise ValueError("coverage_end is not a valid date or datetime.")

    if (
        requested_start is not None
        and requested_end is not None
        and requested_start > requested_end
    ):
        raise ValueError("coverage_start must not be after coverage_end.")

    if minimum_size_bytes is not None and maximum_size_bytes is not None:
        if minimum_size_bytes > maximum_size_bytes:
            raise ValueError(
                "minimum_size_bytes cannot exceed maximum_size_bytes."
            )

    if minimum_rows is not None and maximum_rows is not None:
        if minimum_rows > maximum_rows:
            raise ValueError("minimum_rows cannot exceed maximum_rows.")

    if minimum_columns is not None and maximum_columns is not None:
        if minimum_columns > maximum_columns:
            raise ValueError(
                "minimum_columns cannot exceed maximum_columns."
            )

    if maximum_missing_percentage is not None:
        if not 0 <= maximum_missing_percentage <= 100:
            raise ValueError(
                "maximum_missing_percentage must be between 0 and 100."
            )

    selected = []
    rejected = []

    for dataset in records:
        dataset_id = _get_nested(
            dataset,
            "dataset_id",
            "id",
            "file_id",
        )

        record_investigation_id = dataset.get("investigation_id")

        rejection_reasons = []

        # Investigation scope validation
        if record_investigation_id is None:
            if not catalog_is_scoped:
                rejection_reasons.append(
                    "Dataset has no investigation_id; "
                    "catalog_is_scoped was not enabled."
                )
        elif str(record_investigation_id) != investigation_id:
            rejection_reasons.append(
                "Dataset belongs to a different investigation."
            )

        # Text criteria
        searchable_text = _extract_dataset_text(dataset)

        if name_contains:
            name = _normalize_text(
                _get_nested(
                    dataset,
                    "name",
                    "dataset_name",
                    "filename",
                    "file_name",
                )
            )

            if _normalize_text(name_contains) not in name:
                rejection_reasons.append(
                    f"Dataset name does not contain '{name_contains}'."
                )

        if description_contains:
            description = _normalize_text(
                _get_nested(
                    dataset,
                    "description",
                    "metadata.description",
                )
            )

            if _normalize_text(description_contains) not in description:
                rejection_reasons.append(
                    "Dataset description does not match the requested text."
                )

        if requested_keywords:
            if not any(keyword in searchable_text for keyword in requested_keywords):
                rejection_reasons.append(
                    "Dataset does not contain any requested keyword."
                )

        # File type
        actual_file_type = _normalize_text(
            _get_nested(
                dataset,
                "file_type",
                "extension",
                "file_metadata.extension",
            )
        )

        if actual_file_type:
            actual_file_type = actual_file_type.lstrip(".")

        if requested_file_types:
            normalized_requested_types = {
                item.lstrip(".")
                for item in requested_file_types
            }

            if actual_file_type not in normalized_requested_types:
                rejection_reasons.append(
                    f"File type '{actual_file_type or 'unknown'}' "
                    "does not match."
                )

        # Data format
        actual_format = _normalize_text(
            _get_nested(
                dataset,
                "data_format",
                "format",
                "profile.data_format",
            )
        )

        if requested_formats and actual_format not in requested_formats:
            rejection_reasons.append(
                f"Data format '{actual_format or 'unknown'}' does not match."
            )

        # Categories
        actual_category = _normalize_text(
            _get_nested(dataset, "category", "dataset_category")
        )

        if requested_categories and actual_category not in requested_categories:
            rejection_reasons.append(
                f"Dataset category '{actual_category or 'unknown'}' does not match."
            )

        # Data types
        actual_data_type = _normalize_text(
            _get_nested(
                dataset,
                "data_type",
                "dataset_type",
                "profile.data_type",
            )
        )

        if requested_data_types and actual_data_type not in requested_data_types:
            rejection_reasons.append(
                f"Dataset type '{actual_data_type or 'unknown'}' does not match."
            )

        # Processing status
        actual_status = _normalize_text(
            _get_nested(
                dataset,
                "processing_status",
                "status",
            )
        )

        if requested_statuses and actual_status not in requested_statuses:
            rejection_reasons.append(
                f"Processing status '{actual_status or 'unknown'}' does not match."
            )

        # Tags
        actual_tags = _normalize_tags(
            _get_nested(dataset, "tags", "metadata.tags", default=[])
        )

        missing_tags = requested_tags - actual_tags

        if missing_tags:
            rejection_reasons.append(
                f"Missing required tags: {sorted(missing_tags)}."
            )

        # Variables
        actual_variables = _extract_variable_names(dataset)

        missing_variables = requested_variables - actual_variables

        if missing_variables:
            rejection_reasons.append(
                f"Missing required variables: {sorted(missing_variables)}."
            )

        # Dataset IDs
        if included_ids and str(dataset_id) not in included_ids:
            rejection_reasons.append(
                "Dataset ID is not in the requested dataset ID list."
            )

        if str(dataset_id) in excluded_ids:
            rejection_reasons.append(
                "Dataset ID was explicitly excluded."
            )

        # File size
        size = _extract_size(dataset)

        if minimum_size_bytes is not None:
            if size is None or size < minimum_size_bytes:
                rejection_reasons.append(
                    "Dataset size is unknown or below the minimum."
                )

        if maximum_size_bytes is not None:
            if size is None or size > maximum_size_bytes:
                rejection_reasons.append(
                    "Dataset size is unknown or above the maximum."
                )

        # Row count
        row_count = _extract_row_count(dataset)

        if minimum_rows is not None:
            if row_count is None or row_count < minimum_rows:
                rejection_reasons.append(
                    "Row count is unknown or below the minimum."
                )

        if maximum_rows is not None:
            if row_count is None or row_count > maximum_rows:
                rejection_reasons.append(
                    "Row count is unknown or above the maximum."
                )

        # Column count
        column_count = _extract_column_count(dataset)

        if minimum_columns is not None:
            if column_count is None or column_count < minimum_columns:
                rejection_reasons.append(
                    "Column count is unknown or below the minimum."
                )

        if maximum_columns is not None:
            if column_count is None or column_count > maximum_columns:
                rejection_reasons.append(
                    "Column count is unknown or above the maximum."
                )

        # Missing-value percentage
        missing_percentage = _extract_missing_percentage(dataset)

        if maximum_missing_percentage is not None:
            if (
                missing_percentage is None
                or missing_percentage > maximum_missing_percentage
            ):
                rejection_reasons.append(
                    "Missing-value percentage is unknown or exceeds the maximum."
                )

        # Time coverage overlap
        if requested_start is not None or requested_end is not None:
            dataset_start_raw, dataset_end_raw = _extract_date_coverage(dataset)

            dataset_start = _to_datetime(dataset_start_raw)
            dataset_end = _to_datetime(dataset_end_raw)

            if dataset_start is None or dataset_end is None:
                rejection_reasons.append(
                    "Dataset time coverage is missing or invalid."
                )
            else:
                # The dataset must overlap the requested time interval.
                if requested_start is not None and dataset_end < requested_start:
                    rejection_reasons.append(
                        "Dataset ends before the requested time coverage."
                    )

                if requested_end is not None and dataset_start > requested_end:
                    rejection_reasons.append(
                        "Dataset starts after the requested time coverage."
                    )

        if rejection_reasons:
            rejected.append({
                "dataset_id": dataset_id,
                "dataset": dataset,
                "reasons": rejection_reasons,
            })
        else:
            selected.append({
                "dataset_id": dataset_id,
                "dataset": dataset,
            })

    applied_filters = {
        "investigation_id": investigation_id,
        "name_contains": name_contains,
        "description_contains": description_contains,
        "keywords": sorted(requested_keywords),
        "file_types": sorted(requested_file_types),
        "data_formats": sorted(requested_formats),
        "categories": sorted(requested_categories),
        "data_types": sorted(requested_data_types),
        "processing_statuses": sorted(requested_statuses),
        "required_tags": sorted(requested_tags),
        "required_variables": sorted(requested_variables),
        "minimum_size_bytes": minimum_size_bytes,
        "maximum_size_bytes": maximum_size_bytes,
        "minimum_rows": minimum_rows,
        "maximum_rows": maximum_rows,
        "minimum_columns": minimum_columns,
        "maximum_columns": maximum_columns,
        "maximum_missing_percentage": maximum_missing_percentage,
        "coverage_start": str(coverage_start) if coverage_start is not None else None,
        "coverage_end": str(coverage_end) if coverage_end is not None else None,
        "dataset_ids": sorted(included_ids),
        "excluded_dataset_ids": sorted(excluded_ids),
    }

    return {
        "investigation_id": investigation_id,
        "total_datasets": len(records),
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "selected": selected,
        "rejected": rejected,
        "applied_filters": applied_filters,
    }


def select_dataset_records(
    catalog: Any,
    dataset_ids: Iterable[str],
    *,
    investigation_id: str,
    catalog_is_scoped: bool = False,
) -> list[dict]:
    """
    Retrieve specific dataset records by ID from an investigation catalog.

    This is useful after the SI-assistant has identified relevant dataset IDs.
    """
    requested_ids = {str(item) for item in dataset_ids}

    if not requested_ids:
        return []

    records = normalize_dataset_catalog(catalog)

    selected = []

    for dataset in records:
        record_investigation_id = dataset.get("investigation_id")

        if record_investigation_id is None and not catalog_is_scoped:
            continue

        if (
            record_investigation_id is not None
            and str(record_investigation_id) != str(investigation_id)
        ):
            continue

        dataset_id = _get_nested(
            dataset,
            "dataset_id",
            "id",
            "file_id",
        )

        if str(dataset_id) in requested_ids:
            selected.append(dataset)

    return selected