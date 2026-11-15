from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

DEFAULT_PERCENTILES = [
    0.05,
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
]


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def load_dataframe(
    data: pd.DataFrame | str | Path,
) -> pd.DataFrame:
    """
    Accept either a pandas DataFrame or a Parquet file path.
    """

    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Statistics module currently accepts DataFrames "
            "or Parquet files."
        )

    return pd.read_parquet(path)


def get_numeric_column(
    dataframe: pd.DataFrame,
    column: str,
) -> pd.Series:
    """
    Retrieve and validate a numeric column.

    Infinite values are treated as invalid measurements.
    """

    if column not in dataframe.columns:
        raise KeyError(
            f"Column '{column}' does not exist in the dataset."
        )

    numeric = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    numeric = numeric.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if numeric.empty:
        raise ValueError(
            f"Column '{column}' contains no valid numeric values."
        )

    return numeric


def extract_unit(column_name: str) -> str | None:
    """
    Extract an explicitly declared unit from a column name.
    """

    import re

    match = re.search(
        r"[\(\[]\s*([^\)\]]+)\s*[\)\]]",
        column_name,
    )

    return match.group(1).strip() if match else None


def json_safe(value: Any) -> Any:
    """
    Convert NumPy and pandas values into JSON-compatible values.
    """

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float) and not np.isfinite(value):
        return None

    if pd.isna(value):
        return None

    return value


# ---------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------

def calculate_descriptive_statistics(
    data: pd.DataFrame | str | Path,
    column: str,
) -> dict[str, Any]:
    """
    Calculate descriptive statistics for one numeric variable.

    Returns:
        Count, mean, median, mode, standard deviation,
        variance, minimum, maximum, range, quartiles,
        percentiles, skewness, and kurtosis.
    """

    dataframe = load_dataframe(data)

    series = get_numeric_column(
        dataframe,
        column,
    )

    count = len(series)

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)

    statistics = {
        "column": column,
        "unit": extract_unit(column),

        "count": count,

        "central_tendency": {
            "mean": series.mean(),
            "median": series.median(),
            "mode": series.mode().tolist(),
        },

        "dispersion": {
            "standard_deviation": series.std(),
            "variance": series.var(),
            "range": series.max() - series.min(),
            "interquartile_range": q3 - q1,
            "coefficient_of_variation": (
                series.std() / abs(series.mean())
                if series.mean() != 0
                else None
            ),
        },

        "extremes": {
            "minimum": series.min(),
            "maximum": series.max(),
        },

        "quartiles": {
            "q1": q1,
            "q2": series.median(),
            "q3": q3,
        },

        "percentiles": {
            f"p{int(p * 100):02d}": series.quantile(p)
            for p in DEFAULT_PERCENTILES
        },

        "shape": {
            "skewness": series.skew(),
            "kurtosis": series.kurtosis(),
        },

        "data_quality": {
            "original_count": len(dataframe),
            "valid_count": count,
            "excluded_count": len(dataframe) - count,
        },
    }

    return json_safe(statistics)


# ---------------------------------------------------------
# Frequency analysis
# ---------------------------------------------------------

def calculate_frequency_statistics(
    data: pd.DataFrame | str | Path,
    column: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Calculate frequencies for categorical variables.

    Useful for examining experimental categories,
    conditions, labels, or classifications.
    """

    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    dataframe = load_dataframe(data)

    if column not in dataframe.columns:
        raise KeyError(
            f"Column '{column}' does not exist."
        )

    series = dataframe[column].dropna()

    if series.empty:
        raise ValueError(
            f"Column '{column}' contains no valid values."
        )

    frequencies = series.value_counts()

    total = len(series)

    result = {
        "column": column,
        "total_values": total,
        "unique_values": int(series.nunique()),
        "missing_values": int(dataframe[column].isna().sum()),

        "frequencies": [
            {
                "value": str(value),
                "count": int(count),
                "percentage": round(
                    count / total * 100,
                    2,
                ),
            }
            for value, count in frequencies.head(top_n).items()
        ],
    }

    return json_safe(result)


# ---------------------------------------------------------
# Grouped statistical analysis
# ---------------------------------------------------------

def calculate_grouped_statistics(
    data: pd.DataFrame | str | Path,
    value_column: str,
    group_column: str,
) -> dict[str, Any]:
    """
    Calculate descriptive statistics for a numeric variable
    separated by categories in another column.

    Example:
        Compare flame temperature across different
        experimental conditions.
    """

    dataframe = load_dataframe(data)

    if group_column not in dataframe.columns:
        raise KeyError(
            f"Group column '{group_column}' does not exist."
        )

    if value_column not in dataframe.columns:
        raise KeyError(
            f"Value column '{value_column}' does not exist."
        )

    dataframe[value_column] = pd.to_numeric(
        dataframe[value_column],
        errors="coerce",
    )

    dataframe[value_column] = dataframe[value_column].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    dataframe = dataframe.dropna(
        subset=[value_column, group_column]
    )

    if dataframe.empty:
        raise ValueError(
            "No valid observations are available for grouping."
        )

    grouped = dataframe.groupby(
        group_column,
        dropna=True,
    )[value_column]

    results = []

    for group_name, values in grouped:
        results.append({
            "group": str(group_name),
            "count": int(values.count()),
            "mean": values.mean(),
            "median": values.median(),
            "standard_deviation": values.std(),
            "minimum": values.min(),
            "maximum": values.max(),
        })

    return json_safe({
        "value_column": value_column,
        "value_unit": extract_unit(value_column),
        "group_column": group_column,
        "groups": results,
    })


# ---------------------------------------------------------
# Summary of multiple numeric variables
# ---------------------------------------------------------

def summarize_numeric_variables(
    data: pd.DataFrame | str | Path,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generate descriptive statistics for multiple numeric variables.

    If columns is omitted, all numeric columns are selected.
    """

    dataframe = load_dataframe(data)

    if columns is None:
        columns = dataframe.select_dtypes(
            include="number"
        ).columns.tolist()

    if not columns:
        raise ValueError(
            "No numeric columns were selected."
        )

    summaries = {}

    for column in columns:
        summaries[column] = calculate_descriptive_statistics(
            dataframe,
            column,
        )

    return {
        "dataset_rows": len(dataframe),
        "variables_analyzed": len(summaries),
        "statistics": summaries,
    }


# ---------------------------------------------------------
# Main analysis interface
# ---------------------------------------------------------

def analyze_statistics(
    data: pd.DataFrame | str | Path,
    analysis_type: str,
    **parameters: Any,
) -> dict[str, Any]:
    """
    Central entry point for statistical analysis.

    Supported analysis types:
        descriptive
        frequency
        grouped
        summary
    """

    analysis_functions = {
        "descriptive": calculate_descriptive_statistics,
        "frequency": calculate_frequency_statistics,
        "grouped": calculate_grouped_statistics,
        "summary": summarize_numeric_variables,
    }

    if analysis_type not in analysis_functions:
        raise ValueError(
            f"Unsupported analysis type: {analysis_type}. "
            f"Supported types: {list(analysis_functions)}"
        )

    function = analysis_functions[analysis_type]

    result = function(
        data,
        **parameters,
    )

    return {
        "analysis_type": analysis_type,
        "status": "completed",
        "result": result,
    }