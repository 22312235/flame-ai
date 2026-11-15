from __future__ import annotations
from .exceptions import CatalogNotFoundError

from datetime import datetime
from typing import Any, Protocol

from .investigation_catalog_builder import (
    build_investigation_catalog,
)


class CatalogRepository(Protocol):
    """
    Contract that every catalog storage implementation must satisfy.
    """

    def save(self, catalog: dict) -> dict:
        ...

    def get(self, investigation_id: str) -> dict:
        ...

    def exists(self, investigation_id: str) -> bool:
        ...

    def delete(self, investigation_id: str) -> bool:
        ...

    def list_catalogs(self) -> list[dict]:
        ...


class CatalogManager:
    """
    Manages investigation catalog creation, retrieval,
    synchronization, and deletion.
    """

    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    # -----------------------------------------------------
    # Creation and rebuilding
    # -----------------------------------------------------

    def create_catalog(
        self,
        investigation: dict,
        datasets: list[dict],
        *,
        profiles_by_dataset: dict[str, dict] | None = None,
    ) -> dict:
        """
        Create a catalog for a new investigation.

        Raises an error if a catalog already exists.
        """

        investigation_id = self._get_investigation_id(investigation)

        if self.repository.exists(investigation_id):
            raise ValueError(
                f"Catalog already exists for {investigation_id}."
            )

        catalog = self._build(
            investigation,
            datasets,
            profiles_by_dataset=profiles_by_dataset,
        )

        return self.repository.save(catalog)

    def rebuild_catalog(
        self,
        investigation: dict,
        datasets: list[dict],
        *,
        profiles_by_dataset: dict[str, dict] | None = None,
    ) -> dict:
        """
        Rebuild an existing catalog from the latest authoritative
        investigation and dataset records.

        This operation also creates the catalog if it does not exist.
        """

        catalog = self._build(
            investigation,
            datasets,
            profiles_by_dataset=profiles_by_dataset,
        )

        return self.repository.save(catalog)

    def _build(
        self,
        investigation: dict,
        datasets: list[dict],
        *,
        profiles_by_dataset: dict[str, dict] | None = None,
    ) -> dict:

        return build_investigation_catalog(
            investigation,
            datasets,
            profiles_by_dataset=profiles_by_dataset,
        )

    # -----------------------------------------------------
    # Retrieval
    # -----------------------------------------------------

    def get_catalog(self, investigation_id: str) -> dict:
        """
        Retrieve a complete investigation catalog.
        """

        return self.repository.get(str(investigation_id))

    def catalog_exists(self, investigation_id: str) -> bool:
        return self.repository.exists(str(investigation_id))

    def list_catalogs(self) -> list[dict]:
        """
        Retrieve lightweight catalog summaries.
        """

        return self.repository.list_catalogs()

    # -----------------------------------------------------
    # Dataset synchronization
    # -----------------------------------------------------

    def synchronize_datasets(
        self,
        investigation: dict,
        datasets: list[dict],
        *,
        profiles_by_dataset: dict[str, dict] | None = None,
    ) -> dict:
        """
        Synchronize a catalog with the latest complete dataset registry.

        The supplied datasets are treated as the authoritative list
        for this investigation.

        This means:
          - New datasets are added.
          - Existing datasets are updated.
          - Datasets absent from the supplied list are removed
            from the generated catalog.

        Original scientific files are not deleted.
        """

        return self.rebuild_catalog(
            investigation,
            datasets,
            profiles_by_dataset=profiles_by_dataset,
        )

    def upsert_dataset(
        self,
        investigation: dict,
        dataset: dict,
        *,
        profile: dict | None = None,
    ) -> dict:
        """
        Add or update one dataset without replacing other datasets.
        """

        investigation_id = self._get_investigation_id(investigation)

        try:
            current_catalog = self.get_catalog(investigation_id)
            existing_datasets = current_catalog.get("datasets", [])

        except CatalogNotFoundError:
            existing_datasets = []

        dataset_id = self._get_dataset_id(dataset)

        updated_datasets = []
        found = False

        for existing in existing_datasets:
            existing_id = self._get_dataset_id(existing)

            if existing_id == dataset_id:
                updated_datasets.append(dataset)
                found = True
            else:
                updated_datasets.append(existing)

        if not found:
            updated_datasets.append(dataset)

        profiles = {}

        # Retain the profiles already embedded in the existing
        # normalized dataset records, and apply the new profile
        # explicitly if one was supplied.
        if profile is not None:
            profiles[dataset_id] = profile

        return self.rebuild_catalog(
            investigation,
            updated_datasets,
            profiles_by_dataset=profiles,
        )

    def remove_dataset(
        self,
        investigation: dict,
        dataset_id: str,
    ) -> dict:
        """
        Remove a dataset from the catalog and rebuild its aggregates.

        This does not delete the original file or database record.
        """

        investigation_id = self._get_investigation_id(investigation)

        current_catalog = self.get_catalog(investigation_id)

        existing_datasets = current_catalog.get("datasets", [])

        remaining_datasets = [
            dataset
            for dataset in existing_datasets
            if self._get_dataset_id(dataset) != str(dataset_id)
        ]

        if len(remaining_datasets) == len(existing_datasets):
            raise ValueError(
                f"Dataset {dataset_id} was not found in {investigation_id}."
            )

        return self.rebuild_catalog(
            investigation,
            remaining_datasets,
        )

    # -----------------------------------------------------
    # Deletion
    # -----------------------------------------------------

    def delete_catalog(self, investigation_id: str) -> bool:
        """
        Delete the generated catalog.

        Does not delete investigation records or scientific files.
        """

        return self.repository.delete(str(investigation_id))

    # -----------------------------------------------------
    # Validation helpers
    # -----------------------------------------------------

    @staticmethod
    def _get_investigation_id(investigation: dict) -> str:
        if not isinstance(investigation, dict):
            raise TypeError("Investigation must be a dictionary.")

        investigation_id = (
            investigation.get("investigation_id")
            or investigation.get("id")
        )

        if not investigation_id:
            raise ValueError("Investigation ID is required.")

        return str(investigation_id)

    @staticmethod
    def _get_dataset_id(dataset: dict) -> str:
        if not isinstance(dataset, dict):
            raise TypeError("Dataset must be a dictionary.")

        dataset_id = (
            dataset.get("dataset_id")
            or dataset.get("id")
            or dataset.get("file_id")
        )

        if not dataset_id:
            raise ValueError("Dataset ID is required.")

        return str(dataset_id)