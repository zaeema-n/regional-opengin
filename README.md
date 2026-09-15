# regional-opengin

FastAPI adapter to OpenGIN, plus a YAML-driven seeder for Sri Lanka region entities.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set OpenGIN hosts in `.env`:

```
READ_BASE_URL=http://localhost:8081
INGESTION_BASE_URL=http://localhost:8080
```

OpenGIN read (query) and ingestion (write) must be running at those URLs.

## Run the API

```bash
uvicorn main:app --reload
```

- Health: `GET http://localhost:8000/health`
- Docs: `http://localhost:8000/docs`

This app forwards to OpenGIN:

| Method | Path |
| --- | --- |
| POST | `/v1/entities/search` |
| POST | `/v1/entities/{id}/relations` |
| GET | `/v1/entities/{id}/metadata` |
| POST | `/v1/entities/{id}/attributes/{name}` |
| POST | `/entities` |
| PUT | `/entities/{id}` |

## Seed regions

The seeder talks to **OpenGIN ingestion** (`INGESTION_BASE_URL`) directly. You do not need uvicorn running for seed.

From the repo root, with `.env` loaded:

```bash
python scripts/seed.py
```

Today that inserts, deepest first:

1. Grama niladhari divisions (`gnd.csv`, kind `region` / `country-level-4+lk-grama-niladhari-division`)
2. Divisional secretariat divisions (`dsd.csv`, kind `region` / `country-level-3+lk-divisional-secretariat-division`) with `grama_niladhari_division` edges
3. Local governments (`lg.csv`, kind `region` / `country-level-3+lk-local-government`)
4. Medical officers of health (`moh.csv`, kind `region` / `country-level-3+lk-medical-officer-of-health`)
5. Administrative districts (`district.csv`, kind `region` / `country-level-2+lk-administrative-district`) with `divisional_secretariat_division`, `local_government`, and `medical_officer_of_health` edges
6. Electoral polling divisions (`pd.csv`, kind `region` / `country-level-3+lk-electoral-polling-division`)
7. Electoral districts (`ed.csv`, kind `region` / `country-level-2+lk-electoral-district`) with `electoral_polling_division` edges
8. Provinces (`LK-1` … `LK-9`, kind `region` / `country-level-1+lk-province`) with `administrative_district` and `electoral_district` edges
9. Sri Lanka (`LK`, kind `region` / `country`) with `province` edges

The seeder looks up each entity by id on the read API first. If it exists, it is updated; otherwise it is created.

### Seed data

| File | Role |
| --- | --- |
| [`data/seed/hierarchy.yaml`](data/seed/hierarchy.yaml) | Kinds and parent→child edges |
| [`data/seed/country.csv`](data/seed/country.csv) | `id,name` |
| [`data/seed/province.csv`](data/seed/province.csv) | `id,name,country_id` |
| [`data/seed/district.csv`](data/seed/district.csv) | `id,name,province_id` |
| [`data/seed/dsd.csv`](data/seed/dsd.csv) | `id,name,district_id` |
| [`data/seed/gnd.csv`](data/seed/gnd.csv) | `id,name,dsd_id` |
| [`data/seed/lg.csv`](data/seed/lg.csv) | `id,name,district_id` |
| [`data/seed/moh.csv`](data/seed/moh.csv) | `id,name,district_id` |
| [`data/seed/ed.csv`](data/seed/ed.csv) | `id,name,province_id` |
| [`data/seed/pd.csv`](data/seed/pd.csv) | `id,name,ed_id` |

YAML currently:

```yaml
major: region
minor: country
file: country.csv
children:
  - minor: country-level-1+lk-province
    file: province.csv
    parent_column: country_id
    relation: province
    children:
      - minor: country-level-2+lk-administrative-district
        file: district.csv
        parent_column: province_id
        relation: administrative_district
        children:
          - minor: country-level-3+lk-divisional-secretariat-division
            file: dsd.csv
            parent_column: district_id
            relation: divisional_secretariat_division
            children:
              - minor: country-level-4+lk-grama-niladhari-division
                file: gnd.csv
                parent_column: dsd_id
                relation: grama_niladhari_division
          - minor: country-level-3+lk-local-government
            file: lg.csv
            parent_column: district_id
            relation: local_government
          - minor: country-level-3+lk-medical-officer-of-health
            file: moh.csv
            parent_column: district_id
            relation: medical_officer_of_health
      - minor: country-level-2+lk-electoral-district
        file: ed.csv
        parent_column: province_id
        relation: electoral_district
        children:
          - minor: country-level-3+lk-electoral-polling-division
            file: pd.csv
            parent_column: ed_id
            relation: electoral_polling_division
```

To add a level later: append a child in `hierarchy.yaml` and add a CSV under `data/seed/` (`id`, `name`, parent id column). No new Python builders.

### Check after seed

With the API (or OpenGIN read) up:

- Search `kind.major=region`, `kind.minor=country` → Sri Lanka / `LK`
- Search `kind.minor=country-level-1+lk-province` → nine provinces
- Search `kind.minor=country-level-2+lk-administrative-district` → 25 districts
- Search `kind.minor=country-level-3+lk-divisional-secretariat-division` → 331 DSDs
- Search `kind.minor=country-level-4+lk-grama-niladhari-division` → 14021 GNDs
- Search `kind.minor=country-level-3+lk-local-government` → 338 LGs
- Search `kind.minor=country-level-3+lk-medical-officer-of-health` → 333 MOHs
- Search `kind.minor=country-level-2+lk-electoral-district` → 22 EDs
- Search `kind.minor=country-level-3+lk-electoral-polling-division` → 182 PDs
- `POST /v1/entities/LK/relations` with `{ "name": "province" }` → `LK-1` … `LK-9`
- `POST /v1/entities/LK-1/relations` with `{ "name": "administrative_district" }` → Colombo, Gampaha, Kalutara
- `POST /v1/entities/LK-1/relations` with `{ "name": "electoral_district" }` → Colombo, Gampaha, Kalutara EDs
- `POST /v1/entities/LK-11/relations` with `{ "name": "divisional_secretariat_division" }` → DSDs in Colombo district
- `POST /v1/entities/LK-1103/relations` with `{ "name": "grama_niladhari_division" }` → GNDs in Colombo DSD

## Tests

```bash
pytest
```
