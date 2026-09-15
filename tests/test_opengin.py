from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.opengin import ingestion_service, read_service

SAMPLE_ENTITY = {
    "id": "org_01",
    "name": "Finance",
    "kind": {"major": "Organisation", "minor": "department"},
    "created": "2020-01-01T00:00:00Z",
    "terminated": "",
}

SAMPLE_RELATION = {
    "name": "AS_DEPARTMENT",
    "activeAt": "",
    "relatedEntityId": "org_02",
    "startTime": "2020-01-01T00:00:00Z",
    "endTime": "",
    "id": "rel_01",
    "direction": "OUTGOING",
}

SAMPLE_CREATE = {
    "id": "org_01",
    "kind": {"major": "Organisation", "minor": "department"},
    "created": "2020-01-01T00:00:00Z",
    "terminated": "",
    "name": {"startTime": "", "endTime": "", "value": "Finance"},
    "metadata": [],
    "attributes": [],
    "relationships": [],
}


@pytest.fixture
def client():
    read_service.get_entities = AsyncMock(return_value=[SAMPLE_ENTITY])
    read_service.fetch_relations = AsyncMock(return_value=[SAMPLE_RELATION])
    read_service.get_entity_metadata = AsyncMock(
        return_value={"id": "org_01", "source": "opengin"}
    )
    read_service.get_entity_attribute = AsyncMock(
        return_value={"columns": ["year"], "rows": [[2020]]}
    )
    ingestion_service.create_entity = AsyncMock(return_value={"id": "org_01"})
    ingestion_service.update_entity = AsyncMock(return_value={"id": "org_01"})

    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_entities(client: TestClient):
    response = client.post("/v1/entities/search", json=SAMPLE_ENTITY)
    assert response.status_code == 200
    assert response.json()[0]["id"] == "org_01"
    read_service.get_entities.assert_awaited_once()


def test_fetch_relations(client: TestClient):
    response = client.post(
        "/v1/entities/org_01/relations",
        json={"name": "AS_DEPARTMENT", "direction": "OUTGOING"},
    )
    assert response.status_code == 200
    assert response.json()[0]["relatedEntityId"] == "org_02"
    read_service.fetch_relations.assert_awaited_once()


def test_get_entity_metadata(client: TestClient):
    response = client.get("/v1/entities/org_01/metadata")
    assert response.status_code == 200
    assert response.json()["id"] == "org_01"
    read_service.get_entity_metadata.assert_awaited_once()


def test_get_entity_attribute(client: TestClient):
    response = client.post(
        "/v1/entities/org_01/attributes/budget",
        params={"startTime": "2020-01-01T00:00:00Z"},
        json={"records": [{"field_name": "year", "operator": "eq", "value": "2020"}]},
    )
    assert response.status_code == 200
    assert "columns" in response.json()
    read_service.get_entity_attribute.assert_awaited_once()


def test_create_entity(client: TestClient):
    response = client.post("/entities", json=SAMPLE_CREATE)
    assert response.status_code == 200
    assert response.json()["id"] == "org_01"
    ingestion_service.create_entity.assert_awaited_once()


def test_update_entity(client: TestClient):
    response = client.put("/entities/org_01", json=SAMPLE_CREATE)
    assert response.status_code == 200
    assert response.json()["id"] == "org_01"
    ingestion_service.update_entity.assert_awaited_once()
