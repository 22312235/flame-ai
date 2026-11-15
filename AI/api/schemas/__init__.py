"""Pydantic request and response schemas for the Flame API."""

# ============================================================
# Common schemas
# ============================================================

from .common import (
    APIModel,
    FilterOperator,
    FilterCombine,
    FilterCondition,
    FilterSet,
    PaginationParams,
    PaginationMetadata,
    DataSourceReference,
    APIErrorDetail,
    APIErrorResponse,
)

# ============================================================
# Catalog schemas
# ============================================================

from .catalog import (
    CatalogResponse,
    CatalogListResponse,
    CatalogDatasetsResponse,
    CatalogVariablesResponse,
    CatalogRebuildResponse,
)

# ============================================================
# Filtering schemas
# ============================================================

from .filtering import (
    InvestigationFilterRequest,
    InvestigationFilterResponse,
    DatasetFilterRequest,
    DatasetFilterResponse,
    VariableFilterRequest,
    VariableFilterResponse,
    RowFilterRequest,
    RowFilterResponse,
)

# ============================================================
# Analysis schemas
# ============================================================

from .analysis import (
    StatisticsAnalysisType,
    CorrelationMethod,
    StatisticsRequest,
    StatisticsResponse,
    CorrelationRequest,
    CorrelationResponse,
)


__all__ = [
    # Common
    "APIModel",
    "FilterOperator",
    "FilterCombine",
    "FilterCondition",
    "FilterSet",
    "PaginationParams",
    "PaginationMetadata",
    "DataSourceReference",
    "APIErrorDetail",
    "APIErrorResponse",

    # Catalog
    "CatalogResponse",
    "CatalogListResponse",
    "CatalogDatasetsResponse",
    "CatalogVariablesResponse",
    "CatalogRebuildResponse",

    # Filtering
    "InvestigationFilterRequest",
    "InvestigationFilterResponse",
    "DatasetFilterRequest",
    "DatasetFilterResponse",
    "VariableFilterRequest",
    "VariableFilterResponse",
    "RowFilterRequest",
    "RowFilterResponse",

    # Analysis
    "StatisticsAnalysisType",
    "CorrelationMethod",
    "StatisticsRequest",
    "StatisticsResponse",
    "CorrelationRequest",
    "CorrelationResponse",
]