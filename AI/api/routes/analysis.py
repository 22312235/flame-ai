from fastapi import APIRouter, HTTPException, status

from api.dependencies import (
    DatabaseSession,
    AnalysisServiceDependency,
)

from api.schemas.analysis import (
    StatisticsRequest,
    StatisticsResponse,
    CorrelationRequest,
    CorrelationResponse,
)

from services.dataset_service import (
    DatasetNotFoundError,
    DatasetAccessError,
    DatasetStorageError,
    DatasetColumnError,
)

from services.analysis_service import (
    AnalysisValidationError,
    AnalysisExecutionError,
)


router = APIRouter(
    prefix="/analysis",
    tags=["Scientific Analysis"],
)


# =========================================================
# Error Handling
# =========================================================

def handle_analysis_error(error: Exception) -> None:
    """Translate service errors into appropriate HTTP responses."""

    if isinstance(error, DatasetNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if isinstance(error, DatasetAccessError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found in the requested investigation.",
        ) from error

    if isinstance(
        error,
        (DatasetColumnError, AnalysisValidationError),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    if isinstance(error, DatasetStorageError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if isinstance(error, AnalysisExecutionError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scientific analysis could not be completed.",
        ) from error

    raise error


# =========================================================
# Statistical Analysis
# =========================================================

@router.post(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Analyze dataset statistics",
)
def analyze_statistics(
    request: StatisticsRequest,
    db: DatabaseSession,
    service: AnalysisServiceDependency,
):
    """
    Calculate statistical measurements.

    Supported analysis types:
        - descriptive
        - frequency
        - grouped
        - summary

    Filtering conditions may be applied before analysis.
    """

    try:
        return service.analyze_statistics(
            db=db,
            request=request,
        )

    except (
        DatasetNotFoundError,
        DatasetAccessError,
        DatasetStorageError,
        DatasetColumnError,
        AnalysisValidationError,
        AnalysisExecutionError,
    ) as error:
        handle_analysis_error(error)


# =========================================================
# Correlation Analysis
# =========================================================

@router.post(
    "/correlation",
    response_model=CorrelationResponse,
    summary="Analyze variable correlations",
)
def analyze_correlations(
    request: CorrelationRequest,
    db: DatabaseSession,
    service: AnalysisServiceDependency,
):
    """
    Calculate correlations between numerical variables.

    Supported methods:
        - Pearson
        - Spearman

    Returns:
        - Correlation matrix.
        - Pairwise sample counts.
        - Strong correlations.
        - Scientific limitations.
    """

    try:
        return service.analyze_correlations(
            db=db,
            request=request,
        )

    except (
        DatasetNotFoundError,
        DatasetAccessError,
        DatasetStorageError,
        DatasetColumnError,
        AnalysisValidationError,
        AnalysisExecutionError,
    ) as error:
        handle_analysis_error(error)