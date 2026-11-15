from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# A column must have at least this proportion of parseable values
# before we classify it as a datetime candidate.
DATETIME_THRESHOLD = 0.95

# A value outside these bounds is flagged as a potential outlier.
IQR_MULTIPLIER = 1.5

# Limit the number of example outlier values stored in the profile.
MAX_OUTLIER_EXAMPLES = 10


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def json_safe(value: Any) -> Any:
    """Convert pandas and NumPy values into JSON-compatible values."""

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    if isinstance(value, np.generic):
        return json_safe(value.item())

    if isinstance(value, float) and not np.isfinite(value):
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def extract_unit(column_name: str) -> str | None:
    """
    Extract an explicitly declared unit from a column name.

    Examples:
        Temperature (K) -> K
        Diameter [mm] -> mm

    Units are never inferred.
    """

    match = re.search(
        r"[\(\[]\s*([^\)\]]+)\s*[\)\]]",
        column_name,
    )

    return match.group(1).strip() if match else None


def infer_variable_type(series: pd.Series) -> str:
    """Classify a variable without aggressively converting its values."""

    non_null = series.dropna()

    if non_null.empty:
        return "empty"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Try datetime detection only for non-numeric data.
    parsed = pd.to_datetime(
        non_null,
        errors="coerce",
        format="mixed",
    )

    success_rate = parsed.notna().sum() / len(non_null)

    if success_rate >= DATETIME_THRESHOLD:
        return "datetime"

    return "text"


# ---------------------------------------------------------
# Numeric analysis
# ---------------------------------------------------------

def profile_numeric_column(series: pd.Series) -> dict[str, Any]:
    """
    Calculate descriptive statistics and identify potential outliers.

    Outliers are flagged, not removed.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    ).replace([np.inf, -np.inf], np.nan).dropna()

    if numeric.empty:
        return {
            "statistics": {},
            "distribution": {},
            "outliers": {
                "method": "IQR",
                "count": 0,
                "percentage": 0.0,
                "lower_bound": None,
                "upper_bound": None,
                "examples": [],
            },
        }

    q1 = numeric.quantile(0.25)
    median = numeric.quantile(0.50)
    q3 = numeric.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - IQR_MULTIPLIER * iqr
    upper_bound = q3 + IQR_MULTIPLIER * iqr

    outlier_mask = (
        (numeric < lower_bound)
        | (numeric > upper_bound)
    )

    outliers = numeric[outlier_mask]

    statistics = {
        "count": int(numeric.count()),
        "mean": numeric.mean(),
        "median": median,
        "standard_deviation": numeric.std(),
        "variance": numeric.var(),
        "minimum": numeric.min(),
        "maximum": numeric.max(),
        "range": numeric.max() - numeric.min(),
        "sum": numeric.sum(),
    }

    distribution = {
        "minimum": numeric.min(),
        "p05": numeric.quantile(0.05),
        "p25": q1,
        "p50": median,
        "p75": q3,
        "p95": numeric.quantile(0.95),
        "maximum": numeric.max(),
    }

    outlier_percentage = (
        len(outliers) / len(numeric) * 100
    )

    outlier_info = {
        "method": "IQR",
        "multiplier": IQR_MULTIPLIER,
        "count": int(len(outliers)),
        "percentage": round(outlier_percentage, 2),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "examples": outliers.head(
            MAX_OUTLIER_EXAMPLES
        ).tolist(),
    }

    return {
        "statistics": json_safe(statistics),
        "distribution": json_safe(distribution),
        "outliers": json_safe(outlier_info),
    }


# ---------------------------------------------------------
# Individual variable profiling
# ---------------------------------------------------------

def profile_variable(
    name: str,
    series: pd.Series,
) -> dict[str, Any]:

    variable_type = infer_variable_type(series)

    total_count = len(series)
    missing_count = int(series.isna().sum())
    non_null = series.dropna()

    missing_percentage = (
        missing_count / total_count * 100
        if total_count > 0
        else 0.0
    )

    result = {
        "name": name,
        "type": variable_type,
        "unit": extract_unit(name),
        "total_count": total_count,
        "non_null_count": int(len(non_null)),
        "missing_count": missing_count,
        "missing_percentage": round(
            missing_percentage,
            2,
        ),
        "unique_count": int(non_null.nunique()),
        "sample_values": [
            json_safe(value)
            for value in non_null.head(5).tolist()
        ],
    }

    if variable_type == "numeric":
        result.update(
            profile_numeric_column(series)
        )

    elif variable_type == "datetime":
        parsed = pd.to_datetime(
            non_null,
            errors="coerce",
            format="mixed",
        ).dropna()

        result["datetime_range"] = {
            "earliest": json_safe(parsed.min()),
            "latest": json_safe(parsed.max()),
        }

    elif variable_type == "text":
        result["most_common_values"] = json_safe(
            non_null.value_counts().head(5).to_dict()
        )

    return result


# ---------------------------------------------------------
# Time-column detection
# ---------------------------------------------------------

def detect_time_columns(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Identify potential time columns using names and data types.

    This is a candidate detector, not a scientific assertion.
    """

    candidates = []

    time_keywords = (
        "time",
        "timestamp",
        "datetime",
        "date",
        "elapsed",
    )

    for column in dataframe.columns:
        name = str(column)
        normalized_name = name.lower()

        variable_type = infer_variable_type(
            dataframe[column]
        )

        name_matches = any(
            keyword in normalized_name
            for keyword in time_keywords
        )

        if name_matches or variable_type == "datetime":
            candidates.append({
                "column": name,
                "type": variable_type,
                "reason": (
                    "column_name"
                    if name_matches
                    else "datetime_values"
                ),
            })

    return candidates


# ---------------------------------------------------------
# Dataset profiling
# ---------------------------------------------------------

def profile_dataset(
    dataframe: pd.DataFrame,
    dataset_id: str,
    source_file: str | None = None,
) -> dict[str, Any]:
    """
    Generate a reusable analytical profile for a dataset.

    The input dataframe is never modified.
    """

    df = dataframe.copy()

    variables = [
        profile_variable(
            name=str(column),
            series=df[column],
        )
        for column in df.columns
    ]

    numeric_columns = [
        variable["name"]
        for variable in variables
        if variable["type"] == "numeric"
    ]

    datetime_columns = [
        variable["name"]
        for variable in variables
        if variable["type"] == "datetime"
    ]

    empty_columns = [
        variable["name"]
        for variable in variables
        if variable["type"] == "empty"
    ]

    duplicate_rows = int(df.duplicated().sum())

    fully_empty_rows = int(
        df.isna().all(axis=1).sum()
    )

    missing_cells = int(df.isna().sum().sum())

    total_cells = int(df.shape[0] * df.shape[1])

    missing_cell_percentage = (
        missing_cells / total_cells * 100
        if total_cells > 0
        else 0.0
    )

    warnings = []

    if duplicate_rows > 0:
        warnings.append(
            f"{duplicate_rows} duplicate rows detected."
        )

    if empty_columns:
        warnings.append(
            f"{len(empty_columns)} entirely empty columns detected."
        )

    if missing_cells > 0:
        warnings.append(
            f"{missing_cells} missing cells detected."
        )

    result = {
        "dataset_id": dataset_id,
        "source_file": source_file,
        "profile_type": "scientific_dataset_profile",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "overview": {
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "memory_usage_bytes": int(
                df.memory_usage(
                    index=True,
                    deep=True,
                ).sum()
            ),
            "duplicate_rows": duplicate_rows,
            "fully_empty_rows": fully_empty_rows,
        },

        "data_quality": {
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "missing_cell_percentage": round(
                missing_cell_percentage,
                2,
            ),
            "empty_columns": empty_columns,
        },

        "variable_summary": {
            "numeric": numeric_columns,
            "datetime": datetime_columns,
            "total_numeric_variables": len(numeric_columns),
            "total_datetime_variables": len(datetime_columns),
        },

        "time_columns": detect_time_columns(df),

        "variables": variables,

        "warnings": warnings,

        "limitations": [
            "Potential outliers are identified statistically, not scientifically.",
            "Units are extracted only when explicitly declared in column names.",
            "Time columns are candidates and require validation.",
            "No causal relationships or scientific conclusions are inferred.",
        ],
    }

    return json_safe(result)


# ---------------------------------------------------------
# Parquet input
# ---------------------------------------------------------

def profile_parquet(
    parquet_path: str | Path,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Load a processed Parquet dataset and profile it."""

    parquet_path = Path(parquet_path)

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {parquet_path}"
        )

    dataframe = pd.read_parquet(parquet_path)

    return profile_dataset(
        dataframe=dataframe,
        dataset_id=dataset_id or parquet_path.stem,
        source_file=parquet_path.name,
    )


# ---------------------------------------------------------
# JSON export
# ---------------------------------------------------------

def save_profile(
    profile: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Save a dataset profile as JSON."""

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            json_safe(profile),
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

    return output_path