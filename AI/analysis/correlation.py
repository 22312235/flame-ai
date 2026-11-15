from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


CorrelationMethod = Literal["pearson", "spearman"]


def load_dataframe(data: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Load a DataFrame or Parquet file without modifying the original."""

    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Correlation analysis accepts a DataFrame or Parquet file."
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


def interpret_correlation(
    coefficient: float,
) -> dict[str, str]:
    """
    Provide a descriptive interpretation of correlation strength.

    These thresholds are heuristic, not universal scientific standards.
    """

    absolute_value = abs(coefficient)

    if absolute_value < 0.10:
        strength = "negligible"
    elif absolute_value < 0.30:
        strength = "weak"
    elif absolute_value < 0.50:
        strength = "moderate"
    elif absolute_value < 0.70:
        strength = "strong"
    else:
        strength = "very strong"

    direction = (
        "positive"
        if coefficient > 0
        else "negative"
        if coefficient < 0
        else "none"
    )

    return {
        "strength": strength,
        "direction": direction,
    }


def calculate_pair_correlation(
    data: pd.DataFrame,
    column_a: str,
    column_b: str,
    method: CorrelationMethod = "pearson",
    minimum_samples: int = 3,
) -> dict[str, Any]:
    """
    Calculate correlation between two numerical variables.

    Rows with missing or non-finite values in either variable
    are excluded pairwise.

    Pearson:
        Measures linear association.

    Spearman:
        Measures monotonic association using ranks.
    """

    if method not in {"pearson", "spearman"}:
        raise ValueError(
            "method must be 'pearson' or 'spearman'."
        )

    if column_a not in data.columns:
        raise ValueError(f"Column not found: {column_a}")

    if column_b not in data.columns:
        raise ValueError(f"Column not found: {column_b}")

    if column_a == column_b:
        raise ValueError("Select two different columns.")

    if minimum_samples < 3:
        raise ValueError("minimum_samples must be at least 3.")

    values = pd.DataFrame({
        "a": pd.to_numeric(data[column_a], errors="coerce"),
        "b": pd.to_numeric(data[column_b], errors="coerce"),
    })

    values = values.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    sample_count = len(values)

    result = {
        "variable_a": column_a,
        "variable_b": column_b,
        "method": method,
        "sample_count": sample_count,
        "excluded_pair_count": len(data) - sample_count,
    }

    if sample_count < minimum_samples:
        return {
            **result,
            "available": False,
            "reason": (
                f"At least {minimum_samples} valid paired observations "
                "are required."
            ),
        }

    a = values["a"].to_numpy(dtype=float)
    b = values["b"].to_numpy(dtype=float)

    if np.unique(a).size < 2 or np.unique(b).size < 2:
        return {
            **result,
            "available": False,
            "reason": (
                "Correlation cannot be calculated when either "
                "variable has no variation."
            ),
        }

    if method == "pearson":
        coefficient, p_value = pearsonr(a, b)
    else:
        coefficient, p_value = spearmanr(a, b)

    interpretation = interpret_correlation(
        float(coefficient)
    )

    return {
        **result,
        "available": True,
        "coefficient": float(coefficient),
        "p_value": float(p_value),
        "interpretation": interpretation,
        "statistical_significance": {
            "alpha": 0.05,
            "significant_at_alpha": bool(p_value < 0.05),
        },
        "limitations": [
            "Correlation does not establish causation.",
            "Outliers can influence Pearson correlation.",
            "A strong correlation may be driven by confounding variables.",
            "Statistical significance does not establish scientific importance.",
            "The p-value assumes observations are suitable for the "
            "chosen statistical test.",
        ],
    }


def calculate_correlation_matrix(
    data: pd.DataFrame | str | Path,
    columns: list[str] | None = None,
    method: CorrelationMethod = "pearson",
    minimum_samples: int = 3,
) -> dict[str, Any]:
    """
    Calculate a correlation matrix for selected numerical variables.

    Pairwise deletion is used: each pair is calculated using
    observations valid for those two variables.
    """

    if method not in {"pearson", "spearman"}:
        raise ValueError(
            "method must be 'pearson' or 'spearman'."
        )

    df = load_dataframe(data)

    if columns is None:
        selected = df.select_dtypes(
            include=["number"]
        ).columns.tolist()
    else:
        selected = columns

        missing_columns = [
            column
            for column in selected
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Columns not found: {missing_columns}"
            )

    if len(selected) < 2:
        raise ValueError(
            "At least two numerical variables are required."
        )

    numeric_df = df[selected].apply(
        pd.to_numeric,
        errors="coerce",
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    )

    matrix = numeric_df.corr(
        method=method,
        min_periods=minimum_samples,
    )

    sample_counts = pd.DataFrame(
        index=selected,
        columns=selected,
        dtype=int,
    )

    for column_a in selected:
        for column_b in selected:
            valid_pairs = numeric_df[
                [column_a, column_b]
            ].dropna()

            sample_counts.loc[
                column_a,
                column_b,
            ] = len(valid_pairs)

    return json_safe({
        "analysis_type": "correlation_matrix",
        "method": method,
        "variables": selected,
        "correlation_matrix": matrix.to_dict(),
        "pair_sample_counts": sample_counts.to_dict(),
        "limitations": [
            "Correlation does not establish causation.",
            "Each pair may use a different number of observations.",
            "Correlations can be affected by outliers and confounding variables.",
            "Time-dependent observations may violate independence assumptions.",
        ],
    })


def find_strong_correlations(
    matrix_result: dict[str, Any],
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Extract unique variable pairs whose absolute correlation
    meets or exceeds the selected threshold.

    This function uses the correlation matrix only.
    It does not calculate p-values.
    """

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")

    matrix = matrix_result["correlation_matrix"]
    method = matrix_result["method"]
    variables = matrix_result["variables"]

    results = []

    for index, column_a in enumerate(variables):
        for column_b in variables[index + 1:]:
            coefficient = matrix[column_a][column_b]

            if coefficient is None:
                continue

            if abs(coefficient) >= threshold:
                results.append({
                    "variable_a": column_a,
                    "variable_b": column_b,
                    "method": method,
                    "coefficient": coefficient,
                    "interpretation": interpret_correlation(
                        coefficient
                    ),
                })

    results.sort(
        key=lambda item: abs(item["coefficient"]),
        reverse=True,
    )

    return results


def analyze_correlations(
    data: pd.DataFrame | str | Path,
    columns: list[str] | None = None,
    method: CorrelationMethod = "pearson",
    threshold: float = 0.5,
    minimum_samples: int = 3,
) -> dict[str, Any]:
    """
    Run a complete correlation analysis.

    Returns:
      - Correlation matrix
      - Pairwise sample counts
      - Strong correlation pairs
      - Method and limitations
    """

    matrix_result = calculate_correlation_matrix(
        data=data,
        columns=columns,
        method=method,
        minimum_samples=minimum_samples,
    )

    strong_pairs = find_strong_correlations(
        matrix_result,
        threshold=threshold,
    )

    return json_safe({
        **matrix_result,
        "strong_correlations": strong_pairs,
        "strong_correlation_threshold": threshold,
    })