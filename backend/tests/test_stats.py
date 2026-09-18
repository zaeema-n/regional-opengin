from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from main import app
from models import Entity, Kind, Relation
from routers.opengin import read_service
from services.stats_service import normalize_attribute_table

GENDER_HUB = Entity(
    id="population-gender",
    name="Region Population by Gender",
    kind=Kind(major="Category", minor="DataCategory"),
)
UNKNOWN_HUB = Entity(
    id="unmapped-hub",
    name="Unmapped Dataset",
    kind=Kind(major="Category", minor="DataCategory"),
)
WESTERN = Entity(
    id="LK-1",
    name="Western",
    kind=Kind(major="region", minor="country-level-1+lk-province"),
)

GENDER_TABLE = {
    "columns": ["entity_id", "male", "female"],
    "rows": [["LK-1", 1234.0, 5678.0]],
}

ENTITIES_BY_ID = {
    entity.id: entity for entity in (GENDER_HUB, UNKNOWN_HUB, WESTERN)
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _relation(related_id: str) -> Relation:
    return Relation(
        name="AS_CATEGORY",
        relatedEntityId=related_id,
        direction="OUTGOING",
    )


async def _get_entities(entity: Entity):
    match = ENTITIES_BY_ID.get(entity.id)
    return [match] if match else []


def _mock_read(*, related_ids: list[str], attribute_payload=None, attribute_error=None):
    read_service.fetch_relations = AsyncMock(
        return_value=[_relation(related_id) for related_id in related_ids]
    )
    read_service.get_entities = AsyncMock(side_effect=_get_entities)
    if attribute_error is not None:
        read_service.get_entity_attribute = AsyncMock(side_effect=attribute_error)
    else:
        read_service.get_entity_attribute = AsyncMock(return_value=attribute_payload)


def test_get_region_stats_returns_gender_table(client: TestClient):
    _mock_read(related_ids=["population-gender"], attribute_payload=GENDER_TABLE)

    response = client.get("/v1/regions/LK-1/stats")

    assert response.status_code == 200
    assert response.json() == {
        "region_id": "LK-1",
        "datasets": [
            {
                "id": "population-gender",
                "name": "Region Population by Gender",
                "kind": {"major": "Category", "minor": "DataCategory"},
                "attribute": "Population by Gender",
                "columns": ["entity_id", "male", "female"],
                "rows": [["LK-1", 1234.0, 5678.0]],
            }
        ],
    }

    relation = read_service.fetch_relations.await_args.args[1]
    assert read_service.fetch_relations.await_args.args[0] == "LK-1"
    assert relation.name == "AS_CATEGORY"
    assert relation.direction == "OUTGOING"

    attribute_call = read_service.get_entity_attribute.await_args.kwargs
    assert attribute_call["entityId"] == "population-gender"
    assert attribute_call["attributeName"] == "Population by Gender"
    record = attribute_call["filters"].records[0]
    assert record.field_name == "entity_id"
    assert record.operator == "eq"
    assert record.value == "LK-1"


def test_get_region_stats_drops_non_data_category(client: TestClient):
    _mock_read(related_ids=["LK-1"], attribute_payload=GENDER_TABLE)

    response = client.get("/v1/regions/LK-1/stats")

    assert response.status_code == 200
    assert response.json() == {"region_id": "LK-1", "datasets": []}
    read_service.get_entities.assert_awaited()
    read_service.get_entity_attribute.assert_not_awaited()


def test_get_region_stats_skips_hub_missing_yaml_attribute(client: TestClient):
    _mock_read(related_ids=["unmapped-hub"], attribute_payload=GENDER_TABLE)

    response = client.get("/v1/regions/LK-1/stats")

    assert response.status_code == 200
    assert response.json() == {"region_id": "LK-1", "datasets": []}
    read_service.get_entities.assert_awaited()
    read_service.get_entity_attribute.assert_not_awaited()


def test_get_region_stats_empty_as_category(client: TestClient):
    _mock_read(related_ids=[], attribute_payload=GENDER_TABLE)

    response = client.get("/v1/regions/LK-1/stats")

    assert response.status_code == 200
    assert response.json() == {"region_id": "LK-1", "datasets": []}
    read_service.fetch_relations.assert_awaited_once()
    read_service.get_entities.assert_not_awaited()
    read_service.get_entity_attribute.assert_not_awaited()


def test_get_region_stats_failed_table_is_empty(client: TestClient):
    _mock_read(
        related_ids=["population-gender"],
        attribute_error=RuntimeError("opengin unavailable"),
    )

    response = client.get("/v1/regions/LK-1/stats")

    assert response.status_code == 200
    dataset = response.json()["datasets"][0]
    assert dataset["id"] == "population-gender"
    assert dataset["columns"] == []
    assert dataset["rows"] == []


def test_normalize_attribute_table_bare_and_values_envelope():
    assert normalize_attribute_table(GENDER_TABLE) == (
        ["entity_id", "male", "female"],
        [["LK-1", 1234.0, 5678.0]],
    )
    assert normalize_attribute_table({"values": [GENDER_TABLE]}) == (
        ["entity_id", "male", "female"],
        [["LK-1", 1234.0, 5678.0]],
    )


def test_normalize_attribute_table_concatenates_chunks():
    payload = {
        "values": [
            {"columns": ["entity_id", "male"], "rows": [["LK-1", 1]]},
            {"columns": ["entity_id", "male"], "rows": [["LK-11", 2]]},
        ]
    }
    columns, rows = normalize_attribute_table(payload)
    assert columns == ["entity_id", "male"]
    assert rows == [["LK-1", 1], ["LK-11", 2]]


def test_normalize_attribute_table_empty():
    assert normalize_attribute_table(None) == ([], [])
    assert normalize_attribute_table({}) == ([], [])
    assert normalize_attribute_table([]) == ([], [])
