from pathlib import Path

from scripts.seed_utils import load_seed_payloads

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"

PROVINCE_IDS = [
    "LK-1",
    "LK-2",
    "LK-3",
    "LK-4",
    "LK-5",
    "LK-6",
    "LK-7",
    "LK-8",
    "LK-9",
]


def test_seed_csvs_map_to_country_and_province_payloads():
    items = load_seed_payloads(SEED_DIR)
    entities = [item.entity for item in items]
    provinces = [
        e for e in entities if e.kind.minor == "country-level-1+lk-province"
    ]
    countries = [e for e in entities if e.kind.minor == "country"]

    assert [p.id for p in provinces] == PROVINCE_IDS
    for province in provinces:
        assert province.kind.major == "region"
        assert province.name.value
        assert province.relationships == []
        assert province.metadata == []
        assert province.attributes == []

    names = {p.id: p.name.value for p in provinces}
    assert names["LK-1"] == "Western"
    assert names["LK-9"] == "Sabaragamuwa"

    assert len(countries) == 1
    country = countries[0]
    assert country.id == "LK"
    assert country.name.value == "Sri Lanka"
    assert country.kind.major == "region"
    assert country.kind.minor == "country"
    assert country.metadata == []
    assert country.attributes == []

    related_ids = [rel.value.relatedEntityId for rel in country.relationships]
    assert related_ids == PROVINCE_IDS
    for rel in country.relationships:
        assert rel.key == "province"
        assert rel.value.name == "province"
