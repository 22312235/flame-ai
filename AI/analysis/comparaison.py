from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scipy.stats import mannwhitneyu, ttest_ind


def load_dataframe(data: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Load a DataFrame or Parquet file without modifying the original."""

    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Comparison accepts a DataFrame or Parquet file."
        )

    return pd.read_parquet(path)


def json_safe(value: Any) -> Any:
    """Convert NumPy and pandas values into JSON-compatible values."""

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

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


def prepare_numeric_values(
    data: pd.Series,
) -> tuple[np.ndarray, int]:
    """Extract finite numerical observations."""

    numeric = pd.to_numeric(
        data,
        errors="coerce",
    )

    values = numeric.to_numpy(dtype=float)

    valid = values[np.isfinite(values)]

    excluded_count = len(values) - len(valid)

    return valid, excluded_count


def describe_group(
    values: np.ndarray,
) -> dict[str, Any]:
    """Calculate descriptive statistics for one group."""

    if len(values) == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "minimum": None,
            "maximum": None,
            "range": None,
        }

    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "standard_deviation": (
            float(np.std(values, ddof=1))
            if len(values) > 1
            else None
        ),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "range": float(np.max(values) - np.min(values)),
    }


def check_comparability(
    metadata_a: dict[str, Any] | None = None,
    metadata_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compare supplied metadata for two datasets.

    Recognized fields:
      - unit
      - variable_definition
      - measurement_method
      - experimental_conditions
      - population
      - collection_protocol

    Only explicitly supplied fields are checked.
    Missing metadata is reported as unverified, not assumed equivalent.
    """

    metadata_a = metadata_a or {}
    metadata_b = metadata_b or {}

    fields = [
        "unit",
        "variable_definition",
        "measurement_method",
        "experimental_conditions",
        "population",
        "collection_protocol",
    ]

    checks = {}

    for field in fields:
        value_a = metadata_a.get(field)
        value_b = metadata_b.get(field)

        if value_a is None or value_b is None:
            status = "unverified"
        elif value_a == value_b:
            status = "matching"
        else:
            status = "different"

        checks[field] = {
            "dataset_a": value_a,
            "dataset_b": value_b,
            "status": status,
        }

    differences = [
        field
        for field, check in checks.items()
        if check["status"] == "different"
    ]

    unverified = [
        field
        for field, check in checks.items()
        if check["status"] == "unverified"
    ]

    return {
        "checks": checks,
        "different_fields": differences,
        "unverified_fields": unverified,
        "all_supplied_fields_match": (
            len(differences) == 0
            and len(unverified) == 0
        ),
        "warning": (
            "Matching metadata does not by itself prove that two "
            "datasets are scientifically comparable."
        ),
    }


def calculate_effect_size(
    values_a: np.ndarray,
    values_b: np.ndarray,
) -> float | None:
    """
    Calculate Cohen's d using the pooled standard deviation.

    Returns None when the pooled standard deviation is zero
    or cannot be calculated.
    """

    if len(values_a) < 2 or len(values_b) < 2:
        return None

    variance_a = np.var(values_a, ddof=1)
    variance_b = np.var(values_b, ddof=1)

    degrees_of_freedom = (
        len(values_a) + len(values_b) - 2
    )

    pooled_variance = (
        (len(values_a) - 1) * variance_a
        + (len(values_b) - 1) * variance_b
    ) / degrees_of_freedom

    if pooled_variance <= 0:
        return None

    pooled_std = np.sqrt(pooled_variance)

    return float(
        (np.mean(values_a) - np.mean(values_b))
        / pooled_std
    )


def compare_two_groups(
    values_a: np.ndarray,
    values_b: np.ndarray,
    label_a: str,
    label_b: str,
    minimum_samples: int = 2,
) -> dict[str, Any]:
    """
    Compare two independent groups.

    Statistical tests:
      - Welch's t-test: difference in group means.
      - Mann-Whitney U: difference in distributions/ranks.

    Both tests assume independent observations.
    """

    if len(values_a) < minimum_samples:
        raise ValueError(
            f"Group '{label_a}' has fewer than "
            f"{minimum_samples} valid observations."
        )

    if len(values_b) < minimum_samples:
        raise ValueError(
            f"Group '{label_b}' has fewer than "
            f"{minimum_samples} valid observations."
        )

    mean_a = float(np.mean(values_a))
    mean_b = float(np.mean(values_b))

    absolute_difference = mean_a - mean_b

    percentage_difference = (
        absolute_difference / abs(mean_b) * 100
        if mean_b != 0
        else None
    )

    t_test = ttest_ind(
        values_a,
        values_b,
        equal_var=False,
    )

    mann_whitney = mannwhitneyu(
        values_a,
        values_b,
        alternative="two-sided",
    )

    return {
        "groups": {
            label_a: describe_group(values_a),
            label_b: describe_group(values_b),
        },
        "mean_difference": {
            "definition": f"{label_a} minus {label_b}",
            "absolute": absolute_difference,
            "percentage": percentage_difference,
        },
        "effect_size": {
            "name": "Cohen's d",
            "value": calculate_effect_size(
                values_a,
                values_b,
            ),
        },
        "statistical_tests": {
            "welch_t_test": {
                "statistic": float(t_test.statistic),
                "p_value": float(t_test.pvalue),
                "alpha": 0.05,
                "significant_at_alpha": bool(
                    t_test.pvalue < 0.05
                ),
            },
            "mann_whitney_u": {
                "statistic": float(mann_whitney.statistic),
                "p_value": float(mann_whitney.pvalue),
                "alpha": 0.05,
                "significant_at_alpha": bool(
                    mann_whitney.pvalue < 0.05
                ),
            },
        },
    }


def compare_groups(
    data: pd.DataFrame | str | Path,
    group_column: str,
    value_column: str,
    groups: list[Any] | None = None,
    minimum_samples: int = 2,
) -> dict[str, Any]:
    """
    Compare numerical measurements across groups in one dataset.

    If groups is omitted, all available groups are included.

    Descriptive statistics are calculated for every group.
    Inferential statistical tests are performed only when exactly
    two groups are selected.
    """

    df = load_dataframe(data)

    if group_column not in df.columns:
        raise ValueError(
            f"Group column not found: {group_column}"
        )

    if value_column not in df.columns:
        raise ValueError(
            f"Value column not found: {value_column}"
        )

    if group_column == value_column:
        raise ValueError(
            "Group and measurement columns must be different."
        )

    if minimum_samples < 2:
        raise ValueError("minimum_samples must be at least 2.")

    df = df[[group_column, value_column]].copy()

    df[value_column] = pd.to_numeric(
        df[value_column],
        errors="coerce",
    )

    df[value_column] = df[value_column].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    excluded_count = int(
        df[group_column].isna().sum()
        + (
            df[group_column].notna()
            & df[value_column].isna()
        ).sum()
    )

    df = df.dropna(
        subset=[group_column, value_column]
    )

    if groups is None:
        selected_groups = df[group_column].drop_duplicates().tolist()
    else:
        selected_groups = groups

    if len(selected_groups) < 2:
        raise ValueError(
            "At least two groups must be selected."
        )

    group_values = {}

    for group in selected_groups:
        values, _ = prepare_numeric_values(
            df.loc[
                df[group_column] == group,
                value_column,
            ]
        )

        if len(values) == 0:
            raise ValueError(
                f"No valid numerical observations for group '{group}'."
            )

        group_values[str(group)] = values

    descriptions = {
        group: describe_group(values)
        for group, values in group_values.items()
    }

    result = {
        "analysis_type": "group_comparison",
        "group_column": group_column,
        "value_column": value_column,
        "selected_groups": list(group_values.keys()),
        "excluded_row_count": excluded_count,
        "group_statistics": descriptions,
        "pairwise_comparison": None,
        "limitations": [
            "Groups must represent meaningful experimental categories.",
            "The statistical tests assume independent observations.",
            "A statistically significant difference does not establish causation.",
            "Confounding variables may explain observed differences.",
            "Comparing multiple groups requires correction for multiple testing "
            "if many pairwise tests are performed.",
        ],
    }

    if len(group_values) == 2:
        labels = list(group_values.keys())

        result["pairwise_comparison"] = compare_two_groups(
            values_a=group_values[labels[0]],
            values_b=group_values[labels[1]],
            label_a=labels[0],
            label_b=labels[1],
            minimum_samples=minimum_samples,
        )

    return json_safe(result)


def compare_two_datasets(
    dataset_a: pd.DataFrame | str | Path,
    dataset_b: pd.DataFrame | str | Path,
    value_column_a: str,
    value_column_b: str,
    label_a: str = "Dataset A",
    label_b: str = "Dataset B",
    metadata_a: dict[str, Any] | None = None,
    metadata_b: dict[str, Any] | None = None,
    minimum_samples: int = 2,
) -> dict[str, Any]:
    """
    Compare a numerical variable from two separate datasets.

    The column names do not need to be identical.

    Metadata is checked separately to help assess scientific
    comparability before interpreting the numerical results.
    """

    df_a = load_dataframe(dataset_a)
    df_b = load_dataframe(dataset_b)

    if value_column_a not in df_a.columns:
        raise ValueError(
            f"Column not found in dataset A: {value_column_a}"
        )

    if value_column_b not in df_b.columns:
        raise ValueError(
            f"Column not found in dataset B: {value_column_b}"
        )

    values_a, excluded_a = prepare_numeric_values(
        df_a[value_column_a]
    )

    values_b, excluded_b = prepare_numeric_values(
        df_b[value_column_b]
    )

    comparison = compare_two_groups(
        values_a=values_a,
        values_b=values_b,
        label_a=label_a,
        label_b=label_b,
        minimum_samples=minimum_samples,
    )

    comparability = check_comparability(
        metadata_a=metadata_a,
        metadata_b=metadata_b,
    )

    return json_safe({
        "analysis_type": "dataset_comparison",
        "datasets": {
            label_a: {
                "variable": value_column_a,
                "original_row_count": len(df_a),
                "excluded_value_count": excluded_a,
            },
            label_b: {
                "variable": value_column_b,
                "original_row_count": len(df_b),
                "excluded_value_count": excluded_b,
            },
        },
        "comparability": comparability,
        "comparison": comparison,
        "interpretation_warning": (
            "Numerical differences have been calculated, but their "
            "scientific interpretation depends on whether the datasets "
            "measure equivalent variables under comparable conditions."
        ),
    })