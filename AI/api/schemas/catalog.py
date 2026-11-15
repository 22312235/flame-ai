from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CatalogResponse(BaseModel):
    """Full investigation catalogue response."""

    model_config = ConfigDict(extra="allow")

    schema_version: str | None = None
    investigation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    variable_catalog: Any = None
    variables: Any = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class CatalogListResponse(BaseModel):
    """Response containing catalogue summaries."""

    catalogs: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class CatalogDatasetsResponse(BaseModel):
    """Datasets belonging to an investigation catalogue."""

    investigation_id: str
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class CatalogVariablesResponse(BaseModel):
    """Variables belonging to an investigation catalogue."""

    investigation_id: str
    variables: Any = Field(default_factory=list)
    total: int = 0


class CatalogRebuildResponse(BaseModel):
    """Result of rebuilding an investigation catalogue."""

    message: str
    investigation_id: str
    catalog: CatalogResponse