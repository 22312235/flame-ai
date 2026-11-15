from fastapi import APIRouter, HTTPException, status

from api.dependencies import (
    DatabaseSession,
    FilteringServiceDependency,
)

from api.schemas.filtering import (
    InvestigationFilterRequest,
    InvestigationFilterResponse,
    DatasetFilterRequest,
    DatasetFilterResponse,
    VariableFilterRequest,
    VariableFilterResponse,
    RowFilterRequest,
    RowFilterResponse,
)

from services.dataset_service import (
    DatasetNotFoundError,
    DatasetAccessError,
    DatasetStorageError,
    DatasetColumnError,
)


router = APIRouter(
    prefix="/filtering",
    tags=["Filtering"],
)


# =========================================================
# Shared Error Handling
# =========================================================

def handle_dataset_error(error: Exception) -> None:
    """Translate dataset service exceptions into HTTP errors."""

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

    if isinstance(error, DatasetColumnError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    if isinstance(error, DatasetStorageError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    raise error


# =========================================================
# Investigation Filtering
# =========================================================

@router.post(
    "/investigations",
    response_model=InvestigationFilterResponse,
    summary="Filter investigations",
)
def filter_investigations(
    request: InvestigationFilterRequest,
    db: DatabaseSession,
    service: FilteringServiceDependency,
):
    """
    Search investigations using metadata criteria.

    Useful for:
        - Investigation catalog interfaces.
        - AI-assisted investigation discovery.
    """

    return service.filter_investigations(
        db=db,
        request=request,
    )


# =========================================================
# Dataset Filtering
# =========================================================

@router.post(
    "/datasets",
    response_model=DatasetFilterResponse,
    summary="Filter investigation datasets",
)
def filter_datasets(
    request: DatasetFilterRequest,
    db: DatabaseSession,
    service: FilteringServiceDependency,
):
    """
    Retrieve datasets matching scientific metadata criteria.
    """

    try:
        return service.filter_datasets(
            db=db,
            request=request,
        )

    except (
        DatasetNotFoundError,
        DatasetAccessError,
        DatasetStorageError,
        DatasetColumnError,
    ) as error:
        handle_dataset_error(error)


# =========================================================
# Variable Filtering
# =========================================================

@router.post(
    "/variables",
    response_model=VariableFilterResponse,
    summary="Filter dataset variables",
)
def filter_variables(
    request: VariableFilterRequest,
    db: DatabaseSession,
    service: FilteringServiceDependency,
):
    """
    Retrieve variables matching metadata criteria.

    This endpoint reads variable profiles from PostgreSQL.
    It does not load numerical observations from Parquet.
    """

    try:
        return service.filter_variables(
            db=db,
            request=request,
        )

    except (
        DatasetNotFoundError,
        DatasetAccessError,
        DatasetStorageError,
        DatasetColumnError,
    ) as error:
        handle_dataset_error(error)


# =========================================================
# Numerical Row Filtering
# =========================================================

@router.post(
    "/rows",
    response_model=RowFilterResponse,
    summary="Filter numerical observations",
)
def filter_rows(
    request: RowFilterRequest,
    db: DatabaseSession,
    service: FilteringServiceDependency,
):
    """
    Apply conditions to numerical observations.

    Returns:
        - Matching observations.
        - Pagination metadata.
        - Filtering metadata.
        - Source references.
    """

    try:
        return service.filter_rows(
            db=db,
            request=request,
        )

    except (
        DatasetNotFoundError,
        DatasetAccessError,
        DatasetStorageError,
        DatasetColumnError,
    ) as error:
        handle_dataset_error(error) 