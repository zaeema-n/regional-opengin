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
from scripts.seed_utils import load_seed_payloads
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
    items = load_seed_payloads()
    read = ReadService()
    ingestion = IngestionService()

    await http_client.start()
    try:
        for item in items:
            entity = item.entity
            status = await upsert_entity(read, ingestion, entity)
            logger.info(
                f"{entity.kind.minor} {entity.id} ({entity.name.value}): {status}"
            )
    finally:
        await http_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
