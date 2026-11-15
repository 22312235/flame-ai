"""Business logic services for the Flame API."""

# ============================================================
# Catalog service
# ============================================================

from .catalog_service import CatalogService

# ============================================================
# Dataset service
# ============================================================

from .dataset_service import (
    DatasetService,
    DatasetServiceError,
    DatasetNotFoundError,
    DatasetAccessError,
    DatasetStorageError,
    DatasetColumnError,
)

# ============================================================
# Filtering service
# ============================================================

from .filtering_service import FilteringService

# ============================================================
# Analysis service
# ============================================================

from .analysis_service import (
    AnalysisService,
    AnalysisServiceError,
    AnalysisValidationError,
    AnalysisExecutionError,
)


__all__ = [
    # Catalog
    "CatalogService",

    # Dataset
    "DatasetService",
    "DatasetServiceError",
    "DatasetNotFoundError",
    "DatasetAccessError",
    "DatasetStorageError",
    "DatasetColumnError",

    # Filtering
    "FilteringService",

    # Analysis
    "AnalysisService",
    "AnalysisServiceError",
    "AnalysisValidationError",
    "AnalysisExecutionError",
]