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
WESTERN_DISTRICT_IDS = ["LK-11", "LK-12", "LK-13"]
WESTERN_ED_IDS = ["EC-01", "EC-02", "EC-03"]


def _related_ids(entity, relation_name: str) -> list[str]:
    return [
        rel.value.relatedEntityId
        for rel in entity.relationships
        if rel.value.name == relation_name
    ]


def test_seed_csvs_map_to_full_region_hierarchy_payloads():
    items = load_seed_payloads(SEED_DIR)
    entities = [item.entity for item in items]
    by_minor: dict[str, list] = {}
    for entity in entities:
        by_minor.setdefault(entity.kind.minor, []).append(entity)

    gnds = by_minor["country-level-4+lk-grama-niladhari-division"]
    dsds = by_minor["country-level-3+lk-divisional-secretariat-division"]
    lgs = by_minor["country-level-3+lk-local-government"]
    mohs = by_minor["country-level-3+lk-medical-officer-of-health"]
    pds = by_minor["country-level-3+lk-electoral-polling-division"]
    districts = by_minor["country-level-2+lk-administrative-district"]
    eds = by_minor["country-level-2+lk-electoral-district"]
    provinces = by_minor["country-level-1+lk-province"]
    countries = by_minor["country"]

    assert len(gnds) == 14021
    for gnd in gnds:
        assert gnd.kind.major == "region"
        assert gnd.name.value
        assert gnd.relationships == []
    gnd_names = {g.id: g.name.value for g in gnds}
    assert gnd_names["LK-1103005"] == "Sammanthranapura"
    assert gnd_names["LK-1103010"] == "Mattakkuliya"

    assert len(dsds) == 331
    colombo_dsd = next(d for d in dsds if d.id == "LK-1103")
    assert colombo_dsd.name.value == "Colombo"
    gnd_ids_in_colombo = _related_ids(colombo_dsd, "grama_niladhari_division")
    assert gnd_ids_in_colombo[:3] == ["LK-1103005", "LK-1103010", "LK-1103015"]
    assert len(gnd_ids_in_colombo) == 35
    for rel in colombo_dsd.relationships:
        assert rel.value.name == "grama_niladhari_division"
        assert (
            rel.key
            == rel.value.id
            == f"LK-1103-grama_niladhari_division-{rel.value.relatedEntityId}"
        )

    assert len(lgs) == 338
    assert {lg.id: lg.name.value for lg in lgs}["LG-11031"] == "Colombo MC"
    for lg in lgs:
        assert lg.kind.major == "region"
        assert lg.relationships == []

    assert len(mohs) == 333
    assert {moh.id: moh.name.value for moh in mohs}["MOH-11031"] == "CMC"
    for moh in mohs:
        assert moh.kind.major == "region"
        assert moh.relationships == []

    assert len(pds) == 182
    assert {pd.id: pd.name.value for pd in pds}["EC-01A"] == "Colombo North"
    for pd in pds:
        assert pd.kind.major == "region"
        assert pd.relationships == []

    assert [d.id for d in districts][0:3] == WESTERN_DISTRICT_IDS
    assert len(districts) == 25
    colombo = next(d for d in districts if d.id == "LK-11")
    assert colombo.name.value == "Colombo"
    assert colombo.kind.major == "region"
    assert _related_ids(colombo, "divisional_secretariat_division")[:2] == [
        "LK-1103",
        "LK-1106",
    ]
    assert _related_ids(colombo, "local_government")[:3] == [
        "LG-11031",
        "LG-11061",
        "LG-11062",
    ]
    assert _related_ids(colombo, "medical_officer_of_health")[:3] == [
        "MOH-11031",
        "MOH-11060",
        "MOH-11091",
    ]
    assert len(_related_ids(colombo, "local_government")) == 13
    assert len(_related_ids(colombo, "medical_officer_of_health")) == 16
    for rel in colombo.relationships:
        assert rel.value.name in {
            "divisional_secretariat_division",
            "local_government",
            "medical_officer_of_health",
        }
        assert (
            rel.key
            == rel.value.id
            == f"LK-11-{rel.value.name}-{rel.value.relatedEntityId}"
        )

    assert len(eds) == 22
    colombo_ed = next(ed for ed in eds if ed.id == "EC-01")
    assert colombo_ed.name.value == "Colombo"
    assert colombo_ed.kind.major == "region"
    pd_ids_in_colombo = _related_ids(colombo_ed, "electoral_polling_division")
    assert pd_ids_in_colombo[:3] == ["EC-01A", "EC-01B", "EC-01C"]
    assert len(pd_ids_in_colombo) == 16
    for rel in colombo_ed.relationships:
        assert rel.value.name == "electoral_polling_division"
        assert (
            rel.key
            == rel.value.id
            == f"EC-01-electoral_polling_division-{rel.value.relatedEntityId}"
        )

    assert [p.id for p in provinces] == PROVINCE_IDS
    western = next(p for p in provinces if p.id == "LK-1")
    assert western.name.value == "Western"
    assert _related_ids(western, "administrative_district") == WESTERN_DISTRICT_IDS
    assert _related_ids(western, "electoral_district") == WESTERN_ED_IDS
    for rel in western.relationships:
        assert rel.value.name in {"administrative_district", "electoral_district"}
        assert (
            rel.key
            == rel.value.id
            == f"LK-1-{rel.value.name}-{rel.value.relatedEntityId}"
        )

    assert len(countries) == 1
    country = countries[0]
    assert country.id == "LK"
    assert country.name.value == "Sri Lanka"
    related_ids = [rel.value.relatedEntityId for rel in country.relationships]
    assert related_ids == PROVINCE_IDS
    for rel, province_id in zip(country.relationships, PROVINCE_IDS, strict=True):
        relation_id = f"LK-province-{province_id}"
        assert rel.key == relation_id
        assert rel.value.id == relation_id
        assert rel.value.name == "province"
        assert rel.value.startTime == "1970-01-01T00:00:00Z"
        assert rel.value.endTime == ""
