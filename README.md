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

Today that inserts:

1. Nine provinces (`LK-1` … `LK-9`, kind `region` / `country-level-1+lk-province`)
2. Sri Lanka (`LK`, kind `region` / `country`) with `province` edges to those ids

The seeder looks up each entity by id on the read API first. If it exists, it is updated; otherwise it is created.

### Seed data

| File | Role |
| --- | --- |
| [`data/seed/hierarchy.yaml`](data/seed/hierarchy.yaml) | Kinds and parent→child edges |
| [`data/seed/country.csv`](data/seed/country.csv) | `id,name` |
| [`data/seed/province.csv`](data/seed/province.csv) | `id,name,country_id` |

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
```

To add a level later: append a child in `hierarchy.yaml` and add a CSV under `data/seed/` (`id`, `name`, parent id column). No new Python builders.

### Check after seed

With the API (or OpenGIN read) up:

- Search `kind.major=region`, `kind.minor=country` → Sri Lanka / `LK`
- Search `kind.minor=country-level-1+lk-province` → nine provinces
- `POST /v1/entities/LK/relations` with `{ "name": "province" }` → `LK-1` … `LK-9`

## Tests

```bash
pytest
```
