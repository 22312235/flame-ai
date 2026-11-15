
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_DIRECTORY = PROJECT_ROOT / "AI"

sys.path.insert(0, str(AI_DIRECTORY))

from main import app
from api.catalog import get_catalog_service
from catalog.exceptions import CatalogNotFoundError


TEST_INVESTIGATION_ID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def catalog():
    return {
        "investigation_id": TEST_INVESTIGATION_ID,
        "metadata": {},
        "summary": {},
        "datasets": [],
        "variable_catalog": {},
        "variables": [],
        "provenance": {},
    }


@pytest.fixture
def mock_service(catalog):

    class MockCatalogService:

        def list_catalogs(self, limit=50, offset=0):
            return [{
                "investigation_id": TEST_INVESTIGATION_ID,
                "metadata": {},
                "summary": {},
                "dataset_count": 0,
                "processing_status": {},
            }]

        def count_catalogs(self):
            return 12

        def get_catalog(self, investigation_id):
            if investigation_id != TEST_INVESTIGATION_ID:
                raise CatalogNotFoundError(
                    "Investigation not found."
                )
            return catalog

        def rebuild_catalog(self, investigation_id):
            return self.get_catalog(investigation_id)

        def get_datasets(self, investigation_id):
            self.get_catalog(investigation_id)
            return []

        def get_variables(self, investigation_id):
            self.get_catalog(investigation_id)
            return {}

    return MockCatalogService()


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_catalog_service] = (
        lambda: mock_service
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_list_catalogs(client):
    response = client.get("/api/v1/catalogs")

    assert response.status_code == 200
    assert response.json()["total"] == 12
    assert len(response.json()["catalogs"]) == 1


def test_get_catalog(client):
    response = client.get(
        f"/api/v1/catalogs/{TEST_INVESTIGATION_ID}"
    )

    assert response.status_code == 200
    assert response.json()["investigation_id"] == (
        TEST_INVESTIGATION_ID
    )


def test_rebuild_catalog(client):
    response = client.post(
        f"/api/v1/catalogs/{TEST_INVESTIGATION_ID}/rebuild"
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Catalogue generated successfully."
    )


def test_get_catalog_datasets(client):
    response = client.get(
        f"/api/v1/catalogs/{TEST_INVESTIGATION_ID}/datasets"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_catalog_variables(client):
    response = client.get(
        f"/api/v1/catalogs/{TEST_INVESTIGATION_ID}/variables"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_invalid_investigation_id(client):
    response = client.get(
        "/api/v1/catalogs/not-a-uuid"
    )

    assert response.status_code == 400


def test_missing_investigation(client):
    response = client.get(
        "/api/v1/catalogs/123e4567-e89b-12d3-a456-426614174001"
    )

    assert response.status_code == 404
