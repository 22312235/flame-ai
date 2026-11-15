from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable
import math


def _as_list(value: Any) -> list:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return [value]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _normalize_set(value: Any) -> set[str]:
    return {
        _normalize_text(item)
        for item in _as_list(value)
        if _normalize_text(item)
    }


def _get_nested(data: dict, *paths: str, default=None):
    """Return the first non-None value found in the supplied paths."""

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


def normalize_investigation_catalog(catalog: Any) -> list[dict]:
    """
    Accept a list of investigations or a catalog dictionary.

    Supported dictionary forms:
        {"investigations": [...]}
        {"items": [...]}
    """

    if isinstance(catalog, list):
        records = catalog

    elif isinstance(catalog, dict):
        records = catalog.get("investigations")

        if records is None:
            records = catalog.get("items")

        if records is None:
            raise ValueError(
                "Catalog must contain 'investigations' or 'items'."
            )

    else:
        raise TypeError(
            "Catalog must be a list or a dictionary."
        )

    if not isinstance(records, list):
        raise TypeError("Investigation catalog entries must be a list.")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Investigation at index {index} must be a dictionary."
            )

    return records


def _extract_searchable_text(investigation: dict) -> str:
    """
    Collect descriptive metadata for keyword matching.
    """

    fields = [
        "title",
        "name",
        "investigation_name",
        "description",
        "summary",
        "scientific_objective",
        "objective",
        "research_question",
        "abstract",
        "metadata.title",
        "metadata.description",
        "metadata.objective",
    ]

    values = []

    for field in fields:
        value = _get_nested(investigation, field)

        if isinstance(value, str):
            values.append(value)

    return " ".join(values).lower()


def _extract_investigation_topics(investigation: dict) -> set[str]:
    values = _get_nested(
        investigation,
        "topics",
        "research_topics",
        "scientific_topics",
        "metadata.topics",
        default=[],
    )

    return _normalize_set(values)


def _extract_tags(investigation: dict) -> set[str]:
    values = _get_nested(
        investigation,
        "tags",
        "keywords",
        "metadata.tags",
        "metadata.keywords",
        default=[],
    )

    return _normalize_set(values)


def _extract_datasets(investigation: dict) -> list[dict]:
    datasets = _get_nested(
        investigation,
        "datasets",
        "files",
        "data_files",
        default=[],
    )

    if not isinstance(datasets, list):
        return []

    return [
        dataset for dataset in datasets
        if isinstance(dataset, dict)
    ]


def _extract_dataset_count(investigation: dict) -> float | None:
    explicit_count = _to_number(
        _get_nested(
            investigation,
            "dataset_count",
            "number_of_datasets",
            "metadata.dataset_count",
        )
    )

    if explicit_count is not None:
        return explicit_count

    datasets = _extract_datasets(investigation)

    if datasets:
        return float(len(datasets))

    return None


def _extract_variable_names(investigation: dict) -> set[str]:
    """
    Collect variables recorded directly on an investigation and
    variables recorded in its dataset metadata.
    """

    result = set()

    direct_variables = _get_nested(
        investigation,
        "variables",
        "measured_variables",
        "metadata.variables",
        default=[],
    )

    if isinstance(direct_variables, dict):
        result.update(
            _normalize_text(name)
            for name in direct_variables.keys()
        )

    else:
        for variable in _as_list(direct_variables):
            if isinstance(variable, dict):
                name = variable.get("name") or variable.get("column")
            else:
                name = variable

            if name:
                result.add(_normalize_text(name))

    for dataset in _extract_datasets(investigation):
        variables = _get_nested(
            dataset,
            "variables",
            "profile.variables",
            "dataset_profile.variables",
            default=[],
        )

        if isinstance(variables, dict):
            result.update(
                _normalize_text(name)
                for name in variables.keys()
            )

        else:
            for variable in _as_list(variables):
                if isinstance(variable, dict):
                    name = variable.get("name") or variable.get("column")
                else:
                    name = variable

                if name:
                    result.add(_normalize_text(name))

    return result


def _extract_file_types(investigation: dict) -> set[str]:
    result = set()

    direct_types = _get_nested(
        investigation,
        "file_types",
        "available_file_types",
        "metadata.file_types",
        default=[],
    )

    result.update(
        item.lstrip(".")
        for item in _normalize_set(direct_types)
    )

    for dataset in _extract_datasets(investigation):
        file_type = _get_nested(
            dataset,
            "file_type",
            "extension",
            "file_metadata.extension",
        )

        if file_type:
            result.add(
                _normalize_text(file_type).lstrip(".")
            )

    return result


def _extract_data_formats(investigation: dict) -> set[str]:
    result = set()

    direct_formats = _get_nested(
        investigation,
        "data_formats",
        "available_formats",
        "metadata.data_formats",
        default=[],
    )

    result.update(_normalize_set(direct_formats))

    for dataset in _extract_datasets(investigation):
        data_format = _get_nested(
            dataset,
            "data_format",
            "format",
            "profile.data_format",
        )

        if data_format:
            result.add(_normalize_text(data_format))

    return result


def _extract_processing_status(investigation: dict) -> str:
    return _normalize_text(
        _get_nested(
            investigation,
            "processing_status",
            "status",
            "metadata.processing_status",
            default="",
        )
    )


def _extract_dataset_processing_statuses(
    investigation: dict,
) -> set[str]:
    result = set()

    for dataset in _extract_datasets(investigation):
        status = _get_nested(dataset, "processing_status", "status")

        if status:
            result.add(_normalize_text(status))

    return result


def _extract_date_coverage(
    investigation: dict,
) -> tuple[Any, Any]:
    start = _get_nested(
        investigation,
        "start_time",
        "start_date",
        "date_range.start",
        "time_coverage.start",
        "metadata.start_date",
    )

    end = _get_nested(
        investigation,
        "end_time",
        "end_date",
        "date_range.end",
        "time_coverage.end",
        "metadata.end_date",
    )

    return start, end


def filter_investigation_catalog(
    catalog: Any,
    *,
    keywords: Iterable[str] | None = None,
    topics: Iterable[str] | None = None,
    required_tags: Iterable[str] | None = None,
    required_variables: Iterable[str] | None = None,
    file_types: Iterable[str] | None = None,
    data_formats: Iterable[str] | None = None,
    processing_statuses: Iterable[str] | None = None,

    minimum_dataset_count: int | None = None,
    maximum_dataset_count: int | None = None,

    investigation_ids: Iterable[str] | None = None,
    excluded_investigation_ids: Iterable[str] | None = None,

    coverage_start: str | datetime | date | None = None,
    coverage_end: str | datetime | date | None = None,

    require_all_keywords: bool = False,
) -> dict:
    """
    Filter an investigation catalog using descriptive and structural
    metadata.

    All supplied filter categories are combined using AND logic.

    Within a category:
      - keywords use OR by default, or AND when require_all_keywords=True.
      - required topics, tags, variables, file types, and formats
        require all requested values to be present.

    Missing metadata does not satisfy a requested filter.

    This function does not perform authorization or database access.
    """

    records = normalize_investigation_catalog(catalog)

    requested_keywords = _normalize_set(keywords)
    requested_topics = _normalize_set(topics)
    requested_tags = _normalize_set(required_tags)
    requested_variables = _normalize_set(required_variables)

    requested_file_types = {
        item.lstrip(".")
        for item in _normalize_set(file_types)
    }

    requested_formats = _normalize_set(data_formats)
    requested_statuses = _normalize_set(processing_statuses)

    included_ids = {
        str(item)
        for item in _as_list(investigation_ids)
    }

    excluded_ids = {
        str(item)
        for item in _as_list(excluded_investigation_ids)
    }

    if (
        minimum_dataset_count is not None
        and minimum_dataset_count < 0
    ):
        raise ValueError("minimum_dataset_count cannot be negative.")

    if (
        maximum_dataset_count is not None
        and maximum_dataset_count < 0
    ):
        raise ValueError("maximum_dataset_count cannot be negative.")

    if (
        minimum_dataset_count is not None
        and maximum_dataset_count is not None
        and minimum_dataset_count > maximum_dataset_count
    ):
        raise ValueError(
            "minimum_dataset_count cannot exceed maximum_dataset_count."
        )

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

    selected = []
    rejected = []

    for investigation in records:
        investigation_id = _get_nested(
            investigation,
            "investigation_id",
            "id",
        )

        investigation_id = (
            str(investigation_id)
            if investigation_id is not None
            else None
        )

        reasons = []

        if investigation_id is None:
            reasons.append("Investigation has no identifiable ID.")

        elif included_ids and investigation_id not in included_ids:
            reasons.append(
                "Investigation ID is not in the requested ID list."
            )

        if investigation_id in excluded_ids:
            reasons.append("Investigation was explicitly excluded.")

        # Search descriptive metadata
        searchable_text = _extract_searchable_text(investigation)

        if requested_keywords:
            matching_keywords = {
                keyword
                for keyword in requested_keywords
                if keyword in searchable_text
            }

            if require_all_keywords:
                if matching_keywords != requested_keywords:
                    missing = requested_keywords - matching_keywords
                    reasons.append(
                        f"Missing keywords: {sorted(missing)}."
                    )

            elif not matching_keywords:
                reasons.append(
                    "No requested keyword was found in the investigation "
                    "description or title."
                )

        # Scientific topics
        actual_topics = _extract_investigation_topics(investigation)
        missing_topics = requested_topics - actual_topics

        if missing_topics:
            reasons.append(
                f"Missing research topics: {sorted(missing_topics)}."
            )

        # Tags
        actual_tags = _extract_tags(investigation)
        missing_tags = requested_tags - actual_tags

        if missing_tags:
            reasons.append(
                f"Missing required tags: {sorted(missing_tags)}."
            )

        # Variables
        actual_variables = _extract_variable_names(investigation)
        missing_variables = requested_variables - actual_variables

        if missing_variables:
            reasons.append(
                f"Missing required variables: {sorted(missing_variables)}."
            )

        # File types
        actual_file_types = _extract_file_types(investigation)
        missing_file_types = requested_file_types - actual_file_types

        if missing_file_types:
            reasons.append(
                f"Missing file types: {sorted(missing_file_types)}."
            )

        # Data formats
        actual_formats = _extract_data_formats(investigation)
        missing_formats = requested_formats - actual_formats

        if missing_formats:
            reasons.append(
                f"Missing data formats: {sorted(missing_formats)}."
            )

        # Processing status
        actual_status = _extract_processing_status(investigation)
        dataset_statuses = _extract_dataset_processing_statuses(
            investigation
        )

        if requested_statuses:
            available_statuses = set(dataset_statuses)

            if actual_status:
                available_statuses.add(actual_status)

            if not requested_statuses.intersection(available_statuses):
                reasons.append(
                    "Investigation and its datasets do not have "
                    "a requested processing status."
                )

        # Dataset count
        dataset_count = _extract_dataset_count(investigation)

        if minimum_dataset_count is not None:
            if (
                dataset_count is None
                or dataset_count < minimum_dataset_count
            ):
                reasons.append(
                    "Dataset count is unknown or below the minimum."
                )

        if maximum_dataset_count is not None:
            if (
                dataset_count is None
                or dataset_count > maximum_dataset_count
            ):
                reasons.append(
                    "Dataset count is unknown or above the maximum."
                )

        # Time coverage overlap
        if requested_start is not None or requested_end is not None:
            start_raw, end_raw = _extract_date_coverage(investigation)

            actual_start = _to_datetime(start_raw)
            actual_end = _to_datetime(end_raw)

            if actual_start is None or actual_end is None:
                reasons.append(
                    "Investigation time coverage is missing or invalid."
                )

            else:
                if (
                    requested_start is not None
                    and actual_end < requested_start
                ):
                    reasons.append(
                        "Investigation ends before the requested time range."
                    )

                if (
                    requested_end is not None
                    and actual_start > requested_end
                ):
                    reasons.append(
                        "Investigation starts after the requested time range."
                    )

        if reasons:
            rejected.append({
                "investigation_id": investigation_id,
                "investigation": investigation,
                "reasons": reasons,
            })

        else:
            selected.append({
                "investigation_id": investigation_id,
                "investigation": investigation,
            })

    return {
        "total_investigations": len(records),
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "selected": selected,
        "rejected": rejected,
        "applied_filters": {
            "keywords": sorted(requested_keywords),
            "require_all_keywords": require_all_keywords,
            "topics": sorted(requested_topics),
            "required_tags": sorted(requested_tags),
            "required_variables": sorted(requested_variables),
            "file_types": sorted(requested_file_types),
            "data_formats": sorted(requested_formats),
            "processing_statuses": sorted(requested_statuses),
            "minimum_dataset_count": minimum_dataset_count,
            "maximum_dataset_count": maximum_dataset_count,
            "investigation_ids": sorted(included_ids),
            "excluded_investigation_ids": sorted(excluded_ids),
            "coverage_start": (
                str(coverage_start)
                if coverage_start is not None
                else None
            ),
            "coverage_end": (
                str(coverage_end)
                if coverage_end is not None
                else None
            ),
        },
    }


def select_investigation_records(
    catalog: Any,
    investigation_ids: Iterable[str],
) -> list[dict]:
    """
    Retrieve investigation records by ID from an already-authorized catalog.
    """

    requested_ids = {
        str(item)
        for item in investigation_ids
    }

    if not requested_ids:
        return []

    records = normalize_investigation_catalog(catalog)

    return [
        record
        for record in records
        if str(
            _get_nested(record, "investigation_id", "id")
        ) in requested_ids
    ]