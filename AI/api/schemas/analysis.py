from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from api.schemas.common import (
    APIModel,
    DataSourceReference,
    FilterSet,
)


# =========================================================
# Analysis Types
# =========================================================

class StatisticsAnalysisType(str, Enum):
    DESCRIPTIVE = "descriptive"
    FREQUENCY = "frequency"
    GROUPED = "grouped"
    SUMMARY = "summary"


class CorrelationMethod(str, Enum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"


# =========================================================
# Statistical Analysis
# =========================================================

class StatisticsRequest(APIModel):
    """
    Request statistical analysis for a dataset.

    Compatible with:
        analysis.statistics.analyze_statistics()
    """

    investigation_id: UUID

    dataset_id: UUID

    analysis_type: StatisticsAnalysisType

    filters: FilterSet = Field(
        default_factory=FilterSet,
    )

    # Descriptive and frequency analysis.
    column: str | None = None

    # Summary analysis.
    columns: list[str] | None = None

    # Grouped analysis.
    value_column: str | None = None
    group_column: str | None = None

    # Frequency analysis.
    top_n: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    @model_validator(mode="after")
    def validate_analysis_parameters(self):
        analysis_type = self.analysis_type

        if analysis_type in {
            StatisticsAnalysisType.DESCRIPTIVE,
            StatisticsAnalysisType.FREQUENCY,
        }:
            if not self.column:
                raise ValueError(
                    f"'{analysis_type.value}' analysis requires 'column'."
                )

        elif analysis_type == StatisticsAnalysisType.GROUPED:
            if not self.value_column:
                raise ValueError(
                    "Grouped analysis requires 'value_column'."
                )

            if not self.group_column:
                raise ValueError(
                    "Grouped analysis requires 'group_column'."
                )

        elif analysis_type == StatisticsAnalysisType.SUMMARY:
            if self.columns is not None and not self.columns:
                raise ValueError(
                    "Summary columns cannot be an empty list."
                )

        return self


class StatisticsResponse(APIModel):
    investigation_id: UUID

    dataset_id: UUID

    analysis_type: StatisticsAnalysisType

    status: str = "completed"

    source: DataSourceReference

    filters_applied: FilterSet

    sample_size: int = Field(ge=0)

    result: dict[str, Any]

    warnings: list[str] = Field(
        default_factory=list,
    )


# =========================================================
# Correlation Analysis
# =========================================================

class CorrelationRequest(APIModel):
    """
    Request correlation analysis for selected variables.

    Compatible with:
        analysis.correlation.analyze_correlations()
    """

    investigation_id: UUID

    dataset_id: UUID

    variables: list[str] = Field(
        min_length=2,
        max_length=30,
    )

    method: CorrelationMethod = CorrelationMethod.PEARSON

    threshold: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    minimum_samples: int = Field(
        default=3,
        ge=3,
    )

    filters: FilterSet = Field(
        default_factory=FilterSet,
    )

    @model_validator(mode="after")
    def validate_variables(self):
        if len(set(self.variables)) != len(self.variables):
            raise ValueError(
                "Correlation variables must be unique."
            )

        return self


class CorrelationResponse(APIModel):
    investigation_id: UUID

    dataset_id: UUID

    analysis_type: str = "correlation_matrix"

    status: str = "completed"

    source: DataSourceReference

    filters_applied: FilterSet

    sample_size: int = Field(ge=0)

    result: dict[str, Any]

    warnings: list[str] = Field(
        default_factory=list,
    )