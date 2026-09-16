from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from main import app
from models import Entity, Kind, Relation
from routers.opengin import read_service
from routers.regions import region_service
from services.region_service import extract_geojson

SRI_LANKA = Entity(
    id="LK",
    name="Sri Lanka",
    kind=Kind(major="region", minor="country"),
)
WESTERN = Entity(
    id="LK-1",
    name="Western",
    kind=Kind(major="region", minor="country-level-1+lk-province"),
)
COLOMBO = Entity(
    id="LK-11",
    name="Colombo",
    kind=Kind(major="region", minor="country-level-2+lk-administrative-district"),
)
GND = Entity(
    id="LK-1103005",
    name="Sammanthranapura",
    kind=Kind(major="region", minor="country-level-4+lk-grama-niladhari-division"),
)

ENTITIES_BY_ID = {
    entity.id: entity for entity in (SRI_LANKA, WESTERN, COLOMBO, GND)
}

LK_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "LK",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[80.0, 6.0], [81.0, 6.0], [81.0, 7.0], [80.0, 6.0]]],
            },
        }
    ],
}

WESTERN_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "LK-1",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[79.8, 6.7], [80.2, 6.7], [80.2, 7.2], [79.8, 6.7]]],
            },
        }
    ],
}

GEOJSON_BY_ID = {
    "LK": LK_GEOJSON,
    "LK-1": WESTERN_GEOJSON,
}


def _entity_geojson(entity_id: str):
    geojson = GEOJSON_BY_ID.get(entity_id)
    if geojson is None:
        return []
    return [{"key": "geojson", "value": geojson}]


async def fake_get_entities(entity: Entity):
    if entity.id:
        match = ENTITIES_BY_ID.get(entity.id)
        return [match] if match else []
    if entity.kind.major == "region" and entity.kind.minor == "country":
        return [SRI_LANKA]
    return []


async def fake_fetch_relations(entity_id: str, relation: Relation):
    if entity_id == "LK" and relation.name == "province":
        return [
            Relation(
                name="province",
                relatedEntityId="LK-1",
                direction="OUTGOING",
            )
        ]
    return []


async def fake_get_entity_metadata(entity_id: str):
    return _entity_geojson(entity_id)


@pytest.fixture
def client():
    read_service.get_entities = AsyncMock(side_effect=fake_get_entities)
    read_service.fetch_relations = AsyncMock(side_effect=fake_fetch_relations)
    read_service.get_entity_metadata = AsyncMock(side_effect=fake_get_entity_metadata)

    with TestClient(app) as test_client:
        yield test_client


def test_hierarchy_country_navigations_are_province():
    navs = region_service.navigations_for("country")
    assert [nav.relation for nav in navs] == ["province"]
    assert navs[0].label == "Province"
    assert navs[0].minor == "country-level-1+lk-province"


def test_hierarchy_province_navigations_are_admin_and_electoral():
    navs = region_service.navigations_for("country-level-1+lk-province")
    assert [nav.relation for nav in navs] == [
        "administrative_district",
        "electoral_district",
    ]
    assert [nav.label for nav in navs] == [
        "Administrative District",
        "Electoral District",
    ]
    assert [nav.minor for nav in navs] == [
        "country-level-2+lk-administrative-district",
        "country-level-2+lk-electoral-district",
    ]


def test_hierarchy_admin_district_forks_into_dsd_lg_moh():
    navs = region_service.navigations_for(
        "country-level-2+lk-administrative-district"
    )
    assert [nav.relation for nav in navs] == [
        "divisional_secretariat_division",
        "local_government",
        "medical_officer_of_health",
    ]


def test_get_root_region(client: TestClient):
    response = client.get("/v1/regions/root")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "LK"
    assert body["name"] == "Sri Lanka"
    assert body["kind"] == {"major": "region", "minor": "country"}
    assert body["geojson"]["features"][0]["id"] == "LK"
    assert [nav["relation"] for nav in body["navigations"]] == ["province"]
    read_service.get_entities.assert_awaited_once()
    read_service.get_entity_metadata.assert_awaited_once_with("LK")


def test_get_region(client: TestClient):
    response = client.get("/v1/regions/LK-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "LK-1"
    assert body["name"] == "Western"
    assert body["geojson"]["features"][0]["id"] == "LK-1"
    assert [nav["relation"] for nav in body["navigations"]] == [
        "administrative_district",
        "electoral_district",
    ]
    assert [nav["label"] for nav in body["navigations"]] == [
        "Administrative District",
        "Electoral District",
    ]
    read_service.get_entities.assert_awaited_once()
    read_service.get_entity_metadata.assert_awaited_once_with("LK-1")


def test_get_region_not_found(client: TestClient):
    response = client.get("/v1/regions/MISSING")
    assert response.status_code == 404


def test_get_region_children_names_only(client: TestClient):
    response = client.get("/v1/regions/LK/children", params={"relation": "province"})
    assert response.status_code == 200
    body = response.json()
    assert body["relation"] == "province"
    assert body["items"] == [
        {
            "id": "LK-1",
            "name": "Western",
            "kind": {
                "major": "region",
                "minor": "country-level-1+lk-province",
            },
        }
    ]
    read_service.fetch_relations.assert_awaited_once()
    read_service.get_entity_metadata.assert_not_awaited()


def test_get_region_children_include_geojson(client: TestClient):
    response = client.get(
        "/v1/regions/LK/children",
        params={"relation": "province", "include_geojson": True},
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["hasGeometry"] is True
    assert item["geojson"]["features"][0]["id"] == "LK-1"
    read_service.get_entity_metadata.assert_awaited_once_with("LK-1")


def test_get_region_children_requires_relation(client: TestClient):
    response = client.get("/v1/regions/LK/children")
    assert response.status_code == 422


def test_leaf_region_has_empty_navigations(client: TestClient):
    response = client.get("/v1/regions/LK-1103005")
    assert response.status_code == 200
    assert response.json()["navigations"] == []
    assert response.json()["geojson"] is None


def test_cors_allows_browser_origin(client: TestClient):
    response = client.get(
        "/v1/regions/root",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_extract_geojson_from_key_value_list():
    assert extract_geojson([{"key": "geojson", "value": LK_GEOJSON}]) == LK_GEOJSON


def test_extract_geojson_from_dict_key():
    assert extract_geojson({"geojson": LK_GEOJSON}) == LK_GEOJSON


def test_extract_geojson_wraps_feature():
    feature = LK_GEOJSON["features"][0]
    wrapped = extract_geojson([{"key": "geojson", "value": feature}])
    assert wrapped == {"type": "FeatureCollection", "features": [feature]}


def test_extract_geojson_missing():
    assert extract_geojson([]) is None
    assert extract_geojson({"source": "opengin"}) is None
    assert extract_geojson(None) is None
