import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from exception import NotFoundError
from models import Entity, EntityCreate
from scripts.seed_utils import (
    HIERARCHY_FILE,
    SEED_DIR,
    collect_payloads,
    load_geojson_index,
    load_hierarchy,
    load_rows_for_tree,
)
from services import IngestionService, ReadService
from utils import http_client, logger


async def _entity_exists(read: ReadService, entity_id: str) -> bool:
    try:
        matches = await read.get_entities(Entity(id=entity_id))
    except NotFoundError:
        return False
    return any(match.id == entity_id for match in matches)


async def upsert_entity(
    read: ReadService, ingestion: IngestionService, entity: EntityCreate
) -> str:
    if await _entity_exists(read, entity.id):
        await ingestion.update_entity(entity.id, entity)
        return "updated"
    await ingestion.create_entity(entity)
    return "created"


async def seed() -> None:
    root = load_hierarchy(SEED_DIR / HIERARCHY_FILE)
    items = collect_payloads(
        root,
        load_rows_for_tree(root, SEED_DIR),
        load_geojson_index(root, SEED_DIR),
    )
    missing_geojson = [item.entity.id for item in items if not item.entity.metadata]
    if missing_geojson:
        logger.info(
            f"Skipping geojson for {len(missing_geojson)} entities with no geometry: "
            f"{', '.join(missing_geojson)}"
        )
    read = ReadService()
    ingestion = IngestionService()

    await http_client.start()
    try:
        for item in items:
            entity = item.entity
            status = await upsert_entity(read, ingestion, entity)
            geo_status = "geojson" if entity.metadata else "no geojson"
            logger.info(
                f"{entity.kind.minor} {entity.id} ({entity.name.value}): "
                f"{status} / {geo_status}"
            )
    finally:
        await http_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
