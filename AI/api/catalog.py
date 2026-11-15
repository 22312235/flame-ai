
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from repositories.catalog_repository import CatalogRepository
from services.catalog_service import CatalogService
from catalog.exceptions import CatalogNotFoundError

from schemas.catalog import (
    CatalogResponse,
    CatalogListResponse,
    CatalogDatasetsResponse,
    CatalogVariablesResponse,
    CatalogRebuildResponse,
)


router = APIRouter(
    prefix="/api/v1/catalogs",
    tags=["Catalogs"],
)


def get_catalog_service():
    """Provide a catalogue service with a managed database session."""

    from Database.connection import SessionLocal

    db: Session = SessionLocal()

    try:
        repository = CatalogRepository(db)
        service = CatalogService(repository)
        yield service
    finally:
        db.close()


def validate_investigation_id(investigation_id: str) -> str:
    try:
        UUID(investigation_id)
        return investigation_id
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid investigation ID.",
        )


@router.get("", response_model=CatalogListResponse)
def list_catalogs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: CatalogService = Depends(get_catalog_service),
):
    catalogs = service.list_catalogs(
        limit=limit,
        offset=offset,
    )

    total = service.count_catalogs()

    return {
        "catalogs": catalogs,
        "total": total,
    }


@router.get("/{investigation_id}", response_model=CatalogResponse)
def get_catalog(
    investigation_id: str,
    service: CatalogService = Depends(get_catalog_service),
):
    validate_investigation_id(investigation_id)

    try:
        return service.get_catalog(investigation_id)
    except CatalogNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.post(
    "/{investigation_id}/rebuild",
    response_model=CatalogRebuildResponse,
)
def rebuild_catalog(
    investigation_id: str,
    service: CatalogService = Depends(get_catalog_service),
):
    validate_investigation_id(investigation_id)

    try:
        catalog = service.rebuild_catalog(investigation_id)

        return {
            "message": "Catalogue generated successfully.",
            "investigation_id": investigation_id,
            "catalog": catalog,
        }
    except CatalogNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get(
    "/{investigation_id}/datasets",
    response_model=CatalogDatasetsResponse,
)
def get_catalog_datasets(
    investigation_id: str,
    service: CatalogService = Depends(get_catalog_service),
):
    validate_investigation_id(investigation_id)

    try:
        datasets = service.get_datasets(investigation_id)

        return {
            "investigation_id": investigation_id,
            "datasets": datasets,
            "total": len(datasets),
        }
    except CatalogNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get(
    "/{investigation_id}/variables",
    response_model=CatalogVariablesResponse,
)
def get_catalog_variables(
    investigation_id: str,
    service: CatalogService = Depends(get_catalog_service),
):
    validate_investigation_id(investigation_id)

    try:
        variables = service.get_variables(investigation_id)

        total = (
            len(variables)
            if isinstance(variables, (list, dict))
            else 0
        )

        return {
            "investigation_id": investigation_id,
            "variables": variables,
            "total": total,
        }
    except CatalogNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )
