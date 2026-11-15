from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import math


SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------

def json_safe(value: Any) -> Any:
    """Convert common Python and NumPy values into JSON-safe values."""

    if value is None:
        return None

    if isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (ValueError, TypeError):
            pass

    if isinstance(value, Mapping):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    return str(value)


def first_value(record: dict, *keys: str, default=None):
    """Return the first non-None value among possible metadata keys."""

    for key in keys:
        value = record.get(key)

        if value is not None:
            return value

    return default


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_extension(value: Any) -> str | None:
    if not value:
        return None

    extension = normalize_text(value).lower()

    if not extension:
        return None

    if not extension.startswith("."):
        extension = f".{extension}"

    return extension


def normalize_list(value: Any) -> list:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, (tuple, set)):
        return list(value)

    return [value]


def get_nested(record: dict, *paths: str, default=None):
    """Retrieve metadata from alternative nested paths."""

    for path in paths:
        current = record

        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break

            current = current[part]

        if current is not None:
            return current

    return default


def extract_variables(profile: Any) -> list[dict]:
    """
    Extract variable metadata from supported profiling structures.

    Supports:
        {"variables": [{"name": "temperature", ...}]}

        {"variables": {
            "temperature": {"type": "numeric", ...}
        }}
    """

    if not isinstance(profile, dict):
        return []

    variables = get_nested(
        profile,
        "variables",
        "profile.variables",
        "dataset_profile.variables",
        default=[],
    )

    if isinstance(variables, dict):
        result = []

        for name, metadata in variables.items():
            if isinstance(metadata, dict):
                result.append({
                    "name": str(name),
                    **{
                        key: value
                        for key, value in metadata.items()
                        if key != "name"
                    },
                })
            else:
                result.append({
                    "name": str(name),
                    "type": metadata,
                })

        return result

    if isinstance(variables, list):
        return [
            item
            for item in variables
            if isinstance(item, dict)
        ]

    return []


# ---------------------------------------------------------
# Dataset normalization
# ---------------------------------------------------------

def normalize_dataset_record(
    dataset: dict,
    investigation_id: str,
    profile: dict | None = None,
) -> dict:
    """
    Normalize a registered dataset into a consistent catalog record.

    The dataset must already have been associated with the supplied
    investigation by the ingestion/service layer.
    """

    if not isinstance(dataset, dict):
        raise TypeError("Dataset must be a dictionary.")

    dataset_id = first_value(
        dataset,
        "dataset_id",
        "id",
        "file_id",
    )

    if dataset_id is None:
        raise ValueError("Every dataset must have a dataset_id or id.")

    existing_investigation_id = dataset.get("investigation_id")

    if (
        existing_investigation_id is not None
        and str(existing_investigation_id) != str(investigation_id)
    ):
        raise ValueError(
            f"Dataset {dataset_id} belongs to investigation "
            f"{existing_investigation_id}, not {investigation_id}."
        )

    # Prefer an explicitly supplied profile, otherwise use
    # a profile already attached to the dataset.
    dataset_profile = profile

    if dataset_profile is None:
        dataset_profile = first_value(
            dataset,
            "profile",
            "dataset_profile",
            default={},
        )

    if not isinstance(dataset_profile, dict):
        dataset_profile = {}

    extension = normalize_extension(
        first_value(
            dataset,
            "extension",
            "file_type",
            default=get_nested(
                dataset,
                "file_metadata.extension",
            ),
        )
    )

    filename = first_value(
        dataset,
        "filename",
        "file_name",
        "original_filename",
        default=get_nested(dataset, "file_metadata.filename"),
    )

    dataset_name = first_value(
        dataset,
        "dataset_name",
        "name",
        default=filename or str(dataset_id),
    )

    file_size = first_value(
        dataset,
        "size_bytes",
        "file_size_bytes",
        default=get_nested(dataset, "file_metadata.size_bytes"),
    )

    file_category = first_value(
        dataset,
        "category",
        "file_category",
        default="unknown",
    )

    detected_type = first_value(
        dataset,
        "detected_type",
        "mime_type",
        default=None,
    )

    data_format = first_value(
        dataset,
        "data_format",
        "format",
        default=None,
    )

    processing_status = first_value(
        dataset,
        "processing_status",
        "status",
        default="pending",
    )

    variables = extract_variables(dataset_profile)

    # Some processors may store variables directly on the dataset.
    if not variables:
        variables = extract_variables(dataset)

    variable_names = [
        normalize_text(
            first_value(variable, "name", "column")
        )
        for variable in variables
    ]

    variable_names = [
        name for name in variable_names if name
    ]

    overview = get_nested(
        dataset_profile,
        "overview",
        default={},
    )

    if not isinstance(overview, dict):
        overview = {}

    row_count = first_value(
        dataset,
        "row_count",
        default=first_value(
            overview,
            "row_count",
            default=get_nested(dataset_profile, "row_count"),
        ),
    )

    column_count = first_value(
        dataset,
        "column_count",
        default=first_value(
            overview,
            "column_count",
            default=get_nested(dataset_profile, "column_count"),
        ),
    )

    if column_count is None and variables:
        column_count = len(variables)

    data_quality = get_nested(
        dataset_profile,
        "data_quality",
        default={},
    )

    if not isinstance(data_quality, dict):
        data_quality = {}

    missing_percentage = first_value(
        dataset,
        "missing_percentage",
        default=first_value(
            data_quality,
            "missing_percentage",
            "missing_percent",
        ),
    )

    # Preserve original source metadata without copying
    # the potentially large profile into multiple fields.
    source_metadata = first_value(
        dataset,
        "metadata",
        default={},
    )

    if not isinstance(source_metadata, dict):
        source_metadata = {}

    return {
        "dataset_id": str(dataset_id),
        "investigation_id": str(investigation_id),

        "name": normalize_text(dataset_name),
        "filename": normalize_text(filename) if filename else None,

        "extension": extension,
        "file_category": json_safe(file_category),
        "detected_type": json_safe(detected_type),
        "data_format": json_safe(data_format),

        "storage_path": first_value(
            dataset,
            "storage_path",
            "path",
            "original_path",
        ),

        "size_bytes": json_safe(file_size),

        "processing_status": normalize_text(processing_status).lower(),

        "row_count": json_safe(row_count),
        "column_count": json_safe(column_count),
        "missing_percentage": json_safe(missing_percentage),

        "variables": json_safe(variables),
        "variable_names": sorted(set(variable_names)),
        "file_type": extension.lstrip(".") if extension else None,

        "tags": json_safe(
            normalize_list(dataset.get("tags"))
        ),

        "description": first_value(
            dataset,
            "description",
            default=None,
        ),

        "source_metadata": json_safe(source_metadata),

        "profile_available": (
            bool(dataset_profile)
            or bool(dataset.get("profile_available"))
        ),

        "profile_version": first_value(
            dataset_profile,
            "profile_version",
            "version",
            default=dataset.get("profile_version"),
        ),
    }


# ---------------------------------------------------------
# Investigation-level aggregation
# ---------------------------------------------------------

def aggregate_variable_catalog(
    datasets: list[dict],
) -> dict:
    """
    Aggregate variables across datasets.

    Each variable retains the dataset IDs where it was found.
    """

    catalog = {}

    for dataset in datasets:
        dataset_id = dataset["dataset_id"]

        for variable in dataset["variables"]:
            name = normalize_text(
                first_value(variable, "name", "column")
            )

            if not name:
                continue

            key = name.lower()

            if key not in catalog:
                catalog[key] = {
                    "name": name,
                    "dataset_ids": [],
                    "types": [],
                    "units": [],
                    "definitions": [],
                }

            entry = catalog[key]

            if dataset_id not in entry["dataset_ids"]:
                entry["dataset_ids"].append(dataset_id)

            variable_type = first_value(
                variable,
                "type",
                "data_type",
                "inferred_type",
            )

            unit = first_value(
                variable,
                "unit",
                "units",
            )

            definition = first_value(
                variable,
                "description",
                "definition",
            )

            if variable_type is not None:
                entry["types"].append(str(variable_type))

            if unit is not None:
                entry["units"].append(str(unit))

            if definition is not None:
                entry["definitions"].append(str(definition))

    result = {}

    for key, variable in catalog.items():
        result[key] = {
            "name": variable["name"],
            "dataset_ids": sorted(variable["dataset_ids"]),
            "types": sorted(set(variable["types"])),
            "units": sorted(set(variable["units"])),
            "definitions": sorted(set(variable["definitions"])),
            "dataset_count": len(variable["dataset_ids"]),
        }

    return result


def aggregate_processing_status(
    datasets: list[dict],
) -> dict:
    """
    Summarize processing status without claiming that an investigation
    is complete merely because one dataset has been processed.
    """

    statuses = {}

    for dataset in datasets:
        status = dataset["processing_status"] or "unknown"

        statuses[status] = statuses.get(status, 0) + 1

    total = len(datasets)

    completed = statuses.get("completed", 0)

    failed = statuses.get("failed", 0)

    pending = statuses.get("pending", 0)

    processing = statuses.get("processing", 0)

    if total == 0:
        overall_status = "no_datasets"

    elif completed == total:
        overall_status = "completed"

    elif failed == total:
        overall_status = "failed"

    elif completed > 0:
        overall_status = "partially_completed"

    elif processing > 0:
        overall_status = "processing"

    elif pending == total:
        overall_status = "pending"

    else:
        overall_status = "incomplete"

    return {
        "overall_status": overall_status,
        "dataset_status_counts": statuses,
        "total_datasets": total,
        "completed_datasets": completed,
        "failed_datasets": failed,
        "pending_datasets": pending,
        "processing_datasets": processing,
    }


def aggregate_file_types(
    datasets: list[dict],
) -> dict:
    result = {}

    for dataset in datasets:
        extension = dataset["extension"] or "unknown"

        result[extension] = result.get(extension, 0) + 1

    return result


def aggregate_data_formats(
    datasets: list[dict],
) -> dict:
    result = {}

    for dataset in datasets:
        data_format = dataset["data_format"] or "unknown"

        result[data_format] = result.get(data_format, 0) + 1

    return result


def aggregate_dataset_statistics(
    datasets: list[dict],
) -> dict:
    """
    Aggregate known dataset dimensions.

    Unknown values are excluded from sums rather than treated as zero.
    """

    known_row_counts = [
        dataset["row_count"]
        for dataset in datasets
        if isinstance(dataset["row_count"], (int, float))
        and not isinstance(dataset["row_count"], bool)
        and math.isfinite(dataset["row_count"])
    ]

    known_sizes = [
        dataset["size_bytes"]
        for dataset in datasets
        if isinstance(dataset["size_bytes"], (int, float))
        and not isinstance(dataset["size_bytes"], bool)
        and math.isfinite(dataset["size_bytes"])
    ]

    return {
        "total_rows_known": sum(known_row_counts),
        "datasets_with_row_counts": len(known_row_counts),

        "total_size_bytes_known": sum(known_sizes),
        "datasets_with_size_information": len(known_sizes),

        "datasets_with_profiles": sum(
            1 for dataset in datasets
            if dataset["profile_available"]
        ),

        "datasets_with_variables": sum(
            1 for dataset in datasets
            if dataset["variable_names"]
        ),
    }


# ---------------------------------------------------------
# Main catalog builder
# ---------------------------------------------------------

def build_investigation_catalog(
    investigation: dict,
    datasets: list[dict],
    *,
    profiles_by_dataset: dict[str, dict] | None = None,
    generated_at: datetime | None = None,
) -> dict:
    """
    Build a searchable investigation catalog from investigation
    metadata and registered datasets.

    Parameters
    ----------
    investigation:
        Investigation-level metadata.

    datasets:
        Dataset registry records already associated with this
        investigation by the calling service.

    profiles_by_dataset:
        Optional mapping:
            {
                "DATA-001": {...profile...},
                "DATA-002": {...profile...}
            }

    generated_at:
        Optional timestamp for reproducible catalog generation.

    Returns
    -------
    dict
        JSON-safe investigation catalog.
    """

    if not isinstance(investigation, dict):
        raise TypeError("Investigation metadata must be a dictionary.")

    if not isinstance(datasets, list):
        raise TypeError("datasets must be a list.")

    investigation_id = first_value(
        investigation,
        "investigation_id",
        "id",
    )

    if investigation_id is None:
        raise ValueError("Investigation must have an ID.")

    investigation_id = str(investigation_id)

    profiles_by_dataset = profiles_by_dataset or {}

    normalized_datasets = []

    for dataset in datasets:
        if not isinstance(dataset, dict):
            raise TypeError("Every dataset must be a dictionary.")

        dataset_id = first_value(
            dataset,
            "dataset_id",
            "id",
            "file_id",
        )

        if dataset_id is None:
            raise ValueError("A dataset is missing its ID.")

        external_profile = profiles_by_dataset.get(str(dataset_id))

        normalized = normalize_dataset_record(
            dataset,
            investigation_id,
            profile=external_profile,
        )

        normalized_datasets.append(normalized)

    # Prevent accidental duplicate records.
    dataset_ids = [
        dataset["dataset_id"]
        for dataset in normalized_datasets
    ]

    if len(dataset_ids) != len(set(dataset_ids)):
        raise ValueError(
            "Duplicate dataset IDs found in the investigation."
        )

    # Aggregate metadata.
    variable_catalog = aggregate_variable_catalog(
        normalized_datasets
    )

    processing = aggregate_processing_status(
        normalized_datasets
    )

    file_types = aggregate_file_types(
        normalized_datasets
    )

    data_formats = aggregate_data_formats(
        normalized_datasets
    )

    dataset_statistics = aggregate_dataset_statistics(
        normalized_datasets
    )

    # Preserve original investigation information.
    title = first_value(
        investigation,
        "title",
        "name",
        "investigation_name",
        default=investigation_id,
    )

    description = first_value(
        investigation,
        "description",
        "summary",
        default="",
    )

    topics = normalize_list(
        first_value(
            investigation,
            "topics",
            "research_topics",
            "scientific_topics",
            default=[],
        )
    )

    tags = normalize_list(
        first_value(
            investigation,
            "tags",
            "keywords",
            default=[],
        )
    )

    scientific_objective = first_value(
        investigation,
        "scientific_objective",
        "objective",
        "research_question",
        default=None,
    )

    # Retain source dates as supplied.
    start_date = first_value(
        investigation,
        "start_date",
        "start_time",
        default=None,
    )

    end_date = first_value(
        investigation,
        "end_date",
        "end_time",
        default=None,
    )

    generated_at = generated_at or datetime.now(timezone.utc)

    catalog = {
        "schema_version": SCHEMA_VERSION,
        "topics": json_safe(topics),
        "tags": json_safe(tags),
        "file_types": sorted(file_types.keys()),
        "data_formats": sorted(data_formats.keys()),
        "dataset_count": len(normalized_datasets),
        "processing_status": processing["overall_status"],
        "variables": sorted(
            variable["name"]
            for variable in variable_catalog.values()
        ),

        "investigation_id": investigation_id,

        "metadata": {
            "title": normalize_text(title),
            "description": normalize_text(description),
            "scientific_objective": json_safe(scientific_objective),

            "topics": json_safe(topics),
            "tags": json_safe(tags),

            "start_date": json_safe(start_date),
            "end_date": json_safe(end_date),

            "source": json_safe(
                first_value(
                    investigation,
                    "source",
                    "source_name",
                    default="unknown",
                )
            ),

            "source_identifier": json_safe(
                first_value(
                    investigation,
                    "source_identifier",
                    "external_id",
                    "nasa_investigation_id",
                    default=None,
                )
            ),

            "original_metadata": json_safe(
                first_value(
                    investigation,
                    "metadata",
                    default={},
                )
            ),
        },

        "summary": {
            "dataset_count": len(normalized_datasets),

            "variable_count": len(variable_catalog),

            "variables": sorted(
                variable["name"]
                for variable in variable_catalog.values()
            ),

            "file_types": file_types,

            "data_formats": data_formats,

            "processing": processing,

            "statistics": dataset_statistics,
        },

        "variable_catalog": variable_catalog,

        "datasets": normalized_datasets,

        "provenance": {
            "builder": "investigation_catalog_builder",
            "schema_version": SCHEMA_VERSION,
            "generated_at": json_safe(generated_at),
            "source_investigation_id": investigation_id,
            "source_dataset_ids": sorted(dataset_ids),
            "profiled_dataset_ids": sorted(
                dataset["dataset_id"]
                for dataset in normalized_datasets
                if dataset["profile_available"]
            ),
        },
    }

    return json_safe(catalog)