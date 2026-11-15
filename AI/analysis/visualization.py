from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Suitable for backend/server environments.

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_dataframe(data: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Load a DataFrame or Parquet file without modifying the original."""

    if isinstance(data, pd.DataFrame):
        return data.copy()

    path = Path(data)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            "Visualization accepts a DataFrame or Parquet file."
        )

    return pd.read_parquet(path)


def prepare_output_path(
    output_dir: str | Path,
    filename: str,
) -> Path:
    """Create the output directory and validate the filename."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    filename = Path(filename).name

    if not filename:
        raise ValueError("A valid output filename is required.")

    if not filename.lower().endswith(".png"):
        filename += ".png"

    return directory / filename


def save_figure(
    fig: plt.Figure,
    output_path: Path,
    dpi: int = 150,
) -> dict[str, Any]:
    """Save a Matplotlib figure and release its resources."""

    try:
        fig.savefig(
            output_path,
            dpi=dpi,
            bbox_inches="tight",
            format="png",
        )
    finally:
        plt.close(fig)

    return {
        "path": str(output_path),
        "filename": output_path.name,
        "format": "png",
    }


def numeric_series(data: pd.Series) -> pd.Series:
    """Convert a Series to finite numerical values."""

    values = pd.to_numeric(data, errors="coerce")

    return values.replace(
        [np.inf, -np.inf],
        np.nan,
    )


def plot_time_series(
    data: pd.DataFrame | str | Path,
    time_column: str,
    value_column: str,
    output_dir: str | Path = "output/charts",
    filename: str = "time_series.png",
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a line chart showing a variable over time."""

    df = load_dataframe(data)

    for column in [time_column, value_column]:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

    df[value_column] = numeric_series(df[value_column])

    df = df.dropna(
        subset=[time_column, value_column]
    )

    if df.empty:
        raise ValueError("No valid observations available for plotting.")

    # Parse datetime values when possible; otherwise retain numeric values.
    if pd.api.types.is_numeric_dtype(df[time_column]):
        df = df.sort_values(time_column)
    else:
        parsed_time = pd.to_datetime(
            df[time_column],
            errors="coerce",
        )

        if parsed_time.notna().all():
            df[time_column] = parsed_time
            df = df.sort_values(time_column)

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(
        df[time_column],
        df[value_column],
        marker="o",
        linewidth=1.5,
    )

    ax.set_title(title or f"{value_column} over time")
    ax.set_xlabel(time_column)
    ax.set_ylabel(value_column)

    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "time_series",
        "x_column": time_column,
        "y_column": value_column,
        "observation_count": len(df),
        **chart,
    }


def plot_histogram(
    data: pd.DataFrame | str | Path,
    column: str,
    bins: int = 20,
    output_dir: str | Path = "output/charts",
    filename: str = "histogram.png",
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a histogram showing a variable's distribution."""

    if bins < 1:
        raise ValueError("bins must be at least 1.")

    df = load_dataframe(data)

    if column not in df.columns:
        raise ValueError(f"Column not found: {column}")

    values = numeric_series(df[column]).dropna()

    if values.empty:
        raise ValueError("No valid numerical values available.")

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(
        values,
        bins=bins,
        edgecolor="black",
    )

    ax.set_title(title or f"Distribution of {column}")
    ax.set_xlabel(column)
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "histogram",
        "column": column,
        "observation_count": len(values),
        "bins": bins,
        **chart,
    }


def plot_scatter(
    data: pd.DataFrame | str | Path,
    x_column: str,
    y_column: str,
    output_dir: str | Path = "output/charts",
    filename: str = "scatter.png",
    title: str | None = None,
    show_trendline: bool = False,
) -> dict[str, Any]:
    """Generate a scatter plot for two numerical variables."""

    df = load_dataframe(data)

    for column in [x_column, y_column]:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

    df[x_column] = numeric_series(df[x_column])
    df[y_column] = numeric_series(df[y_column])

    df = df.dropna(
        subset=[x_column, y_column]
    )

    if len(df) < 2:
        raise ValueError(
            "At least two valid paired observations are required."
        )

    x = df[x_column].to_numpy(dtype=float)
    y = df[y_column].to_numpy(dtype=float)

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(x, y, alpha=0.7)

    if show_trendline and len(np.unique(x)) >= 2:
        slope, intercept = np.polyfit(x, y, 1)

        predicted = slope * x + intercept

        order = np.argsort(x)

        ax.plot(
            x[order],
            predicted[order],
            linestyle="--",
            label="Linear trend",
        )

        ax.legend()

    ax.set_title(
        title or f"{y_column} vs {x_column}"
    )
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    ax.grid(True, alpha=0.3)

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "scatter",
        "x_column": x_column,
        "y_column": y_column,
        "observation_count": len(df),
        "trendline_included": show_trendline,
        **chart,
    }


def plot_correlation_heatmap(
    data: pd.DataFrame | str | Path,
    columns: list[str] | None = None,
    method: str = "pearson",
    output_dir: str | Path = "output/charts",
    filename: str = "correlation_heatmap.png",
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a correlation heatmap for numerical variables."""

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

        missing = [
            column for column in selected
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Columns not found: {missing}"
            )

    if len(selected) < 2:
        raise ValueError(
            "At least two numerical variables are required."
        )

    numeric = df[selected].apply(
        pd.to_numeric,
        errors="coerce",
    )

    numeric = numeric.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    correlation = numeric.corr(method=method)

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(9, 7))

    matrix = correlation.to_numpy(dtype=float)

    image = ax.imshow(
        matrix,
        vmin=-1,
        vmax=1,
        aspect="auto",
    )

    ax.set_xticks(range(len(selected)))
    ax.set_yticks(range(len(selected)))

    ax.set_xticklabels(selected, rotation=45, ha="right")
    ax.set_yticklabels(selected)

    ax.set_title(
        title or f"{method.capitalize()} correlation matrix"
    )

    # Display coefficients inside the cells.
    for row in range(len(selected)):
        for column in range(len(selected)):
            value = matrix[row, column]

            if np.isfinite(value):
                ax.text(
                    column,
                    row,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                )

    fig.colorbar(
        image,
        ax=ax,
        label="Correlation coefficient",
    )

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "correlation_heatmap",
        "method": method,
        "variables": selected,
        **chart,
    }


def plot_group_comparison(
    data: pd.DataFrame | str | Path,
    group_column: str,
    value_column: str,
    output_dir: str | Path = "output/charts",
    filename: str = "group_comparison.png",
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a bar chart comparing group means."""

    df = load_dataframe(data)

    for column in [group_column, value_column]:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

    df[value_column] = numeric_series(df[value_column])

    df = df.dropna(
        subset=[group_column, value_column]
    )

    if df.empty:
        raise ValueError("No valid group observations available.")

    summary = df.groupby(
        group_column,
        observed=True,
    )[value_column].agg(
        ["mean", "std", "count"]
    )

    if summary.empty:
        raise ValueError("No groups available for comparison.")

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(9, 5))

    positions = np.arange(len(summary))

    standard_errors = (
        summary["std"] / np.sqrt(summary["count"])
    ).fillna(0)

    ax.bar(
        positions,
        summary["mean"],
        yerr=standard_errors,
        capsize=5,
    )

    ax.set_xticks(positions)
    ax.set_xticklabels(
        [str(value) for value in summary.index],
        rotation=30,
        ha="right",
    )

    ax.set_title(
        title or f"Mean {value_column} by {group_column}"
    )

    ax.set_xlabel(group_column)
    ax.set_ylabel(f"Mean {value_column}")
    ax.grid(axis="y", alpha=0.3)

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "group_comparison",
        "group_column": group_column,
        "value_column": value_column,
        "group_count": len(summary),
        "error_bars": "standard error of the mean",
        **chart,
    }


def plot_boxplot(
    data: pd.DataFrame | str | Path,
    group_column: str,
    value_column: str,
    output_dir: str | Path = "output/charts",
    filename: str = "boxplot.png",
    title: str | None = None,
) -> dict[str, Any]:
    """Generate box plots showing distributions across groups."""

    df = load_dataframe(data)

    for column in [group_column, value_column]:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

    df[value_column] = numeric_series(df[value_column])

    df = df.dropna(
        subset=[group_column, value_column]
    )

    grouped_values = [
        group[value_column].to_numpy(dtype=float)
        for _, group in df.groupby(
            group_column,
            observed=True,
            sort=False,
        )
    ]

    labels = [
        str(group)
        for group, _ in df.groupby(
            group_column,
            observed=True,
            sort=False,
        )
    ]

    if not grouped_values:
        raise ValueError("No valid groups available.")

    output_path = prepare_output_path(
        output_dir,
        filename,
    )

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.boxplot(
        grouped_values,
        tick_labels=labels,
    )

    ax.set_title(
        title or f"Distribution of {value_column} by {group_column}"
    )

    ax.set_xlabel(group_column)
    ax.set_ylabel(value_column)

    ax.grid(axis="y", alpha=0.3)

    chart = save_figure(fig, output_path)

    return {
        "chart_type": "boxplot",
        "group_column": group_column,
        "value_column": value_column,
        "group_count": len(grouped_values),
        **chart,
    }