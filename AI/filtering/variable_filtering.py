from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SUPPORTED_OPERATORS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "in",
    "not_in",
    "contains",
    "is_missing",
    "not_missing",
}


def load_dataframe(
    data: pd.DataFrame | str | Path,
) -> pd.DataFrame:
    """Load a DataFrame or Parquet file without modifying the original."""

    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Filtering accepts a DataFrame or Parquet file."
        )

    return pd.read_parquet(path)


def normalize_variable_catalog(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Normalize the variable section of a dataset profile.

    Supports either:
      - A dictionary mapping variable names to metadata.
      - A list of variable metadata dictionaries.

    This makes the filtering module less dependent on the exact
    representation used by profiling.py.
    """

    variables = profile.get("variables", [])

    normalized = []

    if isinstance(variables, dict):
        for name, metadata in variables.items():
            if not isinstance(metadata, dict):
                metadata = {}

            normalized.append({
                "name": name,
                **metadata,
            })

    elif isinstance(variables, list):
        for item in variables:
            if not isinstance(item, dict):
                continue

            name = (
                item.get("name")
                or item.get("column")
                or item.get("variable")
            )

            if name is None:
                continue

            normalized.append({
                **item,
                "name": name,
            })

    else:
        raise ValueError(
            "Profile variables must be a dictionary or list."
        )

    return normalized


def get_variable_type(
    variable: dict[str, Any],
) -> str | None:
    """Extract a variable's type from common profile representations."""

    return (
        variable.get("type")
        or variable.get("data_type")
        or variable.get("inferred_type")
    )


def get_variable_unit(
    variable: dict[str, Any],
) -> str | None:
    """Extract an explicitly recorded measurement unit."""

    return (
        variable.get("unit")
        or variable.get("units")
    )


def get_missing_percentage(
    variable: dict[str, Any],
) -> float | None:
    """Extract the missing-value percentage."""

    value = (
        variable.get("missing_percentage")
        if "missing_percentage" in variable
        else variable.get("missing_percent")
    )

    if value is not None:
        return float(value)

    missing_count = variable.get("missing_count")
    total_count = variable.get("count")

    if (
        missing_count is not None
        and total_count is not None
        and total_count > 0
    ):
        return float(missing_count / total_count * 100)

    return None


def get_numeric_statistics(
    variable: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract numerical statistics from different profile structures.

    Supports:
      variable["numeric_statistics"]
      variable["statistics"]
      variable["statistics"]["numeric"]
    """

    statistics = (
        variable.get("numeric_statistics")
        or variable.get("statistics")
        or {}
    )

    if not isinstance(statistics, dict):
        return {}

    nested = statistics.get("numeric")

    if isinstance(nested, dict):
        return nested

    return statistics


def filter_variable_catalog(
    profile: dict[str, Any],
    name_contains: str | None = None,
    keywords: list[str] | None = None,
    variable_types: list[str] | None = None,
    units: list[str] | None = None,
    minimum_unique_values: int | None = None,
    maximum_unique_values: int | None = None,
    maximum_missing_percentage: float | None = None,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
) -> dict[str, Any]:
    """
    Filter a dataset's variable catalog according to user specifications.

    All supplied criteria are combined using AND logic.

    Unit matching is exact. No automatic unit conversion is performed.
    """

    variables = normalize_variable_catalog(profile)

    if maximum_missing_percentage is not None:
        if not 0 <= maximum_missing_percentage <= 100:
            raise ValueError(
                "maximum_missing_percentage must be between 0 and 100."
            )

    if (
        minimum_unique_values is not None
        and maximum_unique_values is not None
        and minimum_unique_values > maximum_unique_values
    ):
        raise ValueError(
            "minimum_unique_values cannot exceed maximum_unique_values."
        )

    if (
        minimum_value is not None
        and maximum_value is not None
        and minimum_value > maximum_value
    ):
        raise ValueError(
            "minimum_value cannot exceed maximum_value."
        )

    selected = []
    rejected = []

    normalized_keywords = [
        keyword.casefold()
        for keyword in (keywords or [])
    ]

    normalized_types = {
        value.casefold()
        for value in (variable_types or [])
    }

    normalized_units = {
        value.casefold()
        for value in (units or [])
    }

    for variable in variables:
        name = str(variable["name"])
        normalized_name = name.casefold()

        reasons = []

        variable_type = get_variable_type(variable)
        variable_unit = get_variable_unit(variable)

        # Name matching.
        if name_contains:
            if name_contains.casefold() not in normalized_name:
                reasons.append("name does not match")

        # Keyword matching.
        if normalized_keywords:
            searchable_text = " ".join([
                normalized_name,
                str(variable.get("description", "")).casefold(),
            ])

            if not any(
                keyword in searchable_text
                for keyword in normalized_keywords
            ):
                reasons.append("no requested keyword found")

        # Type matching.
        if normalized_types:
            if (
                variable_type is None
                or str(variable_type).casefold() not in normalized_types
            ):
                reasons.append("variable type does not match")

        # Unit matching.
        if normalized_units:
            if (
                variable_unit is None
                or str(variable_unit).casefold() not in normalized_units
            ):
                reasons.append("unit does not match")

        # Unique-value count.
        unique_count = variable.get("unique_count")

        if unique_count is not None:
            if (
                minimum_unique_values is not None
                and unique_count < minimum_unique_values
            ):
                reasons.append("too few unique values")

            if (
                maximum_unique_values is not None
                and unique_count > maximum_unique_values
            ):
                reasons.append("too many unique values")

        elif (
            minimum_unique_values is not None
            or maximum_unique_values is not None
        ):
            reasons.append("unique-value count unavailable")

        # Missing-value percentage.
        missing_percentage = get_missing_percentage(variable)

        if maximum_missing_percentage is not None:
            if missing_percentage is None:
                reasons.append("missing-value percentage unavailable")
            elif missing_percentage > maximum_missing_percentage:
                reasons.append("too many missing values")

        # Numerical range.
        if minimum_value is not None or maximum_value is not None:
            statistics = get_numeric_statistics(variable)

            observed_minimum = statistics.get("min")
            observed_maximum = statistics.get("max")

            if (
                observed_minimum is None
                or observed_maximum is None
            ):
                reasons.append("numerical range unavailable")
            else:
                if (
                    minimum_value is not None
                    and observed_maximum < minimum_value
                ):
                    reasons.append(
                        "observed maximum is below requested minimum"
                    )

                if (
                    maximum_value is not None
                    and observed_minimum > maximum_value
                ):
                    reasons.append(
                        "observed minimum is above requested maximum"
                    )

        if reasons:
            rejected.append({
                "name": name,
                "reasons": reasons,
            })
        else:
            selected.append(variable)

    return {
        "selected_variables": selected,
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "rejected_variables": rejected,
        "filters_applied": {
            "name_contains": name_contains,
            "keywords": keywords,
            "variable_types": variable_types,
            "units": units,
            "minimum_unique_values": minimum_unique_values,
            "maximum_unique_values": maximum_unique_values,
            "maximum_missing_percentage": maximum_missing_percentage,
            "minimum_value": minimum_value,
            "maximum_value": maximum_value,
        },
    }


def select_dataframe_columns(
    data: pd.DataFrame | str | Path,
    columns: list[str],
) -> pd.DataFrame:
    """Select requested variables from a dataset."""

    df = load_dataframe(data)

    if not columns:
        raise ValueError("At least one column must be selected.")

    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Requested columns not found: {missing}"
        )

    return df[columns].copy()


def apply_condition(
    series: pd.Series,
    operator: str,
    value: Any = None,
) -> pd.Series:
    """Apply one supported filtering condition to a Series."""

    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(
            f"Unsupported operator: {operator}"
        )

    if operator == "is_missing":
        return series.isna()

    if operator == "not_missing":
        return series.notna()

    if operator in {"gt", "gte", "lt", "lte", "between"}:
        numeric = pd.to_numeric(
            series,
            errors="coerce",
        )

        if operator == "gt":
            return numeric > float(value)

        if operator == "gte":
            return numeric >= float(value)

        if operator == "lt":
            return numeric < float(value)

        if operator == "lte":
            return numeric <= float(value)

        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(
                "The between operator requires [minimum, maximum]."
            )

        lower, upper = map(float, value)

        if lower > upper:
            raise ValueError(
                "The lower bound cannot exceed the upper bound."
            )

        return numeric.between(lower, upper)

    if operator == "eq":
        return series == value

    if operator == "ne":
        return series != value

    if operator == "in":
        if not isinstance(value, (list, tuple, set)):
            raise ValueError(
                "The in operator requires a list of values."
            )

        return series.isin(value)

    if operator == "not_in":
        if not isinstance(value, (list, tuple, set)):
            raise ValueError(
                "The not_in operator requires a list of values."
            )

        return ~series.isin(value)

    if operator == "contains":
        return series.astype("string").str.contains(
            str(value),
            case=False,
            na=False,
            regex=False,
        )

    raise ValueError(f"Unsupported operator: {operator}")


def filter_dataframe_rows(
    data: pd.DataFrame | str | Path,
    conditions: list[dict[str, Any]],
    combine: str = "and",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Filter dataset rows using a list of conditions.

    Example:
        [
            {
                "column": "Temperature (C)",
                "operator": "gte",
                "value": 25
            },
            {
                "column": "Elapsed time (min)",
                "operator": "lte",
                "value": 30
            }
        ]

    combine:
        and -> every condition must match.
        or  -> at least one condition must match.
    """

    if combine not in {"and", "or"}:
        raise ValueError("combine must be 'and' or 'or'.")

    df = load_dataframe(data)

    original_count = len(df)

    if not conditions:
        return df, {
            "original_row_count": original_count,
            "filtered_row_count": original_count,
            "excluded_row_count": 0,
            "conditions": [],
            "combine": combine,
        }

    masks = []

    for condition in conditions:
        column = condition.get("column")
        operator = condition.get("operator")
        value = condition.get("value")

        if column not in df.columns:
            raise ValueError(
                f"Filtering column not found: {column}"
            )

        if operator is None:
            raise ValueError(
                f"Missing operator for column: {column}"
            )

        mask = apply_condition(
            df[column],
            operator,
            value,
        )

        masks.append(mask.fillna(False))

    combined_mask = masks[0]

    for mask in masks[1:]:
        if combine == "and":
            combined_mask = combined_mask & mask
        else:
            combined_mask = combined_mask | mask

    filtered = df.loc[combined_mask].copy()

    metadata = {
        "original_row_count": original_count,
        "filtered_row_count": len(filtered),
        "excluded_row_count": original_count - len(filtered),
        "conditions": conditions,
        "combine": combine,
    }

    return filtered, metadata


def filter_dataset(
    data: pd.DataFrame | str | Path,
    selected_columns: list[str],
    conditions: list[dict[str, Any]] | None = None,
    combine: str = "and",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Select variables and filter observations in one operation.

    Conditions are evaluated against the original dataset so that
    filtering columns do not need to appear in the final selection.
    """

    df = load_dataframe(data)

    filtered, filter_metadata = filter_dataframe_rows(
        data=df,
        conditions=conditions or [],
        combine=combine,
    )

    selected = select_dataframe_columns(
        data=filtered,
        columns=selected_columns,
    )

    metadata = {
        "selected_columns": selected_columns,
        **filter_metadata,
        "final_row_count": len(selected),
        "final_column_count": len(selected.columns),
    }

    return selected, metadata