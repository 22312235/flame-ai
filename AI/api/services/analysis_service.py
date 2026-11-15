from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd

from sqlalchemy.orm import Session

from api.schemas.common import (
    DataSourceReference,
    FilterSet,
)

from api.schemas.analysis import (
    StatisticsAnalysisType,
    StatisticsRequest,
    StatisticsResponse,
    CorrelationRequest,
    CorrelationResponse,
)

from analysis.statistics import (
    analyze_statistics as run_statistics,
)

from analysis.correlation import (
    analyze_correlations as run_correlations,
)

from filtering.variable_filter import (
    filter_dataframe_rows,
)

from services.dataset_service import DatasetService


# =========================================================
# Exceptions
# =========================================================

class AnalysisServiceError(Exception):
    """Base exception for analysis service operations."""


class AnalysisValidationError(AnalysisServiceError):
    """Raised when analysis parameters are invalid."""


class AnalysisExecutionError(AnalysisServiceError):
    """Raised when an analysis cannot be completed."""


# =========================================================
# Analysis Service
# =========================================================

class AnalysisService:
    """
    Application service for scientific data analysis.

    Responsibilities:
        - Retrieve datasets through DatasetService.
        - Verify investigation ownership.
        - Load required Parquet columns.
        - Apply optional observation filters.
        - Execute existing statistical algorithms.
        - Return structured API responses.

    This service does not:
        - Commit database transactions.
        - Modify source datasets.
        - Persist analysis results.
        - Handle HTTP requests directly.
    """

    def __init__(
        self,
        dataset_service: DatasetService | None = None,
    ):
        self.dataset_service = (
            dataset_service or DatasetService()
        )

    # =====================================================
    # JSON Serialization
    # =====================================================

    @classmethod
    def _json_safe(
        cls,
        value: Any,
    ) -> Any:
        """
        Convert pandas, NumPy, datetime, and UUID values
        into JSON-compatible objects.
        """

        if value is None or value is pd.NA or value is pd.NaT:
            return None

        if isinstance(value, dict):
            return {
                str(key): cls._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                cls._json_safe(item)
                for item in value
            ]

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.isoformat()

        if isinstance(value, np.ndarray):
            return cls._json_safe(value.tolist())

        if isinstance(value, np.generic):
            return cls._json_safe(value.item())

        if isinstance(value, float):
            return value if math.isfinite(value) else None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        return value

    # =====================================================
    # Filter Conversion
    # =====================================================

    @staticmethod
    def _conditions_to_dicts(
        filters: FilterSet,
    ) -> list[dict[str, Any]]:
        """Convert Pydantic filtering conditions to dictionaries."""

        return [
            condition.model_dump(mode="json")
            for condition in filters.conditions
        ]

    # =====================================================
    # Required Columns
    # =====================================================

    @staticmethod
    def _required_statistics_columns(
        request: StatisticsRequest,
    ) -> list[str] | None:
        """
        Determine which columns are required for the
        selected statistical analysis.

        Returning None means all columns may be needed.
        """

        analysis_type = request.analysis_type

        if analysis_type in {
            StatisticsAnalysisType.DESCRIPTIVE,
            StatisticsAnalysisType.FREQUENCY,
        }:
            return [request.column]

        if analysis_type == StatisticsAnalysisType.GROUPED:
            return [
                request.value_column,
                request.group_column,
            ]

        if analysis_type == StatisticsAnalysisType.SUMMARY:
            return request.columns

        raise AnalysisValidationError(
            f"Unsupported statistical analysis: {analysis_type}"
        )

    # =====================================================
    # Shared Data Preparation
    # =====================================================

    def _prepare_dataframe(
        self,
        db: Session,
        investigation_id: UUID,
        dataset_id: UUID,
        filters: FilterSet,
        selected_columns: list[str] | None = None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Load the dataset and apply optional row filters.

        Filtering conditions are evaluated before
        restricting the final analysis columns.
        """

        conditions = self._conditions_to_dicts(
            filters
        )

        condition_columns = [
            condition["column"]
            for condition in conditions
        ]

        if selected_columns is None:
            required_columns = None
        else:
            required_columns = list(
                dict.fromkeys(
                    selected_columns + condition_columns
                )
            )

        dataframe = self.dataset_service.load_dataframe(
            db=db,
            dataset_id=dataset_id,
            investigation_id=investigation_id,
            columns=required_columns,
        )

        filtered, metadata = filter_dataframe_rows(
            data=dataframe,
            conditions=conditions,
            combine=filters.combine.value,
        )

        if selected_columns is not None:
            missing_columns = [
                column
                for column in selected_columns
                if column not in filtered.columns
            ]

            if missing_columns:
                raise AnalysisValidationError(
                    f"Unknown analysis columns: {missing_columns}"
                )

            filtered = filtered[selected_columns].copy()

        return filtered, metadata

    # =====================================================
    # Statistical Analysis
    # =====================================================

    def analyze_statistics(
        self,
        db: Session,
        request: StatisticsRequest,
    ) -> StatisticsResponse:
        """
        Execute statistical analysis.

        Supported:
            - descriptive
            - frequency
            - grouped
            - summary

        Uses:
            analysis.statistics.analyze_statistics()
        """

        dataset = self.dataset_service.get_dataset(
            db=db,
            dataset_id=request.dataset_id,
            investigation_id=request.investigation_id,
        )

        selected_columns = (
            self._required_statistics_columns(request)
        )

        dataframe, filter_metadata = (
            self._prepare_dataframe(
                db=db,
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                filters=request.filters,
                selected_columns=selected_columns,
            )
        )

        if dataframe.empty:
            raise AnalysisValidationError(
                "No observations remain after filtering."
            )

        analysis_type = request.analysis_type.value

        # Build parameters expected by statistics.py.
        parameters = {}

        if request.analysis_type == StatisticsAnalysisType.DESCRIPTIVE:
            parameters["column"] = request.column

        elif request.analysis_type == StatisticsAnalysisType.FREQUENCY:
            parameters["column"] = request.column
            parameters["top_n"] = request.top_n

        elif request.analysis_type == StatisticsAnalysisType.GROUPED:
            parameters["value_column"] = request.value_column
            parameters["group_column"] = request.group_column

        elif request.analysis_type == StatisticsAnalysisType.SUMMARY:
            parameters["columns"] = request.columns

        try:
            analysis_result = run_statistics(
                data=dataframe,
                analysis_type=analysis_type,
                **parameters,
            )

        except (ValueError, KeyError, TypeError) as error:
            raise AnalysisValidationError(
                str(error)
            ) from error

        except Exception as error:
            raise AnalysisExecutionError(
                "Statistical analysis failed."
            ) from error

        warnings = []

        if filter_metadata["excluded_row_count"] > 0:
            warnings.append(
                f"{filter_metadata['excluded_row_count']} observations "
                "were excluded by the filtering conditions."
            )

        return StatisticsResponse(
            investigation_id=request.investigation_id,
            dataset_id=request.dataset_id,
            analysis_type=request.analysis_type,
            status="completed",
            source=DataSourceReference(
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                file_id=dataset.file_id,
            ),
            filters_applied=request.filters,
            sample_size=len(dataframe),
            result=self._json_safe(
                analysis_result["result"]
            ),
            warnings=warnings,
        )

    # =====================================================
    # Correlation Analysis
    # =====================================================

    def analyze_correlations(
        self,
        db: Session,
        request: CorrelationRequest,
    ) -> CorrelationResponse:
        """
        Execute correlation analysis.

        Supported:
            - Pearson
            - Spearman

        Returns:
            - Correlation matrix.
            - Pairwise sample counts.
            - Strong correlations.
            - Interpretation.
            - Scientific limitations.

        Uses:
            analysis.correlation.analyze_correlations()
        """

        dataset = self.dataset_service.get_dataset(
            db=db,
            dataset_id=request.dataset_id,
            investigation_id=request.investigation_id,
        )

        dataframe, filter_metadata = (
            self._prepare_dataframe(
                db=db,
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                filters=request.filters,
                selected_columns=request.variables,
            )
        )

        if dataframe.empty:
            raise AnalysisValidationError(
                "No observations remain after filtering."
            )

        try:
            analysis_result = run_correlations(
                data=dataframe,
                columns=request.variables,
                method=request.method.value,
                threshold=request.threshold,
                minimum_samples=request.minimum_samples,
            )

        except (ValueError, KeyError, TypeError) as error:
            raise AnalysisValidationError(
                str(error)
            ) from error

        except Exception as error:
            raise AnalysisExecutionError(
                "Correlation analysis failed."
            ) from error

        warnings = []

        if filter_metadata["excluded_row_count"] > 0:
            warnings.append(
                f"{filter_metadata['excluded_row_count']} observations "
                "were excluded by the filtering conditions."
            )

        # A correlation matrix can be returned even when
        # individual pairs have insufficient valid samples.
        matrix = analysis_result.get(
            "correlation_matrix",
            {}
        )

        unavailable_pairs = 0

        for column_a in request.variables:
            for column_b in request.variables:
                if column_a == column_b:
                    continue

                coefficient = (
                    matrix.get(column_a, {})
                    .get(column_b)
                )

                if coefficient is None:
                    unavailable_pairs += 1

        if unavailable_pairs:
            warnings.append(
                "Some variable pairs could not be correlated "
                "because they contain insufficient valid data "
                "or lack variation."
            )

        return CorrelationResponse(
            investigation_id=request.investigation_id,
            dataset_id=request.dataset_id,
            analysis_type="correlation_matrix",
            status="completed",
            source=DataSourceReference(
                investigation_id=request.investigation_id,
                dataset_id=request.dataset_id,
                file_id=dataset.file_id,
            ),
            filters_applied=request.filters,
            sample_size=len(dataframe),
            result=self._json_safe(
                analysis_result
            ),
            warnings=warnings,
        )