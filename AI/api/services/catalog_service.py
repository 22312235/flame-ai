
from typing import Any

from repositories.catalog_repository import CatalogRepository
from catalog.investigation_catalog_builder import build_investigation_catalog
from catalog.exceptions import CatalogNotFoundError


class CatalogService:
    """Business logic for generating investigation catalogues."""

    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    def get_catalog(self, investigation_id: str) -> dict[str, Any]:
        investigation = self.repository.get_investigation(
            investigation_id
        )

        if investigation is None:
            raise CatalogNotFoundError(
                f"Investigation '{investigation_id}' was not found."
            )

        datasets = self.repository.get_datasets(investigation_id)

        return build_investigation_catalog(
            investigation=investigation,
            datasets=datasets,
        )

    def rebuild_catalog(self, investigation_id: str) -> dict[str, Any]:
        """Regenerate a catalogue using the latest PostgreSQL data."""

        return self.get_catalog(investigation_id)

    def list_catalogs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        investigations = self.repository.list_investigations(
            limit=limit,
            offset=offset,
        )

        catalogs = []

        for investigation in investigations:
            investigation_id = investigation["investigation_id"]

            catalog = self.get_catalog(investigation_id)

            catalogs.append({
                "investigation_id": investigation_id,
                "metadata": catalog.get("metadata", {}),
                "summary": catalog.get("summary", {}),
                "dataset_count": catalog.get("dataset_count", 0),
                "processing_status": catalog.get(
                    "processing_status", {}
                ),
            })

        return catalogs

    def count_catalogs(self) -> int:
        """Return the total number of investigations."""

        return self.repository.count_investigations()

    def get_datasets(
        self,
        investigation_id: str,
    ) -> list[dict[str, Any]]:
        investigation = self.repository.get_investigation(
            investigation_id
        )

        if investigation is None:
            raise CatalogNotFoundError(
                f"Investigation '{investigation_id}' was not found."
            )

        return self.repository.get_datasets(investigation_id)

    def get_variables(
        self,
        investigation_id: str,
    ) -> Any:
        catalog = self.get_catalog(investigation_id)
        return catalog.get("variable_catalog", {})
