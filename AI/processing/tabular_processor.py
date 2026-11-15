from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
NUMERIC_THRESHOLD = 0.95
DATETIME_THRESHOLD = 0.95


@dataclass
class ColumnProfile:
    name: str
    original_name: str
    inferred_type: str
    unit: str | None
    non_null_count: int
    missing_count: int
    missing_percentage: float
    unique_count: int
    sample_values: list[Any] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetProfile:
    dataset_id: str
    source_file: str
    source_format: str
    sheet_name: str | None
    row_count: int
    column_count: int
    duplicate_rows: int
    duplicate_rows_removed: int
    empty_rows_removed: int
    empty_columns_removed: int
    columns: list[ColumnProfile]
    parquet_path: str | None
    profile_path: str | None
    status: str
    warnings: list[str] = field(default_factory=list)
    processed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------
# Header and value utilities
# ---------------------------------------------------------------------

def normalize_headers(columns: list[Any]) -> tuple[list[str], list[str]]:
    """
    Convert column headers into usable, unique names.

    Returns:
        normalized_headers, original_headers
    """
    original_headers = []
    normalized_headers = []
    used_names: dict[str, int] = {}

    for index, column in enumerate(columns):
        original = "" if column is None else str(column).strip()
        original_headers.append(original)

        base = original if original else f"unnamed_column_{index + 1}"

        # Make names easier to use in code and SQL.
        normalized = re.sub(r"\s+", "_", base)
        normalized = re.sub(r"[^\w]", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized).strip("_").lower()

        if not normalized:
            normalized = f"unnamed_column_{index + 1}"

        # Ensure column names are unique.
        count = used_names.get(normalized, 0) + 1
        used_names[normalized] = count

        if count > 1:
            normalized = f"{normalized}_{count}"

        normalized_headers.append(normalized)

    return normalized_headers, original_headers


def extract_unit(column_name: str) -> str | None:
    """
    Extract a unit explicitly written in a column header.

    Examples:
        Temperature (K) -> K
        Flame Diameter [mm] -> mm
        Time (seconds) -> seconds

    This function does not guess units.
    """
    match = re.search(r"[\(\[]\s*([^\)\]]+)\s*[\)\]]", column_name)

    if match:
        return match.group(1).strip()

    return None


def make_json_safe(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-compatible values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


# ---------------------------------------------------------------------
# File readers
# ---------------------------------------------------------------------

def read_csv_file(
    file_path: Path,
    delimiter: str | None = None,
) -> pd.DataFrame:
    """
    Read a CSV file while trying common encodings.

    If delimiter is not provided, pandas attempts to detect it.
    """
    encodings = ["utf-8-sig", "utf-16", "cp1252"]

    last_error = None

    for encoding in encodings:
        try:
            if delimiter:
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    skip_blank_lines=False,
                )

            return pd.read_csv(
                file_path,
                encoding=encoding,
                sep=None,
                engine="python",
                skip_blank_lines=False,
            )

        except (UnicodeDecodeError, pd.errors.ParserError) as error:
            last_error = error

    raise ValueError(
        f"Could not read CSV file {file_path.name}. "
        f"Last error: {last_error}"
    )


def read_excel_sheets(file_path: Path) -> dict[str, pd.DataFrame]:
    """
    Read every sheet in an Excel workbook.

    XLSX uses openpyxl.
    Legacy XLS uses xlrd.
    """
    extension = file_path.suffix.lower()

    if extension == ".xlsx":
        engine = "openpyxl"
    elif extension == ".xls":
        engine = "xlrd"
    else:
        raise ValueError(f"Unsupported Excel extension: {extension}")

    try:
        workbook = pd.ExcelFile(file_path, engine=engine)

        return {
            sheet_name: pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                header=0,
            )
            for sheet_name in workbook.sheet_names
        }

    except ImportError as error:
        raise RuntimeError(
            f"Missing dependency required to read {extension} files. "
            f"Install the appropriate Excel reader."
        ) from error


# ---------------------------------------------------------------------
# Data cleaning and type inference
# ---------------------------------------------------------------------

def clean_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], int, int]:

    df = dataframe.copy()

    normalized_headers, original_headers = normalize_headers(
        list(df.columns)
    )

    df.columns = normalized_headers

    # Replace whitespace-only strings with missing values.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Remove completely empty rows.
    original_row_count = len(df)
    df = df.dropna(axis=0, how="all")

    empty_rows_removed = original_row_count - len(df)

    # Identify non-empty columns before removing them.
    non_empty_mask = df.notna().any(axis=0)

    # Preserve only original names belonging to retained columns.
    retained_original_headers = [
        original
        for original, keep in zip(original_headers, non_empty_mask)
        if keep
    ]

    original_column_count = len(df.columns)

    df = df.loc[:, non_empty_mask]

    empty_columns_removed = original_column_count - len(df.columns)

    return (
        df,
        retained_original_headers,
        empty_rows_removed,
        empty_columns_removed,
    )
    """
    Prepare a copy of the dataframe.

    - Normalize column names.
    - Remove completely empty rows.
    - Remove completely empty columns.

    Returns:
        cleaned_dataframe,
        original_column_names,
        empty_rows_removed,
        empty_columns_removed
    """
    df = dataframe.copy()

    normalized_headers, original_headers = normalize_headers(
        list(df.columns)
    )

    df.columns = normalized_headers

    # Replace whitespace-only strings with missing values.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    original_row_count = len(df)
    df = df.dropna(axis=0, how="all")
    empty_rows_removed = original_row_count - len(df)

    original_column_count = len(df.columns)
    df = df.dropna(axis=1, how="all")
    empty_columns_removed = original_column_count - len(df.columns)

    return (
        df,
        original_headers,
        empty_rows_removed,
        empty_columns_removed,
    )


def infer_column_type(series: pd.Series) -> tuple[str, pd.Series]:
    """
    Infer a column's type conservatively.

    Numeric and datetime conversion is accepted only when at least
    95% of non-null values can be interpreted successfully.
    """
    non_null = series.dropna()

    if non_null.empty:
        return "empty", series

    # Boolean values.
    if pd.api.types.is_bool_dtype(series):
        return "boolean", series

    # Already numeric.
    if pd.api.types.is_numeric_dtype(series):
        return "numeric", pd.to_numeric(series, errors="coerce")

    # Attempt numeric conversion.
    numeric_values = pd.to_numeric(series, errors="coerce")
    numeric_success = numeric_values.notna().sum() / len(non_null)

    if numeric_success >= NUMERIC_THRESHOLD:
        return "numeric", numeric_values

    # Attempt datetime conversion.
    # Avoid interpreting ordinary numeric identifiers as dates.
    datetime_values = pd.to_datetime(
        series,
        errors="coerce",
        format="mixed",
    )
    datetime_success = datetime_values.notna().sum() / len(non_null)

    if datetime_success >= DATETIME_THRESHOLD:
        return "datetime", datetime_values

    return "text", series


# ---------------------------------------------------------------------
# Dataset profiling
# ---------------------------------------------------------------------

def profile_column(
    name: str,
    original_name: str,
    series: pd.Series,
) -> tuple[ColumnProfile, pd.Series]:
    inferred_type, converted_series = infer_column_type(series)

    non_null = converted_series.dropna()
    missing_count = int(converted_series.isna().sum())
    total_count = len(converted_series)

    missing_percentage = (
        (missing_count / total_count) * 100
        if total_count > 0
        else 0.0
    )

    statistics: dict[str, Any] = {}

    if inferred_type == "numeric" and not non_null.empty:
        statistics = {
            "min": make_json_safe(non_null.min()),
            "max": make_json_safe(non_null.max()),
            "mean": make_json_safe(non_null.mean()),
            "median": make_json_safe(non_null.median()),
            "standard_deviation": make_json_safe(non_null.std()),
        }

    sample_values = [
        make_json_safe(value)
        for value in non_null.head(5).tolist()
    ]

    profile = ColumnProfile(
        name=name,
        original_name=original_name,
        inferred_type=inferred_type,
        unit=extract_unit(original_name),
        non_null_count=int(non_null.count()),
        missing_count=missing_count,
        missing_percentage=round(missing_percentage, 2),
        unique_count=int(non_null.nunique()),
        sample_values=sample_values,
        statistics=statistics,
    )

    return profile, converted_series


def profile_dataframe(
    dataframe: pd.DataFrame,
    source_file: str,
    source_format: str,
    sheet_name: str | None,
    original_headers: list[str],
    dataset_id: str,
    output_dir: Path,
    empty_rows_removed: int,
    empty_columns_removed: int,
    write_parquet: bool = True,
    remove_duplicates: bool = False,
) -> DatasetProfile:
    warnings: list[str] = []
    df = dataframe.copy()

    # Map the remaining columns to their original header names.
    original_name_map = {
        normalized: original
        for normalized, original in zip(
            dataframe.columns,
            original_headers,
        )
    }

    # Detect duplicate rows before calculating statistics.
    duplicate_rows = int(df.duplicated().sum())
    duplicate_rows_removed = 0

    # Remove duplicates only when explicitly requested.
    if remove_duplicates and duplicate_rows > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        duplicate_rows_removed = duplicate_rows

    column_profiles = []

    for column_name in df.columns:
        original_name = original_name_map.get(
            column_name,
            str(column_name),
        )

        profile, converted_series = profile_column(
            name=str(column_name),
            original_name=original_name,
            series=df[column_name],
        )

        column_profiles.append(profile)
        df[column_name] = converted_series

    # Detect duplicates before optionally removing them.
    duplicate_rows = int(df.duplicated().sum())
    duplicate_rows_removed = 0

    if remove_duplicates and duplicate_rows > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        duplicate_rows_removed = duplicate_rows

    parquet_path = None
    profile_path = None

    output_dir.mkdir(parents=True, exist_ok=True)

    if write_parquet:
        try:
            parquet_file = output_dir / f"{dataset_id}.parquet"
            df.to_parquet(parquet_file, index=False)
            parquet_path = str(parquet_file)

        except (ImportError, ModuleNotFoundError):
            warnings.append(
                "Parquet export skipped: install pyarrow or fastparquet."
            )

        except Exception as error:
            warnings.append(f"Parquet export failed: {error}")

    profile = DatasetProfile(
        dataset_id=dataset_id,
        source_file=source_file,
        source_format=source_format,
        sheet_name=sheet_name,
        row_count=len(df),
        column_count=len(df.columns),
        duplicate_rows=duplicate_rows,
        duplicate_rows_removed=duplicate_rows_removed,
        empty_rows_removed=empty_rows_removed,
        empty_columns_removed=empty_columns_removed,
        columns=column_profiles,
        parquet_path=parquet_path,
        profile_path=None,
        status="completed",
        warnings=warnings,
    )

    profile_file = output_dir / f"{dataset_id}_profile.json"

    with profile_file.open("w", encoding="utf-8") as file:
        json.dump(
            asdict(profile),
            file,
            indent=4,
            ensure_ascii=False,
        )

    profile.profile_path = str(profile_file)

    # Rewrite the JSON so it includes its own profile path.
    with profile_file.open("w", encoding="utf-8") as file:
        json.dump(
            asdict(profile),
            file,
            indent=4,
            ensure_ascii=False,
        )

    return profile


# ---------------------------------------------------------------------
# Main processing function
# ---------------------------------------------------------------------

def process_tabular_file(
    file_path: str | Path,
    output_dir: str | Path,
    dataset_id_prefix: str | None = None,
    delimiter: str | None = None,
    write_parquet: bool = True,
    remove_duplicates: bool = False,
) -> list[DatasetProfile]:
    """
    Process a CSV, XLS, or XLSX file.

    CSV:
        Produces one dataset.

    XLS/XLSX:
        Produces one dataset per worksheet.

    Returns a list of dataset profiles.
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}. "
            f"Supported formats: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    prefix = dataset_id_prefix or file_path.stem
    prefix = re.sub(r"[^\w-]+", "_", prefix).strip("_")

    datasets: list[DatasetProfile] = []

    if extension == ".csv":
        raw_dataframe = read_csv_file(file_path, delimiter=delimiter)

        cleaned, original_headers, empty_rows, empty_columns = (
            clean_dataframe(raw_dataframe)
        )

        dataset = profile_dataframe(
            dataframe=cleaned,
            source_file=file_path.name,
            source_format="csv",
            sheet_name=None,
            original_headers=original_headers,
            dataset_id=f"{prefix}_csv",
            output_dir=output_dir,
            empty_rows_removed=empty_rows,
            empty_columns_removed=empty_columns,
            write_parquet=write_parquet,
        )

        datasets.append(dataset)

    else:
        sheets = read_excel_sheets(file_path)

        for index, (sheet_name, raw_dataframe) in enumerate(
            sheets.items(),
            start=1,
        ):
            cleaned, original_headers, empty_rows, empty_columns = (
                clean_dataframe(raw_dataframe)
            )

            safe_sheet_name = re.sub(
                r"[^\w-]+",
                "_",
                sheet_name,
            ).strip("_")

            dataset = profile_dataframe(
                dataframe=cleaned,
                source_file=file_path.name,
                source_format=extension.lstrip("."),
                sheet_name=sheet_name,
                original_headers=original_headers,
                dataset_id=f"{prefix}_sheet_{index}_{safe_sheet_name}",
                output_dir=output_dir,
                empty_rows_removed=empty_rows,
                remove_duplicates=remove_duplicates,
                empty_columns_removed=empty_columns,
                write_parquet=write_parquet,
            )

            datasets.append(dataset)

    return datasets


# ---------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process CSV, XLS, and XLSX scientific datasets."
    )

    parser.add_argument("file", help="Path to the input file")
    parser.add_argument(
        "--output-dir",
        default="processed",
        help="Directory for Parquet files and JSON profiles",
    )
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Optional CSV delimiter, for example ';' or ','",
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Generate JSON profiles without exporting Parquet",
    )

    parser.add_argument(
        "--remove-duplicates",
        action="store_true",
        help="Remove duplicate rows from processed datasets",
    )

    args = parser.parse_args()

    profiles = process_tabular_file(
        file_path=args.file,
        output_dir=args.output_dir,
        delimiter=args.delimiter,
        write_parquet=not args.no_parquet,
        remove_duplicates=args.remove_duplicates,
    )
    print(json.dumps(
        [asdict(profile) for profile in profiles],
        indent=4,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()