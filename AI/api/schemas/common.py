from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class APIModel(BaseModel):
    """Base configuration shared by API schemas."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


# =========================================================
# Filtering Operators
# =========================================================

class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"

    BETWEEN = "between"

    IN = "in"
    NOT_IN = "not_in"

    CONTAINS = "contains"

    IS_MISSING = "is_missing"
    NOT_MISSING = "not_missing"


class FilterCombine(str, Enum):
    AND = "and"
    OR = "or"


class FilterCondition(APIModel):
    """
    Represents one filtering condition.

    Compatible with:
        filtering.variable_filter.apply_condition()
        filtering.variable_filter.filter_dataframe_rows()
    """

    column: str = Field(
        min_length=1,
        max_length=300,
    )

    operator: FilterOperator

    value: Any = None

    @model_validator(mode="after")
    def validate_condition(self):
        operator = self.operator

        if operator in {
            FilterOperator.IS_MISSING,
            FilterOperator.NOT_MISSING,
        }:
            if self.value is not None:
                raise ValueError(
                    f"Operator '{operator.value}' does not accept a value."
                )

            return self

        if self.value is None:
            raise ValueError(
                f"Operator '{operator.value}' requires a value."
            )

        if operator == FilterOperator.BETWEEN:
            if (
                not isinstance(self.value, list)
                or len(self.value) != 2
            ):
                raise ValueError(
                    "The between operator requires [minimum, maximum]."
                )

            try:
                lower = float(self.value[0])
                upper = float(self.value[1])
            except (TypeError, ValueError):
                raise ValueError(
                    "Between boundaries must be numeric."
                )

            if lower > upper:
                raise ValueError(
                    "The lower boundary cannot exceed the upper boundary."
                )

        if operator in {
            FilterOperator.IN,
            FilterOperator.NOT_IN,
        }:
            if not isinstance(self.value, list):
                raise ValueError(
                    f"Operator '{operator.value}' requires a list."
                )

        if operator in {
            FilterOperator.GT,
            FilterOperator.GTE,
            FilterOperator.LT,
            FilterOperator.LTE,
        }:
            try:
                float(self.value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Operator '{operator.value}' requires a numeric value."
                )

        return self


class FilterSet(APIModel):
    """A reusable collection of filtering conditions."""

    conditions: list[FilterCondition] = Field(
        default_factory=list,
        max_length=30,
    )

    combine: FilterCombine = FilterCombine.AND


# =========================================================
# Pagination
# =========================================================

class PaginationParams(APIModel):
    """Pagination parameters for data retrieval."""

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )


class PaginationMetadata(APIModel):
    """Pagination information returned to clients."""

    total: int = Field(ge=0)

    limit: int = Field(ge=1)

    offset: int = Field(ge=0)

    returned: int = Field(ge=0)

    has_more: bool


# =========================================================
# Data Provenance
# =========================================================

class DataSourceReference(APIModel):
    """
    Identifies the scientific data used in an operation.
    """

    investigation_id: UUID | None = None

    dataset_id: UUID | None = None

    file_id: UUID | None = None


# =========================================================
# API Errors
# =========================================================

class APIErrorDetail(APIModel):
    code: str

    message: str

    details: dict[str, Any] | None = None


class APIErrorResponse(APIModel):
    error: APIErrorDetail