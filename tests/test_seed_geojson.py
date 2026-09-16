import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

from models import Entity, Kind
from scripts.seed import upsert_entity
from scripts.seed_utils import (
    SEED_DIR as REAL_SEED_DIR,
    collect_payloads,
    geojson_metadata,
    load_geojson_index,
    load_hierarchy,
    load_rows_for_tree,
    load_seed_payloads,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "seed_geojson"


def _fixture_items():
    root = load_hierarchy(FIXTURE_DIR / "hierarchy.yaml")
    return collect_payloads(
        root,
        load_rows_for_tree(root, FIXTURE_DIR),
        load_geojson_index(root, FIXTURE_DIR),
    )


def _entity_by_id(items, entity_id: str):
    return next(item.entity for item in items if item.entity.id == entity_id)


def test_lk_payload_wraps_one_feature_collection():
    country = _entity_by_id(_fixture_items(), "LK")
    assert len(country.metadata) == 1
    entry = country.metadata[0]
    assert entry["key"] == "geojson"
    value = entry["value"]
    assert value["type"] == "FeatureCollection"
    assert len(value["features"]) == 1
    assert value["features"][0]["id"] == "LK"


def test_unknown_id_is_skipped():
    items = _fixture_items()
    unknown = _entity_by_id(items, "ZZ")
    assert unknown.metadata == []
    index = load_geojson_index(
        load_hierarchy(FIXTURE_DIR / "hierarchy.yaml"), FIXTURE_DIR
    )
    assert "ZZ" not in index
    assert "EC-01P" not in index
    assert "LK" in index


def test_upsert_update_sends_id_and_geojson_metadata():
    feature = load_geojson_index(
        load_hierarchy(FIXTURE_DIR / "hierarchy.yaml"), FIXTURE_DIR
    )["LK"]
    entity = _entity_by_id(_fixture_items(), "LK")
    read = AsyncMock()
    read.get_entities = AsyncMock(return_value=[Entity(id="LK")])
    ingestion = AsyncMock()

    status = asyncio.run(upsert_entity(read, ingestion, entity))

    assert status == "updated"
    ingestion.update_entity.assert_awaited_once_with("LK", entity)
    ingestion.create_entity.assert_not_awaited()
    sent = ingestion.update_entity.await_args.args[1]
    dumped = sent.model_dump()
    assert dumped["id"] == "LK"
    assert dumped["metadata"] == geojson_metadata(feature)
    assert dumped["metadata"][0]["key"] == "geojson"
    assert dumped["metadata"][0]["value"]["type"] == "FeatureCollection"
    assert dumped["metadata"][0]["value"]["features"][0]["id"] == "LK"


def test_load_seed_payloads_omits_geojson():
    country = _entity_by_id(load_seed_payloads(REAL_SEED_DIR), "LK")
    assert country.kind == Kind(major="region", minor="country")
    assert country.metadata == []
