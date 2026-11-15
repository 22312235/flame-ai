from __future__ import annotations
from .exceptions import (
    CatalogNotFoundError,
    CatalogRepositoryError,
)

import json
import os
import tempfile
import threading

from pathlib import Path
from typing import Any
from hashlib import sha256


class CatalogNotFoundError(Exception):
    pass


class CatalogRepositoryError(Exception):
    pass


class JSONCatalogRepository:
    """
    Local JSON implementation of the catalog repository.

    Intended for development and single-process prototypes.

    For multi-worker production deployments, use a shared database
    repository instead.
    """

    def __init__(self, storage_directory: str | Path):
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

    def _get_path(self, investigation_id: str) -> Path:
        """
        Generate a safe, deterministic filename.

        The original investigation ID is stored inside the JSON document.
        """

        identifier = str(investigation_id)

        if not identifier.strip():
            raise ValueError("investigation_id cannot be empty.")

        filename = sha256(
            identifier.encode("utf-8")
        ).hexdigest()

        return self.storage_directory / f"{filename}.json"

    def save(self, catalog: dict) -> dict:
        """
        Persist a complete catalog using an atomic file replacement.
        """

        if not isinstance(catalog, dict):
            raise TypeError("Catalog must be a dictionary.")

        investigation_id = catalog.get("investigation_id")

        if not investigation_id:
            raise ValueError(
                "Catalog must contain an investigation_id."
            )

        path = self._get_path(str(investigation_id))

        try:
            serialized = json.dumps(
                catalog,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

            with self._lock:
                file_descriptor, temporary_path = tempfile.mkstemp(
                    dir=self.storage_directory,
                    prefix=".catalog_",
                    suffix=".tmp",
                )

                try:
                    with os.fdopen(
                        file_descriptor,
                        "w",
                        encoding="utf-8",
                    ) as file:
                        file.write(serialized)
                        file.flush()
                        os.fsync(file.fileno())

                    os.replace(temporary_path, path)

                except Exception:
                    if os.path.exists(temporary_path):
                        os.unlink(temporary_path)

                    raise

            return catalog

        except (TypeError, ValueError, OSError) as exc:
            raise CatalogRepositoryError(
                f"Could not save catalog {investigation_id}: {exc}"
            ) from exc

    def get(self, investigation_id: str) -> dict:
        """
        Retrieve one investigation catalog.
        """

        path = self._get_path(investigation_id)

        with self._lock:
            if not path.exists():
                raise CatalogNotFoundError(
                    f"Catalog not found: {investigation_id}"
                )

            try:
                with path.open("r", encoding="utf-8") as file:
                    catalog = json.load(file)

            except (OSError, json.JSONDecodeError) as exc:
                raise CatalogRepositoryError(
                    f"Could not read catalog {investigation_id}: {exc}"
                ) from exc

        if str(catalog.get("investigation_id")) != str(investigation_id):
            raise CatalogRepositoryError(
                "Catalog identifier does not match its storage key."
            )

        return catalog

    def exists(self, investigation_id: str) -> bool:
        return self._get_path(investigation_id).exists()

    def delete(self, investigation_id: str) -> bool:
        """
        Delete one catalog.

        Returns False if it did not exist.
        """

        path = self._get_path(investigation_id)

        with self._lock:
            if not path.exists():
                return False

            try:
                path.unlink()
                return True

            except OSError as exc:
                raise CatalogRepositoryError(
                    f"Could not delete catalog {investigation_id}: {exc}"
                ) from exc

    def list_catalogs(self) -> list[dict]:
        """
        Return lightweight summaries of stored catalogs.

        Dataset records and variable profiles are not included.
        """

        summaries = []

        with self._lock:
            paths = list(self.storage_directory.glob("*.json"))

            for path in paths:
                try:
                    with path.open("r", encoding="utf-8") as file:
                        catalog = json.load(file)

                    metadata = catalog.get("metadata", {})
                    summary = catalog.get("summary", {})

                    summaries.append({
                        "investigation_id": catalog.get("investigation_id"),
                        "title": metadata.get("title"),
                        "description": metadata.get("description"),
                        "dataset_count": summary.get("dataset_count", 0),
                        "variable_count": summary.get("variable_count", 0),
                        "processing_status": (
                            summary.get("processing", {}).get("overall_status")
                        ),
                        "generated_at": (
                            catalog.get("provenance", {}).get("generated_at")
                        ),
                    })

                except (OSError, json.JSONDecodeError):
                    # Do not silently present corrupted records as valid.
                    # The caller can inspect storage for recovery.
                    continue

        return sorted(
            summaries,
            key=lambda item: str(item["investigation_id"]),
        )