from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd


DuplicatePolicy = Literal["keep", "mean", "error"]


def load_dataframe(data: pd.DataFrame | str | Path) -> pd.DataFrame:
    """
    Load a DataFrame directly or read a Parquet file.

    The input DataFrame is copied so that analysis never modifies
    the caller's original data.
    """
    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Time-series analysis accepts a DataFrame or a Parquet file."
        )

    return pd.read_parquet(path)


def json_safe(value: Any) -> Any:
    """Convert common NumPy and pandas values into JSON-compatible values."""

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        if not np.isfinite(value):
            return None
        return float(value)

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if value is pd.NA or value is pd.NaT:
        return None

    return value


def extract_unit(column_name: str) -> str | None:
    """
    Extract a unit explicitly written in parentheses or square brackets.

    Examples:
        "Temperature (°C)" -> "°C"
        "Elapsed time [min]" -> "min"
        "Temperature" -> None
    """
    import re

    match = re.search(r"[\[(]\s*([^\])]+?)\s*[\])]", column_name)

    if match:
        return match.group(1).strip()

    return None


def prepare_time_series(
    data: pd.DataFrame | str | Path,
    time_column: str,
    value_column: str,
    duplicate_time_policy: DuplicatePolicy = "keep",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Validate and prepare a time-series dataset.

    Time columns can be:
      - Datetime columns
      - Date/time strings
      - Numeric time values

    Duplicate timestamps can be:
      - keep: retain every observation
      - mean: average measurements sharing the same timestamp
      - error: reject the dataset
    """

    if duplicate_time_policy not in {"keep", "mean", "error"}:
        raise ValueError(
            "duplicate_time_policy must be 'keep', 'mean', or 'error'."
        )

    df = load_dataframe(data)

    if time_column not in df.columns:
        raise ValueError(f"Time column not found: {time_column}")

    if value_column not in df.columns:
        raise ValueError(f"Value column not found: {value_column}")

    if time_column == value_column:
        raise ValueError("Time and value columns must be different.")

    original_count = len(df)

    time_series = df[time_column]
    value_series = pd.to_numeric(df[value_column], errors="coerce")

    # Determine whether the time column is numeric or datetime-like.
    if pd.api.types.is_numeric_dtype(time_series):
        parsed_time = pd.to_numeric(time_series, errors="coerce")
        time_kind = "numeric"
        time_unit = extract_unit(time_column)

    elif pd.api.types.is_datetime64_any_dtype(time_series):
        parsed_time = pd.to_datetime(time_series, errors="coerce")
        time_kind = "datetime"
        time_unit = "second"

    else:
        # Text-based dates are parsed as datetimes.
        parsed_time = pd.to_datetime(
            time_series,
            errors="coerce",
            utc=True,
        )

        time_kind = "datetime"
        time_unit = "second"

    working = pd.DataFrame({
        "time": parsed_time,
        "value": value_series,
        "original_index": df.index,
    })

    # Exclude invalid timestamps, missing measurements, and infinities.
    numeric_values = working["value"].to_numpy(dtype=float)

    valid_mask = (
        working["time"].notna()
        & np.isfinite(numeric_values)
    )

    invalid_count = int((~valid_mask).sum())

    working = working.loc[valid_mask].copy()

    if working.empty:
        raise ValueError(
            "No valid observations remain after removing invalid "
            "timestamps and measurements."
        )

    # Sort observations chronologically.
    working = working.sort_values(
        "time",
        kind="stable",
    ).reset_index(drop=True)

    duplicate_count = int(
        working["time"].duplicated(keep=False).sum()
    )

    duplicate_timestamp_count = int(
        working["time"].duplicated().sum()
    )

    if duplicate_timestamp_count > 0:
        if duplicate_time_policy == "error":
            raise ValueError(
                "Duplicate timestamps were found. "
                "Choose 'keep' or 'mean' to continue."
            )

        if duplicate_time_policy == "mean":
            working = (
                working.groupby("time", as_index=False)
                .agg(value=("value", "mean"))
                .sort_values("time")
                .reset_index(drop=True)
            )

    metadata = {
        "original_observation_count": original_count,
        "valid_observation_count": len(working),
        "invalid_observation_count": invalid_count,
        "duplicate_observation_count": duplicate_count,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "duplicate_time_policy": duplicate_time_policy,
        "time_kind": time_kind,
        "time_unit": time_unit,
        "value_unit": extract_unit(value_column),
    }

    return working, metadata


def convert_time_axis(
    df: pd.DataFrame,
    time_kind: str,
) -> tuple[np.ndarray, list[Any], str]:
    """
    Convert the time column into numeric coordinates for calculations.

    Datetime values become elapsed seconds from the first observation.
    Numeric values retain their original scale.
    """

    if time_kind == "datetime":
        timestamps = pd.to_datetime(df["time"], utc=True)

        origin = timestamps.iloc[0]

        elapsed_seconds = (
            timestamps - origin
        ).dt.total_seconds().to_numpy(dtype=float)

        display_times = [
            timestamp.isoformat()
            for timestamp in timestamps
        ]

        return elapsed_seconds, display_times, "second"

    numeric_times = pd.to_numeric(
        df["time"],
        errors="coerce",
    ).to_numpy(dtype=float)

    display_times = [
        json_safe(value)
        for value in df["time"].tolist()
    ]

    return numeric_times, display_times, "numeric time unit"


def calculate_rate_of_change(
    x: np.ndarray,
    y: np.ndarray,
) -> list[dict[str, Any]]:
    """
    Calculate the rate of change between consecutive observations.

    Formula:
        rate = (current_value - previous_value)
               / (current_time - previous_time)

    Intervals with identical timestamps are excluded because
    division by zero would make the rate undefined.
    """

    results = []

    for index in range(1, len(x)):
        time_difference = x[index] - x[index - 1]

        if time_difference == 0:
            rate = None
        else:
            rate = (
                y[index] - y[index - 1]
            ) / time_difference

        results.append({
            "from_observation": index - 1,
            "to_observation": index,
            "time_difference": float(time_difference),
            "value_difference": float(
                y[index] - y[index - 1]
            ),
            "rate_of_change": (
                float(rate) if rate is not None else None
            ),
        })

    return results


def detect_local_extrema(
    times: list[Any],
    values: np.ndarray,
) -> dict[str, list[dict[str, Any]]]:
    """
    Detect strict local maxima and minima.

    A local maximum must be greater than both neighboring values.
    A local minimum must be lower than both neighboring values.

    The first and last observations are not considered local extrema.
    Flat plateaus are not classified as peaks or valleys.
    """

    peaks = []
    valleys = []

    for index in range(1, len(values) - 1):
        previous_value = values[index - 1]
        current_value = values[index]
        next_value = values[index + 1]

        if (
            current_value > previous_value
            and current_value > next_value
        ):
            peaks.append({
                "index": index,
                "time": times[index],
                "value": float(current_value),
            })

        elif (
            current_value < previous_value
            and current_value < next_value
        ):
            valleys.append({
                "index": index,
                "time": times[index],
                "value": float(current_value),
            })

    return {
        "local_maxima": peaks,
        "local_minima": valleys,
    }


def fit_linear_trend(
    x: np.ndarray,
    y: np.ndarray,
) -> dict[str, Any]:
    """
    Fit a simple linear trend:

        y = slope * x + intercept

    R² describes how well this linear model fits the observations.
    It does not establish causation or prove a scientific mechanism.
    """

    if len(x) < 2:
        return {
            "available": False,
            "reason": "At least two valid observations are required.",
        }

    if len(np.unique(x)) < 2:
        return {
            "available": False,
            "reason": "At least two distinct time values are required.",
        }

    slope, intercept = np.polyfit(x, y, 1)

    predicted = slope * x + intercept

    residual_sum = np.sum((y - predicted) ** 2)
    total_sum = np.sum((y - np.mean(y)) ** 2)

    if total_sum == 0:
        r_squared = 1.0 if residual_sum == 0 else None
    else:
        r_squared = 1 - (residual_sum / total_sum)

    if slope > 0:
        direction = "increasing"
    elif slope < 0:
        direction = "decreasing"
    else:
        direction = "constant"

    return {
        "available": True,
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": (
            float(r_squared)
            if r_squared is not None
            else None
        ),
        "direction": direction,
        "observation_count": len(x),
    }


def analyze_time_series(
    data: pd.DataFrame | str | Path,
    time_column: str,
    value_column: str,
    duplicate_time_policy: DuplicatePolicy = "keep",
) -> dict[str, Any]:
    """
    Run a complete basic time-series analysis.

    Returns:
      - Dataset metadata
      - Overall statistics
      - Minimum and maximum observations
      - Consecutive rates of change
      - Local maxima and minima
      - Linear trend
      - Prepared observations
    """

    df, metadata = prepare_time_series(
        data=data,
        time_column=time_column,
        value_column=value_column,
        duplicate_time_policy=duplicate_time_policy,
    )

    time_values, display_times, rate_time_unit = convert_time_axis(
        df,
        metadata["time_kind"],
    )

    if metadata["time_kind"] == "numeric":
        rate_time_unit = metadata["time_unit"] or "unspecified time unit"

    values = df["value"].to_numpy(dtype=float)

    minimum_index = int(np.argmin(values))
    maximum_index = int(np.argmax(values))

    # Overall changes.
    total_change = float(values[-1] - values[0])

    if values[0] != 0:
        percentage_change = float(
            (total_change / abs(values[0])) * 100
        )
    else:
        percentage_change = None

    rates = calculate_rate_of_change(
        time_values,
        values,
    )

    extrema = detect_local_extrema(
        display_times,
        values,
    )

    trend = fit_linear_trend(
        time_values,
        values,
    )

    observations = []

    for index in range(len(values)):
        observations.append({
            "index": index,
            "time": display_times[index],
            "value": float(values[index]),
        })

    result = {
        "analysis_type": "time_series",
        "dataset": {
            "time_column": time_column,
            "value_column": value_column,
            "observation_count": len(values),
            **metadata,
        },
        "units": {
            "time": metadata["time_unit"],
            "value": metadata["value_unit"],
            "rate_of_change": (
                f"{metadata['value_unit']} per {rate_time_unit}"
                if metadata["value_unit"]
                else f"value units per {rate_time_unit}"
            ),
        },
        "summary": {
            "minimum": {
                "time": display_times[minimum_index],
                "value": float(values[minimum_index]),
            },
            "maximum": {
                "time": display_times[maximum_index],
                "value": float(values[maximum_index]),
            },
            "first_value": float(values[0]),
            "last_value": float(values[-1]),
            "total_change": total_change,
            "percentage_change": percentage_change,
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "standard_deviation": (
                float(np.std(values, ddof=1))
                if len(values) > 1
                else None
            ),
        },
        "rate_of_change": rates,
        "extrema": extrema,
        "linear_trend": trend,
        "observations": observations,
        "limitations": [
            "A linear trend is a simplified description of the data.",
            "R-squared does not establish causation.",
            "Local extrema are based on neighboring observations only.",
            "Flat plateaus are not classified as local extrema.",
            "The analysis does not automatically account for "
            "experimental conditions or measurement uncertainty.",
        ],
    }

    return json_safe(result)


def save_time_series_analysis(
    result: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Save analysis results as a JSON file."""

    import json

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            json_safe(result),
            file,
            indent=4,
            ensure_ascii=False,
        )

    return path